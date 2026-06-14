import streamlit as st
import pandas as pd
from datetime import datetime
from modules.logic import obtener_estudiantes

# Configuración de página adaptada para celulares
st.set_page_config(page_title="Asistencia - FCA UNJu", layout="wide", initial_sidebar_state="collapsed")

# 1. Recuperar comisión activa del estado global
comision_activa = st.session_state.get("global_comision", "Comisión A1")

# 2. Inicialización de la base de datos de asistencia en memoria de sesión
# Estructura: st.session_state.db_asistencia[comision][fecha][alumno_id] = True/False
if "db_asistencia" not in st.session_state:
    st.session_state.db_asistencia = {}

if comision_activa not in st.session_state.db_asistencia:
    st.session_state.db_asistencia[comision_activa] = {}

# --- BARRA LATERAL / PANEL DE CONTROL COMPACTO ---
st.title(f"📅 Asistencia - {comision_activa}")

with st.expander("📅 Selección de Fecha y Parámetros", expanded=True):
    fecha_seleccionada = st.date_input("Día de la Clase:", value=datetime.now().date())
    fecha_str = str(fecha_seleccionada)
    
    # Inicializar la fecha específica para esta comisión si no existe
    if fecha_str not in st.session_state.db_asistencia[comision_activa]:
        st.session_state.db_asistencia[comision_activa][fecha_str] = {}

    # Reglas e indicadores mínimos de presencialidad
    if "asistencia_reglas" not in st.session_state:
        st.session_state.asistencia_reglas = {"promo_asist": 80, "regular_asist": 60}
        
    st.session_state.asistencia_reglas["promo_asist"] = st.slider(
        "% Mínimo Promoción", 0, 100, int(st.session_state.asistencia_reglas["promo_asist"])
    )
    st.session_state.asistencia_reglas["regular_asist"] = st.slider(
        "% Mínimo Regularidad", 0, 100, int(st.session_state.asistencia_reglas["regular_asist"])
    )

st.info(f"Clase: **{fecha_seleccionada.strftime('%d/%m/%Y')}**")

# 3. Obtener y filtrar alumnos de la DB nativa que pertenezcan a la comisión activa
todos_alumnos = obtener_estudiantes()
alumnos_comision = [a for a in todos_alumnos if a.domicilio == comision_activa] if todos_alumnos else []

if not alumnos_comision:
    st.warning(f"No hay alumnos registrados en la {comision_activa}. Cargue alumnos en la sección de inicio.")
else:
    # Puntero directo al diccionario de asistencias de hoy
    asistencias_hoy = st.session_state.db_asistencia[comision_activa][fecha_str]

    # --- BOTONES DE ACCIÓN MASIVA (DISEÑO RESPONSIVE EN FILA) ---
    col_masivo, col_reset = st.columns(2)
    
    with col_masivo:
        if st.button("🚀 Seleccionar Todos (Presente)", use_container_width=True):
            for alu in alumnos_comision:
                asistencias_hoy[alu.id] = True
            st.success("Se marcó PRESENTE a toda la planilla.")
            st.rerun()

    with col_reset:
        # Botón de reinicio seguro solicitado en caso de error
        with st.popover("🔄 Reiniciar Planilla", use_container_width=True):
            st.warning(f"¿Seguro que desea vaciar la asistencia del día {fecha_seleccionada.strftime('%d/%m/%Y')}?")
            confirmar_reinicio = st.checkbox("Sí, deseo borrar los datos de hoy por error", key="confirm_reset_asist")
            if st.button("Confirmar Reinicio", type="primary", use_container_width=True):
                if confirmar_reinicio:
                    # Limpiamos el diccionario de la fecha actual
                    st.session_state.db_asistencia[comision_activa][fecha_str] = {}
                    st.success("Asistencia reiniciada correctamente.")
                    st.rerun()
                else:
                    st.error("Debe tildar la casilla de confirmación.")

    st.divider()

    # --- LISTADO INDIVIDUAL DE ASISTENCIA ---
    st.subheader("📋 Control de Presentismo")
    
    # Formato optimizado para celulares en forma de tarjetas limpias o filas expandidas
    for alu in alumnos_comision:
        # Extraer legajo del campo descripción empaquetado del SIU
        leg_val = alu.descripcion.split("Legajo:")[1].split("|")[0].strip() if "Legajo:" in alu.descripcion else "S/D"
        
        # Verificar estado actual guardado (por defecto False/Ausente)
        estado_actual = asistencias_hoy.get(alu.id, False)
        
        # Contenedor para cada fila de alumno
        with st.container(border=True):
            c_info, c_check = st.columns([3, 1])
            
            with c_info:
                st.markdown(f"**{alu.apellido}, {alu.nombre}**")
                st.caption(f"Legajo: {leg_val} | DNI: {alu.dni}")
            
            with c_check:
                # Selector individual táctil
                nuevo_estado = st.checkbox(
                    "Presente", 
                    value=estado_actual, 
                    key=f"chk_{alu.id}_{fecha_str}"
                )
                
                # Guardar el cambio inmediatamente si el docente interactúa con la casilla
                if nuevo_estado != estado_actual:
                    asistencias_hoy[alu.id] = nuevo_estado
                    st.toast(f"Actualizado: {alu.apellido}", icon="📝")

    # --- BOTÓN DE EXPORTACIÓN REGIONAL DE CONTROL ---
    st.divider()
    if st.button("📥 Descargar Planilla del Día (CSV)", use_container_width=True):
        datos_csv = []
        for alu in alumnos_comision:
            leg_val = alu.descripcion.split("Legajo:")[1].split("|")[0].strip() if "Legajo:" in alu.descripcion else "S/D"
            datos_csv.append({
                "Legajo": leg_val,
                "Alumno": f"{alu.apellido}, {alu.nombre}",
                "Documento": alu.dni,
                "Estado": "Presente" if asistencias_hoy.get(alu.id, False) else "Ausente"
            })
        df_export = pd.DataFrame(datos_csv)
        csv = df_export.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="Confirmar Descarga",
            data=csv,
            file_name=f"Asistencia_{comision_activa}_{fecha_str}.csv",
            mime="text/csv",
            use_container_width=True
        )