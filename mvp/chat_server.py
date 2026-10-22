"""알프레도 대시보드 + 채팅 로컬 서버 (2026-10-19, 호연 지시: 알프레도와 채팅, 일단 GPT로).

실행(저장소 루트에서, 먼저 build_board.py): python3 -I mvp/chat_server.py [--port 8787]
→ 브라우저로 http://127.0.0.1:8787/ (맥 안에서만. 127.0.0.1에만 열린다)

- GPT 호출은 Top3와 같은 방식: `codex exec`(ChatGPT 구독 로그인, 읽기 전용, 빈 임시 폴더, 사용자 설정 무시). API 키를 쓰지 않는다.
- AI에 주는 것: 사용자 질문 + 지금 탭·자산의 화면 자료(data/board.json의 합성값)뿐. 개인 자료·계좌·키를 읽지 않는다
  (build_demo의 지킴이가 개인 경로 열기를 막는다). 대화는 저장하지 않고, 서버 기록에도 질문 원문을 남기지 않는다.
- 답 검사: 권유로 읽힐 표현(사라·팔라·매수 추천 등)이 있으면 답을 버리고 정보 안내 문장으로 바꾼다(flagged).
- 화면 문구: 입력은 GPT(OpenAI)로 보내진다는 안내와 AI 고지를 채팅창 위에 둔다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MVP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MVP)
import build_demo as B  # noqa: E402,F401  (불러오는 순간 개인 경로 지킴이가 켜진다. 바깥 호출은 codex 하위 프로세스만)

BOARD_HTML = os.path.join(MVP, "dist", "alfredo_mvp_board.html")
BOARD_JSON = os.path.join(MVP, "data", "board.json")
TOP3_DIR = os.path.realpath(os.path.join(MVP, "top3_home"))
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml"}
MODEL = os.environ.get("ALFREDO_CHAT_MODEL", "gpt-6.1-sol")    # CLAUDE.md 기본값. 바꾸려면 환경 변수
EFFORT = os.environ.get("ALFREDO_CHAT_EFFORT", "low")          # 채팅은 빨라야 해서 low
TIMEOUT = 120
MAX_MSG, MAX_HIST = 500, 6

ADVICE = re.compile(r"(사세요|파세요|사라\b|팔아라|매수하세요|매도하세요|매수를 (?:추천|권)|매도를 (?:추천|권)|"
                    r"(?:지금|당장)\s*(?:사|팔|매수|매도|들어가|진입)|진입하세요|손절하세요|비중을\s*\d+\s*%로\s*(?:늘리|줄이)세요|"
                    r"추천\s*종목|투자하세요|담으세요)")
SAFE = ("그 질문에는 사고팔 시점이나 비중을 정해 드리는 답이 될 수 있어 답하지 않겠습니다. 알프레도는 화면의 확신도와 근거를 "
        "설명하는 정보만 드리고, 최종 결정은 사용자가 합니다. 확신도 계산이나 지표 뜻을 물어 주시면 풀어 드리겠습니다.")

RULES = """너는 '알프레도', 모의투자 정보 서비스의 AI 집사다. 한국어로, 중학생도 알아듣게, 3–6문장으로 답한다.
지킬 것:
- 투자 권유를 하지 않는다. 사라·팔라·지금 들어가라·비중을 얼마로 하라 같은 말을 하지 않는다. 최종 결정은 사용자가 한다.
- 숫자는 아래 '화면 자료'에 있는 것만 쓴다. 없는 숫자를 만들지 않는다. 주식·기타 탭의 가격은 합성값(실제 시세 아님)이고, 코인 탭은 화면 자료의 '안내'를 따른다.
- 확신도는 신호가 같은 방향을 가리키는 정도이고 확률·추천이 아니다. 계산은 코드가 했고 너는 설명만 한다. 판정을 바꾸지 않는다.
- 주식·기타 탭의 정성 신호(뉴스·시황 해석)는 손으로 넣은 예시값이다. 화면 자료에 없는 뉴스나 시세는 모른다고 말한다.
- 개인 정보·계좌·금액을 묻지 않는다. 사용자가 적으면 다루지 않고 적지 말라고 안내한다.
- 마크다운 표·제목 없이 짧은 문단으로 쓴다."""


def facts(board: dict, tab: str, asset: str) -> dict:
    t = board["tabs"][tab]
    a = next(x for x in t["assets"] if x["id"] == asset)
    return {
        "탭": t["name"], "탭 설명": t["note"], "기준일": board["meta"]["end"], "가격 안내": board["meta"]["price_note"],
        "확신도 방법": board["meta"]["method"],
        "자산": {k: a[k] for k in ("id", "name", "price", "chg_pct", "sub", "summary")},
        "확신도": a["conf"], "신호": a["signals"], "변동성 국면": a["badge"],
        "같은 탭 다른 자산": [{"id": x["id"], "name": x["name"], "확신도": x["conf"]["side_pct"], "판정": x["conf"]["label"]}
                         for x in t["assets"] if x["id"] != asset],
    }


LIVE_NOTE = ("코인 탭 자료는 Top 3 Crypto 실시간 화면(바이낸스 현물, 15분마다 갱신)에서 읽은 글이다. 합성값이 아니다. "
             "'4지표 일치 신호'는 MACD 4시간·Stochastic 1시간·StochRSI 1시간·VPCI 15분의 방향(본선−신호선 부호)이 모두 같아진 첫 15분봉이며, "
             "대시보드의 간이 규칙이라 Top3 공식 판정과 다를 수 있다.")


def live_facts(live: dict, asset: str) -> dict:
    raw = json.dumps(live, ensure_ascii=False)[:6000]   # 화면 글만, 길이 제한
    return {"탭": "코인(Top 3 Crypto 실시간)", "고른 코인": asset, "안내": LIVE_NOTE, "화면 자료": raw}


def build_prompt(board: dict, tab: str, asset: str, message: str, history: list[dict], live: dict | None = None) -> str:
    hist = "\n".join(f"{'사용자' if h.get('role') == 'user' else '알프레도'}: {str(h.get('text', ''))[:800]}" for h in history[-MAX_HIST:])
    return (RULES + "\n\n화면 자료(JSON):\n" + json.dumps(live_facts(live, asset) if live is not None else facts(board, tab, asset), ensure_ascii=False)
            + ("\n\n지난 대화:\n" + hist if hist else "") + "\n\n사용자 질문: " + message + "\n\n알프레도의 답:")


def check(answer: str) -> tuple[str, bool]:
    answer = (answer or "").strip()
    if not answer:
        return "답을 만들지 못했습니다. 다시 물어봐 주세요.", True
    if ADVICE.search(answer):
        return SAFE, True
    return answer[:2000], False


def call_gpt(prompt: str) -> str:
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "TMPDIR", "USER") if k in os.environ}  # 비밀값을 넘기지 않는다
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "out.txt")
        cmd = ["codex", "exec", "--ignore-user-config", "-m", MODEL, "-c", f"model_reasoning_effort={EFFORT}",
               "-s", "read-only", "--skip-git-repo-check", "--ephemeral", "-C", d, "-o", out, "-"]
        r = subprocess.run(cmd, input=prompt, text=True, capture_output=True, timeout=TIMEOUT, env=env)
        if r.returncode != 0 or not os.path.exists(out):
            raise RuntimeError(f"GPT 호출 실패(종료 코드 {r.returncode})")
        with open(out, encoding="utf-8") as f:
            return f.read()


class Handler(BaseHTTPRequestHandler):
    server_version = "AlfredoLocal/0"

    def log_message(self, fmt, *args):  # 질문 원문을 남기지 않는다(경로·상태만)
        sys.stderr.write(f"{self.command} {self.path.split('?')[0]} {args[1] if len(args) > 1 else ''}\n")

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        origin = self.headers.get("Origin")
        return host in ("127.0.0.1", "localhost") and (origin is None or re.match(r"^http://(127\.0\.0\.1|localhost)(:\d+)?$", origin))

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "로컬 주소에서만 엽니다"})
        if self.path == "/favicon.ico":  # 화면 머리의 로고가 아이콘을 대신한다
            self.send_response(204); self.end_headers(); return
        if self.path.split("?")[0] in ("/", "/index.html"):
            with open(BOARD_HTML, "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if self.path.startswith("/top3/"):  # 코인 탭: Top3 홈 사본(정적 파일만. 데이터는 브라우저가 Top3 배포본 API에서 받음)
            rel = self.path.split("?")[0][len("/top3/"):] or "index.html"
            p = os.path.realpath(os.path.join(TOP3_DIR, rel))
            if p.startswith(TOP3_DIR + os.sep) and os.path.isfile(p):
                with open(p, "rb") as f:
                    return self._send(200, f.read(), TYPES.get(os.path.splitext(p)[1], "application/octet-stream"))
        return self._json(404, {"error": "없음"})

    def do_POST(self):
        if not self._host_ok():
            return self._json(403, {"error": "로컬 주소에서만 엽니다"})
        if self.path != "/api/chat":
            return self._json(404, {"error": "없음"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 16_000:
                return self._json(413, {"error": "너무 깁니다"})
            req = json.loads(self.rfile.read(n) or b"{}")
            with open(BOARD_JSON, encoding="utf-8") as f:
                board = json.load(f)
            tab, asset = str(req.get("tab", "")), str(req.get("asset", ""))
            if tab not in board["tabs"] or asset not in [a["id"] for a in board["tabs"][tab]["assets"]]:
                return self._json(400, {"error": "탭·자산을 모릅니다"})
            msg = str(req.get("message", "")).strip()[:MAX_MSG]
            if not msg:
                return self._json(400, {"error": "질문이 비었습니다"})
            hist = req.get("history") if isinstance(req.get("history"), list) else []
            live = req.get("live") if tab == "coin" and isinstance(req.get("live"), dict) else None
            answer, flagged = check(call_gpt(build_prompt(board, tab, asset, msg, hist, live)))
            return self._json(200, {"answer": answer, "flagged": flagged, "model": MODEL})
        except subprocess.TimeoutExpired:
            return self._json(504, {"error": f"GPT 응답이 {TIMEOUT}초 안에 오지 않았습니다"})
        except Exception as e:  # noqa: BLE001
            return self._json(500, {"error": str(e)[:200]})


def main() -> int:
    ap = argparse.ArgumentParser(description="알프레도 대시보드 + 채팅 로컬 서버")
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()
    if not os.path.exists(BOARD_HTML):
        raise SystemExit("먼저 python3 -I mvp/build_board.py")
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"http://127.0.0.1:{args.port}/ (모델 {MODEL}, 끄려면 Ctrl+C)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
