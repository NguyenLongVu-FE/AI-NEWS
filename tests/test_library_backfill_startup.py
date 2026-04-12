import importlib
import logging
import sys
import types

from fastapi.testclient import TestClient


def _install_handler_stubs(monkeypatch):
    module_exports = {
        "bot.handlers.start": ["start_handler", "help_handler"],
        "bot.handlers.link": ["link_handler"],
        "bot.handlers.search": [
            "search_handler",
            "filter_handler",
            "tags_handler",
            "unread_handler",
            "today_handler",
            "week_handler",
        ],
        "bot.handlers.manage": [
            "status_handler",
            "note_handler",
            "priority_handler",
            "delete_handler",
            "edit_handler",
            "view_handler",
            "sheet_handler",
            "addcategory_handler",
        ],
        "bot.handlers.callback": ["callback_handler"],
        "bot.handlers.lang": ["lang_handler"],
        "bot.handlers.export": ["export_handler"],
        "bot.handlers.lib": ["lib_handler"],
        "bot.handlers.stats": ["stats_handler"],
        "bot.handlers.remind": ["remind_handler"],
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


def test_startup_hook_invokes_library_group_backfill(monkeypatch):
    index_module = _load_index_module(monkeypatch)
    backfill_calls = []

    def _detect_group(_url: str, _title: str = "", _summary: str = ""):
        return "utils"

    class _SheetsStub:
        def backfill_library_groups(self, detect_group_fn):
            backfill_calls.append(detect_group_fn)

    monkeypatch.setattr(index_module, "detect_library_group", _detect_group)
    monkeypatch.setattr(index_module, "get_sheets_service", lambda: _SheetsStub())

    with TestClient(index_module.app):
        pass

    assert backfill_calls == [_detect_group]


def test_startup_backfill_failure_is_non_blocking(monkeypatch, caplog):
    index_module = _load_index_module(monkeypatch)

    class _FailingSheetsStub:
        def backfill_library_groups(self, _detect_group_fn):
            raise RuntimeError("boom")

    monkeypatch.setattr(index_module, "get_sheets_service", lambda: _FailingSheetsStub())

    with caplog.at_level(logging.WARNING):
        with TestClient(index_module.app) as client:
            response = client.get("/health")

    assert response.status_code == 200
    assert any(
        "Startup library group backfill failed" in record.getMessage()
        for record in caplog.records
    )
