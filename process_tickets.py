# process_tickets.py
import pandas as pd
from transformers import pipeline
from tqdm import tqdm  # <--- ASEGÚRATE QUE ESTÉ IMPORTADO
import torch
import argparse
from utils import find_asset_with_regex, get_text_for_classification
import warnings
import time
import numpy as np
import re

# Suprimir advertencias futuras (limpieza de log)
warnings.simplefilter(action='ignore', category=FutureWarning)

def process_tickets_file(input_file, output_file):
    start_time = time.time()
    
    print("Iniciando el procesamiento del archivo de tickets...")

    device = 0 if torch.cuda.is_available() else -1
    print(f"Dispositivo detectado: {'GPU' if device == 0 else 'CPU'}")

    # --- Carga de Modelos de IA ---
    print("Cargando el modelo de Clasificación...")
    classifier = pipeline("zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli", device=device)
    print("Cargando el modelo NER para extracción de activos...")
    ner_pipeline = pipeline("ner", model="Davlan/bert-base-multilingual-cased-ner-hrl", device=device, aggregation_strategy="simple")
    
    ticket_categories = ["Redes / Conectividad / Seguridad", "Servidores", "Aplicaciones", "Nube", "Correo"]
    
    # --- NUEVO: Diccionario de Palabras Clave para Tipo de CI ---
    keywords = {
        'Redes / Conectividad / Seguridad': [
            'router', 'switch', 'firewall', 'vpn', 'wifi', 'red', 'conexión', 'conexion',
            'internet', 'ip', 'dns', 'lan', 'wan', 'puerto', 'cable', 'conectividad',
            'network', 'wireless', 'acceso remoto', 'proxy', 'nat', 'protocolo', 'bandwidth',
            'latencia', 'ping', 'fibra', 'ethernet', 'routing', 'switching'
        ],
        'Servidores': [
            'servidor', 'windows server', 'linux', 'ubuntu', 'centos', 'vmware',
            'hyper-v', 'esxi', 'dominio', 'active directory', 'ad', 'backup',
            'server', 'virtual machine', 'vm', 'host', 'cluster', 'datacenter',
            'raid', 'storage', 'san', 'nas', 'exchange server', 'sql server'
        ],
        'Nube': [
            'azure', 'aws', 'cloud', 'nube', 'office 365', 'O365','office365','sharepoint',
            'onedrive', 'saas', 'iaas', 'paas', 'cloud computing',
            'amazon', 'microsoft 365', 'teams', 'cloudflare', 'google cloud',
            'digital ocean', 'ibm cloud', 'oracle cloud'
        ],
        'Correo': [
            'outlook', 'exchange', 'email', 'correo', 'spam', 'inbox',
            'owa', 'mail', 'bandeja', 'adjunto', 'smtp', 'pop3', 'imap',
            'correo electrónico', 'outlook web', 'thunderbird', 'mailbox',
            'encuesta', 'newsletter', 'mailing'
        ],
        'Aplicaciones': [
            'software', 'aplicación', 'aplicacion', 'programa', 'instalación', 'instalacion', 
            'licencia', 'actualización', 'actualizacion', 'error', 'bug', 'crash', 'aplicativo', 'app',
            'sistema', 'erp', 'crm', 'instalar', 'desinstalar', 'configuración', 'configuracion',
            'java', 'python', 'php', 'html', 'css', 'javascript', 'base de datos', 'database'
        ]
    }
    
    # --- NUEVO: Función de clasificación por keywords ---
    def classify_ci_type(text, keywords_dict):
        if not isinstance(text, str):
            return "No Identificado"
            
        text_lower = text.lower()
        for category, keys in keywords_dict.items():
            for key in keys:
                # Usamos \b (límite de palabra) para evitar coincidencias parciales (ej. 'app' en 'apple')
                if re.search(r'\b' + re.escape(key.lower()) + r'\b', text_lower):
                    return category
        return "No Identificado"
    
    # --- Fin de nuevas definiciones ---

    print(f"Leyendo el archivo completo: {input_file}...")
    df_full = pd.read_excel(input_file, engine='openpyxl')
    print(f"Archivo leído. {len(df_full)} filas a procesar.")

    df_full['Activo_Identificado'] = np.nan
    df_full['Metodo_Deteccion'] = np.nan

    # --- FASE 1: EXTRACCIÓN DE ACTIVOS CON REGEX (RÁPIDO) ---
    print("\n--- Fase 1: Extrayendo activos con RegEx... ---")
    
    def get_text_for_ner(row):
        asunto = str(row.get('asunto', ''))
        descripcion = str(row.get('descripción', ''))
        cierre = str(row.get('cierresolicitud', ''))
        return f"{asunto} | {descripcion} | {cierre}"

    df_full['full_text'] = df_full.apply(get_text_for_ner, axis=1)
    df_full['Activo_Identificado'] = df_full['full_text'].apply(find_asset_with_regex)
    
    regex_found_mask = df_full['Activo_Identificado'].notna()
    df_full.loc[regex_found_mask, 'Metodo_Deteccion'] = 'RegEx'
    
    # --- FASE 2: EXTRACCIÓN CON IA PARA LOS CASOS FALTANTES ---
    missing_assets_mask = df_full['Activo_Identificado'].isna()
    missing_assets_df = df_full[missing_assets_mask].copy()
    
    if not missing_assets_df.empty:
        print(f"\n--- Fase 2: RegEx no encontró activos en {len(missing_assets_df)} filas. Usando IA como respaldo... ---")
        texts_for_ner = missing_assets_df['full_text'].tolist()
        
        print("Enviando lote a la GPU para procesamiento NER... (Puede tardar)")
        ner_results_list = ner_pipeline(texts_for_ner, batch_size=8)
        print("Procesamiento NER completado. Analizando resultados...")

        assets_from_ner = []
        for result_group in tqdm(ner_results_list, desc="Post-procesando resultados NER"):
            asset = np.nan
            valid_entities = [e['word'] for e in result_group if e['entity_group'] in ['ORG', 'MISC']]
            if valid_entities:
                asset = valid_entities[0]
            assets_from_ner.append(asset)
        
        df_full.loc[missing_assets_mask, 'Activo_Identificado'] = assets_from_ner
        ner_found_mask = missing_assets_mask & df_full['Activo_Identificado'].notna()
        df_full.loc[ner_found_mask, 'Metodo_Deteccion'] = 'NER'
    else:
        print("\n--- Fase 2: RegEx encontró activos en todas las filas. ---")

    df_full['Activo_Identificado'].fillna("No identificado", inplace=True)
    df_full['Metodo_Deteccion'].fillna("No Identificado", inplace=True)

    # --- FASE 3: CLASIFICACIÓN DE TICKETS (POR IA) ---
    print("\n--- Fase 3: Clasificando Categoria de Ticket (IA)... ---")
    df_full['text_for_classification'] = df_full.apply(get_text_for_classification, axis=1)
    texts_to_classify = df_full['text_for_classification'].tolist()

    print("Enviando lote a la GPU para clasificación...")
    classification_results = classifier(texts_to_classify, ticket_categories, multi_label=False, batch_size=8)
    df_full['Categoria_Ticket'] = [result['labels'][0] for result in classification_results]
    
    # --- NUEVA FASE 4: CLASIFICACIÓN DE TIPO DE CI (POR KEYWORDS) ---
    print("\n--- Fase 4: Clasificando Tipo de CI (Keywords)... ---")
    
    # Registra tqdm con pandas para usar .progress_apply()
    tqdm.pandas(desc="Clasificando Tipo de CI")
    
    # Usamos 'full_text' que ya contiene asunto, descripción y cierre
    df_full['Tipo_CI'] = df_full['full_text'].progress_apply(
        lambda text: classify_ci_type(text, keywords)
    )
    # --- Fin de la Fase 4 ---
    
    # Limpieza de columnas auxiliares antes de guardar
    df_full.drop(columns=['full_text', 'text_for_classification'], inplace=True, errors='ignore')

    print("\nGuardando el archivo final...")
    df_full.to_excel(output_file, index=False)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n--- TIEMPO TOTAL DE EJECUCIÓN: {total_time:.2f} segundos ---")
    print(f"✅ ¡Proceso completado! Archivo guardado en: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procesador de Tickets de Mesa de Servicio con IA.")
    parser.add_argument("input_file", type=str, help="Ruta del archivo Excel de entrada.")
    parser.add_argument("output_file", type=str, help="Ruta para guardar el archivo Excel procesado.")
    args = parser.parse_args()
    process_tickets_file(args.input_file, args.output_file)