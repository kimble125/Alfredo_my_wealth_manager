"""대시보드 시험: 바깥 주소를 불러오지 않는지, 넣은 데이터가 CSV와 맞는지(표준 라이브러리만).

실행(저장소 루트에서): python -m unittest discover -s tests
"""
import csv
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "dashboard", "index.html")


class TestDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(HTML, encoding="utf-8") as f:
            cls.html = f.read()
        m = re.search(r"const DATA = (\{.*?\});\nconst DAY", cls.html, re.S)
        cls.data = json.loads(m.group(1)) if m else None

    def test_data_embedded(self):
        self.assertIsNotNone(self.data, "데이터가 HTML 안에 들어 있어야 함")
        self.assertNotIn("/*__DATA__*/", self.html)

    def test_no_external_loads(self):
        # 스크립트·스타일·이미지·글꼴을 바깥에서 불러오지 않는다(출처 표기용 <a href>는 허용)
        self.assertEqual(re.findall(r"<(?:script|link|img|iframe)[^>]+(?:src|href)=\"https?://", self.html), [])
        self.assertNotIn("fetch(", self.html)
        self.assertNotIn("@import", self.html)

    def test_rows_match_csv(self):
        for sym in ["BTC", "ETH", "XRP"]:
            with open(os.path.join(ROOT, "data", "raw", f"coinbase_{sym.lower()}_usd_1d.csv"), encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            close = self.data["coins"][sym]["close"]
            self.assertEqual(sum(v is not None for v in close), len(rows), sym)
            self.assertEqual(self.data["coins"][sym]["start"], rows[0]["date"])
            self.assertAlmostEqual(close[-1], float(rows[-1]["close"]), places=4)

    def test_no_advice_words(self):
        for w in ["매수하세요", "매도하세요", "사세요", "파세요", "추천 종목"]:
            self.assertNotIn(w, self.html)


if __name__ == "__main__":
    unittest.main()
