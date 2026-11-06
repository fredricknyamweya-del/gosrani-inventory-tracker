"""Shared test fixtures."""

import sqlite3
import sys
from importlib import import_module
from pathlib import Path

import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import event

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

create_app = import_module("app").create_app
extensions = import_module("app.extensions")
cache = extensions.cache
db = extensions.db


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        engine = db.engine
        if engine.dialect.name == "sqlite":

            @event.listens_for(engine, "connect")
            def enable_sqlite_foreign_keys(
                connection: sqlite3.Connection, _record: object
            ) -> None:
                cursor = connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        upgrade()
        yield application
        db.session.remove()
        downgrade(revision="base")
        cache.clear()


@pytest.fixture()
def client(app):
    return app.test_client()
