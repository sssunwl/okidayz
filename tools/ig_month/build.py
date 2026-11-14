"""月刊輪播出圖:把 <月份>.json 塞進 template.html,用 headless Chrome 逐頁截圖成 1080×1350。

用法:python3 tools/ig_month/build.py 2026-12
輸出:assets/ig/<slug>/01.jpg…(build.py 會複製到 docs/)(網站文章和 IG 用同一套圖)
照片原檔放 reference/ig-src/<月份>/(不進 git),出處寫在 json 的 credit。
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def main(key: str) -> None:
    data = json.loads((HERE / f"{key}.json").read_text(encoding="utf-8"))
    html = (HERE / "template.html").read_text(encoding="utf-8")
    inject = "<script>window.DATA = " + json.dumps(data, ensure_ascii=False) + ";</script>\n<main"
    page = HERE / "_render.html"  # 要跟 template 同層,相對路徑才對
    page.write_text(html.replace("<main", inject, 1), encoding="utf-8")
    total = 4 + len(data["pages"]) + 2
    out = ROOT / "assets/ig" / data["slug"]
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(1, total + 1):
            png = Path(tmp) / f"{i:02d}.png"
            subprocess.run([
                CHROME, "--headless=new", "--hide-scrollbars", "--allow-file-access-from-files",
                "--window-size=1080,1350", "--virtual-time-budget=8000",
                f"--screenshot={png}", f"file://{page}#p{i}",
            ], check=True, capture_output=True)
            Image.open(png).convert("RGB").save(out / f"{i:02d}.jpg", quality=90)
    page.unlink()
    print(f"{total} 張 → {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2026-12")
