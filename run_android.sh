#!/data/data/com.termux/files/usr/bin/bash
# Prevenir que Android suspenda el proceso al apagar la pantalla
termux-wake-lock 2>/dev/null || true

echo "🏡 Iniciando Buscador de Alquileres en Android..."
python main.py --daemon
