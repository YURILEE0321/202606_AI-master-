import os
from pathlib import Path

from dotenv import load_dotenv

# wiki-assistant-py/.env를 읽는다 (src/config.py와 동일한 .env를 공유).
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

PORT: int = int(os.environ.get("PORT", "8000"))
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
