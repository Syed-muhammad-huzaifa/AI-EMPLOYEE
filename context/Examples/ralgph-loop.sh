#!/bin/bash
# ralph-loop.sh - Start Ralph Wiggum loop

PROMPT="Process all files in /Needs_Action, move to /Done when complete. Follow Company_Handbook.md.
Use Agent Skills. Create Plan.md. Request approval if needed.
When done output <promise>TASK_COMPLETE</promise>"

MAX_ITER=10
iter=0

while [ $iter -lt $MAX_ITER ]; do
    echo "$PROMPT" | claude --headless --cwd .
    
    if grep -q "TASK_COMPLETE" *.md 2>/dev/null; then
        echo "Task complete!"
        break
    fi
    
    iter=$((iter+1))
    sleep 5
done

if [ $iter -eq $MAX_ITER ]; then
    echo "Max iterations reached - moving to /Failed/"
    mkdir -p Failed
    mv Needs_Action/* Failed/ 2>/dev/null
fi