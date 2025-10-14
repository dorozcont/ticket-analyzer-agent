# process_tickets.py
import pandas as pd
from transformers import pipeline
from tqdm import tqdm
import torch
import argparse
from utils import get_asset_from_ticket, get_text_for_classification

def process_tickets_file(input_file, output_file):
    """
    Procesa un archivo Excel de tickets para extraer activos y clasificar cada ticket.
    """
    print("Iniciando el procesamiento del archivo de tickets...")

    # --- Carga de Modelos de IA ---
    device = 0 if torch.cuda.is_available() else -1
    print(f"Dispositivo detectado: {'GPU' if device == 0 else 'CPU'}")

    # 1. Modelo de Clasificación Zero-Shot.
    print("Cargando el modelo de Clasificación...")
    classifier = pipeline(
        "zero-shot-classification",
        model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
        device=device
    )
    
    # 2. Modelo de Reconocimiento de Entidades (NER) para activos
    print("Cargando el modelo NER para extracción de activos...")
    ner_pipeline = pipeline(
        "ner",
        model="Davlan/bert-base-multilingual-cased-ner-hrl",
        device=device
    )
    
    ticket_categories = ["Redes / Conectividad / Seguridad", "Servidores", "Aplicaciones", "Nube", "Correo"]
    
    # --- Procesamiento del Archivo por Lotes (Chunks) ---
    chunk_size = 200  # Reducimos el chunk_size ya que procesar con dos modelos es más intensivo
    final_df_chunks = []

    print(f"Leyendo y procesando el archivo: {input_file}")
    
    for chunk in tqdm(pd.read_excel(input_file, chunksize=chunk_size), desc="Procesando Lotes"):
        # 1. Extracción de Activos con el modelo NER
        chunk['Activo_Identificado'] = chunk.apply(lambda row: get_asset_from_ticket(row, ner_pipeline), axis=1)

        # 2. Clasificación de Tickets con el modelo Zero-Shot
        texts_to_classify = chunk.apply(get_text_for_classification, axis=1).tolist()
        classification_results = classifier(texts_to_classify, ticket_categories, multi_label=False)
        chunk['Categoria_Ticket'] = [result['labels'][0] for result in classification_results]
        
        final_df_chunks.append(chunk)

    # --- Guardado de Resultados ---
    print("Combinando resultados y guardando el archivo final...")
    final_df = pd.concat(final_df_chunks, ignore_index=True)
    final_df.to_excel(output_file, index=False)
    
    print(f"✅ ¡Proceso completado! Archivo guardado en: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procesador de Tickets de Mesa de Servicio con IA.")
    parser.add_argument("input_file", type=str, help="Ruta del archivo Excel de entrada.")
    parser.add_argument("output_file", type=str, help="Ruta para guardar el archivo Excel procesado.")
    args = parser.parse_args()

    process_tickets_file(args.input_file, args.output_file)