#!/bin/bash
# 알프레도 전용 파생지표(OI·롱숏·테이커·펀딩) 수집 진입점. Aside 루틴 / launchd / 수동 공용.
# Top3 팀 수집기(Cripto analysis/02_데이터수집/scripts/run_collect.sh)와는 완전히 별개다.
# 로그: logs/alfredo_collector.log (append). DB: data/alfredo/alfredo_derivs.db (git 제외).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"   # .../12_expert_agents
PY="$(command -v python3 || echo /usr/bin/python3)"
cd "$ROOT" || exit 1
mkdir -p "$ROOT/logs" "$ROOT/data/alfredo"
"$PY" -m alfredo.collectors.binance_derivs "$@"
rc=$?
LOG="$ROOT/logs/alfredo_collector.log"
if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 5242880 ]; then
  tail -n 2000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
exit $rc
