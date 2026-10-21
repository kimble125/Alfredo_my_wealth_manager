# Alfredo — 충실한 투자 집사 (`~/01_Projects/Alfredo`)

> **공개 스냅샷(2026-10-21)**: 이 저장소는 로컬 Alfredo 개발 폴더에서 코드·MVP 대시보드·평가 세트만 골라 올린 공개판이다. 개인 재무 자료, 대화 기록, 참고자료(`reference/`), 운영 문서(`docs/`, `_운영/`), 계좌 연동 코드는 넣지 않았다. 표 속 그런 경로는 로컬에만 있다. 대시보드 가격은 합성 데이터이며 투자 조언이 아니다.


> **주제(2026-10-07 호연 정정)**: **알프레도(Alfredo)** — Top3 Crypto(팀 보드, `~/01_Projects/Cripto analysis`)를 포함해 발전시킨 '충실한 투자 집사' 서비스. 시작점은 Top3 Crypto 프로젝트와 Agents의 자산관리 봇(이 봇도 Alfredo로 이름을 바꿀 예정)을 합친 것이다. 상용화 가능한 형태를 목표로 하되 **자동 투자는 하지 않고 모의투자까지만**, **고객 계좌 등록 없이** 쓸 수 있게 설계한다.
>
> **2026-10-08 폴더 정비**: 옛 이름 `~/01_Projects/12_expert_agents`(임시 링크가 잠시 남아 있음). 비밀값과 개인 자료는 짝 폴더 `~/01_Projects/Alfredo_private`(git 아님)에 있다. 이 저장소가 처음에 담았던 Agents 자료(소피아 정의·평가 세트·강의 전사·지식 팩 스크립트)는 `~/03_Agents`(Agents 본부)로 옮겼다. 공통 부분은 양쪽에 둔다: `agents/asset*`(정본은 03_Agents), `scripts/eval_score.py`·`scripts/tests/`, `docs/에이전트_계층_설계_2026-10-05.md`, `docs/Orca_Aside_역할분담.md`.

## 폴더 지도
| 경로 | 내용 | git |
|---|---|---|
| `alfredo/` | 모의투자 엔진 v0(장부·가격·원칙·보고·CLI)과 시험, `collectors/`(파생지표 수집기, Aside 작업 미커밋) | O |
| `docs/alfredo/` | 인벤토리·범위 경계 확정안·설계서 v0·로드맵(AI용·인간용·시각화)·Orca 패킷·학습계획·종합·검수 | O |
| `eval/alfredo_*` | 알프레도 평가 50문항과 rubric | O |
| `scripts/eval_score.py`, `scripts/tests/` | 채점기(Agents와 공통) | O |
| `scripts/alfredo_collect_derivs.sh`, `scripts/install_launchd_alfredo_derivs.command` | 파생지표 수집 실행·설치(Aside 작업 미커밋) | 미커밋 |
| `agents/asset.md`, `agents/asset/` | 자산 에이전트(옛 가칭 모네타 → Alfredo 예정) 정의 **사본**. 정본은 `~/03_Agents/agents/` | O |
| `data/alfredo/` | 수집 DB(`alfredo_derivs.db`) | X |
| `logs/alfredo_collector.log` | 수집 기록 | X |
| `reference/` | 10-07에 모은 참고자료 사본(Top3·학습 계획 등). Agents 사본은 10-08에 03_Agents로 분리, 개인 재무 원본 사본은 뺌. 색인 `reference/README.md`(10-07 기준) | 일부 |
| `_운영/` | 막힌작업·인수인계·프롬프트. 옛 인계 묶음은 `_운영/인수인계/18_alfredo_dev_learning_plan/` | O |
| `docs/작업현황.md` | 세션 담당표(Agents 줄은 03_Agents `_운영/작업현황.md`로 옮김) | O |

## 지금 상태
- 엔진 v0, 시험 16개 통과: `python3 -I -m unittest discover -s alfredo/tests`(저장소 루트에서).
- 파생지표 수집: Aside 정기 작업 `iTQuXLqxJxc011ju`(매일 03:30·15:30)가 `scripts/alfredo_collect_derivs.sh`를 부른다. 경로 변경은 `~/02_HQ/30_BOARD/Orders/ord_1008_01_경로변경.md`로 Aside에 지시함.
- 인수인계: `_운영/인수인계_2026-10-07.md`(10-07 기준, 머리에 10-08 안내). 막힌작업: `_운영/막힌작업/막힌작업_2026-10-07_alfredo.md`.

## 규칙
- 비밀값(`.env`)은 `Alfredo_private`에만 둔다. 이 저장소에는 넣지 않는다(.gitignore).
- 개인 재무 원본(통신비 진단, 과거 자산 기록, 계좌 캡처)은 `~/02_HQ/10_Office/개인행정`에 있고 에이전트는 읽지 않는다. 필요하면 호연에게 숫자를 요청한다.
- Aside와는 `~/02_HQ/30_BOARD`로 주고받는다(Orders/Reports).
