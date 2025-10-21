# process_tickets.py
import pandas as pd
from transformers import pipeline
from tqdm import tqdm
import torch
import argparse
# Se importa la nueva función de RegEx
from utils import find_asset_with_regex, get_text_for_classification

def process_tickets_file(input_file, output_file):
    print("Iniciando el procesamiento del archivo de tickets...")

    device = 0 if torch.cuda.is_available() else -1
    print(f"Dispositivo detectado: {'GPU' if device == 0 else 'CPU'}")

    # ... Carga de modelos (sin cambios) ...
    print("Cargando el modelo de Clasificación...")
    classifier = pipeline("zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli", device=device)
    print("Cargando el modelo NER para extracción de activos...")
    ner_pipeline = pipeline("ner", model="Davlan/bert-base-multilingual-cased-ner-hrl", device=device)
    ticket_categories = ["Redes / Conectividad / Seguridad", "Servidores", "Aplicaciones", "Nube", "Correo"]
    
    print(f"Leyendo el archivo completo: {input_file}...")
    df_full = pd.read_excel(input_file, engine='openpyxl')
    print(f"Archivo leído. {len(df_full)} filas a procesar.")

    # --- FASE 1: EXTRACCIÓN DE ACTIVOS CON REGEX (RÁPIDO) ---
    print("\n--- Fase 1: Extrayendo activos con RegEx... ---")
    
    def get_text_for_ner(row):
        # Función para obtener el texto completo para el análisis
        descripcion = str(row.get('descripción', ''))
        asunto = str(row.get('asunto', ''))
        cierre = str(row.get('cierresolicitud', ''))
        return f"{descripcion} | {asunto} | {cierre}"

    df_full['full_text'] = df_full.apply(get_text_for_ner, axis=1)
    df_full['Activo_Identificado'] = df_full['full_text'].apply(find_asset_with_regex)
    
    # --- FASE 2: EXTRACCIÓN CON IA PARA LOS CASOS FALTANTES ---
    # Seleccionamos solo las filas donde RegEx no encontró nada
    missing_assets_df = df_full[df_full['Activo_Identificado'].isna()].copy()
    
    if not missing_assets_df.empty:
        print(f"\n--- Fase 2: RegEx no encontró activos en {len(missing_assets_df)} filas. Usando IA como respaldo... ---")
        
        texts_for_ner = missing_assets_df['full_text'].tolist()
        
        print("Enviando lote a la GPU para procesamiento NER... (Puede tardar)")
        ner_results_list = ner_pipeline(texts_for_ner, batch_size=16)
        print("Procesamiento NER completado. Analizando resultados...")

        assets_from_ner = []
        for result_group in tqdm(ner_results_list, desc="Post-procesando resultados NER"):
            asset = "No identificado"
            if result_group:
                # Lógica para agrupar entidades fragmentadas (B-ORG, I-ORG, etc.)
                grouped_entities = []
                current_entity = ""
                for entity_dict in result_group:
                    entity_type = entity_dict['entity']
                    if entity_type.startswith('B-'):
                        if current_entity: grouped_entities.append(current_entity)
                        current_entity = entity_dict['word'].replace("##", "")
                    elif entity_type.startswith('I-') and current_entity:
                        current_entity += entity_dict['word'].replace("##", "")
                if current_entity: grouped_entities.append(current_entity)
                
                # Seleccionamos la primera entidad encontrada como el activo
                if grouped_entities: asset = grouped_entities[0]
            assets_from_ner.append(asset)
        
        # Actualizamos el DataFrame principal con los resultados de la IA
        missing_assets_df['Activo_Identificado'] = assets_from_ner
        df_full.update(missing_assets_df)
    else:
        print("\n--- Fase 2: RegEx encontró activos en todas las filas. ¡Excelente! ---")

    # --- FASE 3: CLASIFICACIÓN DE TICKETS (SIN CAMBIOS) ---
    print("\n--- Fase 3: Clasificando tickets... ---")
    df_full['text_for_classification'] = df_full.apply(get_text_for_classification, axis=1)
    texts_to_classify = df_full['text_for_classification'].tolist()

    classification_results = classifier(texts_to_classify, ticket_categories, multi_label=False, batch_size=16)
    df_full['Categoria_Ticket'] = [result['labels'][0] for result in classification_results]
    
    # Limpieza de columnas auxiliares antes de guardar
    df_full.drop(columns=['full_text', 'text_for_classification'], inplace=True)

    print("\nGuardando el archivo final...")
    df_full.to_excel(output_file, index=False)
    
    print(f"✅ ¡Proceso completado! Archivo guardado en: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procesador de Tickets de Mesa de Servicio con IA.")
    parser.add_argument("input_file", type=str, help="Ruta del archivo Excel de entrada.")
    parser.add_argument("output_file", type=str, help="Ruta para guardar el archivo Excel procesado.")
    args = parser.parse_args()
    process_tickets_file(args.input_file, args.output_file)