
# Imagen base oficial de Python
FROM python:3.10-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos
COPY . /app

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto que usa Dash
EXPOSE 8080

# Comando para ejecutar la app

#despliqgue sin SSL
#CMD ["python", "app.py"]

#Despliqgue con SSL
#CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "4", "app:server"] 
#CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "2", "--threads", "2", "--timeout", "600", "app:server"]
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "5", "--threads", "4", "--worker-class", "gthread", "--timeout", "600", "--preload", "--backlog", "2048", "app:server"]