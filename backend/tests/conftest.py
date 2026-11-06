"""Shared test fixtures."""

import sys
from importlib import import_module
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

create_app = import_module("app").create_app
extensions = import_module("app.extensions")
cache = extensions.cache
db = extensions.db


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()
        cache.clear()


@pytest.fixture()
def client(app):
    return app.test_client()
