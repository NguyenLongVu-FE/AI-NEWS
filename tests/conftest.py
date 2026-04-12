import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.cron import router as cron_router


@pytest.fixture
def cron_client():
    app = FastAPI()
    app.include_router(cron_router)
    with TestClient(app) as client:
        yield client
