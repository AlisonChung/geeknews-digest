"""GitHub Pages용 정적 사이트 빌드.

static/index.html + digest/*.md 를 docs/ 로 복사하고 files.json 목록을 만든다.
페이지는 상대 경로(files.json, files/<name>.md)만 쓰므로 로컬 서버와 Pages에서 똑같이 동작한다.

사용법: python build_site.py
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIGEST = ROOT / "digest"
OUT = ROOT / "docs"


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "files").mkdir(parents=True)
    shutil.copy2(ROOT / "static" / "index.html", OUT / "index.html")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")  # Jekyll 처리 끄기

    files = sorted(DIGEST.glob("*.md"), reverse=True)
    for f in files:
        shutil.copy2(f, OUT / "files" / f.name)
    listing = [{"name": f.name, "size": f.stat().st_size} for f in files]
    (OUT / "files.json").write_text(json.dumps(listing, ensure_ascii=False), encoding="utf-8")
    print(f"built docs/ with {len(files)} file(s)")


if __name__ == "__main__":
    main()
