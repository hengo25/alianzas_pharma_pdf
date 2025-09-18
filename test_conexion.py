from firebase_utils import guardar_producto, obtener_productos

guardar_producto("Producto prueba", 10.5, 15.0, "Esto es una prueba", "https://via.placeholder.com/150")

productos = obtener_productos()
for p in productos:
    print(p)
