import sys
import os

# 🛠️ SOLUCIÓN PARA RENDER: Aseguramos que Python encuentre la carpeta raíz 'modules'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from modules.logic import obtener_estudiantes

# Configuración responsive para visualización en celular
st.set_page_config(page_title="Reportes Finales - FCA UNJu", layout="wide", initial_sidebar_state="collapsed")

# 1. Recuperar la comisión activa seleccionada en la app principal
comision_activa = st.session_state.get("global_comision", "Comisión A1")

st.title(f"📊 Reporte de Rendimiento - {comision_activa}")

# 2. Obtener de Base de Datos y aplicar FILTRO ESTRICTO de comisión
todos_alumnos = obtener_estudiantes()
alumnos_comision = [alu for alu in todos_alumnos if alu.domicilio == comision_activa] if todos_alumnos else []

# 3. Recuperar estructuras compartidas de Asistencia y Evaluaciones
columnas_eval = st.session_state.get("config_evaluaciones", {}).get(comision_activa, ["Observaciones"])
categorias_tipos = st.session_state.get("categorias_tipos", {})
notas_guardadas = st.session_state.get("db_notas_mock", {})

# Estructura de asistencia: st.session_state.db_asistencia[comision][fecha][alumno_id]
diccionario_asistencias = st.session_state.get("db_asistencia", {}).get(comision_activa, {})

if not alumnos_comision:
    st.info(f"📋 No hay alumnos registrados en la {comision_activa}. Registre alumnos para ver métricas.")
else:
    # --- PROCESAMIENTO CONCORDANTE DE DATOS ---
    lista_acta_volante = []
    lista_alertas_criticas = []
    
    # Calcular total de clases dictadas/registradas en esta comisión
    total_clases = len(diccionario_asistencias.keys())

    for alu in alumnos_comision:
        uid = str(alu.id)  # Forzamos conversión a string compatible con MongoDB
        leg_val = alu.descripcion.split("Legajo:")[1].split("|")[0].strip() if "Legajo:" in alu.descripcion else "S/D"
        
        # A) CÁLCULO DE ASISTENCIA REAL
        presentes = 0
        for fecha_str in diccionario_asistencias.keys():
            if diccionario_asistencias[fecha_str].get(uid, False) == True:
                presentes += 1
        
        porcentaje_asistencia = (presentes / total_clases * 100) if total_clases > 0 else 100.0

        # B) CÁLCULO DE EVALUACIONES (NOTAS BAJAS Y TRABAJOS DEBIDOS)
        notas_alumno = notas_guardadas.get(uid, {})
        alertas_academicas = []
        aplazos = 0
        tps_adeudados = 0
        
        for col in columnas_eval:
            if col == "Observaciones": 
                continue
            
            cat_raiz = col.split()[0]
            tipo_dato = categorias_tipos.get(cat_raiz, "Numérico")
            valor_nota = notas_alumno.get(col, None)
            
            if tipo_dato == "Numérico":
                if valor_nota is not None and valor_nota != "":
                    if float(valor_nota) < 4.0:
                        aplazos += 1
                        alertas_academicas.append(f"{col}: {valor_nota}")
                else:
                    tps_adeudados += 1
                    alertas_academicas.append(f"{col}: Sin Nota")
            else:
                # Criterio cualitativo (S/N)
                if valor_nota == "N" or valor_nota is None or valor_nota == "":
                    tps_adeudados += 1
                    alertas_academicas.append(f"{col}: Debe")

        # C) DETERMINACIÓN DE CONDICIÓN (Basada en los sliders de asistencia y notas)
        reglas_asist = st.session_state.get("asistencia_reglas", {"promo_asist": 80, "regular_asist": 60})
        
        if aplazos > 0 or porcentaje_asistencia < reglas_asist["regular_asist"]:
            condicion_final = "🔴 Libre"
        elif tps_adeudados > 0 or porcentaje_asistencia < reglas_asist["promo_asist"]:
            condicion_final = "🟡 Regular"
        else:
            condicion_final = "🟢 Promocionado"

        # Cargar datos consolidados al reporte principal
        lista_acta_volante.append({
            "Legajo": leg_val,
            "Estudiante": f"{alu.apellido}, {alu.nombre}",
            "Asistencia Real": f"{porcentaje_asistencia:.1f}%",
            "Condición Final": condicion_final
        })

        # Si el alumno tiene notas bajas, debe trabajos o está libre, va a la sección de Alertas
        if alertas_academicas or porcentaje_asistencia < reglas_asist["promo_asist"]:
            detalles_alerta = ", ".join(alertas_academicas) if alertas_academicas else "Asistencia baja"
            lista_alertas_criticas.append({
                "Estudiante": f"{alu.apellido}, {alu.nombre}",
                "Asistencia": f"{porcentaje_asistencia:.1f}%",
                "Detalle de Deuda / Aplazos": detalles_alerta
            })

    # =========================================================================
    # 📱 INTERFAZ VISUAL EN PANTALLA (RESPONSIVE MÓVIL)
    # =========================================================================
    
    # Métricas superiores compactas
    df_acta = pd.DataFrame(lista_acta_volante)
    m1, m2 = st.columns(2)
    m1.metric("Alumnos Evaluados", len(df_acta))
    m2.metric("Clases Registradas", total_clases)

    st.divider()

    # Separación por solapas (Tabs) para optimizar espacio táctil
    tab_acta, tab_alertas = st.tabs(["📋 Acta Volante de Comisión", "🚨 Alertas (Bajas Notas / Deudas)"])

    with tab_acta:
        st.subheader("Planilla Consolidada de Condición")
        st.caption("Filtro en tiempo real. Deslice horizontalmente para ver completo.")
        st.dataframe(df_acta, use_container_width=True, hide_index=True)
        
        # Botón para descargar el acta de esta comisión en CSV
        csv_acta = df_acta.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Descargar Acta de Condición (CSV)",
            data=csv_acta,
            file_name=f"Acta_Volante_{comision_activa}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with tab_alertas:
        st.subheader("Seguimiento de Alumnos en Riesgo")
        if lista_alertas_criticas:
            df_alertas = pd.DataFrame(lista_alertas_criticas)
            st.dataframe(df_alertas, use_container_width=True, hide_index=True)
        else:
            st.success("🎉 ¡Excelente! Ningún estudiante presenta notas bajas ni adeuda trabajos en esta comisión.")
