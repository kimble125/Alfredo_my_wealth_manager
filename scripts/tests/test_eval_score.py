"""eval_score.py 단위 시험. 가짜 질문 4개·답변 3개로 채점 경로를 검증한다.
실행(저장소 루트에서): python3 -m unittest scripts.tests.test_eval_score -v
"""
import csv
import json
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eval_score as es  # noqa: E402


class EvalScoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.know = root / "knowledge"
        self.know.mkdir()
        # NFD 파일명(건명원 노트와 같은 상황) — 디스크에는 NFD, 질문에는 NFC로 적는다
        nfd_name = unicodedata.normalize("NFD", "철학사 (6) 4.10.md")
        self.src_a = self.know / "철학사1_10.md"
        self.src_b = self.know / nfd_name
        self.src_a.write_text("[00:24:10] 데카르트는 1649년 스웨덴 크리스티나 여왕의 개인교사로 갔다. "
                              "새벽 5시 수업이 죽음으로 이어졌다.\n", encoding="utf-8")
        self.src_b.write_text("[00:10:00] 스피노자 신학정치론: 인간은 왜 예속을 갈망하는가.\n", encoding="utf-8")
        self.src_b_nfc = unicodedata.normalize("NFC", str(self.src_b))

        self.questions = [
            {"id": "T001", "type": "fact", "pair_id": "P1", "cue": False,
             "question": "데카르트 말년?",
             "gold_answer_points": ["1649년 스웨덴 크리스티나 여왕의 개인교사로 감", "새벽 5시 수업 일정이 죽음으로 이어짐"],
             "gold_sources": [str(self.src_a)], "must_cite": True, "difficulty": 1, "notes": ""},
            {"id": "T002", "type": "fact", "pair_id": "P1", "cue": True,
             "question": "스피노자 핵심 물음?",
             "gold_answer_points": ["인간은 왜 스스로 예속되기를 갈망하는가"],
             "gold_sources": [self.src_b_nfc], "must_cite": True, "difficulty": 1, "notes": ""},
            {"id": "T003", "type": "interpretation", "pair_id": None, "cue": False,
             "question": "데카르트와 스피노자를 비교해 해석?",
             "gold_answer_points": ["데카르트 스웨덴행과 새벽 수업", "스피노자 예속 갈망 물음"],
             "rubric_points": ["[해석] 표시"], "gold_sources": [str(self.src_a), self.src_b_nfc],
             "must_cite": True, "difficulty": 3, "notes": ""},
            # v1처럼 필드가 빠진 문항, 답변도 없음
            {"id": "T004", "type": "multi_hop", "question": "답 없음", "gold_answer_points": ["무엇"],
             "gold_sources": [str(self.src_a)]},
        ]
        self.answers = [
            # 1) 완전 정답 + 맞는 인용 → 2점
            {"id": "T001", "answer": "[내 자료] 1649년 스웨덴으로 가 크리스티나 여왕의 개인교사가 됐고, 새벽 5시 수업 "
                                     "일정이 죽음으로 이어졌다. 근거: " + str(self.src_a),
             "cited_sources": [str(self.src_a)]},
            # 2) 내용은 맞지만 없는 경로를 인용 → 환각 자동 0점 (인용 목록 없음 → 본문에서 추출, NFC 파일명 대응표)
            {"id": "T002", "answer": "인간은 왜 스스로 예속되기를 갈망하는가. 출처 `철학사 (6) 4.10.md` 와 "
                                     + str(self.know / "없는파일_99.md")},
            # 3) 해석형: 근거 2개 인용 + [해석] 태그 + 반론 → 2점
            {"id": "T003", "answer": "[내 자료] 데카르트는 스웨덴행 뒤 새벽 수업으로 죽음에 이르렀다(" + str(self.src_a) +
                                     "). [내 자료] 스피노자는 인간이 예속을 갈망하는 이유를 물었다(" + self.src_b_nfc + "). "
                                     "[해석] 따라서 둘은 권력과 개인의 관계를 반대 방향에서 비교한 셈이다. "
                                     "반론: 반대로 두 사례는 전기적 우연일 뿐이라는 다른 해석도 가능하며, 강의는 그 근거를 "
                                     "생애 서술에서 제공한다. 이 문장은 길이를 채우기 위한 보충 설명이며 추가 맥락을 담는다.",
             "cited_sources": [str(self.src_a), self.src_b_nfc]},
        ]
        self.rows = es.score_all(self.questions, self.answers)
        self.by_id = {r["id"]: r for r in self.rows}

    def tearDown(self):
        self.tmp.cleanup()

    def test_fact_full_score(self):
        r = self.by_id["T001"]
        self.assertEqual(r["score"], 2)
        self.assertEqual((r["points_hit"], r["points_total"]), (2, 2))
        self.assertEqual(r["citation_ok"], 1)
        self.assertEqual(r["hallucinated_citation"], 0)
        self.assertEqual(r["judge"], "rule")

    def test_hallucinated_path_is_zero(self):
        r = self.by_id["T002"]
        self.assertEqual(r["hallucinated_citation"], 1)
        self.assertEqual(r["score"], 0)
        self.assertEqual(r["judge"], "machine0")
        self.assertIn("없는 경로", r["notes"])
        self.assertEqual(r["points_hit"], 1)  # 내용은 맞았음을 기록

    def test_nfc_name_map_resolves_nfd_file(self):
        qs = [es.normalize_question(q) for q in self.questions]
        name_map = es.build_name_map(qs)
        path, ok = es._resolve_one("철학사 (6) 4.10.md", name_map)
        self.assertTrue(ok)
        self.assertEqual(path, self.src_b_nfc)

    def test_interpretation_items(self):
        r = self.by_id["T003"]
        self.assertEqual((r["grounding"], r["reasoning"], r["counter_view"]), (2, 2, 2))
        self.assertEqual(r["score"], 2)

    def test_missing_answer_and_v1_fields(self):
        r = self.by_id["T004"]
        self.assertEqual(r["score"], 0)
        self.assertEqual(r["notes"], "답변 없음")
        self.assertEqual(r["pair_id"], "")

    def test_cli_writes_csv_and_summary(self):
        root = Path(self.tmp.name)
        qf, af, out = root / "q.jsonl", root / "a.jsonl", root / "results"
        qf.write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in self.questions), encoding="utf-8")
        af.write_text("\n".join(json.dumps(a, ensure_ascii=False) for a in self.answers), encoding="utf-8")
        rc = es.main(["--questions", str(qf), "--answers", str(af), "--tag", "t", "--date", "2026-10-07",
                      "--results-dir", str(out)])
        self.assertEqual(rc, 0)
        with open(out / "2026-10-07_t.csv", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([r["id"] for r in rows], ["T001", "T002", "T003", "T004"])
        self.assertEqual(list(rows[0].keys()), es.CSV_COLUMNS)
        md = (out / "2026-10-07_t.md").read_text(encoding="utf-8")
        self.assertIn("환각 인용 문항", md)
        self.assertIn("T002", md)
        self.assertIn("| P1 | 2 | 0 | -2 |", md)
        # 두 번째 실행은 이전 결과와 비교한다
        es.main(["--questions", str(qf), "--answers", str(af), "--tag", "u", "--date", "2026-10-07",
                 "--results-dir", str(out)])
        md2 = (out / "2026-10-07_u.md").read_text(encoding="utf-8")
        self.assertIn("2026-10-07_t.csv", md2)

    def test_judge_llm_hook_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            es.judge_llm(self.questions[0], "x", "")


if __name__ == "__main__":
    unittest.main()
