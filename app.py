import os
import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Ruta al archivo JSON consolidado
RUTA_JSON_DATOS = os.path.join(os.path.dirname(__file__), 'quinielas', 'datos_torneo.json')

# VARIABLE GLOBAL EN MEMORIA RAM
DATOS_MUNDIAL_RAM = {}

def cargar_datos_en_memoria():
    global DATOS_MUNDIAL_RAM
    if os.path.exists(RUTA_JSON_DATOS):
        try:
            with open(RUTA_JSON_DATOS, 'r', encoding='utf-8') as f:
                DATOS_MUNDIAL_RAM = json.load(f)
            print("⚡ ¡ÉXITO!: Datos del torneo cargados en la memoria RAM de Flask instantáneamente.")
        except Exception as e:
            print(f"❌ Error al leer el archivo JSON: {e}")
            DATOS_MUNDIAL_RAM = {}
    else:
        print(f"⚠️ Alerta: El archivo {RUTA_JSON_DATOS} no existe. Corre 'import.py' primero.")
        DATOS_MUNDIAL_RAM = {}

# Cargamos el JSON al arrancar el servidor web
cargar_datos_en_memoria()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/obtener_datos', methods=['POST'])
def obtener_datos():
    fecha_buscada = request.json.get('fecha')
    
    if not fecha_buscada:
        return jsonify({'error': 'Fecha no proporcionada'})

    # Buscamos de forma directa en el diccionario en memoria RAM (Velocidad de la luz)
    # Si la fecha existe, devuelve las quinielas de esa fecha; si no, devuelve un diccionario vacío
    datos_fecha = DATOS_MUNDIAL_RAM.get(str(fecha_buscada), {})

    return jsonify({'datos': datos_fecha})


# RUTA UTILITARIA POR SI ACTUALIZAS EL JSON Y NO QUIERES REINICIAR FLASK
@app.route('/recargar_cache', methods=['GET'])
def recargar_cache():
    cargar_datos_en_memoria()
    return jsonify({"status": "Caché de datos actualizada en el servidor"})


if __name__ == '__main__':
    # Cambiado a debug=True para desarrollo local fácil
    app.run(debug=True, host='0.0.0.0', port=5000)
