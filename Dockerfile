# Usar una imagen base de python
FROM python:3.13.2-alpine3.21

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar los archivos del proyecto al contenedor
COPY . /app

# Instalar las dependencias
RUN pip install -r requirements.txt

# Exponer el puerto en el que correra la app
EXPOSE 5000

# Comando para ejecutar la aplicación
CMD ["gunicorn", "-b", "0.0.0.0:5000", "main:app"]
