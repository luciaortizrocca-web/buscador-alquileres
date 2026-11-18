#!/bin/bash
pkill -f "main.py --daemon" 2>/dev/null || true
nohup /home/luchi/.local/bin/uv run python /home/luchi/buscador-alquileres/main.py --daemon > /home/luchi/buscador-alquileres/bot.log 2>&1 < /dev/null &
echo $! > /home/luchi/buscador-alquileres/bot.pid
echo "Bot iniciado de forma independiente con PID $(cat /home/luchi/buscador-alquileres/bot.pid)"
