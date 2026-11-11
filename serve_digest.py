"""digest 폴더를 서빙하는 로컬 정적 서버.

실행할 때마다 digest/ 안의 .md 파일 목록(files.json)을 만들고,
static/index.html 과 함께 http://localhost:8000 에서 제공한다.
digest/ 와 static/ 밖의 파일은 노출하지 않는다.

사용법: python serve_digest.py [port]
"""
import http.server
import json
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIGEST = ROOT / "digest"
STATIC = ROOT / "static"


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".md": "text/markdown; charset=utf-8",
                      ".json": "application/json; charset=utf-8"}

    def translate_path(self, path):
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path in ("/", "/index.html"):
            return str(STATIC / "index.html")
        if path == "/files.json":
            return self._write_listing()
        if path.startswith("/files/"):
            name = Path(urllib.parse.unquote(path[len("/files/"):])).name  # 하위 경로 차단
            if name.endswith(".md") and (DIGEST / name).is_file():
                return str(DIGEST / name)
        return str(STATIC / "__missing__")

    def _write_listing(self):
        DIGEST.mkdir(exist_ok=True)
        files = sorted(DIGEST.glob("*.md"), reverse=True)
        data = [{"name": f.name, "size": f.stat().st_size} for f in files]
        out = STATIC / "files.json"
        out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return str(out)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"serving on http://localhost:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
