import os
import json
import re
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
        print(f"⚠️ Alerta: El archivo {RUTA_JSON_DATOS} no existe.")

    # 2. Cargar resultados oficiales reales
    if os.path.exists(RUTA_JSON_OFICIAL):
        try:
            with open(RUTA_JSON_OFICIAL, 'r', encoding='utf-8') as f:
                DATOS_OFICIAL_RAM = json.load(f)
            print("⚡ ¡ÉXITO!: Resultados oficiales cargados en la RAM de Flask.")
        except Exception as e:
            print(f"❌ Error al leer resultado_real.json: {e}")
            DATOS_OFICIAL_RAM = {}
    else:
        print(f"⚠️ Alerta: El archivo {RUTA_JSON_OFICIAL} no existe.")

# Carga inicial al arrancar el proceso Flask
cargar_datos_en_memoria()


def normalizar_nombre_seleccion(nombre):
    """
    Diccionario de mapeo homólogo para alinear los nombres que vienen de la 
    API externa (resultado_real.json) con los formatos guardados en las predicciones.
    """
    if not nombre:
        return ""
    
    # Limpieza estándar básica
    nombre_limpio = nombre.strip().lower()
    nombre_limpio = re.sub(r'[áäàâ]', 'a', nombre_limpio)
    nombre_limpio = re.sub(r'[éëèê]', 'e', nombre_limpio)
    nombre_limpio = re.sub(r'[íïìî]', 'i', nombre_limpio)
    nombre_limpio = re.sub(r'[óöòô]', 'o', nombre_limpio)
    nombre_limpio = re.sub(r'[úüùû]', 'u', nombre_limpio)
    nombre_limpio = nombre_limpio.replace('ñ', 'n')

    # Equivalencias de la API Externa -> Formato de tus Quinielas locales
    mapeo = {
        "congo dr": "rd congo",
        "dr congo": "rd congo",
        "mexico": "mexico",
        "republica checa": "republica checa",
        "czech republic": "republica checa",
        "czechia": "republica checa",
        "united states": "usa",
        "usa": "usa",
        "eeuu": "usa",
        "south africa": "sudafrica",
        "sudafrica": "sudafrica",
        "south korea": "corea del sur",
        "corea del sur": "corea del sur",
        "korea republic": "corea del sur",
        "bosnia and herzegovina": "bosnia y herzegovina",
        "bosniaherzegovina": "bosnia y herzegovina",
        "bosnia-herzegovina": "bosnia y herzegovina",
        "saudi arabia": "arabia saudita",
        "arabia saudita": "arabia saudita",
        "new zealand": "nueva zelanda",
        "switzerland": "suiza",
        "morocco": "marruecos",
        "austria": "austria",
        "jordan": "jordania",
        "iraq": "irak",
        "norway": "noruega",
        "algeria": "argelia"
    }
    
    # Si el nombre limpio está en nuestro mapeo, devolvemos el estandarizado
    if nombre_limpio in mapeo:
        return mapeo[nombre_limpio]
        
    # Si no, devolvemos el string simplificado sin caracteres raros
    return re.sub(r'[^a-z0-9 ]', '', nombre_limpio).strip()


def extraer_equipos_normalizados(encuentro_txt):
    """
    Separa el encuentro y normaliza de inmediato ambos equipos con el diccionario homólogo.
    """
    if not encuentro_txt:
        return "", ""
    partes = re.split(r'\s+vs\s+|\s+vrs\s+', encuentro_txt, flags=re.IGNORECASE)
    if len(partes) == 2:
        return normalizar_nombre_seleccion(partes[0]), normalizar_nombre_seleccion(partes[1])
    return normalizar_nombre_seleccion(encuentro_txt), ""


def parsear_marcador(marcador_str):
    """
    Extrae los goles numéricos de una cadena tipo '2-1' o '2 - 1'.
    Devuelve (goles_local, goles_visitante) o (None, None) si es inválido.
    """
    if not marcador_str:
        return None, None
    nums = re.findall(r'\d+', marcador_str)
    if len(nums) == 2:
        return int(nums[0]), int(nums[1])
    return None, None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/obtener_datos', methods=['POST'])
def obtener_datos():
    fecha_buscada = request.json.get('fecha')
    if not fecha_buscada:
        return jsonify({'error': 'Fecha no proporcionada'})
    datos_fecha = DATOS_MUNDIAL_RAM.get(str(fecha_buscada), {})
    return jsonify({'datos': datos_fecha})


@app.route('/obtener_datos_oficiales', methods=['POST'])
def obtener_datos_oficiales():
    fecha_buscada = request.json.get('fecha')
    if not fecha_buscada:
        return jsonify({'error': 'Fecha no proporcionada'})
    datos_fecha_oficial = DATOS_OFICIAL_RAM.get(str(fecha_buscada), {})
    return jsonify({'datos': datos_fecha_oficial})


@app.route('/recargar_cache', methods=['GET'])
def recargar_cache():
    cargar_datos_en_memoria()
    return jsonify({"status": "Caché de quinielas y resultados reales actualizada en el servidor"})


# ==========================================
# RUTA HOMOLOGADA DE POSICIONES
# ==========================================
@app.route('/obtener_posiciones', methods=['GET'])
def obtener_posiciones():
    """
    Calcula la tabla general haciendo el cruce exacto de datos gracias a la
    homologación de los nombres de la API externa.
    """
    tabla = {}

    for fecha, contenido_real in DATOS_OFICIAL_RAM.items():
        partidos_reales = contenido_real.get("Resultado Real", [])
        if not partidos_reales:
            continue

        quinielas_amigos = DATOS_MUNDIAL_RAM.get(fecha, {})

        for participante, predicciones in quinielas_amigos.items():
            if participante not in tabla:
                tabla[participante] = {'pj': 0, 'g': 0, 'e': 0, 'p': 0, 'pts': 0}

            for pred in predicciones:
                marcador_pred = pred.get("marcador", "").strip()
                if not marcador_pred or marcador_pred in ["- / -", "No ingresado", ""]:
                    continue

                eq1_pred, eq2_pred = extraer_equipos_normalizados(pred.get("encuentro", ""))
                
                partido_real_encontrado = None
                invertido = False

                # Buscar el partido oficial de la API usando nombres homologados
                for pr in partidos_reales:
                    marcador_real = pr.get("marcador", "").strip()
                    if marcador_real in ["- / -", "No ingresado", ""]:
                        continue

                    eq1_real, eq2_real = extraer_equipos_normalizados(pr.get("encuentro", ""))
                    
                    if eq1_pred == eq1_real and eq2_pred == eq2_real:
                        partido_real_encontrado = pr
                        invertido = False
                        break
                    elif eq1_pred == eq2_real and eq2_pred == eq1_real:
                        partido_real_encontrado = pr
                        invertido = True
                        break

                # Si el partido coincide plenamente bajo el estándar homólogo, calculamos
                if partido_real_encontrado:
                    g_pred_1, g_pred_2 = parsear_marcador(marcador_pred)
                    g_real_1, g_real_2 = parsear_marcador(partido_real_encontrado.get("marcador", ""))

                    if g_pred_1 is None or g_real_1 is None:
                        continue

                    if invertido:
                        g_real_1, g_real_2 = g_real_2, g_real_1

                    # Registramos el partido jugado
                    tabla[participante]['pj'] += 1

                    # REGLA 1: Marcador Exacto (PMA -> 3 pts)
                    if g_pred_1 == g_real_1 and g_pred_2 == g_real_2:
                        tabla[participante]['pts'] += 3
                        tabla[participante]['g'] += 1
                    else:
                        tendencia_pred = 1 if g_pred_1 > g_pred_2 else (-1 if g_pred_1 < g_pred_2 else 0)
                        tendencia_real = 1 if g_real_1 > g_real_2 else (-1 if g_real_1 < g_real_2 else 0)

                        # REGLA 2: Ganador o Empate Acertado (PRA -> 2 pts)
                        if tendencia_pred == tendencia_real:
                            tabla[participante]['pts'] += 2
                            tabla[participante]['e'] += 1
                        # REGLA 3: Fallado (PNA -> 0 pts)
                        else:
                            tabla[participante]['p'] += 1

    # Preparar el payload para el frontend
    lista_posiciones = []
    for participante, stats in tabla.items():
        lista_posiciones.append({
            'participante': participante,
            'pj': stats['pj'],
            'g': stats['g'],
            'e': stats['e'],
            'p': stats['p'],
            'pts': stats['pts']
        })

    # Criterio deportivo: Mayor puntaje, desempate por cantidad de Plenos/Exactos (g)
    lista_posiciones.sort(key=lambda x: (x['pts'], x['g']), reverse=True)

    return jsonify({'posiciones': lista_posiciones})


if __name__ == '__main__':
    app.run(debug=True)
