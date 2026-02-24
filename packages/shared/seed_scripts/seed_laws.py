import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LAWS_FILE = ROOT / "laws" / "citations.yaml"
OUT_FILE = ROOT / "laws" / "citations.json"


def main() -> None:
    with LAWS_FILE.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()
