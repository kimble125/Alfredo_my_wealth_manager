"""비트코인 시계열 트렌드 분석 (코디세이 미션 'AI 데이터 분석: 데이터 기반 트렌드 분석').

실행(저장소 루트에서):
    python data/collect.py      # (선택) 공개 API에서 데이터 다시 받기
    python analysis.py          # 그림 images/*.png, 숫자 outputs/summary.json, 표 outputs/*.csv

입력: data/raw/coinbase_{btc,eth,xrp}_usd_1d.csv, data/raw/fear_greed_1d.csv
기법: 결측(날짜 재색인)·이상치(z 점수 표시), 이동평균(50·200일), 변화율(일·월·30일 뒤 수익률),
      30일 변동성, 구간별 통계(반감기·국면·공포탐욕 구간), 요일·월 집계, 고전 분해(보너스 A), 베이스라인 예측(보너스 B)
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "data", "raw")
IMG = os.path.join(ROOT, "images")
OUT = os.path.join(ROOT, "outputs")
os.makedirs(IMG, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

# 한글 글꼴: 있는 것을 차례로 쓴다(맥 AppleGothic, 윈도 Malgun Gothic, 리눅스 Nanum/Noto)
_have = {f.name for f in font_manager.fontManager.ttflist}
for _name in ["AppleGothic", "Apple SD Gothic Neo", "Malgun Gothic", "NanumGothic", "Noto Sans CJK KR", "Noto Sans KR"]:
    if _name in _have:
        plt.rcParams["font.family"] = _name
        break
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110
plt.rcParams["savefig.bbox"] = "tight"

HALVINGS = {  # 비트코인 반감기(블록 보상이 절반이 된 날, UTC)
    "2016-07-09": "2차 반감기",
    "2020-05-11": "3차 반감기",
    "2024-04-20": "4차 반감기",
}
FILL_MAX_GAP = 3        # 3일 이하 빈 날만 직전 값으로 채움(거래소 점검 등). 더 긴 공백은 비워 둔다
Z_OUTLIER = 4.0         # 일간 로그수익률 |z| > 4 를 이상치로 '표시'만 한다
TEST_DAYS = 30          # 베이스라인 예측 검증 구간
S = {}                  # summary.json 으로 남길 숫자


def r2(x, n=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


# ---------------------------------------------------------------- 1. 불러오기와 기본 정보
def load_ohlc(sym: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(RAW, f"coinbase_{sym}_usd_1d.csv"), parse_dates=["date"])
    return df.set_index("date").sort_index()


def basic_info(df: pd.DataFrame, name: str) -> dict:
    full = pd.date_range(df.index.min(), df.index.max(), freq="D")
    missing_days = full.difference(df.index)
    bad = (df["high"] < df["low"]) | (df["close"] > df["high"]) | (df["close"] < df["low"]) | (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
    # 빈 날이 이어진 구간
    gaps = []
    if len(missing_days):
        s = pd.Series(1, index=missing_days)
        grp = (s.index.to_series().diff() != pd.Timedelta(days=1)).cumsum()
        for _, g in s.groupby(grp):
            gaps.append((g.index[0].strftime("%Y-%m-%d"), g.index[-1].strftime("%Y-%m-%d"), len(g)))
    info = {
        "rows": int(len(df)), "start": df.index.min().strftime("%Y-%m-%d"), "end": df.index.max().strftime("%Y-%m-%d"),
        "columns": list(df.columns), "na_cells": int(df.isna().sum().sum()), "duplicate_dates": int(df.index.duplicated().sum()),
        "calendar_days": int(len(full)), "missing_days": int(len(missing_days)), "gaps": gaps[:10], "n_gaps": len(gaps),
        "invalid_ohlc_rows": int(bad.sum()),
    }
    print(f"[{name}] {info['rows']}행 {info['start']}–{info['end']} · 열 {info['columns']} · 빈 칸 {info['na_cells']} · "
          f"중복 {info['duplicate_dates']} · 빠진 날 {info['missing_days']}(구간 {info['n_gaps']}) · 값 오류 {info['invalid_ohlc_rows']}")
    return info


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """날짜 재색인 → 짧은 공백만 채움 → 로그수익률·z 점수."""
    full = pd.date_range(df.index.min(), df.index.max(), freq="D")
    d = df.reindex(full)
    miss = d["close"].isna()
    run_id = (miss != miss.shift()).cumsum()
    run_len = miss.groupby(run_id).transform("sum")
    short = miss & (run_len <= FILL_MAX_GAP)
    d["filled"] = short
    d["close"] = d["close"].where(~short, d["close"].ffill())
    d["logret"] = np.log(d["close"]).diff()
    mu, sd = d["logret"].mean(), d["logret"].std()
    d["z"] = (d["logret"] - mu) / sd
    d["outlier"] = d["z"].abs() > Z_OUTLIER
    return d


btc_raw, eth_raw, xrp_raw = load_ohlc("btc"), load_ohlc("eth"), load_ohlc("xrp")
fng = pd.read_csv(os.path.join(RAW, "fear_greed_1d.csv"), parse_dates=["date"]).set_index("date").sort_index()

S["data"] = {"BTC": basic_info(btc_raw, "BTC"), "ETH": basic_info(eth_raw, "ETH"), "XRP": basic_info(xrp_raw, "XRP")}
fng_full = pd.date_range(fng.index.min(), fng.index.max(), freq="D")
S["data"]["FNG"] = {"rows": int(len(fng)), "start": fng.index.min().strftime("%Y-%m-%d"), "end": fng.index.max().strftime("%Y-%m-%d"),
                    "missing_days": int(len(fng_full.difference(fng.index))), "na_cells": int(fng.isna().sum().sum())}
print(f"[FNG] {S['data']['FNG']}")

btc, eth, xrp = prepare(btc_raw), prepare(eth_raw), prepare(xrp_raw)
fng = fng.reindex(fng_full)
fng["value"] = fng["value"].ffill(limit=FILL_MAX_GAP)
fng["classification"] = fng["classification"].ffill(limit=FILL_MAX_GAP)

out = btc[btc["outlier"]].copy()
S["outliers_btc"] = {
    "rule": f"|z| > {Z_OUTLIER} (일간 로그수익률, 전체 기간 평균·표준편차 기준). 지우지 않고 표시만 함",
    "count": int(len(out)),
    "events": [{"date": i.strftime("%Y-%m-%d"), "return_pct": r2((np.exp(v) - 1) * 100), "z": r2(z)} for i, v, z in zip(out.index, out["logret"], out["z"])],
    "filled_days": int(btc["filled"].sum()),
}
out.reset_index(names="date")[["date", "close", "logret", "z"]].to_csv(os.path.join(OUT, "btc_outliers.csv"), index=False)

# ---------------------------------------------------------------- 2. 추세: 이동평균·교차·반감기 (질문 1)
btc["ma50"] = btc["close"].rolling(50).mean()
btc["ma200"] = btc["close"].rolling(200).mean()
sign = np.sign(btc["ma50"] - btc["ma200"])
cross = sign.diff().fillna(0)
golden = btc.index[(cross > 0) & sign.shift().notna() & (sign.shift() != 0)]
dead = btc.index[(cross < 0) & sign.shift().notna() & (sign.shift() != 0)]
btc["fwd30"] = btc["close"].shift(-30) / btc["close"] - 1
above = btc["close"] > btc["ma200"]
valid = btc["ma200"].notna() & btc["fwd30"].notna()
S["trend"] = {
    "golden_cross": [d.strftime("%Y-%m-%d") for d in golden],
    "dead_cross": [d.strftime("%Y-%m-%d") for d in dead],
    "share_days_above_ma200_pct": r2(above[btc["ma200"].notna()].mean() * 100, 1),
    "fwd30_above_ma200": {"n": int((valid & above).sum()), "mean_pct": r2(btc.loc[valid & above, "fwd30"].mean() * 100),
                           "median_pct": r2(btc.loc[valid & above, "fwd30"].median() * 100),
                           "pos_share_pct": r2((btc.loc[valid & above, "fwd30"] > 0).mean() * 100, 1)},
    "fwd30_below_ma200": {"n": int((valid & ~above).sum()), "mean_pct": r2(btc.loc[valid & ~above, "fwd30"].mean() * 100),
                           "median_pct": r2(btc.loc[valid & ~above, "fwd30"].median() * 100),
                           "pos_share_pct": r2((btc.loc[valid & ~above, "fwd30"] > 0).mean() * 100, 1)},
    "last_close": r2(btc["close"].iloc[-1]), "last_ma50": r2(btc["ma50"].iloc[-1]), "last_ma200": r2(btc["ma200"].iloc[-1]),
    "last_date": btc.index[-1].strftime("%Y-%m-%d"),
}
yearly = btc["close"].resample("YE").last().pct_change() * 100
S["trend"]["yearly_return_pct"] = {str(k.year): r2(v, 1) for k, v in yearly.dropna().items()}

halv = []
hdates = [pd.Timestamp(d) for d in HALVINGS]
PEAK_WINDOW = 730  # 반감기 뒤 2년 안의 최고 종가를 그 주기의 꼭지로 본다
for i, h in enumerate(hdates):
    nxt = hdates[i + 1] if i + 1 < len(hdates) else btc.index[-1] + pd.Timedelta(days=1)
    seg = btc.loc[h:nxt - pd.Timedelta(days=1), "close"]
    win = btc.loc[h:h + pd.Timedelta(days=PEAK_WINDOW), "close"]
    p0 = btc.loc[h, "close"]
    p365 = btc["close"].get(h + pd.Timedelta(days=365), np.nan)
    peak_day = win.idxmax()
    trough_after_peak = seg.loc[peak_day:].min()
    halv.append({"halving": h.strftime("%Y-%m-%d"), "price": r2(p0), "ret_365d_pct": r2((p365 / p0 - 1) * 100, 1),
                 "peak_date": peak_day.strftime("%Y-%m-%d"), "days_to_peak": int((peak_day - h).days),
                 "ret_to_peak_pct": r2((win.max() / p0 - 1) * 100, 1),
                 "drawdown_after_peak_pct": r2((trough_after_peak / win.max() - 1) * 100, 1),
                 "trough_date": seg.loc[peak_day:].idxmin().strftime("%Y-%m-%d"),
                 "window_end": seg.index[-1].strftime("%Y-%m-%d"), "peak_window_days": PEAK_WINDOW})
S["halvings"] = halv

fig, ax = plt.subplots(figsize=(12, 5.5))
ax.plot(btc.index, btc["close"], color="#222", lw=0.9, label="종가")
ax.plot(btc.index, btc["ma50"], color="#1f77b4", lw=1.2, label="50일 이동평균")
ax.plot(btc.index, btc["ma200"], color="#d62728", lw=1.4, label="200일 이동평균")
ax.scatter(golden, btc.loc[golden, "ma50"], marker="^", color="#2ca02c", s=60, zorder=5, label=f"골든크로스({len(golden)}회)")
ax.scatter(dead, btc.loc[dead, "ma50"], marker="v", color="#9467bd", s=60, zorder=5, label=f"데드크로스({len(dead)}회)")
for h, lab in HALVINGS.items():
    ax.axvline(pd.Timestamp(h), color="#ff7f0e", ls="--", lw=1)
    ax.text(pd.Timestamp(h), btc["close"].min() * 1.15, f" {lab} ({h})", color="#ff7f0e", rotation=90, va="bottom", ha="right", fontsize=9)
ax.set_yscale("log")
ax.set_title(f"비트코인 일봉 종가(로그 축)와 50·200일 이동평균 · 코인베이스 BTC-USD · {S['data']['BTC']['start']}–{S['data']['BTC']['end']}")
ax.set_ylabel("USD (로그 축)")
ax.legend(loc="lower right", fontsize=9)
ax.grid(alpha=0.3, which="both")
fig.savefig(os.path.join(IMG, "01_btc_price_ma.png"))
plt.close(fig)

# ---------------------------------------------------------------- 3. 변동성과 공포탐욕 (질문 2)
btc["vol30"] = btc["logret"].rolling(30).std() * np.sqrt(365) * 100
j = btc[["vol30", "logret", "fwd30", "close"]].join(fng[["value", "classification"]], how="inner").dropna(subset=["value"])
S["volatility"] = {
    "vol30_by_year_mean_pct": {str(y): r2(v, 1) for y, v in btc["vol30"].groupby(btc.index.year).mean().items() if not np.isnan(v)},
    "vol30_last_pct": r2(btc["vol30"].iloc[-1], 1),
    "vol30_max": {"date": btc["vol30"].idxmax().strftime("%Y-%m-%d"), "pct": r2(btc["vol30"].max(), 1)},
    "corr_vol30_vs_fng": r2(j["vol30"].corr(j["value"]), 3),
    "corr_vol30_vs_fng_distance_from_50": r2(j["vol30"].corr((j["value"] - 50).abs()), 3),
    "overlap_days": int(len(j)),
}
fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 6.5), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
a1.plot(btc.index, btc["vol30"], color="#d62728", lw=0.9)
a1.set_ylabel("30일 변동성(연율, %)")
a1.set_title("비트코인 30일 변동성(일간 로그수익률 표준편차 × √365)과 공포탐욕 지수")
a1.grid(alpha=0.3)
a2.plot(fng.index, fng["value"], color="#555", lw=0.6)
a2.fill_between(fng.index, 0, 100, where=fng["value"] <= 25, color="#d62728", alpha=0.15, label="극단적 공포(≤25)")
a2.fill_between(fng.index, 0, 100, where=fng["value"] >= 76, color="#2ca02c", alpha=0.15, label="극단적 탐욕(≥76)")
a2.set_ylim(0, 100)
a2.set_ylabel("공포탐욕 지수(0–100)")
a2.legend(loc="upper left", fontsize=9)
a2.grid(alpha=0.3)
a2.set_xlim(pd.Timestamp("2018-01-01"), btc.index[-1])
fig.savefig(os.path.join(IMG, "02_volatility_fear_greed.png"))
plt.close(fig)

# ---------------------------------------------------------------- 4. 계절성: 월·요일 (질문 3)
monthly = btc["close"].resample("ME").last().pct_change() * 100
monthly = monthly.loc["2016-01-01":]
mt = pd.DataFrame({"y": monthly.index.year, "m": monthly.index.month, "r": monthly.values}).dropna()
heat = mt.pivot(index="y", columns="m", values="r")
heat.to_csv(os.path.join(OUT, "btc_monthly_returns_pct.csv"))
by_month = mt.groupby("m")["r"].agg(["mean", "median", "std", "count"])
by_month["pos_share"] = mt.groupby("m")["r"].apply(lambda s: (s > 0).mean() * 100)
wd = btc["logret"].dropna()
wd = wd.loc["2016-01-01":]
by_wd = wd.groupby(wd.index.dayofweek).agg(["mean", "std", "count"])
by_wd["ci95"] = 1.96 * by_wd["std"] / np.sqrt(by_wd["count"])
WD = ["월", "화", "수", "목", "금", "토", "일"]
all_mean = wd.mean()
wd_diff_from_all = ((by_wd["mean"] - by_wd["ci95"]) > all_mean) | ((by_wd["mean"] + by_wd["ci95"]) < all_mean)
# 요일 차이가 있는지 한 번에 보는 일원분산분석 F 통계량(직접 계산). F가 1에 가까우면 요일 간 차이가 우연 수준이다
grand = wd.mean()
ss_between = (by_wd["count"] * (by_wd["mean"] - grand) ** 2).sum()
ss_within = ((wd - wd.groupby(wd.index.dayofweek).transform("mean")) ** 2).sum()
F_wd = (ss_between / 6) / (ss_within / (len(wd) - 7))
S["seasonality"] = {
    "weekday_overall_mean_pct": r2(all_mean * 100, 3),
    "weekday_ci_excluding_overall_mean": [WD[int(k)] for k, v in wd_diff_from_all.items() if v],
    "weekday_anova_F": r2(F_wd, 2), "weekday_anova_df": [6, int(len(wd) - 7)],
    "monthly": {int(m): {"mean_pct": r2(r["mean"], 1), "median_pct": r2(r["median"], 1), "pos_share_pct": r2(r["pos_share"], 0), "n": int(r["count"])}
                for m, r in by_month.iterrows()},
    "weekday_mean_daily_logret_pct": {WD[int(k)]: {"mean": r2(r["mean"] * 100, 3), "ci95": r2(r["ci95"] * 100, 3), "n": int(r["count"])}
                                      for k, r in by_wd.iterrows()},
    "weekday_ci_all_include_zero": bool(((by_wd["mean"] - by_wd["ci95"]) < 0).all() and ((by_wd["mean"] + by_wd["ci95"]) > 0).all()),
    "daily_std_pct": r2(wd.std() * 100, 2),
}
fig, ax = plt.subplots(figsize=(12, 6))
vmax = np.nanpercentile(np.abs(heat.values), 95)
im = ax.imshow(heat.values, cmap="RdYlGn", vmin=-vmax, vmax=vmax, aspect="auto")
ax.set_xticks(range(12), [f"{m}월" for m in range(1, 13)])
ax.set_yticks(range(len(heat.index)), heat.index)
for yi in range(heat.shape[0]):
    for mi in range(heat.shape[1]):
        v = heat.values[yi, mi]
        if not np.isnan(v):
            ax.text(mi, yi, f"{v:.0f}", ha="center", va="center", fontsize=8, color="black")
ax.set_title("비트코인 월별 수익률(%) · 월말 종가 기준 · 2016–2026")
fig.colorbar(im, ax=ax, label="월 수익률(%)")
fig.savefig(os.path.join(IMG, "03_monthly_returns_heatmap.png"))
plt.close(fig)

fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6))
a1.bar(range(7), by_wd["mean"] * 100, yerr=by_wd["ci95"] * 100, color="#1f77b4", capsize=4)
a1.axhline(0, color="#333", lw=0.8)
a1.axhline(all_mean * 100, color="#d62728", ls="--", lw=1, label=f"전체 평균 {all_mean * 100:.2f}%")
a1.legend(fontsize=9, loc="lower left")
a1.set_xticks(range(7), WD)
a1.set_title(f"요일별 평균 일간 수익률(%) · 오차막대 = 95% 신뢰구간 · F={F_wd:.2f}")
a1.grid(alpha=0.3, axis="y")
a2.bar(by_month.index, by_month["median"], color="#ff7f0e", label="중앙값")
a2.plot(by_month.index, by_month["mean"], "ko--", ms=4, label="평균")
a2.axhline(0, color="#333", lw=0.8)
a2.set_xticks(range(1, 13), [f"{m}" for m in range(1, 13)])
a2.set_xlabel("월")
a2.set_title("월별 수익률(%) 중앙값·평균 · 해마다 n=10–11")
a2.legend(fontsize=9)
a2.grid(alpha=0.3, axis="y")
fig.savefig(os.path.join(IMG, "04_weekday_month_effects.png"))
plt.close(fig)

# ---------------------------------------------------------------- 5. 공포탐욕 구간 뒤 30일 수익률 (질문 4)
ORDER = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]
KO = {"Extreme Fear": "극단적 공포", "Fear": "공포", "Neutral": "중립", "Greed": "탐욕", "Extreme Greed": "극단적 탐욕"}
jj = j.dropna(subset=["fwd30"])
grp = jj.groupby("classification")["fwd30"]
fwd_tbl = pd.DataFrame({"n": grp.count(), "mean_pct": grp.mean() * 100, "median_pct": grp.median() * 100,
                        "pos_share_pct": grp.apply(lambda s: (s > 0).mean() * 100)}).reindex(ORDER)
base = {"n": int(len(jj)), "mean_pct": r2(jj["fwd30"].mean() * 100), "median_pct": r2(jj["fwd30"].median() * 100),
        "pos_share_pct": r2((jj["fwd30"] > 0).mean() * 100, 1)}
# 겹치는 30일 창 때문에 독립 표본 수는 훨씬 적다: '구간 시작'(연속된 같은 분류의 첫날)만 센 수도 남긴다
first_day = jj["classification"] != jj["classification"].shift()
S["fear_greed_forward"] = {
    "by_class": {KO[k]: {"n_days": int(r["n"]), "n_episodes": int((first_day & (jj["classification"] == k)).sum()),
                         "mean_pct": r2(r["mean_pct"]), "median_pct": r2(r["median_pct"]), "pos_share_pct": r2(r["pos_share_pct"], 1)}
                 for k, r in fwd_tbl.iterrows()},
    "all_days": base,
    "note": "30일 뒤 수익률 창이 서로 겹치므로 날 수(n_days)는 독립 표본 수가 아니다",
}
fig, ax = plt.subplots(figsize=(11, 4.8))
data_box = [jj.loc[jj["classification"] == k, "fwd30"] * 100 for k in ORDER]
bp = ax.boxplot(data_box, showfliers=False, patch_artist=True, widths=0.55)
cols = ["#d62728", "#ff9896", "#c7c7c7", "#98df8a", "#2ca02c"]
for patch, c in zip(bp["boxes"], cols):
    patch.set_facecolor(c)
ax.axhline(base["median_pct"], color="#1f77b4", ls="--", lw=1, label=f"전체 중앙값 {base['median_pct']:.1f}%")
ax.set_xticks(range(1, 6), [f"{KO[k]}\n날 수 {int(fwd_tbl.loc[k, 'n'])} · 중앙 {fwd_tbl.loc[k, 'median_pct']:.1f}%\n오른 비율 {fwd_tbl.loc[k, 'pos_share_pct']:.0f}%"
                            for k in ORDER], fontsize=9)
ax.set_ylabel("30일 뒤 수익률(%)")
ax.set_title("공포탐욕 분류별, 그날 산 경우 30일 뒤 수익률 분포(상자 = 25–75%, 수염 = 1.5 IQR)")
ax.legend(loc="lower right", fontsize=9)
ax.grid(alpha=0.3, axis="y")
fig.savefig(os.path.join(IMG, "05_fear_greed_forward_returns.png"))
plt.close(fig)

# ---------------------------------------------------------------- 6. 보너스 A: 고전 분해(주간 로그가격, 주기 52주)
wk = np.log(btc["close"].resample("W-SUN").last().loc["2016-01-01":])
trend = wk.rolling(52, center=True).mean().rolling(2).mean().shift(-1)  # 2×52 중심 이동평균
detr = wk - trend
woy = pd.Series(np.minimum(wk.index.isocalendar().week.values, 52), index=wk.index)
seas_idx = detr.groupby(woy).mean()
seas_idx = seas_idx - seas_idx.mean()
seasonal = woy.map(seas_idx)
resid = wk - trend - seasonal
ok = resid.notna()
f_seas = max(0.0, 1 - resid[ok].var() / (seasonal[ok] + resid[ok]).var())
f_trend = max(0.0, 1 - resid[ok].var() / (trend[ok] + resid[ok]).var())
S["decomposition"] = {
    "series": "주간 마지막 종가의 자연로그, 2016-01–2026-10",
    "method": "고전 가법 분해: 추세 = 2×52주 중심 이동평균, 계절 = 연중 주차별 평균 편차(합 0), 잔차 = 나머지",
    "seasonal_strength": r2(f_seas, 3), "trend_strength": r2(f_trend, 3),
    "seasonal_amplitude_pct": r2((np.exp(seas_idx.max() - seas_idx.min()) - 1) * 100, 1),
    "resid_std_pct": r2(resid[ok].std() * 100, 1),
    "seasonal_peak_week": int(seas_idx.idxmax()), "seasonal_trough_week": int(seas_idx.idxmin()),
}
fig, axs = plt.subplots(4, 1, figsize=(12, 9), sharex=True)
for a, s, t, c in zip(axs, [wk, trend, seasonal, resid], ["관측값(로그 가격)", "추세(2×52주 이동평균)", "계절(연중 주차 평균, 합 0)", "잔차(노이즈)"],
                      ["#222", "#d62728", "#1f77b4", "#7f7f7f"]):
    a.plot(s.index, s.values, color=c, lw=1)
    a.set_ylabel(t, fontsize=9)
    a.grid(alpha=0.3)
axs[0].set_title(f"보너스 A · 비트코인 주간 로그가격 고전 분해 · 계절 강도 {f_seas:.2f}, 추세 강도 {f_trend:.2f} (0–1, 클수록 뚜렷)")
fig.savefig(os.path.join(IMG, "06_decomposition.png"))
plt.close(fig)

# ---------------------------------------------------------------- 7. 보너스 B: 베이스라인 예측(마지막 30일)
cl = btc["close"].dropna()
train, test = cl.iloc[:-TEST_DAYS], cl.iloc[-TEST_DAYS:]
h = np.arange(1, TEST_DAYS + 1)
last = train.iloc[-1]
drift_daily = (np.log(train.iloc[-1]) - np.log(train.iloc[-366])) / 365
fc = {
    "그대로(naive)": pd.Series(last, index=test.index),
    "추세 연장(drift, 지난 1년 기울기)": pd.Series(last * np.exp(drift_daily * h), index=test.index),
    "7일 평균": pd.Series(train.iloc[-7:].mean(), index=test.index),
    "주간 반복(seasonal naive, 7일)": pd.Series(np.resize(train.iloc[-7:].values, TEST_DAYS), index=test.index),
}
metrics = {}
for k, f in fc.items():
    err = test - f
    metrics[k] = {"MAE_usd": r2(err.abs().mean(), 0), "MAPE_pct": r2((err.abs() / test).mean() * 100, 2),
                  "end_error_pct": r2((f.iloc[-1] / test.iloc[-1] - 1) * 100, 2)}
best = min(metrics, key=lambda k: metrics[k]["MAE_usd"])

# 한 구간만 보면 우연일 수 있다 → 지난 24개월을 30일씩 옮겨 가며 같은 방법을 다시 잰다(rolling origin)
def _forecasts(tr: pd.Series, idx: pd.DatetimeIndex) -> dict:
    hh = np.arange(1, len(idx) + 1)
    lv = tr.iloc[-1]
    dr = (np.log(tr.iloc[-1]) - np.log(tr.iloc[-366])) / 365
    return {"그대로(naive)": np.full(len(idx), lv), "추세 연장(drift, 지난 1년 기울기)": lv * np.exp(dr * hh),
            "7일 평균": np.full(len(idx), tr.iloc[-7:].mean()), "주간 반복(seasonal naive, 7일)": np.resize(tr.iloc[-7:].values, len(idx))}


roll = {k: [] for k in fc}
wins = {k: 0 for k in fc}
N_WIN = 24
for w in range(N_WIN):
    end = len(cl) - w * TEST_DAYS
    tr_w, te_w = cl.iloc[:end - TEST_DAYS], cl.iloc[end - TEST_DAYS:end]
    f_w = _forecasts(tr_w, te_w.index)
    mape_w = {k: float((np.abs(te_w.values - v) / te_w.values).mean() * 100) for k, v in f_w.items()}
    for k, v in mape_w.items():
        roll[k].append(v)
    wins[min(mape_w, key=mape_w.get)] += 1
rolling = {k: {"mean_MAPE_pct": r2(np.mean(v), 2), "median_MAPE_pct": r2(np.median(v), 2), "wins": wins[k]} for k, v in roll.items()}
pd.DataFrame(roll).to_csv(os.path.join(OUT, "forecast_rolling_mape.csv"), index=False)
S["forecast"] = {"rolling_origin": {"windows": N_WIN, "window_days": TEST_DAYS, "by_method": rolling,
                                    "best_by_mean_MAPE": min(rolling, key=lambda k: rolling[k]["mean_MAPE_pct"])},"train_end": train.index[-1].strftime("%Y-%m-%d"), "test": f"{test.index[0]:%Y-%m-%d}–{test.index[-1]:%Y-%m-%d}",
                 "test_days": TEST_DAYS, "metrics": metrics, "best_by_MAE": best,
                 "test_actual_change_pct": r2((test.iloc[-1] / last - 1) * 100, 2), "drift_daily_pct": r2(drift_daily * 100, 3)}
fig, ax = plt.subplots(figsize=(12, 5))
hist = train.iloc[-120:]
ax.plot(hist.index, hist.values, color="#222", lw=1.2, label="학습 구간(마지막 120일)")
ax.plot(test.index, test.values, color="#000", lw=2.2, label="실제(검증 30일)")
for (k, f), c in zip(fc.items(), ["#1f77b4", "#d62728", "#2ca02c", "#9467bd"]):
    ax.plot(f.index, f.values, ls="--", lw=1.5, color=c, label=f"{k} · MAE ${metrics[k]['MAE_usd']:,.0f} · MAPE {metrics[k]['MAPE_pct']:.1f}%")
ax.axvline(test.index[0], color="#999", ls=":")
ax.set_title(f"보너스 B · 베이스라인 예측 4가지와 실제 비교 · 검증 {S['forecast']['test']}")
ax.set_ylabel("USD")
ax.legend(fontsize=8.5, loc="upper left")
ax.grid(alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
fig.savefig(os.path.join(IMG, "07_baseline_forecast.png"))
plt.close(fig)

# ---------------------------------------------------------------- 8. 코인 비교(BTC·ETH·XRP)와 결측 구간
def mdd(c: pd.Series) -> tuple[float, str, str]:
    c = c.dropna()
    dd = c / c.cummax() - 1
    end = dd.idxmin()
    start = c.loc[:end].idxmax()
    return float(dd.min()), start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


rets = pd.DataFrame({"BTC": btc["logret"], "ETH": eth["logret"], "XRP": xrp["logret"]}).loc["2019-02-27":]
corr = rets.corr()
comp = {}
for name, d in [("BTC", btc), ("ETH", eth), ("XRP", xrp)]:
    m, s0, s1 = mdd(d["close"])
    comp[name] = {"ann_vol_pct": r2(d["logret"].std() * np.sqrt(365) * 100, 1), "max_drawdown_pct": r2(m * 100, 1),
                  "mdd_peak": s0, "mdd_trough": s1, "rows": int(d["close"].notna().sum())}
xrp_gaps = S["data"]["XRP"]["gaps"]
S["compare"] = {"daily_return_corr_since_2019_02": {a: {b: r2(corr.loc[a, b], 2) for b in corr.columns} for a in corr.index},
                "stats": comp, "xrp_long_gap": max(xrp_gaps, key=lambda g: g[2]) if xrp_gaps else None}
fig, ax = plt.subplots(figsize=(12, 5))
base_day = pd.Timestamp("2019-02-26")
for name, d, c in [("BTC", btc, "#f7931a"), ("ETH", eth, "#627eea"), ("XRP", xrp, "#23292f")]:
    s = d["close"].loc[base_day:]
    ax.plot(s.index, s / s.dropna().iloc[0] * 100, color=c, lw=1, label=name)
if S["compare"]["xrp_long_gap"]:
    g0, g1, _ = S["compare"]["xrp_long_gap"]
    ax.axvspan(pd.Timestamp(g0), pd.Timestamp(g1), color="#999", alpha=0.2, label=f"XRP 자료 없음 {g0}–{g1}")
ax.set_yscale("log")
ax.set_ylabel("2019-02-26 = 100 (로그 축)")
ax.set_title("세 코인 누적 흐름 비교(코인베이스 일봉) · 회색 = 코인베이스 XRP 거래 중단으로 빈 구간")
ax.legend(fontsize=9)
ax.grid(alpha=0.3, which="both")
fig.savefig(os.path.join(IMG, "08_coin_compare.png"))
plt.close(fig)

with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(S, f, ensure_ascii=False, indent=1)
print("그림:", sorted(os.listdir(IMG)))
print("요약: outputs/summary.json")
