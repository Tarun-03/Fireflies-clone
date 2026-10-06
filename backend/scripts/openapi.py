import json
from pathlib import Path

from app.main import app

if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"
    destination.write_text(json.dumps(app.openapi(), indent=2) + "\n")
