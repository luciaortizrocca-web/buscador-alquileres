import logging
import json
import httpx
from models import Propiedad

logger = logging.getLogger("telegram_bot")

LAST_UPDATE_ID = 0

def enviar_mensaje_telegram(token: str, chat_id: str, texto: str) -> bool:
    if not token or not chat_id:
        logger.warning("Token o Chat ID de Telegram no configurados.")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        resp = httpx.post(url, json=payload, timeout=10.0)
        if resp.status_code == 200:
            return True
        else:
            logger.error(f"Error Telegram {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Error enviando mensaje a Telegram: {e}")
        return False

def enviar_alerta(token: str, chat_id: str, propiedad: Propiedad) -> bool:
    texto = propiedad.formatear_alerta_telegram()
    return enviar_mensaje_telegram(token, chat_id, texto)

def procesar_comandos(token: str, config: dict, config_path: str) -> bool:
    """
    Revisa mensajes pendientes en Telegram mediante getUpdates.
    Retorna True si el usuario pidió ejecutar una búsqueda (/buscar).
    """
    global LAST_UPDATE_ID
    if not token:
        return False
        
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"timeout": 2}
    if LAST_UPDATE_ID > 0:
        params["offset"] = LAST_UPDATE_ID + 1

    pedir_busqueda = False
    try:
        resp = httpx.get(url, params=params, timeout=5.0)
        if resp.status_code != 200:
            return False
        data = resp.json()
        if not data.get("ok"):
            return False

        for update in data.get("result", []):
            LAST_UPDATE_ID = max(LAST_UPDATE_ID, update.get("update_id", 0))
            msg = update.get("message", {})
            texto = msg.get("text", "").strip()
            chat_id = str(msg.get("chat", {}).get("id", ""))
            
            if not texto or not chat_id:
                continue

            # Auto-registrar el chat_id si no estaba guardado
            if not config.get("telegram_chat_id"):
                config["telegram_chat_id"] = chat_id
                guardar_config(config, config_path)
                enviar_mensaje_telegram(token, chat_id, "🤖 *¡Bot vinculado con éxito!*\nTu Chat ID ha sido configurado.")

            partes = texto.split(maxsplit=1)
            comando = partes[0].lower()
            arg = partes[1].strip() if len(partes) > 1 else ""

            if comando in ["/start", "/ayuda", "/help"]:
                respuesta = (
                    "👋 *¡Bienvenido al Buscador de Alquileres!*\n\n"
                    "Comandos que podés usar desde tu celular:\n"
                    "• `/barrios`: Ver los barrios configurados.\n"
                    "• `/barrios palermo, colegiales, caballito`: Actualizar tus barrios.\n"
                    "• `/barrios todos`: Buscar en toda CABA.\n"
                    "• `/precio 1200000`: Cambiar tu presupuesto máximo.\n"
                    "• `/status`: Ver filtros y cantidad de alquileres en la planilla.\n"
                    "• `/buscar`: Forzar una búsqueda de propiedades ahora mismo."
                )
                enviar_mensaje_telegram(token, chat_id, respuesta)

            elif comando == "/barrios":
                if arg:
                    if arg.lower() in ["todos", "all", "caba"]:
                        config["allowed_neighborhoods"] = []
                        guardar_config(config, config_path)
                        enviar_mensaje_telegram(token, chat_id, "✅ *Búsqueda ampliada a toda CABA*.")
                    else:
                        lista_barrios = [b.strip() for b in arg.split(",") if b.strip()]
                        config["allowed_neighborhoods"] = lista_barrios
                        guardar_config(config, config_path)
                        barrios_txt = ", ".join(lista_barrios)
                        enviar_mensaje_telegram(token, chat_id, f"✅ *Barrios actualizados*: {barrios_txt}")
                else:
                    barrios = config.get("allowed_neighborhoods", [])
                    if barrios:
                        barrios_txt = ", ".join(barrios)
                        enviar_mensaje_telegram(token, chat_id, f"📍 *Barrios activos*: {barrios_txt}\n\nPara cambiarlos: `/barrios almagro, urquiza`")
                    else:
                        enviar_mensaje_telegram(token, chat_id, "📍 *Barrios activos*: Toda CABA (sin restricción).\n\nPara limitar: `/barrios palermo, caballito`")

            elif comando == "/precio":
                if arg:
                    digits = "".join(c for c in arg if c.isdigit())
                    if digits:
                        nuevo_precio = int(digits)
                        config["max_price"] = nuevo_precio
                        guardar_config(config, config_path)
                        precio_fmt = f"{nuevo_precio:,}".replace(",", ".")
                        enviar_mensaje_telegram(token, chat_id, f"✅ *Presupuesto máximo actualizado*: $ {precio_fmt} ARS")
                    else:
                        enviar_mensaje_telegram(token, chat_id, "⚠️ Por favor ingresá un número. Ejemplo: `/precio 1100000`")
                else:
                    precio_fmt = f"{config.get('max_price', 1200000):,}".replace(",", ".")
                    enviar_mensaje_telegram(token, chat_id, f"💰 *Presupuesto actual*: $ {precio_fmt} ARS")

            elif comando == "/status":
                from storage import cargar_ids_vistos
                ids = cargar_ids_vistos()
                barrios = config.get("allowed_neighborhoods", [])
                barrios_txt = ", ".join(barrios) if barrios else "Toda CABA"
                precio_fmt = f"{config.get('max_price', 1200000):,}".replace(",", ".")
                
                estado = (
                    "📊 *Estado del Monitor de Alquileres*\n\n"
                    f"• *Presupuesto Máx*: $ {precio_fmt} ARS\n"
                    f"• *Barrios*: {barrios_txt}\n"
                    f"• *Excluyente Balcón/Terraza*: {'Sí' if config.get('require_outdoor_space') else 'No'}\n"
                    f"• *Propiedades registradas en planilla*: {len(ids)}\n"
                    f"• *Portales activos*: Mercado Libre, Argenprop"
                )
                enviar_mensaje_telegram(token, chat_id, estado)

            elif comando == "/buscar":
                enviar_mensaje_telegram(token, chat_id, "🔎 *Iniciando rastreo inmediato de alquileres...* Te avisaré lo nuevo que encuentre.")
                pedir_busqueda = True

    except Exception as e:
        logger.error(f"Error procesando comandos de Telegram: {e}")
        
    return pedir_busqueda

def guardar_config(config: dict, config_path: str):
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando config: {e}")
