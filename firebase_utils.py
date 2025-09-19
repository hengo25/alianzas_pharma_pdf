import base64, json, os
import firebase_admin
from firebase_admin import credentials, firestore, storage
import uuid
from datetime import timedelta
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Inicializa Firebase solo una vez
if not firebase_admin._apps:
    firebase_key = os.getenv("FIREBASE_KEY")
    if not firebase_key:
        raise RuntimeError("⚠️ No se encontró la variable de entorno FIREBASE_KEY en Render")

    # Convertir el string a diccionario JSON
    cred_dict = json.loads(firebase_key)

    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'proyecto2app.appspot.com'
    })
    logging.info("✅ Firebase inicializado correctamente")

db = firestore.client()
bucket = storage.bucket()


def obtener_productos():
    try:
        docs = db.collection("productos").order_by("nombre").stream()
        productos = [d.to_dict() for d in docs]
        logging.info(f"📦 Productos obtenidos: {len(productos)}")
        return productos
    except Exception as e:
        logging.error(f"❌ Error al obtener productos: {e}")
        return []


def _upload_file_and_get_url(file_obj, filename_prefix="productos/"):
    nombre_archivo = f"{filename_prefix}{uuid.uuid4().hex}_{file_obj.filename}"
    blob = bucket.blob(nombre_archivo)

    # Subir desde el stream del archivo
    blob.upload_from_file(file_obj.stream, content_type=file_obj.content_type)

    try:
        url = blob.generate_signed_url(expiration=timedelta(days=365), version="v4")
    except TypeError:
        url = blob.generate_signed_url(expiration=timedelta(days=365))

    logging.info(f"📤 Imagen subida a: {nombre_archivo}")
    return url, nombre_archivo


def agregar_producto(nombre, precio, imagen_file):
    try:
        precio = float(str(precio).replace(",", ".") or 0)
        if not imagen_file or not getattr(imagen_file, "filename", ""):
            raise ValueError("⚠️ No se envió imagen válida")

        url, nombre_archivo = _upload_file_and_get_url(imagen_file)
        doc_ref = db.collection("productos").document()
        doc_ref.set({
            "id": doc_ref.id,
            "nombre": nombre,
            "precio": precio,
            "imagen": url,
            "imagen_path": nombre_archivo
        })
        logging.info(f"✅ Producto agregado: {nombre}")
        return doc_ref.id
    except Exception as e:
        logging.error(f"❌ Error al agregar producto: {e}")
        return None


def actualizar_producto(id, nombre, precio, nueva_imagen=None):
    try:
        precio = float(str(precio).replace(",", ".") or 0)
        update_data = {
            "nombre": nombre,
            "precio": precio
        }
        if nueva_imagen and getattr(nueva_imagen, "filename", ""):
            url, nombre_archivo = _upload_file_and_get_url(nueva_imagen)
            update_data["imagen"] = url
            update_data["imagen_path"] = nombre_archivo
        db.collection("productos").document(id).update(update_data)
        logging.info(f"✏️ Producto actualizado: {id}")
    except Exception as e:
        logging.error(f"❌ Error al actualizar producto: {e}")


def eliminar_producto(id):
    try:
        doc = db.collection("productos").document(id).get()
        if doc.exists:
            d = doc.to_dict()
            path = d.get("imagen_path")
            if path:
                try:
                    bucket.blob(path).delete()
                    logging.info(f"🗑️ Imagen eliminada: {path}")
                except Exception as err:
                    logging.warning(f"⚠️ No se pudo eliminar imagen: {err}")
        db.collection("productos").document(id).delete()
        logging.info(f"🗑️ Producto eliminado: {id}")
    except Exception as e:
        logging.error(f"❌ Error al eliminar producto: {e}")



