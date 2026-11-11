"""GeekNews RSS 다이제스트 생성기.

피드의 제목/요약만 읽어 관심 주제와 맞는 글을 최대 5건 골라
digest/YYYY-MM-DD.md 로 저장한다. 선별·요약은 로컬 `claude -p` CLI가 맡는다.
기사 본문 페이지는 열지 않는다 (피드 내용만 Claude에 전달, 웹 도구 차단).

사용법: python rss_digest.py
"""
import datetime
import html
import json
import re
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

FEED_URL = "https://news.hada.io/rss/news"
TOPICS = ["AI 에이전트", "업무 자동화", "클로드(Claude)"]
MAX_ITEMS = 5
OUT_DIR = Path(__file__).resolve().parent / "digest"
ATOM = "{http://www.w3.org/2005/Atom}"


def fetch_feed(url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "rss-digest/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())

    def text(el, tag):
        node = el.find(tag)
        return (node.text or "") if node is not None else ""

    def clean(s):
        s = re.sub(r"<[^>]+>", " ", html.unescape(s))
        return re.sub(r"\s+", " ", s).strip()

    items = []
    if root.tag == f"{ATOM}feed":  # Atom
        for e in root.findall(f"{ATOM}entry"):
            link = e.find(f"{ATOM}link[@rel='alternate']")
            if link is None:
                link = e.find(f"{ATOM}link")
            items.append({
                "title": clean(text(e, f"{ATOM}title")),
                "summary": clean(text(e, f"{ATOM}content") or text(e, f"{ATOM}summary"))[:600],
                "link": text(e, f"{ATOM}id") or (link.get("href") if link is not None else ""),
            })
    else:  # RSS 2.0
        for e in root.iter("item"):
            items.append({
                "title": clean(text(e, "title")),
                "summary": clean(text(e, "description"))[:600],
                "link": text(e, "link").strip(),
            })
    return items


def ask_claude(items: list[dict]) -> dict:
    numbered = [{"id": i, "title": it["title"], "summary": it["summary"]} for i, it in enumerate(items)]
    prompt = f"""아래는 RSS 피드 글 목록(JSON)이다. 관심 주제: {", ".join(TOPICS)}.

규칙:
- 관심 주제와 실제로 관련된 글만 골라라. 최대 {MAX_ITEMS}건, 관련성 높은 순.
- 아래에 주어진 제목과 요약만 근거로 쓴다. 다른 정보를 지어내지 않는다.
- 각 글을 한국어 두 문장으로 요약하되, 원문 문장을 길게 그대로 옮기지 말고 새 표현으로 다시 쓴다.
- 고른 글들을 아우르는 "오늘의 세 줄 요약"(정확히 3줄)을 쓴다.
- 해당 글이 하나도 없으면 picks를 빈 배열, overview도 빈 배열로 둔다.

출력은 설명 없이 아래 형식의 JSON 하나만:
{{"overview": ["줄1", "줄2", "줄3"], "picks": [{{"id": 0, "summary": "두 문장 요약"}}]}}

글 목록:
{json.dumps(numbered, ensure_ascii=False)}
"""
    claude = shutil.which("claude")
    if not claude:
        sys.exit("claude CLI를 찾을 수 없습니다.")
    res = subprocess.run(
        [claude, "-p", "--output-format", "text",
         "--disallowedTools", "WebFetch,WebSearch,Bash,Read,Edit,Write,Glob,Grep"],
        input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=600,
    )
    if res.returncode != 0:
        sys.exit(f"claude 실행 실패: {res.stderr.strip()[:500]}")
    m = re.search(r"\{.*\}", res.stdout, re.S)
    if not m:
        sys.exit(f"JSON 응답을 찾지 못함: {res.stdout[:500]}")
    return json.loads(m.group(0))


def build_markdown(today: str, items: list[dict], result: dict) -> tuple[str, int]:
    picks = [p for p in result.get("picks", []) if 0 <= int(p.get("id", -1)) < len(items)][:MAX_ITEMS]
    if not picks:
        return "해당 없음\n", 0
    lines = [f"# GeekNews 다이제스트 {today}", "", "## 오늘의 세 줄 요약", ""]
    lines += [f"{i}. {s}" for i, s in enumerate(result.get("overview", [])[:3], 1)]
    lines += ["", "## 기사", ""]
    for p in picks:
        it = items[int(p["id"])]
        lines += [f"### {it['title']}", "", p["summary"].strip(), "", f"원문: {it['link']}", ""]
    return "\n".join(lines), len(picks)


def main():
    today = datetime.date.today().isoformat()
    items = fetch_feed(FEED_URL)
    result = ask_claude(items) if items else {}
    md, count = build_markdown(today, items, result)
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"{today}.md"
    out.write_text(md, encoding="utf-8")  # 같은 날짜 파일은 덮어씀
    print(f"saved: {out} / picked: {count}")


if __name__ == "__main__":
    main()
