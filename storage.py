import csv
import os
import json
import logging
from typing import Set
import httpx
from models import Propiedad

logger = logging.getLogger("storage")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "alquileres.csv")
SEEN_FILE = os.path.join(BASE_DIR, "seen_ids.txt")

CSV_HEADERS = [
    "Fecha",
    "Portal",
    "ID",
    "Tipo",
    "Barrio",
    "Dirección",
    "Alquiler (ARS)",
    "Expensas (ARS)",
    "Total Estimado (ARS)",
    "Ambientes",
    "Superficie",
    "Exterior (Balcón/Terraza)",
    "Título",
    "Enlace",
    "Estado (Gestionar en Celular)"
]

def cargar_ids_vistos() -> Set[str]:
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}

def marcar_id_visto(prop_id: str):
    with open(SEEN_FILE, "a", encoding="utf-8") as f:
        f.write(f"{prop_id}\n")

def inicializar_csv_si_no_existe():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(CSV_HEADERS)

def guardar_en_planilla_csv(propiedad: Propiedad):
    inicializar_csv_si_no_existe()
    with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(propiedad.to_csv_row())

def sincronizar_con_google_sheets(propiedad: Propiedad, webhook_url: str):
    """
    Si el usuario configuró una URL de Webhook de Google Apps Script,
    envía la propiedad para que se agregue automáticamente como fila en su Google Sheet.
    """
    if not webhook_url:
        return
    try:
        payload = {
            "fecha": propiedad.fecha_encontrado,
            "portal": propiedad.portal,
            "id": propiedad.id,
            "tipo": propiedad.tipo,
            "barrio": propiedad.barrio,
            "direccion": propiedad.direccion,
            "alquiler": propiedad.precio,
            "expensas": propiedad.expensas,
            "total": propiedad.precio_total,
            "ambientes": propiedad.ambientes,
            "superficie": propiedad.superficie_m2,
            "exterior": propiedad.detalle_exterior if propiedad.tiene_exterior else "No",
            "titulo": propiedad.titulo,
            "url": propiedad.url,
            "estado": "Nuevo"
        }
        resp = httpx.post(webhook_url, json=payload, timeout=10.0)
        if resp.status_code == 200:
            logger.info(f"Sincronizado con Google Sheets: {propiedad.id}")
        else:
            logger.warning(f"Error sincronizando con Google Sheets: HTTP {resp.status_code}")
    except Exception as e:
        logger.error(f"Fallo envío a Google Sheets webhook: {e}")
