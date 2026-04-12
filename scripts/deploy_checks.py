import argparse
import os
import sys

import requests

BASE_URL = os.environ.get("BASE_URL", "https://infosaver-bot.vercel.app")


def _trim_base(url: str) -> str:
    return url.rstrip("/")


def _check_health(base_url: str) -> str:
    for path in ("/api/health", "/health"):
        response = requests.get(f"{base_url}{path}", timeout=10)
        if response.status_code == 200:
            payload = response.json()
            if payload.get("status") == "ok":
                return path
    raise RuntimeError("Health check failed on /api/health and /health")


def _check_webhook_guard(base_url: str) -> str:
    headers = {"X-Telegram-Bot-Api-Secret-Token": "invalid-secret"}
    for path in ("/api/webhook", "/webhook"):
        response = requests.post(
            f"{base_url}{path}",
            json={"update_id": 0},
            headers=headers,
            timeout=10,
        )
        if response.status_code == 200:
            payload = response.json()
            if payload.get("ok") is False and payload.get("error") == "unauthorized":
                return path
    raise RuntimeError("Webhook guard check failed on /api/webhook and /webhook")


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-deploy checks for InfoSaver Bot")
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help="Deployment base URL, e.g. https://infosaver-bot.vercel.app",
    )
    args = parser.parse_args()

    base_url = _trim_base(args.base_url)

    health_path = _check_health(base_url)
    webhook_path = _check_webhook_guard(base_url)

    print(f"OK: health check passed on {health_path}")
    print(f"OK: webhook guard passed on {webhook_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
