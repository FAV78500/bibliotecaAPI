# Utilizar la imagen oficial de Python en su versión 3.11, basada en un sistema operativo recortado (slim) para ahorrar espacio
FROM python:3.11-slim

# Establecer la carpeta de trabajo dentro del contenedor a /app, todos los comandos posteriores se ejecutarán aquí
WORKDIR /app

# Copiar el archivo de dependencias requirements.txt desde nuestro sistema (anfitrión) al contenedor (origen, destino)
COPY requirements.txt .

# Ejecutar la instalación de las dependencias leídas de requirements.txt, usando bandera para no usar caché con el fin de reducir el tamaño de la imagen resultante
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el contenido del código fuente de nuestro sistema hacia el directorio de trabajo del contenedor (. significa todo al destino actual)
COPY . .

# Exponer el puerto 8000 para indicar en qué puerto el contenedor escuchará las conexiones
EXPOSE 8000

# El comando por defecto que se va a iniciar automáticamente al ejecutar el contenedor
# Llama a uvicorn para correr la aplicación FastAPI apuntando a la variable app del archivo main, escuchando en el puerto 8000 con IP 0.0.0.0
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
