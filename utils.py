# utils.py
import re

# Lista de patrones RegEx, ordenados de más específico a más general.
# Son extensibles: puedes añadir más patrones según tus necesidades.
ASSET_PATTERNS = [
    # 1. Nombres de host/servidor que están junto a una IP entre paréntesis
    # Ej: SvrMgMA(10.99.29.42)
    re.compile(r'\b([a-zA-Z0-9\._-]{5,})\s*\(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\)'),

    # 2. Nombres de activos con guiones (formato común para firewalls, switches)
    # Ej: QR5-MAS-FW-01
    re.compile(r'\b([a-zA-Z0-9]+-[a-zA-Z0-9-]+)\b'),

    # 3. Hostnames que aparecen después de 'on' o 'en' (común en alarmas)
    # Ej: "...occurred on spectrumpm3"
    re.compile(r'\b(?:on|en)\s+([a-zA-Z0-9\._-]{6,})\b', re.IGNORECASE),

    # 4. Palabras que contienen "svr", "host", "rtr", "sw" (servidor, router, switch)
    re.compile(r'\b([a-zA-Z0-9\._-]*?(?:svr|host|rtr|sw|fw)[a-zA-Z0-9\._-]*)\b', re.IGNORECASE),
    
    # 5. Direcciones IP v4 (como último recurso si no hay nombre)
    re.compile(r'\b((?:\d{1,3}\.){3}\d{1,3})\b')
]

def find_asset_with_regex(text):
    """
    Busca un activo en un texto dado usando la lista de patrones RegEx.
    Devuelve el primer activo que encuentra.
    """
    if not isinstance(text, str):
        return None

    for pattern in ASSET_PATTERNS:
        match = pattern.search(text)
        if match:
            # Devuelve el primer grupo capturado en la coincidencia
            return match.group(1)
            
    return None # No se encontró ninguna coincidencia

def get_text_for_classification(row):
    """
    Concatena los campos de texto relevantes para una clasificación más precisa.
    """
    asunto = row.get('asunto', '') or ''
    descripcion = row.get('descripción', '') or ''
    
    return f"{asunto}. {descripcion}"