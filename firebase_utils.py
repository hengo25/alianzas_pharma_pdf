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

    try:
        cred = credentials.Certificate(json.loads(firebase_key))
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'proyecto2app.appspot.com'  # ✅ Bucket correctogs://proyecto2app.firebasestorage.app
        })
        print("✅ Firebase inicializado correctamente")
    except Exception as e:
        print("❌ Error al inicializar Firebase:", e)

db = firestore.client()
bucket = storage.bucket()

def obtener_productos():
    try:
        docs = db.collection("productos").order_by("nombre").stream()
        productos = [d.to_dict() for d in docs]
        print(f"📦 Productos obtenidos: {len(productos)}")
        return productos
    except Exception as e:
        print("❌ Error al obtener productos:", e)
        return []

def _upload_file_and_get_url(file_obj, filename_prefix="productos/"):
    nombre_archivo = f"{filename_prefix}{uuid.uuid4().hex}_{file_obj.filename}"
    blob = bucket.blob(nombre_archivo)
    blob.upload_from_file(file_obj, content_type=file_obj.content_type)
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
        print(f"✅ Producto agregado: {nombre}")
        return doc_ref.id
    except Exception as e:
        print("❌ Error al agregar producto:", e)
        return None

def actualizar_producto(id, nombre, precio, nueva_imagen=None):
    try:
        update_data = {
            "nombre": nombre,
            "precio": float(precio)
        }
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






