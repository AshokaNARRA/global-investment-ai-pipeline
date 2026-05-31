#!/bin/bash
# This script starts the USA Market Agent with the massive global real-time configuration.
# INFINITE RUN MODE: Guarantees 24/7 execution. Restarts automatically if crashed.

echo "==========================================================="
echo " 🚀 Initializing 24/7 Global USA Market Agent Watchdog..."
echo "==========================================================="

cd "/Users/narra/Documents/AI"

while true; do
    echo "[$(date)] Launching Python Agent..."
    
    .venv/bin/python "USA Market News Scraping Agent/execution/usa_market_news_agent.py"
    
    EXIT_CODE=$?
    echo "[$(date)] ⚠️ Agent process exited with code $EXIT_CODE. Restarting in 15 seconds..."
    sleep 15
done
