# process_tickets.py
import pandas as pd
from transformers import pipeline
from tqdm import tqdm
import torch
import argparse
from utils import get_asset_from_ticket, get_text_for_classification

def process_tickets_file(input_file, output_file):
    print("Iniciando el procesamiento del archivo de tickets...")

    # --- Carga de Modelos de IA ---
    device = 0 if torch.cuda.is_available() else -1
    print(f"Dispositivo detectado: {'GPU' if device == 0 else 'CPU'}")

    print("Cargando el modelo de Clasificación...")
    classifier = pipeline("zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli", device=device)
    
    print("Cargando el modelo NER para extracción de activos...")
    ner_pipeline = pipeline("ner", model="Davlan/bert-base-multilingual-cased-ner-hrl", device=device)
    
    ticket_categories = ["Redes / Conectividad / Seguridad", "Servidores", "Aplicaciones", "Nube", "Correo"]
    
    # --- LECTURA DEL ARCHIVO COMPLETO EN MEMORIA ---
    print(f"Leyendo el archivo completo: {input_file}...")
    try:
        df_full = pd.read_excel(input_file, engine='openpyxl')
        print("Archivo leído correctamente en memoria.")
    except Exception as e:
        print(f"Error crítico al leer el archivo Excel: {e}")
        exit()

    # Habilitamos la barra de progreso para las operaciones de Pandas
    tqdm.pandas(desc="Extrayendo Activos")

    # 1. Extracción de Activos con el modelo NER
    df_full['Activo_Identificado'] = df_full.progress_apply(lambda row: get_asset_from_ticket(row, ner_pipeline), axis=1)

    # 2. Clasificación de Tickets con el modelo Zero-Shot
    print("Clasificando tickets...")
    texts_to_classify = df_full.apply(get_text_for_classification, axis=1).tolist()
    classification_results = classifier(texts_to_classify, ticket_categories, multi_label=False, batch_size=8)
    df_full['Categoria_Ticket'] = [result['labels'][0] for result in classification_results]
    
    # --- Guardado de Resultados ---
    print("Guardando el archivo final...")
    df_full.to_excel(output_file, index=False)
    
    print(f"✅ ¡Proceso completado! Archivo guardado en: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procesador de Tickets de Mesa de Servicio con IA.")
    parser.add_argument("input_file", type=str, help="Ruta del archivo Excel de entrada.")
    parser.add_argument("output_file", type=str, help="Ruta para guardar el archivo Excel procesado.")
    args = parser.parse_args()
    process_tickets_file(args.input_file, args.output_file)