import re
import logging
import urllib.parse
from typing import List, Optional
import httpx
from bs4 import BeautifulSoup
from models import Propiedad

logger = logging.getLogger("scrapers.mercadolibre")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
    "Referer": "https://inmuebles.mercadolibre.com.ar/",
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

def buscar_mercadolibre(tipo_cat: str, max_price: int, client: httpx.Client, scraper_api_key: str = "") -> List[Propiedad]:
    """
    tipo_cat: 'ph', 'casas', 'departamentos'
    """
    raw_url = f"https://inmuebles.mercadolibre.com.ar/{tipo_cat}/alquiler/capital-federal/_PriceRange_0ARS-{max_price}ARS"
    
    if scraper_api_key:
        req_url = f"http://api.scraperapi.com?api_key={scraper_api_key}&url={urllib.parse.quote(raw_url)}&country_code=ar"
        req_headers = {}
    else:
        req_url = raw_url
        req_headers = HEADERS

    propiedades = []
    
    try:
        resp = client.get(req_url, headers=req_headers, timeout=35.0, follow_redirects=True)
        if resp.status_code != 200:
            logger.warning(f"ML respondió con status {resp.status_code} para {tipo_cat}")
            return propiedades
            
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".ui-search-layout__item")
        
        for item in items:
            link_elem = item.select_one("a.poly-component__title, a.ui-search-link, a")
            if not link_elem or "href" not in link_elem.attrs:
                continue
            url_item = link_elem["href"].split("#")[0]
            
            # Extraer ID
            match_id = re.search(r"(MLA-?\d+)", url_item)
            item_id = match_id.group(1).replace("-", "") if match_id else url_item
            
            # Título
            title_elem = item.select_one(".poly-component__title, .ui-search-item__title")
            titulo = title_elem.get_text(strip=True) if title_elem else "Sin título"
            
            # Precio y Moneda
            curr_elem = item.select_one(".andes-money-amount__currency-symbol, .price-tag-symbol")
            moneda_sym = curr_elem.get_text(strip=True) if curr_elem else "$"
            if "u$s" in moneda_sym.lower() or "usd" in moneda_sym.lower():
                continue  # Solo ARS
                
            price_elem = item.select_one(".poly-price__current .andes-money-amount__fraction, .price-tag-fraction")
            if not price_elem:
                continue
            precio_raw = re.sub(r"[^\d]", "", price_elem.get_text(strip=True))
            if not precio_raw:
                continue
            precio = int(precio_raw)
            if precio > max_price:
                continue
                
            # Ubicación y Barrio
            loc_elem = item.select_one(".poly-component__location, .ui-search-item__group__element.ui-search-item__location")
            loc_text = loc_elem.get_text(strip=True) if loc_elem else "Capital Federal"
            partes_loc = [p.strip() for p in loc_text.split(",")]
            if len(partes_loc) >= 3:
                direccion = partes_loc[0]
                barrio = partes_loc[1]
            elif len(partes_loc) == 2:
                direccion = partes_loc[0]
                barrio = partes_loc[0] if "capital" in partes_loc[1].lower() else partes_loc[1]
            else:
                direccion = loc_text
                barrio = loc_text
                
            # Atributos (ambientes, m2)
            card_texts = list(item.stripped_strings)
            card_all_text = " ".join(card_texts)
            
            ambientes = ""
            m2 = ""
            for t in card_texts:
                if "amb" in t.lower():
                    ambientes = t
                elif "m²" in t.lower() or "m2" in t.lower():
                    m2 = t
                    
            # Detección de exterior en la tarjeta o título
            tiene_ext, det_ext = detectar_exterior(card_all_text + " " + titulo)
            expensas = 0
            
            # Buscar mención de expensas en el texto de la tarjeta
            match_exp = re.search(r"expensas[:\s]+\$?\s*([\d\.]+)", card_all_text, re.IGNORECASE)
            if match_exp:
                expensas = int(match_exp.group(1).replace(".", ""))
                    
            tipo_nombre = "PH" if tipo_cat == "ph" else ("Casa" if tipo_cat == "casas" else "Departamento")
            
            p = Propiedad(
                id=f"MLA_{item_id}",
                portal="Mercado Libre",
                titulo=titulo,
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
        logger.error(f"Error buscando en Mercado Libre {tipo_cat}: {e}")
        
    return propiedades
