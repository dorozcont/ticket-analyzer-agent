# utils.py
import re

def group_entities(ner_results):
    """
    Función auxiliar para agrupar entidades NER fragmentadas.
    Ej: [..., {'word': 'srv', 'entity': 'B-ORG'}, {'word': '##-web-01', 'entity': 'I-ORG'}] -> "srv-web-01"
    """
    grouped_entities = []
    current_entity = ""
    for result in ner_results:
        entity = result['entity']
        word = result['word']
        
        # Si la entidad empieza con B- (Beginning), empezamos una nueva entidad
        if entity.startswith('B-'):
            # Si ya teníamos una entidad, la guardamos
            if current_entity:
                grouped_entities.append(current_entity)
            current_entity = word
        # Si empieza con I- (Inside), la unimos a la actual
        elif entity.startswith('I-') and current_entity:
            # El "##" indica que es parte de la palabra anterior
            if word.startswith('##'):
                current_entity += word[2:]
            else:
                current_entity += " " + word
    
    # Añadir la última entidad si existe
    if current_entity:
        grouped_entities.append(current_entity)
        
    return grouped_entities

def find_asset_in_text_with_ner(text, ner_pipeline):
    """
    Busca un activo en un texto dado usando un pipeline de NER.
    Devuelve la primera entidad que parece un activo (ORG o MISC).
    """
    if not isinstance(text, str) or not text.strip():
        return None

    # Ejecuta el modelo NER sobre el texto
    ner_results = ner_pipeline(text)

    if not ner_results:
        return None

    # Filtra solo las entidades que nos interesan (ORG o MISC)
    potential_assets = []
    for entity in ner_results:
        # Nos quedamos con entidades de tipo Organización o Misceláneo
        if entity['entity'] in ['B-ORG', 'I-ORG', 'B-MISC', 'I-MISC']:
            potential_assets.append(entity)
    
    if not potential_assets:
        return None
    
    # Agrupamos las palabras que forman una sola entidad y devolvemos la primera
    grouped = group_entities(potential_assets)
    return grouped[0] if grouped else None


def get_asset_from_ticket(row, ner_pipeline):
    """
    Extrae un activo de una fila de ticket usando el modelo NER,
    siguiendo el orden de prioridad: asunto -> descripción -> cierre.
    """
    # 1. Buscar en 'asunto'
    asset = find_asset_in_text_with_ner(row.get('asunto'), ner_pipeline)
    if asset:
        return asset
    
    # 2. Si no se encuentra, buscar en 'descripción'
    asset = find_asset_in_text_with_ner(row.get('descripción'), ner_pipeline)
    if asset:
        return asset

    # 3. Finalmente, buscar en 'cierresolicitud'
    asset = find_asset_in_text_with_ner(row.get('cierresolicitud'), ner_pipeline)
    if asset:
        return asset

    # Si no se encuentra ningún activo en ningún campo
    return "No identificado"

def get_text_for_classification(row):
    """
    Concatena los campos de texto relevantes para una clasificación más precisa.
    """
    asunto = row.get('asunto', '') or ''
    descripcion = row.get('descripción', '') or ''
    
    return f"{asunto}. {descripcion}"