# 🏡 Buscador y Alerta Temprana de Alquileres (CABA)

Aplicación construida a medida para monitorear en tiempo real alquileres de **PHs, Casas y Departamentos** en CABA que cumplan con:
- Presupuesto máximo configurable (por defecto $\le \$1.200.000$ ARS).
- **Balcón o Terraza excluyente**.
- Espacio para 2 dormitorios o living amplio integrado para estudio.
- Bajas expensas / Sin amenities costosos.
- **Base de datos en Planilla de Cálculo**: Se guarda en `alquileres.csv` (compatible con Excel / Calc) y opcionalmente se sincroniza en vivo con **Google Sheets** en tu celular.
- **Bot de Telegram**: Alertas instantáneas con fotos, precio desglosado y comandos para cambiar barrios y filtros desde el teléfono.

---

## 🚀 Uso Rápido

El proyecto está configurado con `uv`.

### 1. Ejecutar un escaneo único (manual):
```bash
uv run python main.py --once
```

### 2. Ejecutar el monitor continuo (Daemon con Telegram):
```bash
uv run python main.py --daemon
```

### 3. Probar envío de alerta a Telegram:
```bash
uv run python main.py --test-telegram
```

---

## 📱 Comandos del Bot de Telegram (desde tu celular)

Una vez iniciado el bot con `--daemon`:
- `/barrios`: Muestra qué barrios están activos.
- `/barrios palermo, caballito, almagro`: Actualiza la búsqueda solo a esos barrios.
- `/barrios todos`: Busca en toda la Ciudad de Buenos Aires.
- `/precio 1100000`: Modifica tu tope de alquiler.
- `/status`: Muestra los filtros actuales y cuántos alquileres hay registrados en la planilla.
- `/buscar`: Dispara un rastreo inmediato sin esperar el intervalo programado.

---

## ⚙️ Archivo de Configuración (`config.json`)

```json
{
  "max_price": 1200000,
  "currency": "ARS",
  "allowed_neighborhoods": [],
  "property_types": ["ph", "casas", "departamentos"],
  "require_outdoor_space": true,
  "min_environments": 2,
  "check_interval_seconds": 600,
  "telegram_bot_token": "",
  "telegram_chat_id": "",
  "google_sheet_webhook_url": ""
}
```

---

## ☁️ Ejecución 24/7 sin servidor propio (Fase 2)

Podés programarlo para que corra cada 5-10 minutos en **GitHub Actions** (100% gratis en la nube) o como un servicio en segundo plano en tu Linux (`systemd` o `crontab`).
