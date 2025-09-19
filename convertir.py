import json
with open("firebase-key.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# reemplaza saltos reales por secuencias escapadas \n (para que sea un string JSON de una línea)
data["private_key"] = data["private_key"].replace("\n", "\\n")

# imprime en una sola línea listo para pegar en Render
print(json.dumps(data))
