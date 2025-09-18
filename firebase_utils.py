# firebase_utils.py
import firebase_admin
from firebase_admin import credentials, firestore, storage
import uuid
from datetime import timedelta
from io import BytesIO

# Cambia esto por tu bucket (sin gs://)
BUCKET_NAME = "TU_BUCKET_AQUI"  # e.g. 'proyecto2app-storage' o 'proyecto2app.appspot.com' o 'proyecto2app.firebasestorage.app'

# Inicializa Firebase (usa tu archivo de credenciales)
if not firebase_admin._apps:
    cred = credentials.Certificate("FIREBASE_KEY")
    firebase_admin.initialize_app(cred, {
        "storageBucket": BUCKET_NAME
    })

db = firestore.client()
bucket = storage.bucket()


def obtener_productos():
    docs = db.collection("productos").stream()
    productos = []
    for d in docs:
        doc = d.to_dict()
        productos.append(doc)
    return productos


def _upload_file_and_get_url(file_obj, filename_prefix="productos/"):
    """
    Subir el archivo (FileStorage) y devolver una URL firmada temporal (v4).
    """
    nombre_archivo = f"{filename_prefix}{uuid.uuid4().hex}_{file_obj.filename}"
    blob = bucket.blob(nombre_archivo)
    # upload_from_file funciona con file-like (werkzeug FileStorage)
    blob.upload_from_file(file_obj, content_type=file_obj.content_type)
    # No usamos blob.make_public() (puede fallar con uniform bucket-level access).
    # Generamos una signed url (válida 365 días por defecto)
    try:
        url = blob.generate_signed_url(expiration=timedelta(days=365), version="v4")
    except TypeError:
        # Algunas versiones usan signature_version
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
        "imagen_path": nombre_archivo  # por si quieres borrar luego
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
    # Opcional: eliminar objeto en Storage si guardaste imagen_path
    doc = db.collection("productos").document(id).get()
    if doc.exists:
        d = doc.to_dict()
        path = d.get("imagen_path")
        if path:
            try:
                b = bucket.blob(path)
                b.delete()  # ignora errores si no existe
            except Exception:
                pass
    db.collection("productos").document(id).delete()

