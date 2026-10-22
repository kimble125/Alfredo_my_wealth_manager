# Alfredo — 나의 투자 집사 (my wealth manager)

**알프레도(Alfredo)** 는 사용자 곁에서 시장을 읽고 근거와 함께 설명해 주는 '투자 집사' 에이전트를 만드는 개인 프로젝트입니다. 이 저장소에는 코디세이 미션 **'AI 데이터 분석: 데이터 기반 트렌드 분석'** 의 결과물(비트코인 시계열 분석 리포트·코드·대시보드)과 알프레도 MVP 코드가 함께 있습니다.

정보 제공·공부용이며 투자 권유가 아닙니다. 가격 자료는 Coinbase, 공포탐욕 지수는 alternative.me에서 받았습니다(Data: Fear & Greed Index by alternative.me).

---

## 평가자용 5분 안내

1. **[REPORT.md](REPORT.md) 0절 '한눈에'**: 결론 5줄(1분)
2. **그림 8장**: [images/](images/) 또는 REPORT 5·7절. 그림마다 '관찰(사실)'과 '해석(가설)'을 나눠 적었습니다(2분)
3. **아래 '미션 요구 충족표'**: 요구마다 어디서 충족했는지 링크(1분)
4. **(선택) 실행**: `pip install -r requirements.txt && python analysis.py` (1분)

## 미션 요구 충족표

| 미션 요구 | 이 저장소에서 | 상태 |
|---|---|---|
| 시계열 데이터 1개, 100개 이상 | 비트코인 일봉 **4,112개**(2015-07-20 – 2026-10-21) · [REPORT 3절](REPORT.md#3-데이터-설명) | 충족 |
| 데이터 출처·기간 명시 | Coinbase Exchange 공개 API, alternative.me API, 기간·행 수 표 · [REPORT 3절](REPORT.md#3-데이터-설명), [11절](REPORT.md#11-출처) | 충족 |
| 분석 질문 3개 이상 | 4개(그래프 확인형·해석형 표시) · [REPORT 2절](REPORT.md#2-분석-질문) | 충족 |
| 기본 정보(기간·컬럼·결측) 확인 | 자료별 빈 칸·중복·빠진 날·값 오류 표 · [REPORT 4절](REPORT.md#4-데이터-정제-결측치와-이상치), `analysis.py` 실행 출력 | 충족 |
| 결측치·이상치 기준과 처리 | 3일 이하 공백만 채움, XRP 904일 공백은 비워 둠(원인 확인), 이상치 \|z\|>4 표시만 · [REPORT 4절](REPORT.md#4-데이터-정제-결측치와-이상치) | 충족 |
| 시계열 기법 2개 이상 | 이동평균(50·200일), 변화율(일·월·30일 뒤), 30일 변동성, 구간별 통계(반감기·국면·심리), 요일·월 집계 · [REPORT 5절](REPORT.md#5-분석-결과와-시각화) | 충족 |
| 시각화 2개 이상(권장 3개 이상) | **8장**([images/](images/)), 리포트 안에서 링크 | 충족 |
| 인사이트 3개 이상(수치 근거, 관찰/해석 구분) | **6개**, 관찰(Fact)·원인 가설(Why)·행동(Action) 표 · [REPORT 6절](REPORT.md#6-인사이트) | 충족 |
| REPORT.md 구성 | 주제·질문·데이터·시각화·인사이트·결론/한계 · [REPORT 1–8절](REPORT.md) | 충족 |
| Python 코드 | [analysis.py](analysis.py)(분석·그림), [data/collect.py](data/collect.py)(수집) | 충족 |
| GitHub: 코드·리포트·데이터 또는 수집 방법 | [data/raw/](data/raw/) CSV 4개 + 수집 스크립트 | 충족 |
| 재현성(의존성·실행 방법·출처/약관) | [requirements.txt](requirements.txt), 아래 '실행', '데이터 출처와 약관' | 충족 |
| 분석 품질(그래프만 나열 금지) | 그림마다 관찰·해석 문단 · [REPORT 5절](REPORT.md#5-분석-결과와-시각화) | 충족 |
| **AI 사용 로그**(작업·이유·검증 방법) | 7개 작업, 검증 방법 포함 · [REPORT 9절](REPORT.md#9-ai-사용-로그) | 충족 |
| 보너스 1: 대시보드(기간·조건 바꿔 탐색) | [dashboard/](dashboard/) | 작업 중 |
| 보너스 2: 분해·예측 + 시각화 | 고전 분해(그림 6), 베이스라인 예측 4종 + 24구간 재검증(그림 7) · [REPORT 7절](REPORT.md#7-보너스-시계열-분해와-베이스라인-예측) | 충족 |

## 실행

```bash
python -m venv .venv && source .venv/bin/activate     # Python 3.10 이상
pip install -r requirements.txt
python data/collect.py --end 2026-10-21    # (선택) 공개 API에서 데이터 다시 받기, 약 30초, 키 필요 없음
python analysis.py                         # images/*.png 8장, outputs/summary.json 생성
```

- 검증 환경: macOS, Python 3.14, pandas 3.0.3, numpy 2.4.6, matplotlib 3.11.1
- 한글 그림 글꼴: 맥 AppleGothic, 윈도 맑은 고딕, 리눅스 Nanum/Noto 중 있는 것을 씁니다.

## 폴더 구조

```
Alfredo_my_wealth_manager/
├── REPORT.md                 # 분석 리포트(미션 결과물)
├── analysis.py               # 정제·분석·그림
├── requirements.txt
├── data/
│   ├── collect.py            # 공개 API 수집(표준 라이브러리)
│   └── raw/                  # coinbase_{btc,eth,xrp}_usd_1d.csv, fear_greed_1d.csv
├── images/                   # 01–08 그림
├── outputs/                  # summary.json(리포트 숫자), 월별 수익률·이상치·예측 오차 표
├── dashboard/                # 보너스 1 대시보드(작업 중)
├── alfredo/  mvp/  eval/  scripts/   # 알프레도 MVP(아래)
└── docs/
```

## 데이터 출처와 약관

| 자료 | 출처 | 약관·주의 |
|---|---|---|
| BTC·ETH·XRP 일봉 | Coinbase Exchange 공개 시세 API https://api.exchange.coinbase.com/products/BTC-USD/candles | 공개 엔드포인트(키 없음). 재배포 조건은 확인 중이며, 문제가 되면 `data/raw/coinbase_*.csv`를 지우고 `data/collect.py`로 직접 받으면 같은 결과가 나옵니다 |
| 공포탐욕 지수 | alternative.me https://alternative.me/crypto/fear-and-greed-index | 이용 규칙: 데이터 옆에 출처를 밝힐 것, alternative.me를 사칭하거나 혼동되는 서비스 금지. 이 저장소와 그림에 출처를 적었습니다 |

## Top 3 Crypto(팀 프로젝트)와의 관계

- **Top 3 Crypto**는 작성자가 참여한 코디세이 파이널 팀 프로젝트입니다. BTC·ETH·XRP 4시간봉 Long/Short 신호 보드입니다(https://top3-crypto.vercel.app , 제출 저장소 https://github.com/kimble125/top3-crypto-final).
- **이 저장소는 작성자 개인 프로젝트**입니다. Top 3 팀의 코드·화면 디자인·매매 조건은 옮기지 않았습니다. 데이터는 공개 API에서 따로 받았고, Top 3 수집본과는 **검증용 대조**만 했습니다(REPORT 3절).

## 알프레도 MVP(이 저장소의 나머지 부분)

| 경로 | 내용 |
|---|---|
| `alfredo/` | 모의투자 엔진 v0(장부·가격·원칙·보고, 시험 16개). 실제 주문은 하지 않습니다 |
| `mvp/` | 대시보드 V3(코인·주식·기타 탭, **합성 가격 데모**)와 알프레도 채팅 로컬 서버(시험 24개) |
| `eval/` | 알프레도 답변 평가 50문항과 채점 기준 |
| `scripts/` | 채점기 등 |

MVP 화면 실행(로컬): `python3 -I mvp/chat_server.py` → http://127.0.0.1:8787/ (이 컴퓨터 안에서만 열림). 채팅은 Codex CLI(ChatGPT 로그인)가 있어야 답하고, 없으면 `mvp/dist/alfredo_mvp_board.html`을 열어 화면만 볼 수 있습니다. 알프레도 채팅은 투자 권유로 읽힐 표현과 지시문 유출 시도를 걸러냅니다.

## AI 사용 고지

분석 코드와 리포트 초안은 AI 도구(Aside, Claude Opus 5.5)의 도움을 받아 만들었고, 무엇을 맡겼고 어떻게 검증했는지는 [REPORT 9절 'AI 사용 로그'](REPORT.md#9-ai-사용-로그)에 적었습니다. 결론의 최종 판단은 작성자가 합니다.

## 저작권

© 2026 김호연(개발자 miru). 코드와 문서는 열람·학습·평가 목적으로 공개합니다. 다시 쓰려면 Issues로 문의해 주세요. 글꼴 Pretendard(SIL OFL 1.1) 사본은 `mvp/fonts/`에 있습니다.
