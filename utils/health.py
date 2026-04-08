"""Flask health check — keeps Render.com from spinning down."""

import logging
import threading

from flask import Flask

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def health():
    return "TeleGuard is running!", 200


def start_health_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Launch Flask in a daemon thread so it never blocks the bot."""
    thread = threading.Thread(
        target=lambda: app.run(host=host, port=port),
        daemon=True,
        name="health-check",
    )
    thread.start()
    logger.info(f"Health check server started on {host}:{port}")
