# 알프레도 메이트 꾸러미 (mate package)

알프레도를 다른 화면이나 서비스(예: 솔루션 메이트 플랫폼)로 옮길 때 **같이 가는 묶음**입니다. 코드가 어디에 있든 이 다섯 파일을 보면 알프레도가 누구이고, 무엇을 할 수 있고, 무엇을 하지 않으며, 어떻게 시험하고, 무엇을 기억하는지 알 수 있습니다.

| 파일 | 내용 | 이 저장소에서 쓰는 곳 |
|---|---|---|
| [identity.md](identity.md) | 이름·역할·말투, 공개 전제 점검 | 대시보드 알프레도 칸, `mvp/chat_server.py` 지시문 |
| [skills.md](skills.md) | 지금 설명할 수 있는 것과 그 숫자의 출처 | `dashboard/template.html`의 `bubbles()`, `REPORT.md` |
| [permissions.md](permissions.md) | 하지 않는 것(투자 권유·개인 정보·실제 주문)과 거르는 장치 | `mvp/chat_server.py`의 ADVICE·PROBE 정규식, 시험 |
| [tests.md](tests.md) | 알프레도를 시험하는 법 | `eval/`, `tests/`, `mvp/tests/` |
| [memory.md](memory.md) | 기억해도 되는 것과 안 되는 것 | (다음 단계) |

상태: v0(2026-10-22, 코디세이 미션 판). 성격 표시(MBTI 같은 단서)와 그림 캐릭터는 작성자가 정하기 전 **초안**입니다(identity.md 3절).
