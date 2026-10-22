"""리포트·데이터·그림이 서로 맞는지 보는 시험(표준 라이브러리만).

실행(저장소 루트에서): python -m unittest discover -s tests
"""
import csv
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rows(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestData(unittest.TestCase):
    def test_csv_shape(self):
        for name in ["btc", "eth", "xrp"]:
            r = rows(f"data/raw/coinbase_{name}_usd_1d.csv")
            self.assertGreaterEqual(len(r), 100)
            dates = [x["date"] for x in r]
            self.assertEqual(dates, sorted(dates), "날짜 오름차순")
            self.assertEqual(len(dates), len(set(dates)), "중복 날짜 없음")
            for x in r:
                self.assertLessEqual(float(x["low"]), float(x["high"]))
        fg = rows("data/raw/fear_greed_1d.csv")
        self.assertGreaterEqual(len(fg), 100)
        self.assertTrue(all(0 <= int(x["value"]) <= 100 for x in fg))

    def test_summary_matches_csv(self):
        with open(os.path.join(ROOT, "outputs/summary.json"), encoding="utf-8") as f:
            s = json.load(f)
        for name in ["BTC", "ETH", "XRP"]:
            self.assertEqual(s["data"][name]["rows"], len(rows(f"data/raw/coinbase_{name.lower()}_usd_1d.csv")))
        self.assertEqual(s["data"]["FNG"]["rows"], len(rows("data/raw/fear_greed_1d.csv")))


class TestReport(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "REPORT.md"), encoding="utf-8") as f:
            self.report = f.read()

    def test_images_exist(self):
        imgs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", self.report)
        self.assertGreaterEqual(len(imgs), 3)
        for p in imgs:
            self.assertTrue(os.path.exists(os.path.join(ROOT, p)), p)

    def test_required_sections(self):
        for h in ["분석 주제", "분석 질문", "데이터 설명", "시각화", "인사이트", "결론", "한계", "AI 사용 로그"]:
            self.assertIn(h, self.report, h)

    def test_readme_local_links(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        for p in re.findall(r"\]\((?!https?://)([^)#]+)(?:#[^)]*)?\)", readme):
            self.assertTrue(os.path.exists(os.path.join(ROOT, p)), p)


if __name__ == "__main__":
    unittest.main()
