from __future__ import annotations

import base64
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import requests
from requests import Response, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv


load_dotenv()

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

logger = logging.getLogger("esp32_camera_client")


def _build_snapshot_url(camera_ip: str) -> str:
    base = camera_ip.strip() or "192.168.1.9"
    if not base.startswith("http://") and not base.startswith("https://"):
        base = f"http://{base}"
    return f"{base.rstrip('/')}/capture"


def _to_float(value: Optional[str], fallback: float) -> float:
    try:
        parsed = float(value) if value is not None else fallback
        return parsed if parsed > 0 else fallback
    except (TypeError, ValueError):
        return fallback


def _create_session() -> Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


@dataclass
class ESP32Config:
    camera_ip: str
    backend_endpoint: str
    send_interval: float

    @classmethod
    def from_env(cls) -> "ESP32Config":
        camera_ip = os.getenv("ESP32_IP", "192.168.1.9")
        backend_endpoint = os.getenv("BACKEND_ENDPOINT", "http://127.0.0.1:8000/predict")
        interval = _to_float(os.getenv("SEND_INTERVAL"), 3.0)
        return cls(camera_ip=camera_ip, backend_endpoint=backend_endpoint, send_interval=interval)

    @property
    def snapshot_url(self) -> str:
        return _build_snapshot_url(self.camera_ip)


class ESP32CameraClient:
    def __init__(self, config: ESP32Config) -> None:
        self.config = config
        self.session = _create_session()
        self.max_payload_age_seconds = 5 * 60  # guard rail for stale frames
        logger.info(
            "ESP32 client configured",
            extra={
                "snapshot_url": self.config.snapshot_url,
                "backend_endpoint": self.config.backend_endpoint,
                "interval": self.config.send_interval,
            },
        )

    def fetch_snapshot(self) -> bytes:
        response = self.session.get(self.config.snapshot_url, timeout=10)
        response.raise_for_status()
        if not response.content:
            raise RuntimeError("Empty snapshot payload received from ESP32-CAM")
        return response.content

    def encode_snapshot(self, snapshot_bytes: bytes) -> str:
        return base64.b64encode(snapshot_bytes).decode("ascii")

    def post_frame(self, encoded_image: str) -> Response:
        payload = {"image": encoded_image}
        response = self.session.post(
            self.config.backend_endpoint,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response

    def run_forever(self) -> None:
        consecutive_failures = 0
        logger.info(
            "Starting ESP32 snapshot ingestion loop (interval=%ss)", self.config.send_interval
        )
        try:
            while True:
                loop_start = time.monotonic()
                try:
                    snapshot = self.fetch_snapshot()
                    encoded = self.encode_snapshot(snapshot)
                    response = self.post_frame(encoded)
                    logger.info(
                        "Frame delivered successfully",
                        extra={
                            "status_code": response.status_code,
                            "payload_bytes": len(snapshot),
                        },
                    )
                    consecutive_failures = 0
                except requests.RequestException as http_exc:
                    consecutive_failures += 1
                    logger.warning(
                        "HTTP error while processing frame (attempt %s): %s",
                        consecutive_failures,
                        http_exc,
                    )
                except Exception as exc:  # noqa: BLE001
                    consecutive_failures += 1
                    logger.exception(
                        "Unexpected error while processing frame (attempt %s): %s",
                        consecutive_failures,
                        exc,
                    )

                if consecutive_failures and consecutive_failures % 5 == 0:
                    logger.error(
                        "ESP32 client hit %s consecutive failures; backing off for 10 seconds",
                        consecutive_failures,
                    )
                    time.sleep(10)

                elapsed = time.monotonic() - loop_start
                sleep_for = max(self.config.send_interval - elapsed, 0.2)
                time.sleep(sleep_for)
        except KeyboardInterrupt:
            logger.info("ESP32 ingestion interrupted by user")
        finally:
            self.session.close()
            logger.info("ESP32 ingestion stopped")


def run() -> None:
    config = ESP32Config.from_env()
    client = ESP32CameraClient(config)
    client.run_forever()


if __name__ == "__main__":
    run()


