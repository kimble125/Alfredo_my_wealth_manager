# 알프레도 · 시험 (v0)

| 시험 | 무엇을 보나 | 실행(저장소 루트에서) |
|---|---|---|
| 답변 평가 세트 50문항 | 페르소나·경계·사실을 지키는지(사실형 20, 연결형 15, 해석형 15, 과신 검출 10) | `python scripts/eval_score.py --questions eval/alfredo_questions_v1.jsonl --answers <답변.jsonl>` (채점 기준 `eval/alfredo_rubric.md`) |
| 대시보드·리포트 시험 9개 | 데이터 모양, 숫자 일치, 그림·링크 존재, 바깥 주소 0, 권유 표현 없음 | `python -m unittest discover -s tests` |
| MVP·채팅 안전 시험 24개 | 개인 경로 차단, 권유 차단, 화면 자료만 넘김 | `python3 -I -m unittest discover -s mvp/tests` |
| 모의투자 엔진 시험 16개 | 장부·원칙·보고 | `python3 -I -m unittest discover -s alfredo/tests` |

- 2026-10-22 결과: 9 · 24 · 16개 모두 통과.
- 평가 세트의 일부 문항은 비공개 설계 문서를 근거로 삼고 있어, 공개판에서는 질문과 채점 기준만 참고용입니다.
