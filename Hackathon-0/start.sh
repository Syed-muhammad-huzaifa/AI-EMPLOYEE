#!/bin/bash
# Startup script for AI Employee system
# This script unsets CLAUDECODE to allow the orchestrator to call Claude CLI

# Unset CLAUDECODE to prevent nested session errors
unset CLAUDECODE

# Set Python path
export PYTHONPATH="/home/syedhuzaifa/AI-EMPLOYEE/Hackathon-0"

# Add Claude CLI to PATH
export PATH="/home/syedhuzaifa/.npm-global/bin:$PATH"

# Run main.py with all arguments
cd /home/syedhuzaifa/AI-EMPLOYEE/Hackathon-0
exec python3 main.py "$@"
