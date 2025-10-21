# Microagente de Análisis de Tickets de Mesa de Servicio

## Descripción
Este microagente está diseñado para procesar archivos masivos de tickets de TI (en formato `.xlsx`) para realizar dos tareas clave de forma automatizada:

1.  **Extracción de Activos (CIs)**: Identifica el activo principal (servidor, IP, router, etc.) mencionado en el ticket.
2.  **Clasificación de Tickets**: Categoriza cada ticket en una de las áreas predefinidas (Redes, Servidores, Aplicaciones, etc.).

El agente está optimizado para manejar grandes volúmenes de datos (60,000+ registros) de manera eficiente.

## Funcionamiento

* **Entrada**: Un archivo Excel (`.xlsx`) que debe contener, como mínimo, las columnas `asunto`, `descripción` y `cierresolicitud`.
* **Agente de IA**:
    * Utiliza un modelo de **Clasificación Zero-Shot** (`MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`) para categorizar los tickets con alta precisión semántica.
    * Emplea **Expresiones Regulares (RegEx)** para una extracción de activos extremadamente rápida y precisa.
* **Resultado**: Un nuevo archivo Excel con los datos originales más dos nuevas columnas: `Activo_Identificado` y `Categoria_Ticket`.

## Cómo Usar (con Docker)

1.  **Construir la imagen de Docker**:
    ```bash
    docker build -t ticket-analyzer .
    ```

2.  **Ejecutar el contenedor**:
    * Coloca tu archivo de tickets (ej. `tickets.xlsx`) en un directorio (ej. `/ruta/a/tus/datos`).
    * Ejecuta el siguiente comando para que Docker pueda leer y escribir en ese directorio.

    ```bash
    docker run --rm -it \
      --gpus all \ # Opcional: usar si tienes una GPU NVIDIA para acelerar el proceso
      -v /ruta/a/tus/datos:/data \
      ticket-analyzer \
      /data/tickets.xlsx /data/tickets_procesados.xlsx
    ```
    * El script procesará `/data/tickets.xlsx` y guardará el resultado en `/data/tickets_procesados.xlsx`.
