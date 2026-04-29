#!/bin/bash

# Frontend run script with logging
cd "$(dirname "$0")"

LOG_DIR="./logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/frontend_$(date +%Y-%m-%d).log"

echo "Starting frontend at $(date)" >> "$LOG_FILE"
echo "Logs: $LOG_FILE"

# Run npm dev with output to log file
nohup npm run dev >> "$LOG_FILE" 2>&1 &

PID=$!
echo $PID > "$LOG_DIR/frontend.pid"
echo "Frontend started with PID: $PID"
echo "Logging to: $LOG_FILE"
