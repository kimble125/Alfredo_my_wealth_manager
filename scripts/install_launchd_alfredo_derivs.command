#!/bin/bash
# [선택] Finder에서 더블클릭하면 알프레도 파생지표 수집기를 macOS launchd에 등록합니다(매일 03:35·15:35).
# Aside 루틴 "Alfredo 파생지표 수집"(03:30·15:30)과 중복 실행돼도 안전합니다(멱등 upsert).
# Aside가 꺼져 있거나 계정 한도에 걸린 날의 보험용입니다. 해제: launchctl bootout gui/$(id -u)/com.kimble.alfredo-derivs
# 주의: Aside가 만든 파일은 Gatekeeper가 막을 수 있습니다. 더블클릭이 안 되면 터미널에서
#   bash scripts/install_launchd_alfredo_derivs.command   (저장소 루트에서)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd -P)"
LABEL="com.kimble.alfredo-derivs"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$LABEL</string>
    <key>ProgramArguments</key>
    <array><string>/bin/bash</string><string>$ROOT/scripts/alfredo_collect_derivs.sh</string></array>
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Hour</key><integer>3</integer><key>Minute</key><integer>35</integer></dict>
        <dict><key>Hour</key><integer>15</integer><key>Minute</key><integer>35</integer></dict>
    </array>
    <key>RunAtLoad</key><false/>
    <key>StandardOutPath</key><string>$ROOT/logs/alfredo_launchd.out.log</string>
    <key>StandardErrorPath</key><string>$ROOT/logs/alfredo_launchd.err.log</string>
    <key>ProcessType</key><string>Background</string>
    <key>LowPriorityIO</key><true/>
</dict>
</plist>
EOF
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo
launchctl list | grep "$LABEL" >/dev/null && echo "=== 등록 완료: 매일 03:35·15:35에 실행됩니다. 로그: $ROOT/logs/alfredo_collector.log ==="
