#!/usr/bin/env python3
"""소피아 평가 세트 채점 스크립트 (P1). 표준 라이브러리만 사용.

입력
  --questions  질문 jsonl (기본 eval/sophia_questions_v2.jsonl). v1 파일도 됨(없는 필드는 빈 값).
  --answers    답변 jsonl. 한 줄에 {"id", "answer", "cited_sources": [...]} (cited_paths도 인정).
               cited_sources가 없으면 답변 본문에서 경로·파일명을 정규식으로 뽑는다.
출력
  eval/results/<YYYY-MM-DD>_<tag>.csv  (열: rubric.md 5절 형식)
  eval/results/<YYYY-MM-DD>_<tag>.md   (한국어 요약: 전체·유형별·합격 여부·환각·짝 문항 단서 효과·난이도·이전 실행 비교)

채점 흐름 (rubric.md 1·2·5절)
  1. 기계 검사: 인용 경로 존재(NFC 정규화 뒤 test -e), gold_sources 일치, 회차 토큰(철학사N_NN) 존재,
     인용문(따옴표 안 12자 이상)이 인용 파일에 있는지, 타임스탬프 ±2분. 걸리면 hallucinated_citation=1, 0점.
  2. 내용 채점: (a) 규칙 기반 키워드 매칭(기본) → points_hit, 해석형 3항목.
               (b) LLM 판정 훅 judge_llm() — 자리만 있음. --judge none 기본, --judge llm 은 아직 미구현.
  3. 점수 환산: 사실형/다중 연결형 0·1·2, 해석형은 근거+추론+반론 합계(0–6)를 0·1·2로.

지식 파일은 읽기만 한다. 질문 파일·지식 파일을 고치지 않는다.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUESTIONS = ROOT / "eval" / "sophia_questions_v2.jsonl"
DEFAULT_RESULTS_DIR = ROOT / "eval" / "results"

CSV_COLUMNS = [
    "id", "type", "pair_id", "cue", "score", "points_hit", "points_total",
    "citation_ok", "hallucinated_citation", "grounding", "reasoning", "counter_view",
    "judge", "notes",
]

PASS_LINE = {"all": 0.70, "fact": 0.80, "multi_hop": 0.60, "interpretation": 0.60}
MAX_HALLUCINATION = 2
TYPE_LABEL = {"fact": "사실형", "multi_hop": "다중 연결형", "interpretation": "해석형"}

# ---------- 문자열 도우미 ----------

def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def squash(s: str) -> str:
    """공백·문장부호를 지운 비교용 문자열(NFC)."""
    s = nfc(s)
    return re.sub(r"[\s\W_]+", "", s, flags=re.UNICODE).lower()


STOP = {"것은", "것이", "무엇", "것을", "대한", "대해", "있다", "없다", "한다", "하는", "되는", "에서", "으로",
        "그리고", "또는", "이다", "있음", "없음", "강의", "설명", "내용", "질문", "답변", "것", "수", "등"}


def keywords(text: str) -> list[str]:
    """정답 포인트에서 비교용 핵심어를 뽑는다. 한글 2자 이상·숫자·라틴 단어. 조사 꼬리는 대충 자른다."""
    text = nfc(text)
    toks = re.findall(r"[가-힣]{2,}|[A-Za-z][A-Za-z\-]{1,}|\d{2,}", text)
    out = []
    for t in toks:
        if re.match(r"[가-힣]", t):
            t = re.sub(r"(으로|에서|에게|부터|까지|이라고|라고|처럼|이란|란|은|는|이|가|을|를|의|에|로|와|과|도|들)$", "", t)
            if len(t) < 2:
                continue
        t = t.lower()
        if t in STOP or t in out:
            continue
        out.append(t)
    return out


def point_hit(point: str, answer_sq: str, ratio: float = 0.5) -> tuple[bool, float]:
    """핵심어의 ratio 이상이 답변에 있으면 포인트 충족. (hit, 비율) 반환."""
    def _ratio(text: str) -> float:
        kws = keywords(text)
        if not kws:
            return 0.0
        n = sum(1 for k in kws if squash(k) and squash(k) in answer_sq)
        return n / len(kws)

    full = _ratio(point)
    # 괄호 안은 보충 설명이므로, 괄호 앞 머리 부분만 맞아도 충족으로 본다
    head = re.split(r"[(（]", point, maxsplit=1)[0]
    head_r = _ratio(head) if head.strip() != point.strip() else full
    best = max(full, head_r)
    return best >= ratio, best


# ---------- 파일·인용 ----------

PATH_RE = re.compile(r"(?<![\w/])(/[^\s`'\"<>()\[\]]+?\.(?:md|txt|pdf|csv|jsonl|json))")
BACKTICK_FILE_RE = re.compile(r"`([^`/\n]+?\.(?:md|txt|pdf))`")
EPISODE_RE = re.compile(r"(철학사\d_\d{2}(?:_\d{2}-\d{2})?|예술철학(?:토론)?_[\d\-]+(?:_\d{2}-\d{2})?)")
QUOTE_RE = re.compile(r"[\"“]([^\"”\n]{12,}?)[\"”]")
TS_RE = re.compile(r"\[(\d{2}):(\d{2}):(\d{2})\]")
GENERAL_TAG = "[일반 지식]"


def extract_cited(answer: str) -> list[str]:
    found = PATH_RE.findall(answer) + BACKTICK_FILE_RE.findall(answer)
    seen, out = set(), []
    for f in found:
        f = nfc(f.strip())
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def _resolve_one(cited: str, name_map: dict[str, str]) -> tuple[str | None, bool]:
    """인용 문자열 → (실제 경로 또는 None, 존재 여부). 파일 이름만 적은 경우 대응표로 바꾼다."""
    c = nfc(cited.strip().rstrip(".,;:)"))
    if c.startswith("/"):
        for cand in (c, unicodedata.normalize("NFD", c)):
            if os.path.exists(cand):
                return c, True
        return c, False
    base = nfc(os.path.basename(c))
    if base in name_map:
        return name_map[base], True
    return c, False


def build_name_map(questions: list[dict]) -> dict[str, str]:
    m: dict[str, str] = {}
    for q in questions:
        for s in q.get("gold_sources", []):
            m[nfc(os.path.basename(s))] = nfc(s)
    return m


_FILE_CACHE: dict[str, str] = {}


def read_file(path: str) -> str:
    if path in _FILE_CACHE:
        return _FILE_CACHE[path]
    text = ""
    for cand in (path, unicodedata.normalize("NFD", path)):
        try:
            text = Path(cand).read_text(encoding="utf-8", errors="ignore")
            break
        except OSError:
            continue
    _FILE_CACHE[path] = text
    return text


def quote_found(quote: str, text_sq: str, text_raw: str) -> bool:
    q = squash(quote)
    if q and q in text_sq:
        return True
    kws = keywords(quote)
    n = sum(1 for k in kws if squash(k) in text_sq)
    return n >= 3


def machine_check(q: dict, answer: str, cited: list[str], name_map: dict[str, str]) -> dict:
    """환각 인용·인용 적합성 검사. 결과 dict: resolved, exists, gold_hit, hallucinated, reasons, readme_only."""
    gold = [nfc(s) for s in q.get("gold_sources", [])]
    reasons: list[str] = []
    resolved, exists_list = [], []
    for c in cited:
        p, ok = _resolve_one(c, name_map)
        if p is None:
            continue
        resolved.append(p)
        exists_list.append(ok)
        if not ok:
            reasons.append(f"없는 경로: {c}")
    gold_hit = sorted({p for p, ok in zip(resolved, exists_list) if ok and p in gold})
    existing = [p for p, ok in zip(resolved, exists_list) if ok]

    # 회차 토큰: 질문 세트 전체의 파일 이름에서 아는 회차만 인정
    known_eps = {m for n in name_map for m in EPISODE_RE.findall(n)}
    known_stems = {nfc(os.path.splitext(n)[0]) for n in name_map}
    for ep in set(EPISODE_RE.findall(nfc(answer))):
        if ep in known_eps or any(st.startswith(ep) for st in known_stems):
            continue
        reasons.append(f"없는 회차 표기: {ep}")

    # 인용문·타임스탬프: 인용한 실제 파일 안에서 찾는다
    if existing:
        texts = {p: read_file(p) for p in existing}
        sqs = {p: squash(t) for p, t in texts.items()}
        for m in QUOTE_RE.finditer(answer):
            before = answer[max(0, m.start() - 60):m.start()]
            after = answer[m.end():m.end() + 40]
            if GENERAL_TAG in before or GENERAL_TAG in after:
                continue
            quote = m.group(1)
            if not any(quote_found(quote, sqs[p], texts[p]) for p in existing):
                reasons.append(f"자료에 없는 인용문: “{quote[:30]}…”")
        ts_in_files = set()
        for t in texts.values():
            ts_in_files.update(int(h) * 3600 + int(mi) * 60 + int(s) for h, mi, s in TS_RE.findall(t))
        if ts_in_files:
            for h, mi, s in TS_RE.findall(answer):
                sec = int(h) * 3600 + int(mi) * 60 + int(s)
                if not any(abs(sec - x) <= 120 for x in ts_in_files):
                    reasons.append(f"자료에 없는 타임스탬프: [{h}:{mi}:{s}]")

    readme_only = bool(existing) and all(os.path.basename(p) == "README.md" for p in existing)
    return {
        "resolved": resolved,
        "existing": existing,
        "gold_hit": gold_hit,
        "hallucinated": bool(reasons),
        "reasons": reasons,
        "readme_only": readme_only,
    }


# ---------- 내용 채점 (규칙 기반) ----------

THRESH_RE = re.compile(r"(\d+)개 중 (\d+)개 이상")
CONNECT_WORDS = ["연결", "이어", "비교", "반면", "대비", "따라서", "그러므로", "즉", "겹치", "다른 점", "공통", "차이",
                 "계승", "비판", "영향", "대조", "한편"]
COUNTER_WORDS = ["반론", "반대로", "다른 해석", "반대 해석", "다르게 읽", "그러나", "하지만", "비판할 수", "반박", "이의",
                 "다른 입장", "반대 입장"]
TAGS = ["[내 자료]", "[일반 지식]", "[해석]"]


def rule_points(q: dict, answer: str) -> tuple[int, int, int, list[str]]:
    """(hit, total, required, 미충족 포인트 목록). notes의 'N개 중 M개 이상'을 허용 기준으로 쓴다."""
    pts = q.get("gold_answer_points", []) or []
    a_sq = squash(answer)
    missed = []
    hit = 0
    for p in pts:
        ok, _ = point_hit(p, a_sq)
        if ok:
            hit += 1
        else:
            missed.append(p)
    required = len(pts)
    m = THRESH_RE.search(q.get("notes", "") or "")
    if m and int(m.group(1)) == len(pts):
        required = int(m.group(2))
    return hit, len(pts), required, missed


def rule_interpretation(q: dict, answer: str, mc: dict, hit: int) -> tuple[int, int, int, list[str]]:
    """해석형 3항목(근거·추론·반론) 0/1/2. 규칙 기반 근사."""
    notes = []
    cited = bool(mc["existing"])
    # 근거
    if hit >= 2 and cited:
        g = 2
    elif hit >= 1 or (hit >= 2 and not cited):
        g = 1
    else:
        g = 0
    # 추론
    has_tag = any(t in answer for t in TAGS)
    has_interp = "[해석]" in answer
    has_connect = any(w in answer for w in CONNECT_WORDS)
    if has_interp and has_connect:
        r = 2
    elif has_connect or has_tag:
        r = 1
    else:
        r = 0
    if not has_tag and r > 1:
        r = 1
        notes.append("태그 없음→추론 최대 1")
    # 반론
    has_counter = any(w in answer for w in COUNTER_WORDS)
    if has_counter and cited and len(answer) > 200:
        c = 2
    elif has_counter:
        c = 1
    else:
        c = 0
    return g, r, c, notes


def interp_to_score(total: int) -> int:
    if total >= 5:
        return 2
    if total >= 3:
        return 1
    return 0


# ---------- LLM 판정 훅 (자리만) ----------

def judge_llm(q: dict, answer: str, rubric_excerpt: str) -> dict | None:
    """LLM 판정 모드. 채점받는 모델과 다른 회사 모델을 쓴다(rubric 5절 3항).
    반환 형식: {"points_hit": int, "grounding": int, "reasoning": int, "counter_view": int, "reason": str}
    아직 미구현. 구현 시 judge_prompt.md 를 읽어 프롬프트를 만들고, 같은 입력은 캐시한다."""
    raise NotImplementedError("LLM 판정은 아직 연결되지 않았다. --judge none 으로 실행하라.")


# ---------- 문항 채점 ----------

def score_item(q: dict, ans: dict | None, name_map: dict[str, str], judge: str = "none") -> dict:
    row = {c: "" for c in CSV_COLUMNS}
    row.update({"id": q["id"], "type": q.get("type", ""), "pair_id": q.get("pair_id") or "",
                "cue": int(bool(q.get("cue", False)))})
    pts_total = len(q.get("gold_answer_points", []) or [])
    row["points_total"] = pts_total
    if ans is None:
        row.update({"score": 0, "points_hit": 0, "citation_ok": 0, "hallucinated_citation": 0,
                    "judge": "none", "notes": "답변 없음"})
        return row

    answer = ans.get("answer", "") or ""
    cited = ans.get("cited_sources") or ans.get("cited_paths") or extract_cited(answer)
    mc = machine_check(q, answer, cited, name_map)
    notes: list[str] = []
    citation_ok = int(bool(mc["gold_hit"]) or (bool(mc["existing"]) and not mc["readme_only"]))
    row["citation_ok"] = citation_ok
    row["hallucinated_citation"] = int(mc["hallucinated"])

    if mc["hallucinated"]:
        hit, total, _, _ = rule_points(q, answer)
        row.update({"score": 0, "points_hit": hit, "judge": "machine0",
                    "notes": "환각 인용 자동 0점: " + "; ".join(mc["reasons"])})
        return row

    judge_used = "rule"
    if judge == "llm":
        res = judge_llm(q, answer, "")
        if res:
            judge_used = "llm"
            hit = int(res.get("points_hit", 0))
            g, r, c = int(res.get("grounding", 0)), int(res.get("reasoning", 0)), int(res.get("counter_view", 0))
            if res.get("reason"):
                notes.append(res["reason"])
            required = pts_total
        else:
            hit, pts_total, required, missed = rule_points(q, answer)
            g = r = c = 0
    else:
        hit, pts_total, required, missed = rule_points(q, answer)
        if missed:
            notes.append("미충족 포인트: " + " / ".join(m[:25] for m in missed))
        g = r = c = 0

    row["points_hit"] = hit
    qtype = q.get("type", "fact")
    must_cite = bool(q.get("must_cite", True))
    distinct_gold = len(mc["gold_hit"])
    cited_any = bool(mc["existing"])

    if qtype == "interpretation":
        if judge_used != "llm":
            g, r, c, inotes = rule_interpretation(q, answer, mc, hit)
            notes.extend(inotes)
        total = g + r + c
        score = interp_to_score(total)
        row.update({"grounding": g, "reasoning": r, "counter_view": c})
        notes.append(f"항목 합계 {total}/6")
    elif qtype == "multi_hop":
        content_full = hit >= required and pts_total > 0
        has_connect = any(w in answer for w in CONNECT_WORDS)
        if content_full and distinct_gold >= 2 and has_connect:
            score = 2
        elif hit >= 1 or distinct_gold >= 1:
            score = 1
        else:
            score = 0
        if mc["readme_only"]:
            score = min(score, 1)
            notes.append("README 색인만 인용→최대 1")
        if content_full and distinct_gold < 2:
            notes.append(f"서로 다른 근거 파일 {distinct_gold}개(2개 필요)")
        if content_full and not has_connect:
            notes.append("연결 설명 없음(규칙 기준)")
    else:  # fact
        content_full = hit >= required and pts_total > 0
        if content_full and citation_ok:
            score = 2
        elif hit >= 1 and pts_total > 0:
            score = 1
        else:
            score = 0
        if content_full and not citation_ok:
            notes.append("내용 충족이나 근거 인용 없음")

    if must_cite and not cited_any:
        score = min(score, 1)
        if "근거 인용 없음" not in " ".join(notes):
            notes.append("must_cite 문항에 인용 없음→최대 1")
    if "내 자료에는 없" in answer or "자료에 없" in answer.replace(" ", ""):
        if hit == 0:
            score = 0
            notes.append("'자료에 없음' 답변(검색 실패)")

    row.update({"score": score, "judge": judge_used, "notes": "; ".join(notes)})
    return row


# ---------- 입출력 ----------

def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_question(q: dict) -> dict:
    q = dict(q)
    for k in ("gold_answer_points", "optional_points", "example_interpretations", "rubric_points", "gold_sources"):
        q.setdefault(k, [])
        if q[k] is None:
            q[k] = []
    q.setdefault("pair_id", None)
    q.setdefault("cue", False)
    q.setdefault("must_cite", True)
    q.setdefault("difficulty", 0)
    q.setdefault("notes", "")
    q.setdefault("type", "fact")
    return q


def score_all(questions: list[dict], answers: list[dict], judge: str = "none") -> list[dict]:
    questions = [normalize_question(q) for q in questions]
    name_map = build_name_map(questions)
    amap = {a["id"]: a for a in answers if "id" in a}
    return [score_item(q, amap.get(q["id"]), name_map, judge) for q in questions]


def pct(n: float, d: float) -> str:
    return "–" if d == 0 else f"{100 * n / d:.1f}%"


def summarize(rows: list[dict], questions: list[dict], tag: str, date: str,
              prev: tuple[str, list[dict]] | None = None, answered_only: bool = False) -> str:
    qmap = {q["id"]: normalize_question(q) for q in questions}
    use = [r for r in rows if not (answered_only and r["notes"] == "답변 없음")]
    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in use:
        by_type[r["type"]].append(r)
    total = sum(int(r["score"]) for r in use)
    denom = 2 * len(use)
    hall = [r["id"] for r in use if int(r["hallucinated_citation"] or 0) == 1]
    lines = [f"# 소피아 평가 결과 요약 — {date} {tag}", "",
             f"- 채점 문항: {len(use)} / 전체 {len(rows)}" + ("(답변 없는 문항 제외)" if answered_only else ""),
             f"- 판정 방식: {sorted({r['judge'] for r in use})}", ""]
    lines += ["## 전체·유형별 점수", "", "| 지표 | 점수 | 비율 | 합격선 | 판정 |", "|---|---:|---:|---:|---|"]

    def verdict(n, d, line):
        if d == 0:
            return "–"
        return "합격" if n / d >= line else "미달"

    lines.append(f"| 전체 | {total}/{denom} | {pct(total, denom)} | {int(PASS_LINE['all'] * 100)}% | {verdict(total, denom, PASS_LINE['all'])} |")
    for t in ("fact", "multi_hop", "interpretation"):
        rs = by_type.get(t, [])
        s, d = sum(int(r["score"]) for r in rs), 2 * len(rs)
        lines.append(f"| {TYPE_LABEL[t]} | {s}/{d} | {pct(s, d)} | {int(PASS_LINE[t] * 100)}% | {verdict(s, d, PASS_LINE[t])} |")
    hall_verdict = "합격" if len(hall) <= MAX_HALLUCINATION else "불합격(3건 이상)"
    lines.append(f"| 환각 인용 | {len(hall)}건 | – | {MAX_HALLUCINATION}건 이하 | {hall_verdict} |")
    overall = (denom > 0 and total / denom >= PASS_LINE["all"] and len(hall) <= MAX_HALLUCINATION)
    lines += ["", f"**종합 판정: {'합격' if overall else '미달'}** (전체 70% 이상 + 환각 2건 이하)", ""]
    lines += ["## 환각 인용 문항", "", ("- " + ", ".join(hall)) if hall else "- 없음", ""]

    # 짝 문항 단서 효과
    pairs: dict[str, dict[int, int]] = defaultdict(dict)
    for r in use:
        if r["pair_id"]:
            pairs[r["pair_id"]][int(r["cue"])] = int(r["score"])
    lines += ["## 짝 문항 단서 효과", "", "| 짝 | 단서 없음 | 단서 있음 | 차이 |", "|---|---:|---:|---:|"]
    diffs = []
    for pid in sorted(pairs):
        p = pairs[pid]
        if 0 in p and 1 in p:
            d = p[1] - p[0]
            diffs.append(d)
            lines.append(f"| {pid} | {p[0]} | {p[1]} | {d:+d} |")
    if diffs:
        avg = sum(diffs) / len(diffs)
        note = " → 검색 실패가 주 원인(0.5 이상)" if avg >= 0.5 else ""
        lines.append(f"| 평균 | | | {avg:+.2f}{note} |")
    else:
        lines.append("| (짝 문항 없음) | | | |")

    # 난이도별
    diff_s: dict[int, list[int]] = defaultdict(list)
    for r in use:
        diff_s[int(qmap[r["id"]].get("difficulty", 0) or 0)].append(int(r["score"]))
    lines += ["", "## 난이도별 점수", "", "| 난이도 | 문항 | 점수 | 비율 |", "|---:|---:|---:|---:|"]
    for d in sorted(diff_s):
        s, n = sum(diff_s[d]), len(diff_s[d])
        lines.append(f"| {d} | {n} | {s}/{2 * n} | {pct(s, 2 * n)} |")

    # 이전 실행 비교
    lines += ["", "## 이전 실행과 비교", ""]
    if prev:
        pname, prows = prev
        pmap = {r["id"]: r for r in prows}
        ptotal = sum(int(r["score"]) for r in prows)
        lines += [f"이전: `{pname}`", "", "| 지표 | 이전 | 이번 | 변화 |", "|---|---:|---:|---:|",
                  f"| 전체 | {ptotal} | {total} | {total - ptotal:+d} |"]
        for t in ("fact", "multi_hop", "interpretation"):
            ps = sum(int(r["score"]) for r in prows if r["type"] == t)
            cs = sum(int(r["score"]) for r in by_type.get(t, []))
            lines.append(f"| {TYPE_LABEL[t]} | {ps} | {cs} | {cs - ps:+d} |")
        changed = [f"{r['id']}({pmap[r['id']]['score']}→{r['score']})" for r in use
                   if r["id"] in pmap and str(pmap[r["id"]]["score"]) != str(r["score"])]
        lines += ["", "점수가 바뀐 문항: " + (", ".join(changed) if changed else "없음")]
    else:
        lines.append("- 이전 결과 없음")

    low = [f"{r['id']}({r['score']})" for r in use if int(r["score"]) < 2]
    lines += ["", "## 2점 미만 문항", "", ("- " + ", ".join(low)) if low else "- 없음", ""]
    lines += ["## 주의", "", "- 규칙 기반 채점(judge=rule)은 핵심어 매칭 근사치다. 해석형·연결 설명 판정은 사람 검수나 LLM 판정으로 보정한다.",
              "- 환각 검사: 경로 존재(NFC 정규화), 회차 토큰, 따옴표 인용문(핵심어 3개 이상), 타임스탬프 ±2분.", ""]
    return "\n".join(lines)


def find_previous(results_dir: Path, current_csv: Path) -> tuple[str, list[dict]] | None:
    cands = sorted(p for p in results_dir.glob("*.csv") if p.resolve() != current_csv.resolve())
    if not cands:
        return None
    p = cands[-1]
    with open(p, encoding="utf-8", newline="") as f:
        return p.name, list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_COLUMNS})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="소피아 평가 세트 채점")
    ap.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    ap.add_argument("--answers", type=Path, required=True, help="답변 jsonl ({id, answer, cited_sources[]})")
    ap.add_argument("--tag", required=True, help="결과 파일 이름 꼬리(예: claude-sonnet, orca-run1)")
    ap.add_argument("--judge", choices=["none", "llm"], default="none", help="내용 채점: none=규칙 기반, llm=판정 모델(미구현)")
    ap.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--answered-only", action="store_true", help="답변 없는 문항을 분모에서 뺀다(부분 세트)")
    args = ap.parse_args(argv)

    questions = load_jsonl(args.questions)
    answers = load_jsonl(args.answers)
    rows = score_all(questions, answers, judge=args.judge)

    csv_path = args.results_dir / f"{args.date}_{args.tag}.csv"
    md_path = args.results_dir / f"{args.date}_{args.tag}.md"
    prev = find_previous(args.results_dir, csv_path) if args.results_dir.exists() else None
    write_csv(csv_path, rows)
    md_path.write_text(summarize(rows, questions, args.tag, args.date, prev, args.answered_only), encoding="utf-8")

    total = sum(int(r["score"]) for r in rows)
    hall = sum(int(r["hallucinated_citation"] or 0) for r in rows)
    print(f"채점 완료: {len(rows)}문항, 총점 {total}/{2 * len(rows)}, 환각 {hall}건")
    print(f"CSV: {csv_path}\n요약: {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
