from firebase_utils import subir_imagen, guardar_producto

# Cambia esta ruta a una imagen real de tu PC
ruta =r"C:\Users\adrim\OneDrive\Desktop\imagen_prueba.jpg.jpg"

url = subir_imagen(ruta)
print("Imagen subida:", url)

guardar_producto("Producto Test", 10.5, 15.0, "Descripción de prueba", url)
print("Producto guardado")
