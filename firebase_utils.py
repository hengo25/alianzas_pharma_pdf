# firebase_utils.py
import os
import json
import base64
import uuid
from datetime import timedelta

import firebase_admin
from firebase_admin import credentials, firestore, storage

def _load_service_account():
    """
    Intenta parsear FIREBASE_KEY desde:
     - variable de entorno (JSON en 1 línea con \\n en private_key)
     - o archivo local firebase-key.json (útil para pruebas locales)
     - o base64 (por si lo guardaste así)
    """
    v = os.getenv("FIREBASE_KEY")
    if v:
        # intento normal
        try:
            return json.loads(v)
        except Exception:
            # si el valor tiene saltos reales, los convertimos a \\n
            try:
                return json.loads(v.replace("\n", "\\n"))
            except Exception:
                # intento base64
                try:
                    decoded = base64.b64decode(v).decode("utf-8")
                    return json.loads(decoded)
                except Exception as e:
                    raise RuntimeError(
                        "No pude parsear FIREBASE_KEY. Debe ser el JSON del service account "
                        "(una línea, private_key con \\n). Error: " + str(e)
                    )

    # fallback local para desarrollo
    if os.path.exists("firebase-key.json"):
        with open("firebase-key.json", "r", encoding="utf-8") as f:
            return json.load(f)

    raise RuntimeError("No se encontró la variable de entorno FIREBASE_KEY ni el archivo firebase-key.json")

# cargar credenciales
service_account_info = _load_service_account()
cred = credentials.Certificate(service_account_info)

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
            # asegurar id en el dict
            obj["id"] = d.id
            productos.append(obj)
        print(f"📦 Productos obtenidos: {len(productos)}")
        return productos
    except Exception as e:
        print("❌ Error al obtener productos:", e)
        return []

def _upload_file_and_get_url(file_obj, filename_prefix="productos/"):
    """
    file_obj: objeto FileStorage de Flask (o similar) con .filename y .stream
    """
    nombre_archivo = f"{filename_prefix}{uuid.uuid4().hex}_{file_obj.filename}"
    blob = bucket.blob(nombre_archivo)

    # subir desde stream (compatible con Flask FileStorage)
    try:
        blob.upload_from_file(file_obj.stream, content_type=getattr(file_obj, "content_type", None))
    except Exception as e:
        # último recurso, intentar subir desde file_obj directamente
        blob.upload_from_file(file_obj, content_type=getattr(file_obj, "content_type", None))

    # obtener URL firmada (v4 si está disponible)
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











