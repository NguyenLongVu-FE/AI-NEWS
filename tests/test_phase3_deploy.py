import importlib
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient

from bot.utils.validation import sanitize_html, validate_note, validate_url


DEPLOY_CHECKS_FILE = Path(__file__).resolve().parents[1] / "scripts" / "deploy_checks.py"


def _install_handler_stubs():
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
        "bot.handlers.stats": ["stats_handler"],
        "bot.handlers.remind": ["remind_handler"],
    }
    for module_name, exports in module_exports.items():
        module = types.ModuleType(module_name)
        for export in exports:
            setattr(module, export, object())
        sys.modules[module_name] = module


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
    _install_handler_stubs()

    sys.modules.pop("api.index", None)
    return importlib.import_module("api.index")


def test_deploy_health_runtime_contract(monkeypatch):
    index_module = _load_index_module(monkeypatch)
    with TestClient(index_module.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_deploy_webhook_runtime_secret_guard(monkeypatch):
    index_module = _load_index_module(monkeypatch)
    with TestClient(index_module.app) as client:
        response = client.post(
            "/webhook",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "unauthorized"}


def test_deploy_validation_rules_and_route_checks():
    deploy_checks_source = DEPLOY_CHECKS_FILE.read_text(encoding="utf-8")

    assert "/api/webhook" in deploy_checks_source
    assert "/webhook" in deploy_checks_source
    assert "/api/health" in deploy_checks_source

    valid_http, _ = validate_url("http://example.com")
    valid_https, _ = validate_url("https://example.com/path")
    invalid_url, _ = validate_url("ftp://example.com")
    note_ok, _ = validate_note("short note")
    note_bad, note_message = validate_note("x" * 501)
    escaped = sanitize_html("<b>unsafe</b>")

    assert valid_http is True
    assert valid_https is True
    assert invalid_url is False
    assert note_ok is True
    assert note_bad is False
    assert "500" in note_message
    assert escaped == "&lt;b&gt;unsafe&lt;/b&gt;", "sanitize_html must escape HTML tags"
