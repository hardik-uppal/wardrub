#!/bin/bash

# Wardrub Local Testing Helper
# This script starts the FastAPI backend and Vite frontend, and terminates them together on exit.

# Get the script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

BACKEND_DIR="$DIR/backend"
FRONTEND_DIR="$DIR/frontend"

# Ports
BACKEND_PORT=8000
FRONTEND_PORT=5174

echo "=========================================="
echo "🚀 Starting Wardrub Local Development Environment"
echo "=========================================="

# Check if ports are already in use
backend_pid=$(lsof -t -i :$BACKEND_PORT 2>/dev/null)
if [ -n "$backend_pid" ]; then
    echo "⚠️ Warning: Port $BACKEND_PORT is already in use by PID $backend_pid."
    read -p "Would you like to terminate the existing backend process? [y/N] " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        kill -9 $backend_pid
        echo "✅ Terminated process $backend_pid"
    else
        echo "❌ Aborting. Please free port $BACKEND_PORT or run manually."
        exit 1
    fi
fi

frontend_pid=$(lsof -t -i :$FRONTEND_PORT 2>/dev/null)
if [ -n "$frontend_pid" ]; then
    echo "⚠️ Warning: Port $FRONTEND_PORT is already in use by PID $frontend_pid."
    read -p "Would you like to terminate the existing frontend process? [y/N] " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        kill -9 $frontend_pid
        echo "✅ Terminated process $frontend_pid"
    else
        echo "❌ Aborting. Please free port $FRONTEND_PORT or run manually."
        exit 1
    fi
fi

# 1. Start Backend
echo "📡 Starting Backend (FastAPI) on port $BACKEND_PORT..."
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "❌ Error: Virtual environment not found at $BACKEND_DIR/venv"
    echo "Please set up the backend virtual environment first."
    exit 1
fi

# Run backend
cd "$BACKEND_DIR"
# Source env if it exists
if [ -f ".env" ]; then
    # Load .env variables
    export $(grep -v '^#' .env | xargs)
fi

# Launch backend in background
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $BACKEND_PORT --reload > backend.log 2>&1 &
BACKEND_PROCESS_PID=$!
echo "✅ Backend started in background (PID: $BACKEND_PROCESS_PID, logs to backend/backend.log)"

# 2. Start Frontend
echo "💻 Starting Frontend (Vite) on port $FRONTEND_PORT..."
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "❌ Error: node_modules not found at $FRONTEND_DIR/node_modules"
    echo "Please run 'npm install' in the frontend directory."
    # Clean up backend before exiting
    kill $BACKEND_PROCESS_PID 2>/dev/null
    exit 1
fi

cd "$FRONTEND_DIR"
# Launch frontend in background
npm run dev > frontend.log 2>&1 &
FRONTEND_PROCESS_PID=$!
echo "✅ Frontend started in background (PID: $FRONTEND_PROCESS_PID, logs to frontend/frontend.log)"

echo "------------------------------------------"
echo "🎉 Services are running!"
echo "   - Frontend: http://localhost:$FRONTEND_PORT"
echo "   - Backend:  http://localhost:$BACKEND_PORT"
echo "------------------------------------------"
echo "Press [Ctrl+C] to stop both servers and exit."

# Cleanup function to kill background processes on exit
cleanup() {
    echo -e "\n🛑 Stopping servers..."
    if [ -n "$BACKEND_PROCESS_PID" ]; then
        kill $BACKEND_PROCESS_PID 2>/dev/null
        wait $BACKEND_PROCESS_PID 2>/dev/null
        echo "✅ Stopped Backend (PID: $BACKEND_PROCESS_PID)"
    fi
    if [ -n "$FRONTEND_PROCESS_PID" ]; then
        kill $FRONTEND_PROCESS_PID 2>/dev/null
        wait $FRONTEND_PROCESS_PID 2>/dev/null
        echo "✅ Stopped Frontend (PID: $FRONTEND_PROCESS_PID)"
    fi
    echo "👋 All servers stopped. Goodbye!"
    exit 0
}

# Trap Ctrl+C (SIGINT) and SIGTERM
trap cleanup SIGINT SIGTERM

# Keep script running to monitor/wait
while true; do
    sleep 1
done
