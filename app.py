import os
import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Rutas a los archivos JSON consolidados
RUTA_JSON_DATOS = os.path.join(os.path.dirname(__file__), 'quinielas', 'datos_torneo.json')
RUTA_JSON_OFICIAL = os.path.join(os.path.dirname(__file__), 'quinielas', 'resultado_real.json')

# VARIABLES GLOBALES EN MEMORIA RAM
DATOS_MUNDIAL_RAM = {}
DATOS_OFICIAL_RAM = {}

def cargar_datos_en_memoria():
    """
    Lee ambos archivos JSON del disco y los almacena en la caché de la memoria RAM
    de Flask instantáneamente al arrancar o recargar el servidor.
    """
    global DATOS_MUNDIAL_RAM, DATOS_OFICIAL_RAM
    
    # 1. Cargar quinielas de los amigos
    if os.path.exists(RUTA_JSON_DATOS):
        try:
            with open(RUTA_JSON_DATOS, 'r', encoding='utf-8') as f:
                DATOS_MUNDIAL_RAM = json.load(f)
            print("⚡ ¡ÉXITO!: Quinielas de amigos cargadas en la RAM de Flask.")
        except Exception as e:
            print(f"❌ Error al leer datos_torneo.json: {e}")
            DATOS_MUNDIAL_RAM = {}
    else:
        print(f"⚠️ Alerta: El archivo {RUTA_JSON_DATOS} no existe. Corre 'import.py' primero.")
        DATOS_MUNDIAL_RAM = {}

    # 2. Cargar resultados reales oficiales
    if os.path.exists(RUTA_JSON_OFICIAL):
        try:
            with open(RUTA_JSON_OFICIAL, 'r', encoding='utf-8') as f:
                DATOS_OFICIAL_RAM = json.load(f)
            print("🌍 ¡ÉXITO!: Resultados reales oficiales cargados en la RAM de Flask.")
        except Exception as e:
            print(f"❌ Error al leer resultado_real.json: {e}")
            DATOS_OFICIAL_RAM = {}
    else:
        print(f"⚠️ Nota: El archivo {RUTA_JSON_OFICIAL} no existe todavía en la carpeta 'quinielas'.")
        DATOS_OFICIAL_RAM = {}

# Cargamos ambos JSON al arrancar el servidor web
cargar_datos_en_memoria()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/obtener_datos', methods=['POST'])
def obtener_datos():
    """
    Devuelve las predicciones de los participantes para una fecha específica desde la RAM.
    """
    fecha_buscada = request.json.get('fecha')
    
    if not fecha_buscada:
        return jsonify({'error': 'Fecha no proporcionada'})

    # Búsqueda directa ultra veloz en el diccionario indexado por fecha
    datos_fecha = DATOS_MUNDIAL_RAM.get(str(fecha_buscada), {})
    return jsonify({'datos': datos_fecha})


@app.route('/obtener_datos_oficiales', methods=['POST'])
def obtener_datos_oficiales():
    """
    Devuelve los resultados reales oficiales para una fecha específica desde la RAM.
    """
    fecha_buscada = request.json.get('fecha')
    
    if not fecha_buscada:
        return jsonify({'error': 'Fecha no proporcionada'})

    # Búsqueda directa ultra veloz en la RAM de resultados reales
    datos_fecha_oficial = DATOS_OFICIAL_RAM.get(str(fecha_buscada), {})
    return jsonify({'datos': datos_fecha_oficial})


# RUTA UTILITARIA POR SI ACTUALIZAS LOS JSON Y NO QUIERES REINICIAR EL PROCESO FLASK
@app.route('/recargar_cache', methods=['GET'])
def recargar_cache():
    cargar_datos_en_memoria()
    return jsonify({"status": "Caché de quinielas y resultados reales actualizada en el servidor"})


if __name__ == '__main__':
    # Configuración debug=True para desarrollo local fácil en tu entorno local/VM
    app.run(debug=True, host='0.0.0.0', port=5000)
