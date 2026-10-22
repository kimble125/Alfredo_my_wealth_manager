"""공개 API에서 코인 일봉과 공포탐욕 지수를 받아 CSV로 저장한다.

실행(저장소 루트에서):
    python data/collect.py              # 전체 기간을 다시 받기(약 1분)
    python data/collect.py --end 2026-10-21

받는 곳(모두 로그인·API 키 없이 쓰는 공개 엔드포인트):
- Coinbase Exchange 공개 시세 API: https://api.exchange.coinbase.com/products/{상품}/candles
  (granularity=86400 = 하루, 요청당 최대 300개, 시각은 UTC 자정 기준)
- alternative.me Crypto Fear & Greed Index API: https://api.alternative.me/fng/?limit=0

결과:
- data/raw/coinbase_{btc,eth,xrp}_usd_1d.csv  열: date, open, high, low, close, volume
- data/raw/fear_greed_1d.csv                 열: date, value, classification

표준 라이브러리만 쓴다(설치 없이 실행). 약관상 재배포 조건은 README '데이터 출처와 약관'을 본다.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "raw")
UA = {"User-Agent": "alfredo-codyssey-timeseries/1.0 (educational project)"}

# 상품별 첫 날짜(코인베이스 상장 무렵). 그 전 구간은 빈 응답이라 건너뛴다.
PRODUCTS = {
    "BTC-USD": "2015-07-20",
    "ETH-USD": "2016-05-18",
    "XRP-USD": "2019-02-26",
}
DAY = 86400
STEP = 300  # 요청당 최대 개수


def get_json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_coinbase_daily(product: str, start: str, end: str) -> list[list]:
    """[date, open, high, low, close, volume] 목록(날짜 오름차순, 중복 없음)."""
    t0 = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    t_end = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
    rows: dict[str, list] = {}
    while t0 <= t_end:
        t1 = min(t0 + timedelta(days=STEP - 1), t_end)
        url = (f"https://api.exchange.coinbase.com/products/{product}/candles?granularity={DAY}"
               f"&start={t0:%Y-%m-%dT%H:%M:%SZ}&end={t1:%Y-%m-%dT%H:%M:%SZ}")
        for attempt in range(3):
            try:
                data = get_json(url)
                break
            except Exception as e:  # 일시 오류는 잠깐 쉬고 다시
                if attempt == 2:
                    raise RuntimeError(f"{product} {t0:%Y-%m-%d} 받기 실패: {e}") from e
                time.sleep(2)
        # 응답 한 줄: [time, low, high, open, close, volume]
        for ts, low, high, opn, close, vol in data:
            d = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            rows[d] = [d, opn, high, low, close, vol]
        t0 = t1 + timedelta(days=1)
        time.sleep(0.35)  # 공개 API 요청 간격(초당 10회 제한보다 넉넉히)
    return [rows[k] for k in sorted(rows)]


def fetch_fear_greed() -> list[list]:
    data = get_json("https://api.alternative.me/fng/?limit=0&format=json")["data"]
    out = {}
    for x in data:
        d = datetime.fromtimestamp(int(x["timestamp"]), tz=timezone.utc).strftime("%Y-%m-%d")
        out[d] = [d, int(x["value"]), x["value_classification"]]
    return [out[k] for k in sorted(out)]


def write_csv(path: str, header: list[str], rows: list[list]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    ap.add_argument("--end", default=yesterday, help="마지막 날짜(UTC, 기본: 어제 = 마감된 마지막 일봉)")
    args = ap.parse_args()

    for product, start in PRODUCTS.items():
        rows = fetch_coinbase_daily(product, start, args.end)
        name = product.split("-")[0].lower()
        path = os.path.join(RAW, f"coinbase_{name}_usd_1d.csv")
        write_csv(path, ["date", "open", "high", "low", "close", "volume"], rows)
        print(f"{product}: {len(rows)}일 ({rows[0][0]} – {rows[-1][0]}) → {os.path.relpath(path)}")

    fg = [r for r in fetch_fear_greed() if r[0] <= args.end]
    path = os.path.join(RAW, "fear_greed_1d.csv")
    write_csv(path, ["date", "value", "classification"], fg)
    print(f"Fear & Greed: {len(fg)}일 ({fg[0][0]} – {fg[-1][0]}) → {os.path.relpath(path)}")


if __name__ == "__main__":
    main()
