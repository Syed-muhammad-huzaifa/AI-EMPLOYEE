#!/bin/bash
# Start AI Employee System
# Usage: ./start.sh

cd "$(dirname "$0")"

echo "Starting AI Employee System..."
echo "=============================="

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Gmail Watcher (checks every 5 seconds)
python -m src.watchers.gmail_watcher > logs/gmail_watcher.log 2>&1 &
GMAIL_PID=$!
echo "✅ Gmail Watcher started (PID: $GMAIL_PID)"

# Start Approved Email Sender
python -m src.watchers.approved_email_sender > logs/approved_email_sender.log 2>&1 &
SENDER_PID=$!
echo "✅ Approved Email Sender started (PID: $SENDER_PID)"

# Start Ralph Loop Manager (Orchestrator)
python -m src.ralph.loop_manager > logs/ralph_loop.log 2>&1 &
RALPH_PID=$!
echo "✅ Ralph Loop Manager started (PID: $RALPH_PID)"

echo ""
echo "All services started successfully!"
echo ""
echo "To check status: ./status.sh"
echo "To view logs: tail -f logs/gmail_watcher.log"
echo "To stop: ./stop.sh"
