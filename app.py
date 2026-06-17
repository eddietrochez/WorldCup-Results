import os
from flask import Flask, render_template, request, jsonify
import pandas as pd
from collections import defaultdict
import datetime

app = Flask(__name__)

CARPETA_QUINIELAS = os.path.join(os.path.dirname(__file__), 'quinielas')


def limpiar_hora(val):
    """
    Normaliza el formato de la hora extraída de Excel de forma robusta.
    Devuelve un string en formato 'HH:MM' o '99:99' si es inválido.
    """
    if pd.isna(val):
        return "99:99"
    
    # Si viene como objeto datetime.time u objeto datetime
    if isinstance(val, (datetime.time, datetime.datetime)):
        return val.strftime('%H:%M')
    
    val_str = str(val).strip()
    
    # Si viene como flotante de Excel (ej: 0.5 para las 12:00 PM)
    try:
        if '.' in val_str and float(val_str) < 1.0:
            segundos_totales = int(round(float(val_str) * 86400))
            horas = segundos_totales // 3600
            minutos = (segundos_totales % 3600) // 60
            return f"{horas:02d}:{minutos:02d}"
    except ValueError:
        pass

    # Si viene como texto 'HH:MM:SS' o 'HH:MM'
    if ':' in val_str:
        partes = val_str.split(':')
        if len(partes) >= 2:
            try:
                h = int(float(partes[0]))
                m = int(float(partes[1]))
                return f"{h:02d}:{m:02d}"
            except ValueError:
                pass

    return "99:99"


def obtener_datos_internal(fecha_buscada):
    if not fecha_buscada:
        return {'error': 'Fecha no proporcionada'}

    archivos = sorted([f for f in os.listdir(CARPETA_QUINIELAS)
                       if f.endswith(('.xlsx', '.xlsm')) and not f.startswith('~$')])

    resultados_por_participante = defaultdict(list)

    for archivo in archivos:
        nombre = os.path.splitext(archivo)[0].replace('_', ' ').title()
        ruta = os.path.join(CARPETA_QUINIELAS, archivo)

        try:
            df_raw = pd.read_excel(ruta, sheet_name="WORLDCUP", header=None)

            # Robust header detection
            fila_header = None
            col_fecha_idx = col_hora_idx = col_local_idx = col_fuera_idx = None
            cols_goles_indices = []

            for idx in range(min(50, len(df_raw))):
                fila_valores = [str(x).strip() for x in df_raw.iloc[idx, :]]
                if any("Fecha" in val for val in fila_valores):
                    fila_header = idx
                    for c_idx, val in enumerate(fila_valores):
                        if "Fecha" in val:
                            col_fecha_idx = c_idx
                        elif "Hora" in val:
                            col_hora_idx = c_idx
                        elif any(x in val for x in ["Casa", "Local"]):
                            col_local_idx = c_idx
                        elif any(x in val for x in ["Fuera", "Visita"]):
                            col_fuera_idx = c_idx
                        elif "Gol" in val:
                            cols_goles_indices.append(c_idx)
                    break

            if fila_header is None or col_fecha_idx is None or len(cols_goles_indices) < 2:
                continue

            col_gol_l_idx = cols_goles_indices[0]
            col_gol_v_idx = cols_goles_indices[1]

            df_partidos = df_raw.iloc[fila_header + 1:].copy().reset_index(drop=True)

            # Robust date handling for protected Excels
            df_partidos['Fecha_Raw'] = df_partidos.iloc[:, col_fecha_idx].ffill()
            df_partidos['Fecha_Str'] = pd.to_datetime(
                df_partidos['Fecha_Raw'], errors='coerce', dayfirst=True
            ).dt.strftime('%Y-%m-%d')

            if df_partidos['Fecha_Str'].isna().all():
                df_partidos['Fecha_Str'] = df_partidos['Fecha_Raw'].astype(str).str[:10]

            matches = df_partidos[df_partidos['Fecha_Str'] == fecha_buscada]

            for _, fila in matches.iterrows():
                local = str(fila.iloc[col_local_idx]).strip()
                visita = str(fila.iloc[col_fuera_idx]).strip()

                if not local or not visita or local.lower() in ['nan', 'none', '', 'grupo', 'casa']:
                    continue

                goles_l = fila.iloc[col_gol_l_idx]
                goles_v = fila.iloc[col_gol_v_idx]

                # Extracción y limpieza robusta de la hora
                hora_raw = fila.iloc[col_hora_idx] if col_hora_idx is not None else None
                hora_limpia = limpiar_hora(hora_raw)

                if pd.isna(goles_l) or pd.isna(goles_v):
                    marcador = "- / -"
                    resultado = "No ingresado"
                else:
                    try:
                        gl = int(float(goles_l))
                        gv = int(float(goles_v))
                        marcador = f"{gl}-{gv}"
                        resultado = local if gl > gv else (visita if gv > gl else "Empate")
                    except:
                        marcador = "- / -"
                        resultado = "No ingresado"

                resultados_por_participante[nombre].append({
                    'hora': hora_limpia if hora_limpia != "99:99" else "--:--",
                    'encuentro': f"{local} vs {visita}",
                    'marcador': marcador,
                    'resultado': resultado
                })

            if resultados_por_participante[nombre]:
                # Ordenar cronológicamente por el campo 'hora'
                resultados_por_participante[nombre] = sorted(
                    resultados_por_participante[nombre], 
                    key=lambda x: x['hora'] if x['hora'] != "--:--" else "99:99"
                )

        except Exception as e:
            print(f"Error procesando {archivo}: {e}")

    return {'datos': resultados_por_participante}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/obtener_datos', methods=['POST'])
def obtener_datos():
    fecha = request.json.get('fecha')
    return jsonify(obtener_datos_internal(fecha))


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
