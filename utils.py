# utils.py
import re

# Lista de patrones RegEx, ordenados de más específico a más general.
# Son extensibles: puedes añadir más patrones según tus necesidades.
ASSET_PATTERNS = [
    # --- PATRONES DE MONITOREO (Site24x7, etc.) ---

    # 1. Captura el activo después de "Nombre: "
    # Ej: "Estado:CRITICAL Nombre: gemweb4 Tipo de evento:SERVER"
    # Ej: "Nombre: Oracle_psora05k_pdora10k_tbs"
    re.compile(r'Nombre:\s+([a-zA-Z0-9\._/:-]+(?:\.[a-zA-Z]{2,})?(?:[/\w\.-]*)*)'),

    # 2. Captura el activo después de "Site24x7 [ESTADO] "
    # Ej: "Site24x7 DOWN oracle_cdb_gemrac02_CAJAHIST"
    # Ej: "Site24x7 CRITICAL gemweb4"
    re.compile(r'Site24x7\s+(?:DOWN|CRITICAL|TROUBLE|UP)\s+([a-zA-Z0-9\._/:-]+(?:\.[a-zA-Z]{2,})?(?:[/\w\.-]*)*)', re.IGNORECASE),

    # --- PATRONES DE HOSTNAMES Y FQDN ---

    # 3. Captura FQDN (nombres de dominio completos) y URLs.
    # Ej: "MEXZAPATATEST.fordzapata.com.mx"
    # Ej: "sfpya.edomexico.gob.mx/recaudacion/CtrlVeh/MicRemplaca/"
    # Ej: "MXF5_ELEM_SWCON3K01.elementia.lo_Ethernet1/51/1"
    re.compile(r'\b([a-zA-Z0-9\._-]{4,}\.[a-zA-Z0-9\._-]+\.[a-zA-Z\.]{2,}(?:[/\w\.-]*)*)\b'),

    # 4. Captura el patrón "Hostname(IP)" (incluyendo los paréntesis)
    # Ej: "DCW8754(10.248.204.124)"
    re.compile(r'(\b[a-zA-Z0-9\._-]{4,}\s*\(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\))'),
    
    # 5. Captura nombres de host/servidor después de "Host:" o "Server:"
    # Ej: "Alerta Host: abcexaprod01"
    re.compile(r'\b(?:Host|Server):\s+([a-zA-Z0-9\._-]+)\b', re.IGNORECASE),
    
    # 6. Captura nombres de host/servidor que están junto a una IP (sin capturar la IP)
    # Ej: "SvrMgMA(10.99.29.42)" -> captura "SvrMgMA"
    re.compile(r'\b([a-zA-Z0-9\._-]{5,})\s*\(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\)'),

    # --- PATRONES DE HARDWARE Y GENÉRICOS ---
    
    # 7. Captura modelos de hardware comunes
    # Ej: "HP 840 G4", "DELL E7490"
    re.compile(r'\b((?:HP|DELL)\s+[A-Z0-9 ]{3,12})\b'),

    # 8. Nombres de activos con guiones (formato común)
    # Ej: "QR5-MAS-FW-01"
    re.compile(r'\b([a-zA-Z0-9]+-[a-zA-Z0-9-]{3,})\b'),

    # 9. Palabras clave comunes de infraestructura (svr, host, db, oracle, etc.)
    re.compile(r'\b([a-zA-Z0-9\._-]*?(?:svr|host|rtr|sw|fw|db|oracle|cdb)[a-zA-Z0-9\._-]*)\b', re.IGNORECASE),

    # 10. Hostnames que aparecen después de 'on' o 'en'
    # Ej: "...occurred on spectrumpm3"
    re.compile(r'\b(?:on|en)\s+([a-zA-Z0-9\._-]{6,})\b', re.IGNORECASE),
    
    # 11. Direcciones IP v4 (como último recurso)
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
            # .strip() elimina espacios en blanco al inicio o final
            return match.group(1).strip()
            
    return None # No se encontró ninguna coincidencia

def get_text_for_classification(row):
    """
    Concatena los campos de texto relevantes para una clasificación más precisa.
    """
    asunto = row.get('asunto', '') or ''
    descripcion = row.get('descripción', '') or ''
    
    return f"{asunto}. {descripcion}"