# utils.py
import re

# Lista de patrones RegEx, ordenados de más específico a más general.
ASSET_PATTERNS = [
    # --- 1. Patrones Específicos (Prioridad Más Alta) ---

    # Ej: "PROSA T8tldm0111 (192.168.107.21)" -> Captura "T8tldm0111"
    # ¡MOVIDA AL INICIO! Esta regla es la más fiable para este formato.
    re.compile(r'\b([a-zA-Z0-9\._-]{5,})\s*\(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\)'), 

    # Ej: "Site24x7 CRITICAL QR5-MAS-FW-01" -> Captura "QR5-MAS-FW-01"
    re.compile(r'Site24x7\s+(?:DOWN|CRITICAL|TROUBLE|UP)\s+([a-zA-Z0-9\._/:-]+)', re.IGNORECASE),

    # Ej: "URL_CFDI33_FACEMASNEGOCIO($HOSTIP)" -> Captura "URL_CFDI33_FACEMASNEGOCIO"
    re.compile(r'\b(URL_[A-Z0-9_]+)\b'),

    # Ej: "PROSA alerta de informacion Crítico para Servidor T8tldm0209"
    re.compile(r'\b(?:Servidor|Monitor|Host):\s+([a-zA-Z0-9\._-]+)\b', re.IGNORECASE),

    # Ej: "Status_DB_PDBOTOOL2_2024-01-11_08:00" -> Captura "PDBOTOOL2"
    re.compile(r'\bStatus_DB_([a-zA-Z0-9]+)_'),

    # Ej: "Name DB: PDBOECMC"
    re.compile(r'\bName DB:\s+([a-zA-Z0-9\._-]+)\b', re.IGNORECASE),
    
    # Ej: "Nombre: gemweb4"
    re.compile(r'Nombre:\s+([a-zA-Z0-9\._/:-]+(?:\.[a-zA-Z]{2,})?(?:[/\w\.-]*)*)'),

    # --- 2. Patrones de Nomenclatura (Guiones, FQDN) ---

    # Ej: "S6509-B-CORE-SF" o "QR5-MAS-FW-01"
    # MODIFICADA: Ahora requiere que la primera parte contenga al menos una letra.
    # Esto evita que coincida con "2024-01-08".
    re.compile(r'\b([a-zA-Z0-9]*[a-zA-Z][a-zA-Z0-9]*-[a-zA-Z0-9-]{3,})\b'),

    # Ej: FQDN como "mexzapatatest.fordzapata.com.mx"
    re.compile(r'\b([a-zA-Z0-9\._-]{4,}\.[a-zA-Z0-9\._-]+\.[a-zA-Z\.]{2,}(?:[/\w\.-]*)*)\b'),
    
    # --- 3. Patrones de Hardware y Seriales ---
    re.compile(r'\b((?:DELL|HP|LENOVO|IMPRESORA|LAPTOP)[\w\d-]{10,})\b', re.IGNORECASE),
    re.compile(r'\b((?:HP|DELL)\s+[A-Z0-9 ]{3,12})\b', re.IGNORECASE),

    # --- 4. Patrones Genéricos (Prioridad Baja) ---
    re.compile(r'\b(WIN-[\w\d]{10,})\b'),
    re.compile(r'\b([a-zA-Z]{2,}[0-9]{1,}[a-zA-Z0-9]+|[a-zA-Z]+[0-9]{1,}[a-zA-Z]{2,})[0-9]{1,}\b'),
    re.compile(r'\b(NIMSOFT|WEBLOGIC|ORACLE|PDB[A-Z0-9]+)\b', re.IGNORECASE),
    re.compile(r'\b(?:on|en)\s+([a-zA-Z0-9\._-]{6,})\b', re.IGNORECASE),

    # --- 5. Patrón de Último Recurso (Captura IPs si todo lo demás falla) ---
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
            return match.group(1).strip()
            
    return None # No se encontró ninguna coincidencia

def get_text_for_classification(row):
    """
    Concatena los campos de texto relevantes para una clasificación más precisa.
    """
    asunto = row.get('asunto', '') or ''
    descripcion = row.get('descripción', '') or ''
    
    return f"{asunto}. {descripcion}"