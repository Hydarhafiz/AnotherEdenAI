"""RED phase stub — fails with ImportError until src/web/app.py is created."""
import pytest


def test_app_importable():
    """RED: src.web.app must be importable after implementation."""
    from src.web.app import app  # noqa: F401
    assert app is not None


def test_dependencies_importable():
    """RED: src.web.dependencies must export get_driver and verify_admin_key."""
    from src.web.dependencies import get_driver, verify_admin_key  # noqa: F401
    assert callable(get_driver)
    assert callable(verify_admin_key)


def test_api_router_importable():
    """RED: src.web.routes.api must export router."""
    from src.web.routes.api import router  # noqa: F401
    assert router is not None


def test_admin_router_importable():
    """RED: src.web.routes.admin must export router."""
    from src.web.routes.admin import router  # noqa: F401
    assert router is not None
