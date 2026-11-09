"""幫 data/places.json 的景點找一張 Wikimedia Commons 照片(可商用授權，要標作者)。
用法：python3 tools/spot_photos.py [--force]。搜尋字用 photo_q；找到後一定要人工看過，抓錯就改 photo_q 重跑。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocean_photos import find_photo  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data" / "places.json"


def main():
    force = "--force" in sys.argv
    data = json.loads(DATA.read_text(encoding="utf-8"))
    for spot in data["spots"]:
        if spot.get("photo") and not force:
            continue
        photo = find_photo(spot.get("photo_q") or spot["name"]["ja"])
        spot["photo"] = photo
        print(("✓" if photo else "✗"), spot["slug"], (photo or {}).get("page", ""))
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
