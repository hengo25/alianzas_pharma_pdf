# firebase_utils.py
import os
import json
import uuid
from datetime import timedelta

import firebase_admin
from firebase_admin import credentials, firestore, storage

# ✅ Leer JSON desde variable de entorno
firebase_key = os.environ.get("FIREBASE_KEY")
if not firebase_key:
    raise RuntimeError("⚠️ No se encontró la variable de entorno FIREBASE_KEY")

# ⚠️ Arreglar las barras invertidas en la clave privada (\n)
firebase_key = firebase_key.replace('\\n', '\n')

# Convertir el string a dict
service_account_info = json.loads(firebase_key)

# obtener bucket desde env y limpiar gs:// si existe
bucket_name = os.getenv("FIREBASE_BUCKET", "").strip()
if bucket_name.startswith("gs://"):
    bucket_name = bucket_name[len("gs://"):]

# si no viene bucket en env, intentar adivinar con el project_id
if not bucket_name:
    project_id = service_account_info.get("project_id")
    if project_id:
        bucket_name = f"{project_id}.appspot.com"  # intento razonable

if not bucket_name:
    raise RuntimeError("No se encontró FIREBASE_BUCKET y no pude inferirla. Añade FIREBASE_BUCKET en Render.")

# inicializar firebase (esto debe hacerse **antes** de llamar a firestore.client())
if not firebase_admin._apps:
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
    print("✅ Firebase inicializado. Bucket:", bucket_name)

db = firestore.client()
bucket = storage.bucket()

# funciones CRUD
def obtener_productos():
    try:
        docs = db.collection("productos").order_by("nombre").stream()
        productos = []
        for d in docs:
            obj = d.to_dict()
            obj["id"] = d.id
            productos.append(obj)
        print(f"📦 Productos obtenidos: {len(productos)}")
        return productos
    except Exception as e:
        print("❌ Error al obtener productos:", e)
        return []

def _upload_file_and_get_url(file_obj, filename_prefix="productos/"):
    nombre_archivo = f"{filename_prefix}{uuid.uuid4().hex}_{file_obj.filename}"
    blob = bucket.blob(nombre_archivo)
    try:
        blob.upload_from_file(file_obj.stream, content_type=getattr(file_obj, "content_type", None))
    except Exception:
        blob.upload_from_file(file_obj, content_type=getattr(file_obj, "content_type", None))

    try:
        url = blob.generate_signed_url(expiration=timedelta(days=365), version="v4")
    except TypeError:
        url = blob.generate_signed_url(expiration=timedelta(days=365))
    print(f"📤 Imagen subida a: {nombre_archivo}")
    return url, nombre_archivo

def agregar_producto(nombre, precio, imagen_file):
    try:
        url, nombre_archivo = _upload_file_and_get_url(imagen_file)
        doc_ref = db.collection("productos").document()
        doc_ref.set({
            "id": doc_ref.id,
            "nombre": nombre,
            "precio": float(precio),
            "imagen": url,
            "imagen_path": nombre_archivo
        })
        print(f"✅ Producto agregado: {nombre} (id={doc_ref.id})")
        return doc_ref.id
    except Exception as e:
        print("❌ Error al agregar producto:", e)
        return None

def actualizar_producto(id, nombre, precio, nueva_imagen=None):
    try:
        update_data = {"nombre": nombre, "precio": float(precio)}
        if nueva_imagen and getattr(nueva_imagen, "filename", ""):
            url, nombre_archivo = _upload_file_and_get_url(nueva_imagen)
            update_data["imagen"] = url
            update_data["imagen_path"] = nombre_archivo
        db.collection("productos").document(id).update(update_data)
        print(f"✏️ Producto actualizado: {id}")
    except Exception as e:
        print("❌ Error al actualizar producto:", e)

def eliminar_producto(id):
    try:
        doc = db.collection("productos").document(id).get()
        if doc.exists:
            d = doc.to_dict()
            path = d.get("imagen_path")
            if path:
                try:
                    bucket.blob(path).delete()
                except Exception:
                    pass
        db.collection("productos").document(id).delete()
        print(f"🗑️ Producto eliminado: {id}")
    except Exception as e:
        print("❌ Error al eliminar producto:", e)












