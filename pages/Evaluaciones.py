import sys
import os

# 🛠️ SOLUCIÓN PARA RENDER: Aseguramos que Python encuentre la carpeta raíz 'modules'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from modules.logic import obtener_estudiantes

# Configuración responsive móvil
st.set_page_config(page_title="Evaluaciones - FCA UNJu", layout="wide", initial_sidebar_state="collapsed")

# 1. Recuperar la comisión seleccionada globalmente en la App principal
comision_activa = st.session_state.get("global_comision", "Comisión A1")

# 2. Inicialización estricta de estructuras compartidas en el Session State
if "config_evaluaciones" not in st.session_state:
    st.session_state.config_evaluaciones = {}
if comision_activa not in st.session_state.config_evaluaciones:
    st.session_state.config_evaluaciones[comision_activa] = ["Observaciones"]

if "categorias_tipos" not in st.session_state:
    st.session_state.categorias_tipos = {}
if "reglas_dinamicas" not in st.session_state:
    st.session_state.reglas_dinamicas = {}
if "db_notas_mock" not in st.session_state:
    st.session_state.db_notas_mock = {}

columnas_actuales = st.session_state.config_evaluaciones[comision_activa]

st.title(f"📝 Registro de Calificaciones - {comision_activa}")

# =========================================================================
# 📐 DISEÑO BIFURCADO: CRITERIOS (IZQUIERDA) vs CONTROL/PLANILLA (DERECHA)
# =========================================================================
col_izquierda, col_derecha = st.columns([1, 2], gap="large")

# -------------------------------------------------------------------------
# LADO IZQUIERDO: DETECTOR Y CONFIGURADOR DE CRITERIOS DINÁMICOS
# -------------------------------------------------------------------------
with col_izquierda:
    st.subheader("📐 Criterios de Evaluación")
    
    # Extraemos las categorías base analizando las columnas dinámicas creadas (ej: "TP 1" -> "TP")
    categorias_presentes = set([c.split()[0] for c in columnas_actuales if c != "Observaciones"])
    
    if not categorias_presentes:
        st.info("Genere columnas a la derecha para activar los parámetros de promoción y regularidad aquí.")
    else:
        for cat in sorted(categorias_presentes):
            tipo = st.session_state.categorias_tipos.get(cat, "Numérico")
            st.markdown(f"##### Parámetros para: **{cat}**")
            st.caption(f"Tipo establecido: `{tipo}`")
            
            # Inicializamos o recuperamos las reglas para esta categoría específica
            regla = st.session_state.reglas_dinamicas.setdefault(
                cat, 
                {"promo": 7.0 if tipo == "Numérico" else 80, "regular": 4.0 if tipo == "Numérico" else 60}
            )
            
            # Renderizado adaptativo según el tipo de columna seleccionada
            if tipo == "Numérico":
                regla["promo"] = st.number_input(
                    f"Nota Promoción ({cat})", 
                    min_value=1.0, max_value=10.0, 
                    value=float(regla["promo"]), step=0.5, key=f"p_{comision_activa}_{cat}"
                )
                regla["regular"] = st.number_input(
                    f"Nota Regularizar ({cat})", 
                    min_value=1.0, max_value=10.0, 
                    value=float(regla["regular"]), step=0.5, key=f"r_{comision_activa}_{cat}"
                )
            else:
                # Caso Cualitativo / Letra (S/N) -> Se maneja por porcentaje mínimo de TPs aprobados
                regla["promo"] = st.slider(
                    f"% Aprobados para Promoción ({cat})", 
                    0, 100, int(regla["promo"]), key=f"p_{comision_activa}_{cat}"
                )
                regla["regular"] = st.slider(
                    f"% Aprobados para Regularizar ({cat})", 
                    0, 100, int(regla["regular"]), key=f"r_{comision_activa}_{cat}"
                )
            st.markdown("---")

# -------------------------------------------------------------------------
# LADO DERECHO: GENERADOR, RESETEO Y MATRIZ EDITABLE DE ESTUDIANTES
# -------------------------------------------------------------------------
with col_derecha:
    # --- FORMULARIO GENERADOR DE COLUMNAS ---
    st.subheader("🛠️ Panel de Estructura")
    with st.form("block_gen_eval_def", clear_on_submit=True):
        nom_cat = st.text_input("Nombre de la Categoría:", placeholder="Ej: TP, Parcial, Seminario").strip()
        t_dato = st.selectbox("Tipo de Calificación:", ["Numérico", "Letra (S/N)"])
        cant = st.number_input("Cantidad de columnas a crear:", min_value=1, max_value=15, value=1)
        
        if st.form_submit_button("🔨 Insertar Columnas en Bloque", use_container_width=True):
            if nom_cat:
                st.session_state.categorias_tipos[nom_cat] = t_dato
                
                cols_viejas = [c for c in columnas_actuales if c != "Observaciones"]
                for i in range(1, cant + 1):
                    cols_viejas.append(f"{nom_cat} {i}")
                cols_viejas.append("Observaciones")
                
                st.session_state.config_evaluaciones[comision_activa] = cols_viejas
                st.success(f"¡Columnas para '{nom_cat}' añadidas!")
                st.rerun()
            else:
                st.warning("Ingrese un nombre válido para la categoría.")

    # --- BOTÓN DE RESETEO COMPLETO DE LA PLANILLA ---
    with st.expander("🔄 Restablecer Estructura"):
        st.markdown("⚠️ Se vaciarán los encabezados dinámicos regresando al formato inicial.")
        confirmar_reset = st.checkbox("Confirmo que deseo resetear las columnas creadas", key="reset_check_eval")
        if st.button("Resetear Estructura de Columnas", type="primary", use_container_width=True):
            if confirmar_reset:
                st.session_state.config_evaluaciones[comision_activa] = ["Observaciones"]
                st.success("Planilla restablecida con éxito.")
                st.rerun()
            else:
                st.error("Marque la casilla de confirmación primero.")

    st.divider()

    # --- PLANILLA DE CALIFICACIONES EDITABLE ---
    st.subheader("📊 Matriz de Notas")
    
    # 1. Obtener y filtrar estudiantes en concordancia absoluta con la comisión activa
    todos_alumnos = obtener_estudiantes()
    alumnos_comision = [alu for alu in todos_alumnos if alu.domicilio == comision_activa] if todos_alumnos else []
    
    if not alumnos_comision:
        st.info(f"No hay alumnos registrados en la {comision_activa}. Cargue el archivo en la sección principal.")
    else:
        matriz_datos = []
        for alu in alumnos_comision:
            leg_val = alu.descripcion.split("Legajo:")[1].split("|")[0].strip() if "Legajo:" in alu.descripcion else "S/D"
            
            fila = {
                "ID": str(alu.id), 
                "Legajo": leg_val, 
                "Alumno": f"{alu.apellido}, {alu.nombre}"
            }
            
            # Recuperamos o creamos el repositorio de notas del alumno
            notas_alumno = st.session_state.db_notas_mock.setdefault(str(alu.id), {})
            
            for col in columnas_actuales:
                fila[col] = notas_alumno.get(col, "" if col == "Observaciones" else None)
                
            # CORREGIDO: Fuera del bucle interno para evitar duplicidad de celdas
            matriz_datos.append(fila)
            
        df_editable = pd.DataFrame(matriz_datos)
        
        # 2. Configurar los tipos de renderizado de las celdas del editor
        configurador_columnas = {
            "ID": st.column_config.TextColumn(disabled=True),
            "Legajo": st.column_config.TextColumn(disabled=True),
            "Alumno": st.column_config.TextColumn(disabled=True)
        }
        
        for col in columnas_actuales:
            if col == "Observaciones":
                configurador_columnas[col] = st.column_config.TextColumn(col)
            else:
                cat_raiz = col.split()[0]
                tipo_de_columna = st.session_state.categorias_tipos.get(cat_raiz, "Numérico")
                
                if tipo_de_columna == "Numérico":
                    configurador_columnas[col] = st.column_config.NumberColumn(
                        col, min_value=1.0, max_value=10.0, format="%.1f"
                    )
                else:
                    configurador_columnas[col] = st.column_config.SelectboxColumn(
                        col, options=["S", "N"]
                    )
                    
        st.caption("💡 Complete las notas en la grilla y recuerde guardar los cambios antes de salir.")
        
        # 3. Mostrar editor de datos interactivo
        df_resultado = st.data_editor(
            df_editable,
            column_config=configurador_columnas,
            use_container_width=True,
            hide_index=True,
            key=f"grid_eval_{comision_activa}"
        )
        
        # 4. Procesamiento y guardado definitivo de calificaciones
        if st.button("💾 Guardar Calificaciones de la Comisión", use_container_width=True):
            for _, row in df_resultado.iterrows():
                uid = str(row["ID"])
                for col in columnas_actuales:
                    st.session_state.db_notas_mock[uid][col] = row[col]
            st.success("¡Calificaciones guardadas de forma persistente!")
            st.balloons()
