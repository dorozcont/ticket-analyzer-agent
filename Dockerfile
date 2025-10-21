# Usa una imagen base de Python con PyTorch, que ya incluye CUDA para aceleración por GPU
FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos de requerimientos e instala las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de tu código al contenedor
COPY . .

# Comando por defecto para mostrar la ayuda si no se especifican argumentos
ENTRYPOINT ["python", "process_tickets.py"]
CMD ["--help"]