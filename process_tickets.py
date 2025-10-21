# process_tickets.py
import pandas as pd
from transformers import pipeline
from tqdm import tqdm
import torch
import argparse
# Se importa la nueva función de RegEx
from utils import find_asset_with_regex, get_text_for_classification
import warnings

# Suprimir advertencias futuras de Pandas y HuggingFace (opcional, para limpieza de log)
warnings.simplefilter(action='ignore', category=FutureWarning)

def process_tickets_file(input_file, output_file):
    print("Iniciando el procesamiento del archivo de tickets...")

    device = 0 if torch.cuda.is_available() else -1
    print(f"Dispositivo detectado: {'GPU' if device == 0 else 'CPU'}")

    # --- Carga de Modelos de IA ---
    print("Cargando el modelo de Clasificación...")
    classifier = pipeline("zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli", device=device)
    print("Cargando el modelo NER para extracción de activos...")
    # Usamos "aggregation_strategy=simple" para que el modelo agrupe entidades (ej. "Alejandro", "Javier" -> "Alejandro Javier")
    ner_pipeline = pipeline("ner", model="Davlan/bert-base-multilingual-cased-ner-hrl", device=device, aggregation_strategy="simple")
    
    ticket_categories = ["Redes / Conectividad / Seguridad", "Servidores", "Aplicaciones", "Nube", "Correo"]
    
    print(f"Leyendo el archivo completo: {input_file}...")
    df_full = pd.read_excel(input_file, engine='openpyxl')
    print(f"Archivo leído. {len(df_full)} filas a procesar.")

    # --- FASE 1: EXTRACCIÓN DE ACTIVOS CON REGEX (RÁPIDO) ---
    print("\n--- Fase 1: Extrayendo activos con RegEx... ---")
    
    def get_text_for_ner(row):
        # Función para obtener el texto completo para el análisis
        asunto = str(row.get('asunto', ''))
        descripcion = str(row.get('descripción', ''))
        cierre = str(row.get('cierresolicitud', ''))
        return f"{asunto} | {descripcion} | {cierre}"

    df_full['full_text'] = df_full.apply(get_text_for_ner, axis=1)
    df_full['Activo_Identificado'] = df_full['full_text'].apply(find_asset_with_regex)
    
    # --- FASE 2: EXTRACCIÓN CON IA PARA LOS CASOS FALTANTES ---
    # Seleccionamos solo las filas donde RegEx no encontró nada (NaN/None)
    missing_assets_mask = df_full['Activo_Identificado'].isna()
    missing_assets_df = df_full[missing_assets_mask].copy()
    
    if not missing_assets_df.empty:
        print(f"\n--- Fase 2: RegEx no encontró activos en {len(missing_assets_df)} filas. Usando IA como respaldo... ---")
        
        texts_for_ner = missing_assets_df['full_text'].tolist()
        
        print("Enviando lote a la GPU para procesamiento NER... (Puede tardar)")
        # El batch_size=8 es un buen equilibrio para la GPU
        ner_results_list = ner_pipeline(texts_for_ner, batch_size=8)
        print("Procesamiento NER completado. Analizando resultados...")

        assets_from_ner = []
        
        # Usamos tqdm para ver el progreso del post-procesamiento
        for result_group in tqdm(ner_results_list, desc="Post-procesando resultados NER"):
            asset = "No identificado"
            
            # ======== INICIO DE LÓGICA DE FILTRADO DE IA ========
            # Iteramos sobre las entidades encontradas (ej. [{'entity_group': 'PER', 'word': 'Alejandro...'}, {'entity_group': 'ORG', 'word': '...'}])
            
            # 1. Filtramos para quedarnos SÓLO con ORG (Organización) o MISC (Misceláneo)
            valid_entities = [
                entity['word'] for entity in result_group 
                if entity['entity_group'] in ['ORG', 'MISC']
            ]
            
            # 2. Si encontramos entidades válidas, tomamos la primera
            if valid_entities:
                asset = valid_entities[0]
            # Si no hay entidades ORG o MISC, 'asset' permanecerá como "No identificado"
            # Esto evita que se seleccionen nombres de personas (PER) o lugares (LOC).
            # ======== FIN DE LÓGICA DE FILTRADO DE IA ========
            
            assets_from_ner.append(asset)
        
        # Actualizamos el DataFrame principal con los resultados de la IA
        # Usamos .loc para asignar los valores de vuelta al DataFrame original
        df_full.loc[missing_assets_mask, 'Activo_Identificado'] = assets_from_ner
    else:
        print("\n--- Fase 2: RegEx encontró activos en todas las filas. ¡Excelente! ---")

    # Rellenamos cualquier NaN restante (si RegEx falló y la IA también)
    df_full['Activo_Identificado'].fillna("No identificado", inplace=True)

    # --- FASE 3: CLASIFICACIÓN DE TICKETS (SIN CAMBIOS) ---
    print("\n--- Fase 3: Clasificando tickets... ---")
    df_full['text_for_classification'] = df_full.apply(get_text_for_classification, axis=1)
    texts_to_classify = df_full['text_for_classification'].tolist()

    print("Enviando lote a la GPU para clasificación...")
    classification_results = classifier(texts_to_classify, ticket_categories, multi_label=False, batch_size=8)
    df_full['Categoria_Ticket'] = [result['labels'][0] for result in classification_results]
    
    # Limpieza de columnas auxiliares antes de guardar
    df_full.drop(columns=['full_text', 'text_for_classification'], inplace=True, errors='ignore')

    print("\nGuardando el archivo final...")
    df_full.to_excel(output_file, index=False)
    
    print(f"✅ ¡Proceso completado! Archivo guardado en: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procesador de Tickets de Mesa de Servicio con IA.")
    parser.add_argument("input_file", type=str, help="Ruta del archivo Excel de entrada.")
    parser.add_argument("output_file", type=str, help="Ruta para guardar el archivo Excel procesado.")
    args = parser.parse_args()
    process_tickets_file(args.input_file, args.output_file)