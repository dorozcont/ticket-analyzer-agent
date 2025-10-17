# process_tickets.py
import pandas as pd
from transformers import pipeline
from tqdm import tqdm
import torch
import argparse
from utils import get_asset_from_ticket, get_text_for_classification

# --- FUNCIÓN AUXILIAR PARA PROCESAMIENTO POR LOTES ---
# Modificamos esta función para que acepte el pipeline como argumento
def extract_asset_from_batch(row, ner_results_map):
    """
    Busca el resultado del NER pre-calculado para una fila específica.
    """
    # Usamos el índice de la fila para buscar su resultado en el mapa
    return ner_results_map.get(row.name, "No identificado")

def process_tickets_file(input_file, output_file):
    print("Iniciando el procesamiento del archivo de tickets...")

    device = 0 if torch.cuda.is_available() else -1
    print(f"Dispositivo detectado: {'GPU' if device == 0 else 'CPU'}")

    print("Cargando el modelo de Clasificación...")
    classifier = pipeline("zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli", device=device)
    
    print("Cargando el modelo NER para extracción de activos...")
    ner_pipeline = pipeline("ner", model="Davlan/bert-base-multilingual-cased-ner-hrl", device=device)
    
    ticket_categories = ["Redes / Conectividad / Seguridad", "Servidores", "Aplicaciones", "Nube", "Correo"]
    
    print(f"Leyendo el archivo completo: {input_file}...")
    try:
        df_full = pd.read_excel(input_file, engine='openpyxl')
        print(f"Archivo leído correctamente en memoria. {len(df_full)} filas a procesar.")
    except Exception as e:
        print(f"Error crítico al leer el archivo Excel: {e}")
        exit()

    # --- PROCESAMIENTO POR LOTES PARA EXTRACCIÓN DE ACTIVOS (OPTIMIZADO) ---
    print("Extrayendo activos (procesamiento por lotes)...")
    # 1. Creamos la lista de textos a procesar, siguiendo la misma lógica de prioridad
    texts_for_ner = []
    for index, row in df_full.iterrows():
        asunto = row.get('asunto', '') or ''
        descripcion = row.get('descripción', '') or ''
        cierre = row.get('cierresolicitud', '') or ''
        # Concatenamos todo para darle el máximo contexto al modelo NER
        texts_for_ner.append(f"{asunto} | {descripcion} | {cierre}")

    # 2. Pasamos la lista completa al pipeline del NER
    # El batch_size le dice al pipeline cuántos textos procesar a la vez en la GPU
    ner_results_list = ner_pipeline(texts_for_ner, batch_size=16)

    # 3. Procesamos los resultados para extraer solo la primera entidad (el activo)
    final_assets = []
    for result_group in tqdm(ner_results_list, desc="Procesando resultados NER"):
        asset = "No identificado"
        # La salida del pipeline puede ser una lista de entidades para cada texto
        if result_group:
            # Agrupamos las entidades fragmentadas (ej: 'srv', '-', 'web')
            grouped_entities = []
            current_entity = ""
            for entity_dict in result_group:
                word = entity_dict['word']
                if entity_dict['entity'].startswith('B-'):
                    if current_entity: grouped_entities.append(current_entity)
                    current_entity = word.replace("##", "")
                elif entity_dict['entity'].startswith('I-') and current_entity:
                    current_entity += word.replace("##", "")
            if current_entity: grouped_entities.append(current_entity)

            if grouped_entities:
                asset = grouped_entities[0] # Nos quedamos con la primera entidad encontrada
        final_assets.append(asset)
        
    df_full['Activo_Identificado'] = final_assets

    # --- PROCESAMIENTO POR LOTES PARA CLASIFICACIÓN ---
    print("Clasificando tickets (procesamiento por lotes)...")
    texts_to_classify = df_full.apply(get_text_for_classification, axis=1).tolist()
    classification_results = classifier(texts_to_classify, ticket_categories, multi_label=False, batch_size=16)
    df_full['Categoria_Ticket'] = [result['labels'][0] for result in classification_results]
    
    print("Guardando el archivo final...")
    df_full.to_excel(output_file, index=False)
    
    print(f"✅ ¡Proceso completado! Archivo guardado en: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procesador de Tickets de Mesa de Servicio con IA.")
    parser.add_argument("input_file", type=str, help="Ruta del archivo Excel de entrada.")
    parser.add_argument("output_file", type=str, help="Ruta para guardar el archivo Excel procesado.")
    args = parser.parse_args()
    process_tickets_file(args.input_file, args.output_file)