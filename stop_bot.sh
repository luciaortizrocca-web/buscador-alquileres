#!/bin/bash
pkill -f "main.py --daemon" 2>/dev/null || true
rm -f /home/luchi/buscador-alquileres/bot.pid
echo "Bot detenido."
