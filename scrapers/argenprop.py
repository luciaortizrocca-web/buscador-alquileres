import re
import logging
from typing import List
import httpx
from bs4 import BeautifulSoup
from models import Propiedad

logger = logging.getLogger("scrapers.argenprop")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
}

def detectar_exterior(texto: str) -> tuple[bool, str]:
    texto_l = texto.lower()
    hallazgos = []
    if "terraza" in texto_l:
        hallazgos.append("Terraza")
    if "balcon" in texto_l or "balcón" in texto_l:
        hallazgos.append("Balcón")
    if "patio" in texto_l:
        hallazgos.append("Patio")
    if "jardin" in texto_l or "jardín" in texto_l:
        hallazgos.append("Jardín")
    
    if hallazgos:
        return True, ", ".join(hallazgos)
    return False, ""

def buscar_argenprop(tipo_cat: str, max_price: int, client: httpx.Client) -> List[Propiedad]:
    """
    tipo_cat: 'ph', 'departamento', 'casa'
    """
    url = f"https://www.argenprop.com/{tipo_cat}-alquiler-localidad-capital-federal-hasta-{max_price}-pesos"
    propiedades = []
    
    try:
        resp = client.get(url, headers=HEADERS, timeout=15.0, follow_redirects=True)
        if resp.status_code != 200:
            logger.warning(f"Argenprop respondió con status {resp.status_code} para {tipo_cat}")
            return propiedades
            
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".listing__item")
        
        for item in items:
            link_elem = item.select_one("a")
            if not link_elem or "href" not in link_elem.attrs:
                continue
            path = link_elem["href"]
            url_item = f"https://www.argenprop.com{path}" if path.startswith("/") else path
            
            # Extraer ID de la URL
            match_id = re.search(r"--(\d+)", url_item)
            item_id = match_id.group(1) if match_id else url_item.split("/")[-1]
            
            # Precio
            price_elem = item.select_one(".card__price")
            if not price_elem:
                continue
            price_text = price_elem.get_text(strip=True)
            if "u$s" in price_text.lower() or "usd" in price_text.lower():
                continue
            precio_digits = re.sub(r"[^\d]", "", price_text)
            if not precio_digits:
                continue
            precio = int(precio_digits)
            if precio > max_price:
                continue
                
            # Expensas
            expensas = 0
            exp_elem = item.select_one(".card__expenses")
            if exp_elem:
                exp_digits = re.sub(r"[^\d]", "", exp_elem.get_text(strip=True))
                if exp_digits:
                    expensas = int(exp_digits)
                    
            # Dirección y Barrio
            loc_elem = item.select_one(".card__address")
            loc_text = loc_elem.get_text(strip=True) if loc_elem else "Capital Federal"
            partes_loc = [p.strip() for p in loc_text.split(",")]
            if len(partes_loc) >= 2:
                direccion = partes_loc[0]
                barrio = partes_loc[1]
            else:
                direccion = loc_text
                barrio = loc_text
                
            # Título y Descripción
            card_all_text = " ".join(item.stripped_strings)
            title_elem = item.select_one(".card__title--primary, .card__title")
            titulo = title_elem.get_text(strip=True) if title_elem else "Propiedad en alquiler"
            
            # Ambientes y M2
            ambientes = ""
            m2 = ""
            for tag in item.select(".card__main-features li, .card__feature"):
                feat = tag.get_text(strip=True)
                if "amb" in feat.lower():
                    ambientes = feat
                elif "m²" in feat.lower():
                    m2 = feat
            if not ambientes:
                match_amb = re.search(r"(\d+\s*amb(?:ientes)?)", card_all_text, re.IGNORECASE)
                if match_amb:
                    ambientes = match_amb.group(1)
            if not m2:
                match_m2 = re.search(r"(\d+\s*m²)", card_all_text)
                if match_m2:
                    m2 = match_m2.group(1)
                    
            tiene_ext, det_ext = detectar_exterior(card_all_text)
            
            tipo_nombre = "PH" if tipo_cat == "ph" else ("Casa" if tipo_cat == "casa" else "Departamento")
            
            p = Propiedad(
                id=f"ARG_{item_id}",
                portal="Argenprop",
                titulo=titulo if titulo else f"{tipo_nombre} en {barrio}",
                tipo=tipo_nombre,
                precio=precio,
                expensas=expensas,
                moneda="ARS",
                barrio=barrio,
                direccion=direccion,
                ambientes=ambientes if ambientes else "No especifica",
                superficie_m2=m2 if m2 else "No especifica",
                tiene_exterior=tiene_ext,
                detalle_exterior=det_ext,
                url=url_item
            )
            propiedades.append(p)
            
    except Exception as e:
        logger.error(f"Error buscando en Argenprop {tipo_cat}: {e}")
        
    return propiedades
