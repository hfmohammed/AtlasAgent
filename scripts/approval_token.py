"""Issue a local-demo approval token for a pending action ID."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.services.tools import approval_token  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action_id", help="Pending action ID returned by POST /api/chat")
    arguments = parser.parse_args()
    print(approval_token(arguments.action_id, get_settings().approval_secret))
