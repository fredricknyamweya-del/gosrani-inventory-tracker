"""Location lookup endpoints."""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import select

from app.api_utils import current_user, user_location_ids
from app.extensions import db
from app.models import Location, UserRole

locations_bp = Blueprint("locations", __name__, url_prefix="/api/locations")


@locations_bp.get("")
@jwt_required()
def list_locations():
    """List active locations available to the signed-in user."""
    user = current_user()
    query = select(Location).where(Location.active.is_(True))
    if user.role != UserRole.ADMIN:
        query = query.where(Location.id.in_(user_location_ids(user.id)))
    locations = db.session.scalars(query.order_by(Location.name, Location.id)).all()
    return jsonify(
        {
            "data": [
                {"id": location.id, "code": location.code, "name": location.name}
                for location in locations
            ]
        }
    )
