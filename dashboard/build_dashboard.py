"""보너스 1 대시보드 만들기: CSV와 분석 요약을 HTML 한 파일에 넣는다(표준 라이브러리만).

실행(저장소 루트에서, 먼저 python analysis.py):
    python dashboard/build_dashboard.py
결과: dashboard/index.html  (더블클릭으로 열림, 인터넷·서버 필요 없음)
"""
from __future__ import annotations

import csv
import json
import os
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
HERE = os.path.dirname(os.path.abspath(__file__))
FNG_CODE = {"Extreme Fear": 0, "Fear": 1, "Neutral": 2, "Greed": 3, "Extreme Greed": 4}


def daily_series(path: str, col: str, cast=float):
    """날짜 빈칸을 null로 채운 하루 간격 배열과 시작일."""
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    d0 = date.fromisoformat(rows[0]["date"])
    d1 = date.fromisoformat(rows[-1]["date"])
    vals = {r["date"]: r[col] for r in rows}
    out = []
    d = d0
    while d <= d1:
        v = vals.get(d.isoformat())
        out.append(None if v is None else cast(v))
        d += timedelta(days=1)
    return d0.isoformat(), out, len(rows)


def main() -> None:
    data = {"coins": {}, "rows": {}}
    for sym in ["btc", "eth", "xrp"]:
        start, close, n = daily_series(os.path.join(RAW, f"coinbase_{sym}_usd_1d.csv"), "close")
        data["coins"][sym.upper()] = {"start": start, "close": [None if v is None else round(v, 6 if v < 10 else 2) for v in close]}
        data["rows"][sym.upper()] = n
    start, fv, n = daily_series(os.path.join(RAW, "fear_greed_1d.csv"), "value", int)
    _, fc, _ = daily_series(os.path.join(RAW, "fear_greed_1d.csv"), "classification", lambda s: FNG_CODE[s])
    data["fng"] = {"start": start, "v": fv, "c": fc}
    data["rows"]["FNG"] = n
    with open(os.path.join(ROOT, "outputs", "summary.json"), encoding="utf-8") as f:
        s = json.load(f)
    data["ref"] = {
        "fwd30_above_ma200": s["trend"]["fwd30_above_ma200"],
        "fwd30_below_ma200": s["trend"]["fwd30_below_ma200"],
        "fng_forward": s["fear_greed_forward"]["by_class"],
        "halvings": s["halvings"],
        "rolling_forecast": s["forecast"]["rolling_origin"]["by_method"],
        "seasonal_strength": s["decomposition"]["seasonal_strength"],
        "trend_strength": s["decomposition"]["trend_strength"],
    }
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as f:
        html = f.read()
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = html.replace("/*__DATA__*/null", blob)
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"dashboard/index.html ({len(html) // 1024} KB) · 행 수 {data['rows']}")


if __name__ == "__main__":
    main()
