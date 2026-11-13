"""Tests for product-specific bale inventory and catalogue summaries."""

from datetime import date

from flask_jwt_extended import create_access_token
from sqlalchemy import select

from app.extensions import db
from app.models import (
    AuditAction,
    AuditEntity,
    AuditLog,
    Category,
    InventoryRecord,
    InventoryUnit,
    Item,
    ItemRequest,
    Location,
    RequestStatus,
    Specification,
    User,
    UserLocation,
    UserRole,
)


def create_case(*, inventory_unit=InventoryUnit.BALE, pieces_per_bale=5):
    admin = User(
        name="Inventory Admin",
        email="admin@example.com",
        password_hash="not-a-real-password-hash",
        role=UserRole.ADMIN,
    )
    user = User(
        name="Inventory User",
        email="user@example.com",
        password_hash="not-a-real-password-hash",
        role=UserRole.USER,
    )
    location = Location(code="ELD", name="Eldoret Godown")
    category = Category(name="Bedding")
    db.session.add_all([admin, user, location, category])
    db.session.flush()
    item = Item(
        category_id=category.id,
        name="Configured Duvet",
        inventory_unit=inventory_unit,
        pieces_per_bale=pieces_per_bale,
    )
    ordinary_item = Item(
        category_id=category.id,
        name="Pillow Kiss Case",
        inventory_unit=InventoryUnit.PCS,
    )
    db.session.add_all([item, ordinary_item])
    db.session.flush()
    specification = Specification(
        item_id=item.id,
        label="4x6",
        pack_size=pieces_per_bale if inventory_unit == InventoryUnit.BALE else None,
    )
    ordinary_specification = Specification(
        item_id=ordinary_item.id, label="Standard"
    )
    db.session.add_all([specification, ordinary_specification])
    db.session.add_all(
        [
            UserLocation(user_id=admin.id, location_id=location.id),
            UserLocation(user_id=user.id, location_id=location.id),
        ]
    )
    db.session.commit()
    return admin, user, location, category, item, specification, ordinary_item, ordinary_specification


def authorization(user):
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def transaction_payload(item_name, size, **overrides):
    return {
        "date": date.today().isoformat(),
        "category": "Bedding",
        "item": item_name,
        "size": size,
        "quantityIn": 1,
        "handledBy": "Stock handler",
        **overrides,
    }


def test_bale_transactions_normalize_and_keep_the_original_unit(client):
    admin, _, _, _, _, specification, _, _ = create_case()

    received = client.post(
        "/api/inventory",
        json=transaction_payload("Configured Duvet", "4x6", quantityIn=5),
        headers=authorization(admin),
    )

    assert received.status_code == 201
    record = received.json["data"][0]
    assert record["quantityIn"] == 5
    assert record["enteredUnit"] == "BALE"
    assert record["piecesPerUnit"] == 5
    assert record["normalizedQuantityIn"] == 25

    issued = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Configured Duvet",
            "4x6",
            quantityIn=None,
            quantityOut=2,
            enteredUnit="BALE",
        ),
        headers=authorization(admin),
    )
    assert issued.status_code == 201
    assert issued.json["data"][0]["normalizedQuantityOut"] == 10

    stock = client.get(
        f"/api/inventory/{record['id']}/stock",
        headers=authorization(admin),
    )
    assert stock.status_code == 200
    assert stock.json["data"]["unit"] == "PCS"
    assert stock.json["data"]["quantity"] == 15
    assert stock.json["data"]["equivalentPieces"] == 15
    assert stock.json["data"]["display"] == "3 bales"
    assert stock.json["data"]["secondaryDisplay"] == "(15 pcs)"

    persisted = db.session.get(Specification, specification.id)
    assert persisted is not None


def test_bale_and_piece_entries_store_base_units_and_share_stock_display(client):
    admin, _, _, _, _, specification, _, _ = create_case()

    bale_entry = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Configured Duvet",
            "4x6",
            quantityIn=2,
            enteredUnit="BALE",
        ),
        headers=authorization(admin),
    )
    piece_entry = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Configured Duvet",
            "4x6",
            quantityIn=5,
            enteredUnit="PCS",
        ),
        headers=authorization(admin),
    )

    assert bale_entry.status_code == 201
    bale_record = db.session.get(InventoryRecord, bale_entry.json["data"][0]["id"])
    assert bale_record.qty_in == 10
    assert bale_record.qty_in_normalized == 10
    assert bale_entry.json["data"][0]["quantityIn"] == 2
    assert bale_entry.json["data"][0]["quantityInDisplay"] == "2 bales"
    assert (
        bale_entry.json["data"][0]["quantityInSecondaryDisplay"] == "(10 pcs)"
    )
    assert piece_entry.status_code == 201
    assert piece_entry.json["data"][0]["quantityInDisplay"] == "1 bale"
    assert (
        piece_entry.json["data"][0]["quantityInSecondaryDisplay"] == "(5 pcs)"
    )

    stock = client.get(
        f"/api/inventory/{bale_entry.json['data'][0]['id']}/stock",
        headers=authorization(admin),
    )
    assert stock.json["data"]["quantity"] == 15
    assert stock.json["data"]["display"] == "3 bales"
    assert stock.json["data"]["secondaryDisplay"] == "(15 pcs)"

    second_size = Specification(
        item_id=specification.item_id,
        label="5x7",
        pack_size=10,
    )
    db.session.add(second_size)
    db.session.commit()
    second_size_entry = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Configured Duvet",
            "5x7",
            quantityIn=100,
            enteredUnit="PCS",
        ),
        headers=authorization(admin),
    )
    assert second_size_entry.status_code == 201

    summary = client.get(
        "/api/catalog/summary",
        headers=authorization(admin),
    )
    size_rows = [
        row
        for row in summary.json["data"]["stockBySpecification"]
        if row["itemName"] == "Configured Duvet"
    ]
    assert {row["size"]: row["remainingStock"] for row in size_rows} == {
        "4x6": 15,
        "5x7": 100,
    }


def test_editing_entered_unit_reconverts_to_base_once(client):
    admin, _, _, _, _, _, _, _ = create_case()
    received = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Configured Duvet",
            "4x6",
            quantityIn=2,
            enteredUnit="BALE",
        ),
        headers=authorization(admin),
    )
    record_id = received.json["data"][0]["id"]

    updated = client.patch(
        f"/api/inventory/{record_id}",
        json={"enteredUnit": "PCS", "quantityIn": 7},
        headers=authorization(admin),
    )

    assert updated.status_code == 200
    assert updated.json["data"]["enteredUnit"] == "PCS"
    assert updated.json["data"]["quantityIn"] == 7
    assert updated.json["data"]["quantityInDisplay"] == "1 bale + 2 pcs"
    assert updated.json["data"]["quantityInSecondaryDisplay"] == "(7 pcs)"
    record = db.session.get(InventoryRecord, record_id)
    assert record.qty_in == 7
    assert record.qty_in_normalized == 7
    assert record.pieces_per_unit == 1
    stock = client.get(
        f"/api/inventory/{record_id}/stock",
        headers=authorization(admin),
    )
    assert stock.json["data"]["quantity"] == 7


def test_bale_entry_without_specification_pack_size_returns_422(client):
    admin, _, _, _, _, _, _, _ = create_case(
        inventory_unit=InventoryUnit.PCS,
        pieces_per_bale=None,
    )

    response = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Configured Duvet",
            "4x6",
            quantityIn=1,
            enteredUnit="BALE",
        ),
        headers=authorization(admin),
    )

    assert response.status_code == 422
    assert "no pack size" in response.json["errors"][0]["message"]


def test_validate_and_stock_endpoint_display_415_bales_as_base_pieces(client):
    admin, _, _, _, _, _, _, _ = create_case(pieces_per_bale=20)
    payload = transaction_payload(
        "Configured Duvet",
        "4x6",
        quantityIn=415,
        enteredUnit="BALE",
    )

    review = client.post(
        "/api/inventory/validate",
        json=payload,
        headers=authorization(admin),
    )

    assert review.status_code == 200
    reviewed_row = review.json["data"]["rows"][0]
    assert reviewed_row["quantityInDisplay"] == "415 bales"
    assert reviewed_row["quantityInSecondaryDisplay"] == "(8,300 pcs)"

    received = client.post(
        "/api/inventory",
        json=payload,
        headers=authorization(admin),
    )
    assert received.status_code == 201
    record = db.session.get(InventoryRecord, received.json["data"][0]["id"])
    assert record.qty_in == 8300
    assert received.json["data"][0]["quantityInDisplay"] == "415 bales"
    stock = client.get(
        f"/api/inventory/{received.json['data'][0]['id']}/stock",
        headers=authorization(admin),
    )
    assert stock.json["data"]["display"] == "415 bales"
    assert stock.json["data"]["secondaryDisplay"] == "(8,300 pcs)"


def test_bale_and_piece_units_are_allowed_and_stock_out_cannot_exceed_balance(client):
    admin, _, _, _, _, _, _, _ = create_case()
    received = client.post(
        "/api/inventory",
        json=transaction_payload("Configured Duvet", "4x6", quantityIn=1),
        headers=authorization(admin),
    )
    assert received.status_code == 201

    partial_bale = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Configured Duvet",
            "4x6",
            quantityIn=3,
            enteredUnit="PCS",
        ),
        headers=authorization(admin),
    )
    assert partial_bale.status_code == 201
    assert partial_bale.json["data"][0]["piecesPerUnit"] == 1
    assert partial_bale.json["data"][0]["normalizedQuantityIn"] == 3

    summary = client.get(
        "/api/catalog/summary",
        headers=authorization(admin),
    )
    stock = next(
        row
        for row in summary.json["data"]["stockBySpecification"]
        if row["itemName"] == "Configured Duvet"
    )
    assert stock["remainingStock"] == 8
    assert stock["display"] == "1 bale + 3 pcs"
    assert stock["secondaryDisplay"] == "(8 pcs)"
    assert stock["equivalentPieces"] == 8

    wrong_unit = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Configured Duvet",
            "4x6",
            quantityIn=None,
            quantityOut=1,
            enteredUnit="KG",
        ),
        headers=authorization(admin),
    )
    assert wrong_unit.status_code == 422
    assert "BALE or PCS" in wrong_unit.json["errors"][0]["message"]

    excess = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Configured Duvet",
            "4x6",
            quantityIn=None,
            quantityOut=2,
            enteredUnit="BALE",
        ),
        headers=authorization(admin),
    )
    assert excess.status_code == 422
    assert "available stock" in excess.json["errors"][0]["message"]


def test_kilogram_quantities_keep_fractional_precision_in_inventory_summary(client):
    admin, _, _, category, _, _, _, _ = create_case(
        inventory_unit=InventoryUnit.PCS,
        pieces_per_bale=None,
    )
    item = Item(
        category_id=category.id,
        name="Cotton",
        unit="KG",
        inventory_unit=InventoryUnit.KG,
    )
    db.session.add(item)
    db.session.flush()
    db.session.add(Specification(item_id=item.id, label="Bulk"))
    db.session.commit()

    received = client.post(
        "/api/inventory",
        json=transaction_payload("Cotton", "Bulk", quantityIn=1.125),
        headers=authorization(admin),
    )
    assert received.status_code == 201
    assert received.json["data"][0]["enteredUnit"] == "KG"
    assert received.json["data"][0]["normalizedQuantityIn"] == 1.125

    issued = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Cotton",
            "Bulk",
            quantityIn=None,
            quantityOut=0.025,
        ),
        headers=authorization(admin),
    )
    assert issued.status_code == 201

    summary = client.get(
        "/api/catalog/summary",
        headers=authorization(admin),
    )
    assert summary.status_code == 200
    product = next(
        row
        for row in summary.json["data"]["products"]
        if row["productName"] == "Cotton"
    )
    specification = next(
        row
        for row in summary.json["data"]["stockBySpecification"]
        if row["itemName"] == "Cotton"
    )
    assert "totalStockIn" not in product
    assert specification["inventoryUnit"] == "KG"
    assert specification["remainingStock"] == 1.1
    assert specification["totalStockIn"] == 1.125
    assert specification["totalStockOut"] == 0.025
    assert specification["display"] == "1.1 kg"
    assert specification["equivalentPieces"] is None

    invalid_precision = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Cotton",
            "Bulk",
            quantityIn=0.0001,
        ),
        headers=authorization(admin),
    )
    assert invalid_precision.status_code == 422


def test_catalogue_summary_includes_products_without_entries_and_converts_bales(client):
    admin, user, _, _, _, _, ordinary_item, _ = create_case()
    response = client.post(
        "/api/inventory",
        json=transaction_payload("Configured Duvet", "4x6", quantityIn=3),
        headers=authorization(admin),
    )
    assert response.status_code == 201
    piece_response = client.post(
        "/api/inventory",
        json=transaction_payload("Pillow Kiss Case", "Standard", quantityIn=2),
        headers=authorization(admin),
    )
    assert piece_response.status_code == 201
    assert piece_response.json["data"][0]["enteredUnit"] == "PCS"
    assert piece_response.json["data"][0]["normalizedQuantityIn"] == 2

    summary = client.get(
        "/api/catalog/summary",
        headers=authorization(user),
    )

    assert summary.status_code == 200
    products = {row["productName"]: row for row in summary.json["data"]["products"]}
    assert "totalStockIn" not in products["Configured Duvet"]
    assert products["Configured Duvet"]["totalEntries"] == 1
    assert "remainingStock" not in products["Pillow Kiss Case"]
    assert products["Pillow Kiss Case"]["inventoryUnit"] == "PCS"
    assert summary.json["data"]["totals"]["registeredProducts"] == 2
    assert ordinary_item.inventory_unit == InventoryUnit.PCS


def test_admin_must_configure_pillow_conversion_and_users_cannot_edit_it(client):
    admin, user, _, category, _, _, _, _ = create_case(
        inventory_unit=InventoryUnit.PCS,
        pieces_per_bale=None,
    )
    pillow = Item(
        category_id=category.id,
        name="Pillow",
        inventory_unit=InventoryUnit.PCS,
    )
    db.session.add(pillow)
    db.session.flush()
    pillow_specification = Specification(item_id=pillow.id, label="Standard")
    db.session.add(pillow_specification)
    db.session.commit()

    unconfigured_bale_transaction = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Pillow",
            "Standard",
            quantityIn=1,
            enteredUnit="BALE",
        ),
        headers=authorization(user),
    )
    assert unconfigured_bale_transaction.status_code == 422

    invalid_update = client.patch(
        f"/api/catalog/items/{pillow.id}",
        json={"inventoryUnit": "BALE"},
        headers=authorization(admin),
    )
    assert invalid_update.status_code == 422

    forbidden_update = client.patch(
        f"/api/catalog/items/{pillow.id}",
        json={"inventoryUnit": "BALE", "piecesPerBale": 10},
        headers=authorization(user),
    )
    assert forbidden_update.status_code == 403

    configured = client.patch(
        f"/api/catalog/items/{pillow.id}",
        json={"inventoryUnit": "BALE", "piecesPerBale": 10},
        headers=authorization(admin),
    )
    assert configured.status_code == 200
    assert configured.json["data"]["inventoryUnit"] == "BALE"
    assert configured.json["data"]["piecesPerBale"] == 10

    still_unconfigured = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Pillow",
            "Standard",
            quantityIn=1,
            enteredUnit="BALE",
        ),
        headers=authorization(user),
    )
    assert still_unconfigured.status_code == 422
    assert "no pack size" in still_unconfigured.json["errors"][0]["message"]

    baled_specification = Specification(
        item_id=pillow.id,
        label="Baled",
        pack_size=10,
    )
    db.session.add(baled_specification)
    db.session.commit()
    transaction = client.post(
        "/api/inventory",
        json=transaction_payload("Pillow", "Baled", quantityIn=2),
        headers=authorization(user),
    )
    assert transaction.status_code == 201
    assert transaction.json["data"][0]["enteredUnit"] == "BALE"
    assert transaction.json["data"][0]["normalizedQuantityIn"] == 20


def test_conversion_changes_do_not_rewrite_historical_transactions(client):
    admin, _, _, _, item, _, _, _ = create_case()
    received = client.post(
        "/api/inventory",
        json=transaction_payload("Configured Duvet", "4x6", quantityIn=2),
        headers=authorization(admin),
    )
    assert received.status_code == 201
    record_id = received.json["data"][0]["id"]

    updated = client.patch(
        f"/api/catalog/items/{item.id}",
        json={"inventoryUnit": "BALE", "piecesPerBale": 10},
        headers=authorization(admin),
    )
    assert updated.status_code == 200

    record = client.get(
        f"/api/inventory/{record_id}",
        headers=authorization(admin),
    )
    assert record.status_code == 200
    assert record.json["data"]["quantityIn"] == 2
    assert record.json["data"]["enteredUnit"] == "BALE"
    assert record.json["data"]["piecesPerUnit"] == 5
    assert record.json["data"]["normalizedQuantityIn"] == 10

    summary = client.get(
        "/api/catalog/summary",
        headers=authorization(admin),
    )
    configured = next(
        row
        for row in summary.json["data"]["products"]
        if row["productName"] == item.name
    )
    assert configured["totalEntries"] == 1
    size_stock = next(
        row
        for row in summary.json["data"]["stockBySpecification"]
        if row["itemName"] == item.name
    )
    assert size_stock["remainingStock"] == 10
    assert size_stock["display"] == "2 bales"


def test_catalog_item_can_be_permanently_deleted_when_unreferenced(client):
    admin, _, _, _, _, specification, _, _ = create_case()

    response = client.delete(
        f"/api/catalog/items/{specification.item_id}",
        headers=authorization(admin),
    )

    assert response.status_code == 200
    assert response.json["data"]["id"] == specification.item_id
    assert db.session.get(Item, specification.item_id) is None
    assert db.session.get(Specification, specification.id) is None
    audit_entry = db.session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == AuditEntity.ITEM,
            AuditLog.entity_id == specification.item_id,
            AuditLog.action == AuditAction.DELETE,
        )
    )
    assert audit_entry is not None
    assert audit_entry.before["name"] == "Configured Duvet"


def test_catalog_item_deletion_requires_admin_and_preserves_inventory_history(client):
    admin, user, _, _, item, specification, _, _ = create_case()

    forbidden = client.delete(
        f"/api/catalog/items/{item.id}",
        headers=authorization(user),
    )
    assert forbidden.status_code == 403

    received = client.post(
        "/api/inventory",
        json=transaction_payload(item.name, specification.label, quantityIn=1),
        headers=authorization(user),
    )
    assert received.status_code == 201

    response = client.delete(
        f"/api/catalog/items/{item.id}",
        headers=authorization(admin),
    )

    assert response.status_code == 409
    assert response.json["code"] == "item_has_inventory"
    assert db.session.get(Item, item.id) is not None
    assert db.session.get(Specification, specification.id) is not None


def test_catalog_item_deletion_preserves_linked_requests(client):
    admin, user, _, category, item, _, _, _ = create_case()
    request = ItemRequest(
        requested_by=user.id,
        category_id=category.id,
        item_id=item.id,
        item_name=item.name,
        specification="Requested size",
        status=RequestStatus.PENDING,
    )
    db.session.add(request)
    db.session.commit()

    response = client.delete(
        f"/api/catalog/items/{item.id}",
        headers=authorization(admin),
    )

    assert response.status_code == 409
    assert response.json["code"] == "item_has_requests"
    assert db.session.get(Item, item.id) is not None
    assert db.session.get(ItemRequest, request.id) is not None


def test_switching_product_to_pieces_preserves_stock_and_defaults_new_entries(client):
    admin, _, _, _, item, _, _, _ = create_case()
    received = client.post(
        "/api/inventory",
        json=transaction_payload("Configured Duvet", "4x6", quantityIn=1),
        headers=authorization(admin),
    )
    assert received.status_code == 201
    historical_record = received.json["data"][0]

    updated = client.patch(
        f"/api/catalog/items/{item.id}",
        json={"inventoryUnit": "PCS"},
        headers=authorization(admin),
    )
    assert updated.status_code == 200
    assert updated.json["data"]["inventoryUnit"] == "PCS"
    assert updated.json["data"]["piecesPerBale"] is None

    stock = client.get(
        f"/api/inventory/{historical_record['id']}/stock",
        headers=authorization(admin),
    )
    assert stock.status_code == 200
    assert stock.json["data"]["unit"] == "PCS"
    assert stock.json["data"]["quantity"] == 5
    assert stock.json["data"]["display"] == "1 bale"
    assert stock.json["data"]["secondaryDisplay"] == "(5 pcs)"

    new_received = client.post(
        "/api/inventory",
        json=transaction_payload("Configured Duvet", "4x6", quantityIn=2),
        headers=authorization(admin),
    )
    assert new_received.status_code == 201
    assert new_received.json["data"][0]["enteredUnit"] == "PCS"
    assert new_received.json["data"][0]["normalizedQuantityIn"] == 2


def test_catalog_create_requires_positive_whole_bale_rate(client):
    admin, _, _, category, _, _, _, _ = create_case()
    request_body = {
        "categoryId": str(category.id),
        "name": "New bale product",
        "specifications": ["Standard"],
        "inventoryUnit": "BALE",
        "piecesPerBale": 0,
    }

    rejected = client.post(
        "/api/catalog/items",
        json=request_body,
        headers=authorization(admin),
    )
    assert rejected.status_code == 422

    request_body["piecesPerBale"] = 4
    created = client.post(
        "/api/catalog/items",
        json=request_body,
        headers=authorization(admin),
    )
    assert created.status_code == 201
    assert created.json["data"]["inventoryUnit"] == "BALE"
    assert created.json["data"]["piecesPerBale"] == 4


def test_catalogue_summary_is_location_scoped(client):
    admin, user, _, _, item, specification, _, _ = create_case()
    unassigned_location = Location(code="NAK", name="Nakuru Godown")
    db.session.add(unassigned_location)
    db.session.flush()
    db.session.add(
        UserLocation(user_id=admin.id, location_id=unassigned_location.id)
    )
    from app.models import InventoryRecord, RecordStatus

    db.session.add(
        InventoryRecord(
            location_id=unassigned_location.id,
            record_date=date.today(),
            specification_id=specification.id,
            qty_in=2,
            qty_out=None,
            entered_unit="BALE",
            pieces_per_unit=5,
            qty_in_normalized=10,
            qty_out_normalized=None,
            handled_by="Admin",
            status=RecordStatus.SAVED,
            created_by=admin.id,
        )
    )
    db.session.commit()

    response = client.get(
        "/api/catalog/summary",
        headers=authorization(user),
    )

    assert response.status_code == 200
    configured = next(
        row
        for row in response.json["data"]["products"]
        if row["productName"] == item.name
    )
    assert configured["totalEntries"] == 0


def test_catalogue_summary_reports_size_level_stock_in_inventory_units(client):
    admin, _, location, _, item, specification, _, _ = create_case()
    second_specification = Specification(
        item_id=item.id, label="5x7", pack_size=5
    )
    db.session.add(second_specification)
    db.session.commit()

    received = client.post(
        "/api/inventory",
        json=transaction_payload("Configured Duvet", "4x6", quantityIn=3),
        headers=authorization(admin),
    )
    assert received.status_code == 201

    response = client.get(
        "/api/catalog/summary",
        headers=authorization(admin),
    )

    assert response.status_code == 200
    sizes = {
        row["size"]: row
        for row in response.json["data"]["stockBySpecification"]
        if row["itemName"] == item.name
    }
    assert sizes["4x6"] == {
        "id": str(specification.id),
        "itemName": "Configured Duvet",
        "category": "Bedding",
        "size": "4x6",
        "unit": "PCS",
        "inventoryUnit": "BALE",
        "packSize": 5,
        "locationId": str(location.id),
        "locationName": "Eldoret Godown",
        "totalStockIn": 15,
        "totalStockInDisplay": "3 bales",
        "totalStockInSecondaryDisplay": "(15 pcs)",
        "totalStockOut": 0,
        "totalStockOutDisplay": "0",
        "totalStockOutSecondaryDisplay": None,
        "remainingStock": 15,
        "display": "3 bales",
        "secondaryDisplay": "(15 pcs)",
        "equivalentPieces": 15,
    }
    assert sizes["5x7"]["remainingStock"] == 0
