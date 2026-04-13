import importlib
import sys
import types

import pytest
from fastapi.testclient import TestClient


def _install_handler_stubs(monkeypatch):
    module_exports = {
        "bot.handlers.start": ["start_handler", "help_handler"],
        "bot.handlers.link": ["link_handler"],
        "bot.handlers.search": [
            "search_handler",
            "filter_handler",
            "tags_handler",
            "today_handler",
            "week_handler",
        ],
        "bot.handlers.manage": [
            "note_handler",
            "delete_handler",
            "edit_handler",
            "view_handler",
            "sheet_handler",
            "addcategory_handler",
        ],
        "bot.handlers.callback": ["callback_handler"],
        "bot.handlers.lang": ["lang_handler"],
        "bot.handlers.export": ["export_handler"],
        "bot.handlers.topics": ["topics_handler"],
        "bot.handlers.stats": ["stats_handler"],
    }
    for module_name, exports in module_exports.items():
        module = types.ModuleType(module_name)
        for export in exports:
            setattr(module, export, object())
        monkeypatch.setitem(sys.modules, module_name, module)


def _load_index_module(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy-token")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "expected-secret")
    import bot.config as bot_config

    monkeypatch.setattr(bot_config, "TELEGRAM_BOT_TOKEN", "dummy-token")
    monkeypatch.setattr(bot_config, "TELEGRAM_WEBHOOK_SECRET", "expected-secret")

    import telegram.ext as tg_ext

    class _DummyRuntimeApplication:
        def add_handler(self, *_args, **_kwargs):
            return None

        async def initialize(self):
            return None

        async def process_update(self, _update):
            return None

        @property
        def bot(self):
            return object()

    class _DummyBuilder:
        def token(self, *_args, **_kwargs):
            return self

        def build(self):
            return _DummyRuntimeApplication()

    class _DummyApplication:
        @staticmethod
        def builder():
            return _DummyBuilder()

    monkeypatch.setattr(tg_ext, "Application", _DummyApplication)
    _install_handler_stubs(monkeypatch)

    monkeypatch.delitem(sys.modules, "api.index", raising=False)
    return importlib.import_module("api.index")


@pytest.fixture
def fresh_index_module(monkeypatch):
    previous_module = sys.modules.get("api.index")
    module = _load_index_module(monkeypatch)
    try:
        yield module
    finally:
        sys.modules.pop("api.index", None)
        if previous_module is not None:
            sys.modules["api.index"] = previous_module


def test_startup_health_still_available(fresh_index_module):
    index_module = fresh_index_module

    with TestClient(index_module.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_webhook_secret_guard_still_blocks_invalid_secret(fresh_index_module):
    index_module = fresh_index_module

    with TestClient(index_module.app) as client:
        response = client.post(
            "/webhook",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "unauthorized"}
