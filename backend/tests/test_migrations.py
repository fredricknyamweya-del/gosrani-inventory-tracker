"""Round-trip checks for additive unit schema migrations."""

from datetime import date
from decimal import Decimal

from flask_migrate import downgrade, upgrade
from sqlalchemy import select

from app.extensions import db
from app.models import (
    Category,
    EnteredUnit,
    InventoryRecord,
    Item,
    Location,
    Specification,
    User,
    v_stock,
)


def test_entry_unit_migration_round_trip_preserves_stock(app):
    with app.app_context():
        location = Location(code="ELD", name="Eldoret Godown")
        user = User(name="Staff", email="staff@example.com", password_hash="hash")
        category = Category(name="Bedding")
        db.session.add_all([location, user, category])
        db.session.flush()
        bale_item = Item(
            category_id=category.id,
            name="Pillow",
            entry_unit="BALE",
        )
        piece_item = Item(category_id=category.id, name="Pillow case")
        db.session.add_all([bale_item, piece_item])
        db.session.flush()
        bale_specification = Specification(
            item_id=bale_item.id,
            label="Standard",
            pack_size=20,
        )
        piece_specification = Specification(
            item_id=piece_item.id,
            label="Standard",
        )
        db.session.add_all([bale_specification, piece_specification])
        db.session.flush()
        record = InventoryRecord(
            location_id=location.id,
            record_date=date(2026, 11, 13),
            specification_id=bale_specification.id,
            qty_in=Decimal(200),
            qty_in_normalized=Decimal(200),
            entered_unit=EnteredUnit.BALE,
            pieces_per_unit=20,
            created_by=user.id,
        )
        db.session.add(record)
        db.session.commit()
        item_ids = (bale_item.id, piece_item.id)
        record_id = record.id
        location_id = location.id
        specification_id = bale_specification.id
        piece_specification_id = piece_specification.id
        category_id = category.id
        user_id = user.id

        db.session.remove()
        downgrade(revision="f8b2c4d6e0a1")
        upgrade()

        db.session.expire_all()
        migrated_bale = db.session.get(Item, item_ids[0])
        migrated_piece = db.session.get(Item, item_ids[1])
        migrated_record = db.session.get(InventoryRecord, record_id)
        stock = db.session.execute(
            select(v_stock).where(
                v_stock.c.location_id == location_id,
                v_stock.c.specification_id == specification_id,
            )
        ).one()

        assert migrated_bale.entry_unit.value == "BALE"
        assert migrated_piece.entry_unit.value == "PCS"
        assert migrated_record.qty_in == Decimal(200)
        assert migrated_record.pieces_per_bale is None
        assert stock.stock == 200
        assert stock.stock_pieces == 200
        assert stock.stock_bales == 10

        db.session.delete(migrated_record)
        db.session.delete(db.session.get(Specification, specification_id))
        db.session.delete(db.session.get(Specification, piece_specification_id))
        db.session.delete(migrated_bale)
        db.session.delete(migrated_piece)
        db.session.delete(db.session.get(Category, category_id))
        db.session.delete(db.session.get(Location, location_id))
        db.session.delete(db.session.get(User, user_id))
        db.session.commit()
