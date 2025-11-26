@echo off
title Finger Snake - Local Server
echo ============================================
echo     FINGER SNAKE WEB - LOCAL SERVER
echo ============================================

echo Starting local server on http://localhost:8000/
echo Press CTRL + C to stop.
echo.

python -m http.server 8000

pause
