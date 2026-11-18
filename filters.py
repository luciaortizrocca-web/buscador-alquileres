import re
import unicodedata
from models import Propiedad

def normalizar_texto(texto: str) -> str:
    """Elimina tildes y pasa a minúsculas."""
    if not texto:
        return ""
    texto = unicodedata.normalize('NFD', texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.lower().strip()

def cumple_requisitos(propiedad: Propiedad, config: dict) -> tuple[bool, str]:
    """
    Evalúa si la propiedad cumple con los requisitos del usuario.
    Retorna (True, 'OK') o (False, 'Motivo de descarte').
    """
    # 1. Moneda
    if propiedad.moneda != "ARS":
        return False, "Moneda no es ARS"

    # 2. Precio Alquiler y Precio Total
    max_price = config.get("max_price", 1200000)
    if propiedad.precio > max_price:
        return False, f"Alquiler {propiedad.precio} supera {max_price}"
        
    if propiedad.expensas > 0 and propiedad.precio_total > max_price:
        return False, f"Total con expensas {propiedad.precio_total} supera {max_price}"

    # 3. Balcón o Terraza excluyente
    if config.get("require_outdoor_space", True):
        if not propiedad.tiene_exterior:
            return False, "No tiene balcón, terraza o patio detectado"

    # 4. Barrios
    barrios_permitidos = config.get("allowed_neighborhoods", [])
    if barrios_permitidos:
        barrios_norm = [normalizar_texto(b) for b in barrios_permitidos]
        loc_norm = normalizar_texto(f"{propiedad.barrio} {propiedad.direccion} {propiedad.titulo}")
        coincide = any(b in loc_norm for b in barrios_norm)
        if not coincide:
            return False, f"Barrio '{propiedad.barrio}' no está en la lista permitida"

    # 5. Ambientes / Espacio para estudio
    # El usuario busca: 2 dormitorios O 1 dormitorio con living grande para estudio.
    # Descartamos monoambientes puros a menos que tengan estudio/escritorio o > 55m2
    texto_eval = normalizar_texto(f"{propiedad.titulo} {propiedad.ambientes}")
    if "monoambiente" in texto_eval or "1 amb" in texto_eval:
        tiene_estudio = any(k in texto_eval for k in ["estudio", "escritorio", "dividido"])
        m2_num = 0
        match_m2 = re.search(r"(\d+)", propiedad.superficie_m2)
        if match_m2:
            m2_num = int(match_m2.group(1))
        if not tiene_estudio and m2_num < 50:
            return False, "Monoambiente sin estudio o superficie insuficiente"

    # 6. Tipo y Expensas (Evitar amenities y expensas exorbitantes en departamentos)
    if propiedad.tipo.lower() == "departamento" and propiedad.expensas > 200000:
        return False, f"Expensas de {propiedad.expensas} elevadas para el perfil buscado"

    return True, "Cumple todos los requisitos"
