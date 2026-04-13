import api.cron as cron_module


class _DummyExportService:
    def generate_xlsx(self):
        return b"xlsx-bytes"


class _DummyResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code

    @property
    def is_success(self):
        return self.status_code < 400


class _RecordingAsyncClient:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return _DummyResponse(self.status_code)


def test_cron_digest_returns_contract(monkeypatch, cron_client):
    recorder = _RecordingAsyncClient()
    monkeypatch.setattr(cron_module, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(cron_module.httpx, "AsyncClient", lambda: recorder)

    response = cron_client.get("/cron/digest")
    payload = response.json()

    assert response.status_code == 200
    assert payload == {
        "enabled": False,
        "reason": "digest_disabled_in_topic_model",
        "sent": 0,
        "failed": 0,
        "total_users": 0,
    }
    assert recorder.requests == []


def test_cron_digest_alias_matches_canonical(monkeypatch, cron_client):
    recorder = _RecordingAsyncClient()
    monkeypatch.setattr(cron_module, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(cron_module.httpx, "AsyncClient", lambda: recorder)

    canonical = cron_client.get("/cron/digest")
    alias = cron_client.get("/api/cron/digest")

    assert canonical.status_code == 200
    assert alias.status_code == 200
    assert canonical.json() == alias.json()


def test_cron_backup_alias_matches_canonical(monkeypatch, cron_client):
    recorder = _RecordingAsyncClient()
    monkeypatch.setattr(cron_module, "ExportService", _DummyExportService)
    monkeypatch.setattr(cron_module, "ADMIN_TELEGRAM_ID", "777000")
    monkeypatch.setattr(cron_module, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(cron_module.httpx, "AsyncClient", lambda: recorder)

    canonical = cron_client.get("/cron/backup")
    alias = cron_client.get("/api/cron/backup")

    assert canonical.status_code == 200
    assert alias.status_code == 200
    assert canonical.json()["sent"] is True
    assert alias.json()["sent"] is True
    assert "filename" in canonical.json()
    assert "filename" in alias.json()
    assert recorder.requests
    assert recorder.requests[0][0].endswith("/sendDocument")
