import os
import sys
import time
import json
import logging
import argparse
import httpx

from models import Propiedad
from storage import cargar_ids_vistos, marcar_id_visto, guardar_en_planilla_csv, sincronizar_con_google_sheets
from filters import cumple_requisitos
from scrapers.mercadolibre import buscar_mercadolibre
from scrapers.argenprop import buscar_argenprop
import telegram_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("buscador_alquileres")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def cargar_config() -> dict:
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        config["telegram_bot_token"] = os.environ["TELEGRAM_BOT_TOKEN"]
    if os.environ.get("TELEGRAM_CHAT_ID"):
        config["telegram_chat_id"] = os.environ["TELEGRAM_CHAT_ID"]
    return config

def ejecutar_ciclo_busqueda(config: dict) -> int:
    """
    Ejecuta un ciclo completo de rastreo, filtrado, guardado en planilla y notificación.
    Retorna la cantidad de propiedades nuevas encontradas y notificadas.
    """
    logger.info("Iniciando escaneo de portales inmobiliarios...")
    ids_vistos = cargar_ids_vistos()
    max_price = config.get("max_price", 1200000)
    token = config.get("telegram_bot_token", "")
    chat_id = config.get("telegram_chat_id", "")
    sheet_webhook = config.get("google_sheet_webhook_url", "")
    
    todas_encontradas = []
    
    with httpx.Client(timeout=15.0) as client:
        # 1. Mercado Libre
        tipos_ml = []
        if "ph" in config.get("property_types", []):
            tipos_ml.append("ph")
        if "casas" in config.get("property_types", []):
            tipos_ml.append("casas")
        if "departamentos" in config.get("property_types", []):
            tipos_ml.append("departamentos")
            
        for t in tipos_ml:
            logger.info(f"Buscando en Mercado Libre: {t} (hasta ${max_price:,} ARS)")
            props_ml = buscar_mercadolibre(t, max_price, client)
            todas_encontradas.extend(props_ml)
            
        # 2. Argenprop
        tipos_arg = []
        if "ph" in config.get("property_types", []):
            tipos_arg.append("ph")
        if "casas" in config.get("property_types", []):
            tipos_arg.append("casa")
        if "departamentos" in config.get("property_types", []):
            tipos_arg.append("departamento")
            
        for t in tipos_arg:
            logger.info(f"Buscando en Argenprop: {t} (hasta ${max_price:,} ARS)")
            props_arg = buscar_argenprop(t, max_price, client)
            todas_encontradas.extend(props_arg)

    logger.info(f"Total avisos recolectados en crudo: {len(todas_encontradas)}")
    
    nuevas_validas = 0
    for p in todas_encontradas:
        if p.id in ids_vistos:
            continue
            
        cumple, motivo = cumple_requisitos(p, config)
        if not cumple:
            # Descartada por filtros
            continue
            
        logger.info(f"✨ ¡Propiedad encontrada que cumple!: {p.tipo} en {p.barrio} - ${p.precio:,} ARS | {p.detalle_exterior}")
        
        # 1. Guardar en la Planilla CSV
        guardar_en_planilla_csv(p)
        
        # 2. Sincronizar en Google Sheets si está configurado
        if sheet_webhook:
            sincronizar_con_google_sheets(p, sheet_webhook)
            
        # 3. Enviar Alerta a Telegram
        if token and chat_id:
            telegram_bot.enviar_alerta(token, chat_id, p)
            
        # 4. Marcar como vista
        marcar_id_visto(p.id)
        ids_vistos.add(p.id)
        nuevas_validas += 1

    logger.info(f"Ciclo finalizado. Nuevas oportunidades notificadas: {nuevas_validas}")
    return nuevas_validas

def main():
    parser = argparse.ArgumentParser(description="Monitor y Alerta de Alquileres CABA")
    parser.add_argument("--once", action="store_true", help="Ejecutar un solo escaneo y salir")
    parser.add_argument("--daemon", action="store_true", help="Ejecutar en bucle continuo de monitoreo")
    parser.add_argument("--test-telegram", action="store_true", help="Enviar mensaje de prueba a Telegram")
    args = parser.parse_args()

    config = cargar_config()
    token = config.get("telegram_bot_token", "")
    chat_id = config.get("telegram_chat_id", "")

    if args.test_telegram:
        if not token or not chat_id:
            print("❌ Falta configurar telegram_bot_token o telegram_chat_id en config.json")
            sys.exit(1)
        prop_demo = Propiedad(
            id="DEMO-12345",
            portal="Mercado Libre",
            titulo="Hermoso PH 3 Ambientes con Terraza Propia y Parrilla - Sin Expensas",
            tipo="PH",
            precio=850000,
            expensas=0,
            moneda="ARS",
            barrio="Colegiales",
            direccion="Conesa al 1200",
            ambientes="3 amb.",
            superficie_m2="65 m²",
            tiene_exterior=True,
            detalle_exterior="Terraza y Balcón",
            url="https://inmueble.mercadolibre.com.ar/MLA-4135554580-ph-4-ambientes-en-liniers-con-3-dormitorios-terraza-propia-y-dos-plantas-_JM"
        )
        print("Enviando mensaje de prueba a Telegram...")
        exito = telegram_bot.enviar_alerta(token, chat_id, prop_demo)
        if exito:
            print("✅ Mensaje de prueba enviado con éxito a tu Telegram!")
        else:
            print("❌ Hubo un error enviando el mensaje.")
        return

    if args.once:
        ejecutar_ciclo_busqueda(config)
        return

    if args.daemon:
        logger.info("Iniciando servicio de monitoreo en segundo plano (Daemon)...")
        intervalo = config.get("check_interval_seconds", 600)
        ultimo_escaneo = 0

        while True:
            ahora = time.time()
            config_actual = cargar_config()
            token_actual = config_actual.get("telegram_bot_token", "")
            
            # Revisar comandos de Telegram frecuentemente (cada 3-5 segs)
            solicito_busqueda = False
            if token_actual:
                solicito_busqueda = telegram_bot.procesar_comandos(token_actual, config_actual, CONFIG_PATH)

            # Ejecutar escaneo si pasó el intervalo o si el usuario lo pidió por Telegram con /buscar
            if solicito_busqueda or (ahora - ultimo_escaneo >= intervalo):
                ejecutar_ciclo_busqueda(config_actual)
                ultimo_escaneo = time.time()

            time.sleep(4)

    # Por defecto, si no se pasan argumentos, ejecutar una vez
    ejecutar_ciclo_busqueda(config)

if __name__ == "__main__":
    main()
