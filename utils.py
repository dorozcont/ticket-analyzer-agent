# utils.py
import re

# Lista de patrones RegEx, ordenados de más específico a más general.
ASSET_PATTERNS = [
    # --- 1. Patrones de Monitoreo Específicos (Prioridad Más Alta) ---

    # Ej: "Site24x7 CRITICAL QR5-MAS-FW-01" -> Captura "QR5-MAS-FW-01"
    re.compile(r'Site24x7\s+(?:DOWN|CRITICAL|TROUBLE|UP)\s+([a-zA-Z0-9\._/:-]+)', re.IGNORECASE),

    # Ej: "PROSA alerta de informacion Crítico para Servidor T8tldm0209"
    re.compile(r'\b(?:Servidor|Monitor|Host):\s+([a-zA-Z0-9\._-]+)\b', re.IGNORECASE),

    # Ej: "Status_DB_PDBOTOOL2_2024-01-11_08:00" -> Captura "PDBOTOOL2"
    re.compile(r'\bStatus_DB_([a-zA-Z0-9]+)_'),

    # Ej: "Name DB: PDBOECMC"
    re.compile(r'\bName DB:\s+([a-zA-Z0-9\._-]+)\b', re.IGNORECASE),
    
    # Ej: "Nombre: gemweb4"
    re.compile(r'Nombre:\s+([a-zA-Z0-9\._/:-]+(?:\.[a-zA-Z]{2,})?(?:[/\w\.-]*)*)'),

    # --- 2. Patrones de Nomenclatura Específicos (Nombres con guiones, FQDN) ---

    # Ej: "QR5-MAS-FW-01" (Debe empezar con letras y tener guiones)
    re.compile(r'\b([a-zA-Z]{2,}[0-9]?-[\w-]{3,})\b'),

    # Ej: FQDN como "mexzapatatest.fordzapata.com.mx"
    re.compile(r'\b([a-zA-Z0-9\._-]{4,}\.[a-zA-Z0-9\._-]+\.[a-zA-Z\.]{2,}(?:[/\w\.-]*)*)\b'),

    # Ej: "SvrMgMA(10.99.29.42)" -> captura "SvrMgMA"
    re.compile(r'\b([a-zA-Z0-9\._-]{5,})\s*\(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\)'),
    
    # --- 3. Patrones de Hardware y Seriales ---

    # Ej: "IMPRESORADELL2335DN...", "LAP TOPLENOVOL490PF..."
    re.compile(r'\b((?:DELL|HP|LENOVO|IMPRESORA|LAPTOP)[\w\d-]{10,})\b', re.IGNORECASE),
    
    # Ej: "HP 840 G4", "DELL E7490"
    re.compile(r'\b((?:HP|DELL)\s+[A-Z0-9 ]{3,12})\b', re.IGNORECASE),

    # --- 4. Patrones Genéricos (Prioridad Baja - Causante del error anterior) ---

    # Ej: "WIN-54FQ4PQ3M5Q" (de alertas Velocity)
    re.compile(r'\b(WIN-[\w\d]{10,})\b'),

    # Ej: "MEXZAPATANRH1" (combinación de letras y números, min 6 caracteres)
    # Movida al final porque es muy genérica y capturaba "Site24x7"
    re.compile(r'\b([a-zA-Z]{2,}[0-9]{1,}[a-zA-Z0-9]+|[a-zA-Z]+[0-9]{1,}[a-zA-Z]{2,})[0-9]{1,}\b'),

    # Ej: Palabras clave como "NIMSOFT", "WEBLOGIC", "PDBOECMC"
    re.compile(r'\b(NIMSOFT|WEBLOGIC|ORACLE|PDB[A-Z0-9]+)\b', re.IGNORECASE),

    # Ej: "...occurred on spectrumpm3"
    re.compile(r'\b(?:on|en)\s+([a-zA-Z0-9\._-]{6,})\b', re.IGNORECASE),
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