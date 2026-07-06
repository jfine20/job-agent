#!/bin/bash
set -e

echo "Starting Sam's Job Agent..."

# Load env vars
export $(grep -v '^#' .env | xargs)

# Start backend
cd backend
pip install -r ../requirements.txt -q
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend
cd frontend
npm install -q
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Backend running at http://localhost:8000"
echo "Frontend running at http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
