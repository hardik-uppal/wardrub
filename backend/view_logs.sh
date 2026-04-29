#!/bin/bash
# View Wardrub logs
# Usage: ./view_logs.sh [tail|json|errors|search <term>]

LOGS_DIR="$(dirname "$0")/logs"
TODAY=$(date +%Y-%m-%d)
LOG_FILE="$LOGS_DIR/wardrub_$TODAY.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "No log file found for today: $LOG_FILE"
    echo "Available logs:"
    ls -la "$LOGS_DIR"/*.log 2>/dev/null || echo "  No logs yet"
    exit 1
fi

case "${1:-tail}" in
    tail)
        echo "📜 Tailing logs: $LOG_FILE"
        echo "   Press Ctrl+C to stop"
        echo "---"
        tail -f "$LOG_FILE" | while read line; do
            # Pretty print JSON logs
            echo "$line" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    ts = d.get('timestamp', '')[-8:]
    lvl = d.get('level', 'INFO')[:4]
    msg = d.get('message', '')
    
    colors = {'INFO': '32', 'WARN': '33', 'ERRO': '31', 'DEBU': '36'}
    c = colors.get(lvl, '0')
    
    print(f'[\033[{c}m{lvl}\033[0m] {ts} | {msg}')
    if 'exception' in d:
        print(f'  \033[31m{d[\"exception\"][:200]}\033[0m')
except:
    print(sys.stdin.read())
" 2>/dev/null || echo "$line"
        done
        ;;
    
    json)
        echo "📋 Raw JSON logs (last 50 lines):"
        tail -50 "$LOG_FILE"
        ;;
    
    errors)
        echo "❌ Error logs:"
        grep -i '"level":"ERROR"' "$LOG_FILE" | tail -20
        ;;
    
    search)
        if [ -z "$2" ]; then
            echo "Usage: ./view_logs.sh search <term>"
            exit 1
        fi
        echo "🔍 Searching for: $2"
        grep -i "$2" "$LOG_FILE"
        ;;
    
    *)
        echo "Usage: ./view_logs.sh [tail|json|errors|search <term>]"
        echo ""
        echo "Commands:"
        echo "  tail    - Follow logs in real-time (default)"
        echo "  json    - Show last 50 raw JSON log entries"
        echo "  errors  - Show only error logs"
        echo "  search  - Search logs for a term"
        ;;
esac





