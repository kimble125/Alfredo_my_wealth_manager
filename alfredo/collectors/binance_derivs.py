"""알프레도 전용: 바이낸스 USDT-M 선물 공개 파생지표 적립기.

무엇을 모으나
-------------
- `futures/data/*` 5종(미결제약정 OI, 전체 계정 롱숏, 상위 트레이더 포지션·계정 롱숏, 테이커 매수/매도 비율)
  × 심볼(BTC·ETH·XRP) × 주기(15m·1h·4h). 이 계열은 **최근 약 30일치만** 무료로 반환되므로
  매 실행마다 창 전체를 받아 멱등 upsert 한다(며칠 걸러도 30일 안이면 자동 복구).
- 펀딩비(`fapi/v1/fundingRate`): 전체 이력이 열려 있어 마지막 저장 시각 이후만 증분 수집.

왜 따로 있나
------------
Top3 팀 수집기는 2026-10-03 팀 결정으로 이 계열 수집을 껐다(코드·데이터는 남김). 사용자(miru)는
2026-10-07 "Alfredo용으로 계속 수집해 실제 예측과 조응되는지 보자, Top3 목적과 구분하라"고 지시했다.
그래서 이 모듈은 팀 저장소를 읽지도 쓰지도 않고, 알프레도 저장소 안에서 자기 DB(`data/alfredo/`, git 제외)
와 로그(`logs/`)만 쓴다. 스키마(`series` 표, 기본키 source·symbol·metric·period·ts, metric 이름)는
Top3 `market.db`와 같게 두어 나중에 두 DB를 같은 열 이름으로 대조할 수 있게 했다.

사용
----
    python3 -m alfredo.collectors.binance_derivs            # 정기 수집(창 전체 upsert + 펀딩 증분)
    python3 -m alfredo.collectors.binance_derivs --status   # 적재 현황만 출력
    python3 -m alfredo.collectors.binance_derivs --no-funding

종료 요약 줄(로그·stdout 공통): "=== [ALFREDO] 완료: 호출 성공 N / 실패 F / 신규 M행 ==="
표준 라이브러리만 사용. API 키 없음.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]          # .../12_expert_agents
CONF_PATH = REPO_ROOT / "alfredo" / "conf" / "collectors_derivs.json"
BINANCE_DATA = "https://fapi.binance.com/futures/data"
BINANCE_FAPI = "https://fapi.binance.com/fapi/v1"
UA = "alfredo-derivs-collector/0.1 (personal research; stdlib urllib)"

SCHEMA = """
CREATE TABLE IF NOT EXISTS series (
    source       TEXT NOT NULL,    -- binance
    symbol       TEXT NOT NULL,    -- BTCUSDT ...
    metric       TEXT NOT NULL,    -- oi_base | global_acc_long_short_ratio | buy_sell_ratio | funding_rate ...
    period       TEXT NOT NULL,    -- 15m | 1h | 4h | event
    ts           INTEGER NOT NULL, -- 관측 시각(epoch ms, UTC)
    value        REAL,
    collected_at INTEGER NOT NULL, -- 받아온 시각(epoch ms, UTC)
    PRIMARY KEY (source, symbol, metric, period, ts)
);
CREATE INDEX IF NOT EXISTS idx_series_lookup ON series (symbol, metric, period, ts);
CREATE TABLE IF NOT EXISTS runs (
    run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    purpose     TEXT NOT NULL,      -- alfredo
    started_at  INTEGER NOT NULL,
    finished_at INTEGER,
    ok_calls    INTEGER,
    failed_calls INTEGER,
    new_rows    INTEGER,
    note        TEXT
);
"""


def now_ms() -> int:
    return int(time.time() * 1000)


def ms_to_utc(ms: int) -> str:
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M")


def http_json(url: str, timeout: int, retries: int):
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # 4xx/5xx
            body = ""
            try:
                body = exc.read().decode("utf-8")[:200]
            except Exception:  # noqa: BLE001
                pass
            last = RuntimeError(f"HTTP {exc.code} {body}")
            if exc.code in (400, 429, 418):
                # 400(-1130 등: 창 밖) 은 재시도 의미 없음. 429/418 은 쉬었다가.
                if exc.code == 400:
                    raise last
                time.sleep(2.0 * (attempt + 1))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.0 * (attempt + 1))
    raise last if last else RuntimeError("unknown http failure")


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.executescript(SCHEMA)

    def upsert(self, rows) -> int:
        """rows: (source, symbol, metric, period, ts, value). 새로 들어간 행 수를 돌려준다."""
        if not rows:
            return 0
        cur = self.conn.cursor()
        before = cur.execute("SELECT total_changes()").fetchone()[0]
        col = now_ms()
        cur.executemany(
            "INSERT OR IGNORE INTO series (source, symbol, metric, period, ts, value, collected_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(s, sym, m, p, int(ts), float(v), col) for (s, sym, m, p, ts, v) in rows],
        )
        self.conn.commit()
        after = cur.execute("SELECT total_changes()").fetchone()[0]
        return after - before

    def last_ts(self, source, symbol, metric, period):
        row = self.conn.execute(
            "SELECT MAX(ts) FROM series WHERE source=? AND symbol=? AND metric=? AND period=?",
            (source, symbol, metric, period),
        ).fetchone()
        return row[0]

    def start_run(self, purpose: str) -> int:
        cur = self.conn.execute("INSERT INTO runs (purpose, started_at) VALUES (?, ?)", (purpose, now_ms()))
        self.conn.commit()
        return cur.lastrowid

    def finish_run(self, run_id: int, ok: int, failed: int, new: int, note: str = ""):
        self.conn.execute(
            "UPDATE runs SET finished_at=?, ok_calls=?, failed_calls=?, new_rows=?, note=? WHERE run_id=?",
            (now_ms(), ok, failed, new, note, run_id),
        )
        self.conn.commit()

    def status(self):
        return self.conn.execute(
            "SELECT symbol, metric, period, COUNT(*), MIN(ts), MAX(ts) FROM series "
            "GROUP BY symbol, metric, period ORDER BY symbol, metric, period"
        ).fetchall()


# ------------------------------------------------------------------ collectors

def collect_binance_window(conf, store: Store, log):
    """futures/data 5종 × 심볼 × 주기. endTime 을 뒤로 밀며 30일 창 전체를 페이지로 받는다."""
    ok = failed = new = 0
    window_ms = int(conf["window_days"]) * 86400 * 1000
    floor_ts = now_ms() - window_ms
    for group, spec in conf["binance_window_endpoints"].items():
        if group.startswith("_"):
            continue
        for symbol in conf["symbols"]:
            for period in conf["periods"]:
                end_time = None
                pages = 0
                got = 0
                added = 0
                while pages < int(conf["max_pages_per_series"]):
                    url = f"{BINANCE_DATA}/{spec['path']}?symbol={symbol}&period={period}&limit={conf['page_limit']}"
                    if end_time is not None:
                        url += f"&endTime={end_time}"
                    try:
                        data = http_json(url, conf["timeout_sec"], conf["retries"])
                        ok += 1
                    except Exception as exc:  # noqa: BLE001
                        msg = str(exc)
                        if "-1130" in msg or "startTime" in msg:
                            # 창 밖 요청: 정상 종료로 본다
                            break
                        failed += 1
                        log(f"  [FAIL] {group} {symbol} {period} page{pages}: {msg[:160]}")
                        break
                    pages += 1
                    if not data:
                        break
                    rows = []
                    for item in data:
                        ts = int(item["timestamp"])
                        for metric, field in spec["fields"].items():
                            raw = item.get(field)
                            if raw in (None, ""):
                                continue
                            rows.append(("binance", symbol, metric, period, ts, raw))
                    got += len(data)
                    added += store.upsert(rows)
                    oldest = min(int(i["timestamp"]) for i in data)
                    if oldest <= floor_ts or len(data) < int(conf["page_limit"]):
                        break
                    end_time = oldest - 1
                    time.sleep(conf["request_sleep_sec"])
                new += added
                log(f"  binance {group:<26} {symbol:<8} {period:<3} 페이지 {pages} 수신 {got:>5}건 신규 {added:>6}행")
                time.sleep(conf["request_sleep_sec"])
    return ok, failed, new


def collect_funding(conf, store: Store, log):
    """펀딩비 증분 수집. 마지막 저장 시각 + 1ms 부터 1000건씩 앞으로."""
    f = conf["funding"]
    ok = failed = new = 0
    for symbol in conf["symbols"]:
        last = store.last_ts("binance", symbol, f["metric"], f["period"])
        start = (last + 1) if last else int(f["first_ms"])
        pages = 0
        added = 0
        while pages < 40:
            url = f"{BINANCE_FAPI}/fundingRate?symbol={symbol}&startTime={start}&limit={f['page_limit']}"
            try:
                data = http_json(url, conf["timeout_sec"], conf["retries"])
                ok += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                log(f"  [FAIL] funding {symbol} page{pages}: {str(exc)[:160]}")
                break
            pages += 1
            if not data:
                break
            rows = [("binance", symbol, f["metric"], f["period"], int(d["fundingTime"]), d["fundingRate"])
                    for d in data if d.get("fundingRate") not in (None, "")]
            added += store.upsert(rows)
            newest = max(int(d["fundingTime"]) for d in data)
            if len(data) < int(f["page_limit"]):
                break
            start = newest + 1
            time.sleep(conf["request_sleep_sec"])
        new += added
        log(f"  binance funding_rate                {symbol:<8} evt 페이지 {pages} 신규 {added:>6}행")
    return ok, failed, new


# ------------------------------------------------------------------------ main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="알프레도 전용 바이낸스 파생지표 적립기")
    ap.add_argument("--status", action="store_true", help="적재 현황만 출력")
    ap.add_argument("--no-funding", action="store_true", help="펀딩비 증분 수집 생략")
    ap.add_argument("--conf", default=str(CONF_PATH))
    args = ap.parse_args(argv)

    conf = json.loads(Path(args.conf).read_text(encoding="utf-8"))
    db_path = (REPO_ROOT / conf["db_path"]).resolve()
    log_path = (REPO_ROOT / conf["log_path"]).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    store = Store(db_path)

    def log(line: str):
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    if args.status:
        for symbol, metric, period, n, lo, hi in store.status():
            print(f"{symbol:<8} {metric:<28} {period:<5} {n:>7}행  {ms_to_utc(lo)} ~ {ms_to_utc(hi)} UTC")
        return 0

    stamp = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    log(f"########## [ALFREDO] {stamp} 시작 (purpose={conf['purpose']}, db={db_path.name}) ##########")
    run_id = store.start_run(conf["purpose"])
    ok = failed = new = 0
    o, f_, n = collect_binance_window(conf, store, log)
    ok, failed, new = ok + o, failed + f_, new + n
    if conf["funding"].get("enabled", True) and not args.no_funding:
        o, f_, n = collect_funding(conf, store, log)
        ok, failed, new = ok + o, failed + f_, new + n
    note = "" if failed == 0 else f"{failed} failed calls"
    store.finish_run(run_id, ok, failed, new, note)
    log(f"=== [ALFREDO] 완료: 호출 성공 {ok} / 실패 {failed} / 신규 {new}행 ===")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
