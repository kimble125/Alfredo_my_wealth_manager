# Alfredo — 나의 투자 집사 (my wealth manager)

코디세이 미션 **'AI 데이터 분석: 데이터 기반 트렌드 분석'** 제출 저장소입니다. 비트코인 일봉 **4,112개**(2015-07-20 – 2026-10-21)로 추세·변동성·계절성·시장 심리를 분석한 리포트([REPORT.md](REPORT.md))와 코드·그림·데이터, 그리고 실시간 코인 지표를 기간·지표를 바꿔 보는 **대시보드**(알프레도 대시보드 코인 탭)가 있습니다. 알프레도(Alfredo)는 근거와 함께 시장을 설명해 주는 '투자 집사' 에이전트를 만드는 작성자의 개인 프로젝트입니다.

정보 제공·공부용이며 투자 권유가 아닙니다.

---

## 평가자 3분 안내

1. **[REPORT.md](REPORT.md) 0절 '한눈에'**: 결론 6줄(1분)
2. **아래 '요구사항 충족표'**: 미션 요구마다 어디서 충족했는지 링크(1분)
3. **그림·대시보드**: [images/](images/)의 그림 8장(REPORT 5·7절, 그림마다 '관찰'과 '해석'을 나눔), 대시보드는 REPORT 7절 D와 [dashboard/screenshots/](dashboard/screenshots/)(1분)
4. **(선택) 실행**: 아래 '실행'(분석 1분, 대시보드 1분)

## 요구사항 충족표

**2. 최종 결과물**

| 요구 | 이 저장소에서 | 상태 |
|---|---|---|
| 분석 리포트(REPORT.md: 주제·질문·데이터·시각화·인사이트·결론/한계) | [REPORT.md](REPORT.md) 1절 주제, 2절 질문, 3절 데이터, 5·7절 시각화, 6절·7절 D 인사이트, 8절 결론과 한계 | 충족 |
| 시계열 데이터 100개 이상 | 비트코인 일봉 **4,112개** · [REPORT 3절](REPORT.md#3-데이터-설명). 대시보드는 15분봉 7일 673개 × 3코인 | 충족 |
| 시각화 2개 이상(권장 3개 이상), 리포트 안 링크 | 그림 **8장**([images/](images/)) + 대시보드 화면(REPORT 7절 C·D) | 충족 |
| Python 코드(.py) | [analysis.py](analysis.py)(정제·분석·그림), [data/collect.py](data/collect.py)(수집), 대시보드 `mvp/` | 충족 |
| GitHub: 코드·리포트·데이터 또는 수집 방법 | [data/raw/](data/raw/) CSV 4개 + 수집 스크립트, 대시보드 데이터는 Top 3 공개 API | 충족 |

**4. 기능 요구 사항**

| 요구 | 이 저장소에서 | 상태 |
|---|---|---|
| 데이터 1개 선정, 출처·기간 명시 | Coinbase Exchange 공개 API(BTC 일봉), alternative.me 공포탐욕 지수, 기간·행 수 표 · [REPORT 3절](REPORT.md#3-데이터-설명), [11절](REPORT.md#11-출처) | 충족 |
| 분석 질문 3개 이상 | 4개(그래프 확인형·해석형 표시) · [REPORT 2절](REPORT.md#2-분석-질문), 코인 탭 질문은 7절 D | 충족 |
| 기본 정보(기간·컬럼·결측) 확인 | 자료별 빈 칸·중복·빠진 날·값 오류 표와 코드 출력 · [REPORT 4절](REPORT.md#4-데이터-정제-결측치와-이상치), [outputs/run_log.txt](outputs/run_log.txt) | 충족 |
| 결측치·이상치 기준과 처리 | 3일 이하 공백만 채움, XRP 904일 공백은 비워 둠(원인 확인), 이상치 \|z\|>4 표시만 · [REPORT 4절](REPORT.md#4-데이터-정제-결측치와-이상치) | 충족 |
| 시계열 기법 2개 이상 | 이동평균(50·200일), 변화율(일·월·30일 뒤), 30일 변동성, 구간별 통계, 요일·월 집계 · [REPORT 5절](REPORT.md#5-분석-결과와-시각화). 대시보드는 MACD·Stochastic·StochRSI·VPCI(7절 D) | 충족 |
| 인사이트 3개 이상(수치 근거, 관찰/해석 구분) | **10개**: 6절 1–6(일봉 11년), 7절 D 7–10(코인 탭 7일), 관찰(Fact)·원인 가설(Why)·행동(Action) 표 | 충족 |

**5. 보너스**

| 요구 | 이 저장소에서 | 상태 |
|---|---|---|
| 보너스 1: 대시보드(기간·조건을 바꿔 탐색) | **발표 화면: 알프레도 대시보드 http://127.0.0.1:8787/#coin (코인 탭)**. BTC·ETH·XRP 카드 고르기, 기간 1·3·7일(기본 7일), 지표 MACD 4시간·Stochastic 1시간·StochRSI 1시간·VPCI 15분을 나눠 보기·하나만·겹쳐 보기, 가격선 위 노란 점 = 네 지표의 방향이 바뀐 신호, 그 아래 AI 분석·근거, 오른쪽 알프레도 채팅 · [REPORT 7절 D](REPORT.md#d-보너스-1발표-화면-실시간-코인-탭과-지표-일치-신호). 제출 형식 (2) 로컬 실행 + 실행 방법(아래). 파일 하나로 열리는 예전 판: [dashboard/index.html](dashboard/index.html), 스크린샷 5장과 시나리오 [dashboard/README.md](dashboard/README.md). 주식·기타 탭은 미완성 | 충족 |
| 보너스 2: 분해·예측 + 시각화 | 고전 분해(그림 6), 베이스라인 예측 4종 + 30일 창 24개 재검증(그림 7) · [REPORT 7절 A·B](REPORT.md#7-보너스-시계열-분해와-베이스라인-예측) | 충족 |

**7. 제약 사항**

| 요구 | 이 저장소에서 | 상태 |
|---|---|---|
| 재현성: 의존성·실행 방법 | [requirements.txt](requirements.txt), 아래 '실행', [REPORT 10절](REPORT.md#10-재현-방법) | 충족 |
| 데이터 출처·수집 방법·라이선스 주의 | 아래 '데이터 출처와 약관', [REPORT 11절](REPORT.md#11-출처) | 충족 |
| 분석 품질(그래프만 나열 금지, 관찰/해석 구분) | 그림마다 관찰·해석 문단 · [REPORT 5절](REPORT.md#5-분석-결과와-시각화), 인사이트 표 | 충족 |
| AI 사용 로그(작업·이유·검증 방법) | [REPORT 9절](REPORT.md#9-ai-사용-로그) | 충족 |
| 과제 목표(질문·결측·관찰/해석·트렌드/계절성/노이즈·이동평균/변화율·AI 활용) | [REPORT 12절 '과제 목표 점검'](REPORT.md#12-과제-목표-점검어디서-답하나) | 충족 |

## 실행

```bash
python -m venv .venv && source .venv/bin/activate     # Python 3.10 이상
pip install -r requirements.txt
python data/collect.py --end 2026-10-21    # (선택) 공개 API에서 데이터 다시 받기, 약 30초, 키 필요 없음
python analysis.py                         # images/*.png 8장, outputs/summary.json 생성
python -m unittest discover -s tests       # 시험(데이터·리포트·대시보드)

# 대시보드(보너스 1, 발표 화면). 인터넷 필요(코인 탭이 Top 3 공개 API를 읽음)
python3 -I mvp/build_board.py
python3 -I mvp/chat_server.py              # → 브라우저로 http://127.0.0.1:8787/#coin
```

- 대시보드 서버는 이 컴퓨터(127.0.0.1)에서만 열립니다. 채팅 답은 Codex CLI(ChatGPT 로그인)가 있어야 나오고, 없어도 화면은 볼 수 있습니다.
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
├── dashboard/                # 예전 보너스 1 판: index.html(열기만 하면 됨), build_dashboard.py, screenshots/
├── mate/alfredo/             # 알프레도 메이트 꾸러미(정체성·기술·권한·시험·기억)
├── mvp/                      # 알프레도 대시보드(발표 화면): board.html, chat_server.py, top3_home/(코인 탭)
├── alfredo/  eval/  scripts/ # 알프레도 MVP(아래)
└── docs/
```

## 데이터 출처와 약관

| 자료 | 출처 | 약관·주의 |
|---|---|---|
| BTC·ETH·XRP 일봉 | Coinbase Exchange 공개 시세 API https://api.exchange.coinbase.com/products/BTC-USD/candles | 공개 엔드포인트(키 없음). 재배포 조건은 확인 중이며, 문제가 되면 `data/raw/coinbase_*.csv`를 지우고 `data/collect.py`로 직접 받으면 같은 결과가 나옵니다 |
| 코인 탭 실시간 지표·뉴스 | Top 3 Crypto 공개 API https://top3-crypto.vercel.app/api (원자료: 바이낸스·코인베이스 시세, alternative.me 공포탐욕, 네이버 뉴스 검색·GDELT) | 팀 프로젝트의 공개 화면 자료. 각 원자료의 약관은 Top 3 저장소 docs/legal/ 참고 |
| 공포탐욕 지수(비트코인 중심) | alternative.me https://alternative.me/crypto/fear-and-greed-index | 이용 규칙: 데이터 옆에 출처를 밝힐 것, alternative.me를 사칭하거나 혼동되는 서비스 금지. 이 저장소, 그림 아래, 대시보드에 출처를 적었습니다 |

## Top 3 Crypto(팀 프로젝트)와의 관계

- **Top 3 Crypto**는 작성자가 참여한 코디세이 파이널 팀 프로젝트입니다. BTC·ETH·XRP 4시간봉 Long/Short 신호 보드입니다(https://top3-crypto.vercel.app , 제출 저장소 https://github.com/kimble125/top3-crypto-final).
- **이 저장소는 작성자 개인 프로젝트**입니다. 분석(REPORT)의 데이터는 공개 API에서 따로 받았고, Top 3 수집본과는 **검증용 대조**만 했습니다(REPORT 3절).
- 2026-10-22, **팀 동의를 받아** Top 3 홈 화면 파일(`top3-crypto-final` 저장소의 `05_프론트/app`)을 [mvp/top3_home/](mvp/top3_home/)에 복사해 알프레도 대시보드의 **코인 탭**으로 넣었습니다. **원본 저장소는 고치지 않았습니다.** 사본에서 바꾼 것: Top 3 머리·바닥글 숨김(`?embed=1`), 가격선 위에 네 지표의 방향이 바뀐 신호 점 추가, 기본 기간 7일. 데이터는 Top 3 배포본 API(https://top3-crypto.vercel.app/api)에서 받습니다.

## 알프레도 MVP(이 저장소의 나머지 부분)

| 경로 | 내용 |
|---|---|
| `alfredo/` | 모의투자 엔진 v0(장부·가격·원칙·보고, 시험 16개). 실제 주문은 하지 않습니다 |
| `mvp/` | 알프레도 대시보드(코인 탭 = Top 3 실시간 홈, 주식·기타 탭 = **합성 가격 데모, 미완성**)와 알프레도 채팅 로컬 서버(시험 24개) |
| `eval/` | 알프레도 답변 평가 50문항과 채점 기준 |
| `scripts/` | 채점기 등 |
| `mate/alfredo/` | **메이트 꾸러미**: 알프레도를 다른 화면·서비스로 옮길 때 같이 가는 정체성·기술·권한·시험·기억 문서 |

MVP 화면 실행(로컬): `python3 -I mvp/chat_server.py` → http://127.0.0.1:8787/ (이 컴퓨터 안에서만 열림). 채팅은 Codex CLI(ChatGPT 로그인)가 있어야 답하고, 없으면 `mvp/dist/alfredo_mvp_board.html`을 열어 화면만 볼 수 있습니다. 알프레도 채팅은 투자 권유로 읽힐 표현과 지시문 유출 시도를 걸러냅니다.

## AI 사용 고지

분석 코드와 리포트 초안은 AI 도구(Aside, Claude Opus 5.5)의 도움을 받아 만들었고, 무엇을 맡겼고 어떻게 검증했는지는 [REPORT 9절 'AI 사용 로그'](REPORT.md#9-ai-사용-로그)에 적었습니다. 결론의 최종 판단은 작성자가 합니다.

## 저작권

© 2026 김호연(개발자 miru). 코드와 문서는 열람·학습·평가 목적으로 공개합니다. 다시 쓰려면 Issues로 문의해 주세요. 글꼴 Pretendard(SIL OFL 1.1) 사본은 `mvp/fonts/`에 있습니다.

발표·질의 대비 설명문(작성자용): [docs/presenter-guide_ko.md](docs/presenter-guide_ko.md)
