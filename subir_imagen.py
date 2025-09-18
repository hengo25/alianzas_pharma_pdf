from google.cloud import storage
from google.oauth2 import service_account
from datetime import timedelta
import os

def subir_imagen(nombre_local, nombre_remoto):
    ruta_local = os.path.join(os.getcwd(), nombre_local)
    print(f"🔍 Buscando archivo en: {ruta_local}")

    # Cargar credenciales desde tu archivo JSON
    creds = service_account.Credentials.from_service_account_file("firebase_key.json")
    
    # Crear cliente de Storage con credenciales
    storage_client = storage.Client(credentials=creds)
    bucket = storage_client.bucket("proyecto2app-storage")
    blob = bucket.blob(nombre_remoto)

    # Subir archivo
    blob.upload_from_filename(ruta_local)
    print("✅ Imagen subida con éxito")

    # Generar URL firmada válida por 1 hora
    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(hours=1),
        method="GET"
    )
    print("🌐 URL de descarga temporal:", url)

# Ejecutar
subir_imagen("imagen_prueba.jpg", "productos/imagen_prueba.jpg")

