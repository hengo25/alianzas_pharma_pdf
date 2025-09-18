import json
import os
import firebase_admin
from firebase_admin import credentials, firestore, storage
import uuid
from datetime import timedelta

# Inicializa Firebase solo una vez
if not firebase_admin._apps:
    firebase_key = os.getenv("FIREBASE_KEY")

    if not firebase_key:
        raise RuntimeError("⚠️ No se encontró la variable de entorno FIREBASE_KEY en Render")

    # Reemplaza los \n del private_key que se pierden al subir a Render
    firebase_key = firebase_key.replace("\\n", "\n")

    cred = credentials.Certificate(json.loads(firebase_key))
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'proyecto2app.firebasestorage.app'  # <-- asegúrate que sea tu bucket exacto
    })
db = firestore.client()
bucket = storage.bucket()

def obtener_productos():
    docs = db.collection("productos").order_by("nombre").stream()
    return [d.to_dict() for d in docs]

def _upload_file_and_get_url(file_obj, filename_prefix="productos/"):
    """
    Sube el archivo a Cloud Storage y devuelve una URL firmada (válida 1 año)
    """
    nombre_archivo = f"{filename_prefix}{uuid.uuid4().hex}_{file_obj.filename}"
    blob = bucket.blob(nombre_archivo)
    blob.upload_from_file(file_obj, content_type=file_obj.content_type)
    try:
        url = blob.generate_signed_url(expiration=timedelta(days=365), version="v4")
    except TypeError:
        url = blob.generate_signed_url(expiration=timedelta(days=365))
    return url, nombre_archivo

def agregar_producto(nombre, precio, imagen_file):
    url, nombre_archivo = _upload_file_and_get_url(imagen_file)
    doc_ref = db.collection("productos").document()
    doc_ref.set({
        "id": doc_ref.id,
        "nombre": nombre,
        "precio": float(precio),
        "imagen": url,
        "imagen_path": nombre_archivo
    })
    return doc_ref.id

def actualizar_producto(id, nombre, precio, nueva_imagen=None):
    update_data = {
        "nombre": nombre,
        "precio": float(precio)
    }
    if nueva_imagen and getattr(nueva_imagen, "filename", ""):
        url, nombre_archivo = _upload_file_and_get_url(nueva_imagen)
        update_data["imagen"] = url
        update_data["imagen_path"] = nombre_archivo
    db.collection("productos").document(id).update(update_data)

def eliminar_producto(id):
    doc = db.collection("productos").document(id).get()
    if doc.exists:
        d = doc.to_dict()
        path = d.get("imagen_path")
        if path:
            try:
                b = bucket.blob(path)
                b.delete()
            except Exception:
                pass
    db.collection("productos").document(id).delete()








