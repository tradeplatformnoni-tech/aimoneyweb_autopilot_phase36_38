#!/usr/bin/env bash
pkill -f "uvicorn backend.main:app" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
sleep 2
tail -n 10 nohup.out

