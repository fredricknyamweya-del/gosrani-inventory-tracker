"""Shared Flask extension instances."""

from flask_caching import Cache
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base for SQLAlchemy 2.0 typed models."""


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
jwt = JWTManager()
cache = Cache()
