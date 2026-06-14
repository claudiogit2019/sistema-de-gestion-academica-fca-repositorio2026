import streamlit as st
import pandas as pd
import re
from pypdf import PdfReader
from modules.logic import (
    registrar_estudiante, 
    obtener_estudiantes,
    eliminar_todos_los_estudiantes
)

# Configuración responsive móvil optimizada
st.set_page_config(page_title="FCA UNJu - Gestión Directa", layout="wide", initial_sidebar_state="collapsed")

# Inicialización de comisiones en el estado de la sesión
if "comisiones" not in st.session_state:
    st.session_state.comisiones = ["Comisión A1", "Comisión B2", "Comisión C1"]
if "global_comision" not in st.session_state:
    st.session_state.global_comision = "Comisión A1"

st.title("👥 Gestión de Estudiantes")

# =========================================================================
# ⚙️ CONTROL Y CREACIÓN DE COMISIONES
# =========================================================================
with st.container(border=True):
    st.markdown("### 🏫 Selección y Configuración de Comisión")
    
    st.session_state.global_comision = st.selectbox(
        "Seleccione la Comisión con la que va a trabajar:", 
        st.session_state.comisiones,
        index=st.session_state.comisiones.index(st.session_state.global_comision)
    )
    
    with st.form("form_nueva_comision", clear_on_submit=True):
        c_input, c_btn = st.columns([2, 1])
        nueva_com = c_input.text_input("¿Falta una comisión? Escriba el nombre aquí:", placeholder="Ej: Comisión D1")
        if c_btn.form_submit_button("➕ Crear Comisión", use_container_width=True):
            if nueva_com:
                nueva_com_clean = nueva_com.strip()
                if nueva_com_clean not in st.session_state.comisiones:
                    st.session_state.comisiones.append(nueva_com_clean)
                    st.session_state.global_comision = nueva_com_clean
                    st.success(f"¡{nueva_com_clean} creada!")
                    st.rerun()

st.subheader(f"📍 Trabajando en: {st.session_state.global_comision}")
st.divider()

# =========================================================================
# 📥 CARGA INMEDIATA AUTOMÁTICA (ESTILO PROTOTIPO ORIGINAL)
# =========================================================================
tab_siu, tab_manual = st.tabs(["📥 Carga Directa (Excel / PDF SIU)", "📝 Alta Manual Individual"])

with tab_siu:
    st.markdown("Subí el archivo e **importá directamente** a la comisión seleccionada.")
    
    # Al remover el botón, usamos el cambio de archivo como disparador directo
    archivo_cargado = st.file_uploader(
        "Arrastre o seleccione el archivo para cargar e importar inmediatamente:", 
        type=["xlsx", "xls", "pdf"], 
        key="file_uploader_automatico"
    )
    
    if archivo_cargado is not None:
        # Generamos un identificador único para el archivo actual
        token_archivo = f"{archivo_cargado.name}_{archivo_cargado.size}"
        
        # Solo se ejecuta si es un archivo nuevo y no se procesó en este ciclo
        if st.session_state.get("ultimo_token_procesado") != token_archivo:
            nombre_archivo = archivo_cargado.name.lower()
            alumnos_extraidos = []
            
            try:
                # --- PARSEO DE EXCEL ---
                if nombre_archivo.endswith('.xlsx') or nombre_archivo.endswith('.xls'):
                    engine_mecanismo = 'xlrd' if nombre_archivo.endswith('.xls') else 'openpyxl'
                    df = pd.read_excel(archivo_cargado, engine=engine_mecanismo)
                    
                    c_legajo = next((c for c in df.columns if 'legajo' in str(c).lower()), df.columns[0])
                    c_alumno = next((c for c in df.columns if 'alumno' in str(c).lower() or 'nombre' in str(c).lower()), df.columns[1])
                    c_dni = next((c for c in df.columns if 'dni' in str(c).lower() or 'documento' in str(c).lower()), df.columns[2])
                    
                    for _, row in df.iterrows():
                        if pd.isna(row[c_alumno]) or pd.isna(row[c_dni]):
                            continue
                        partes = str(row[c_alumno]).split(',')
                        ape = partes[0].strip() if len(partes) > 0 else "S/A"
                        nom = partes[1].strip() if len(partes) > 1 else "S/N"
                        
                        alumnos_extraidos.append({
                            'legajo': str(row[c_legajo]).split('.')[0].strip(),
                            'apellido': ape, 'nombre': nom,
                            'dni': str(int(float(row[c_dni]))) if isinstance(row[c_dni], (int, float)) else str(row[c_dni]).strip()
                        })
                
                # --- PARSEO DE PDF ---
                elif nombre_archivo.endswith('.pdf'):
                    lector_pdf = PdfReader(archivo_cargado)
                    texto_completo = ""
                    for pagina in lector_pdf.pages:
                        texto_completo += pagina.extract_text() + "\n"
                    
                    lineas = texto_completo.split('\n')
                    for linea in lineas:
                        match_dni = re.search(r'\b(\d{7,8})\b', linea)
                        if match_dni:
                            dni_ext = match_dni.group(1)
                            linea_sin_dni = linea.replace(dni_ext, "").strip()
                            palabras = linea_sin_dni.split()
                            if len(palabras) >= 2:
                                leg_ext = palabras[0]
                                nombre_completo_ext = " ".join(palabras[1:])
                                partes = nombre_completo_ext.split(',')
                                ape = partes[0].strip() if len(partes) > 0 else nombre_completo_ext
                                nom = partes[1].strip() if len(partes) > 1 else "S/N"
                                
                                alumnos_extraidos.append({
                                    'legajo': leg_ext, 'apellido': ape, 'nombre': nom, 'dni': dni_ext
                                })
                
                # --- ACCIÓN DIRECTA: LIMPIEZA E IMPORTACIÓN ---
                if alumnos_extraidos:
                    # 1. Limpiamos la base de datos por completo para evitar duplicaciones viejas
                    eliminar_todos_los_estudiantes()
                    
                    # 2. Guardamos los nuevos alumnos directo a SQLite
                    contador_guardados = 0
                    for alu in alumnos_extraidos:
                        datos_alumno = {
                            'nombre': alu['nombre'], 'apellido': alu['apellido'], 'dni': alu['dni'],
                            'condicion': "Regular", 'domicilio': f"{st.session_state.global_comision}",
                            'descripcion': f"Legajo: {alu['legajo']} | Email: S/D | Tel: S/D"
                        }
                        if registrar_estudiante(datos_alumno):
                            contador_guardados += 1
                    
                    # Guardamos la marca para evitar bucles de recarga infinitos
                    st.session_state.ultimo_token_procesado = token_archivo
                    st.success(f"🚀 ¡Base de datos saneada! Se importaron {contador_guardados} alumnos directo a la {st.session_state.global_comision}.")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error en la carga rápida: {e}")

with tab_manual:
    with st.form("form_alta_manual_def", clear_on_submit=True):
        st.markdown("### Registrar Alumno Individual")
        t_leg = st.text_input("Número de Legajo")
        t_ape = st.text_input("Apellido/s")
        t_nom = st.text_input("Nombre/s")
        t_dni = st.text_input("Documento (DNI)")
        
        if st.form_submit_button("💾 Guardar en Comisión Activa", use_container_width=True):
            if t_ape and t_nom and t_dni:
                datos_m = {
                    'nombre': t_nom, 'apellido': t_ape, 'dni': t_dni, 'condicion': "Regular",
                    'domicilio': f"{st.session_state.global_comision}",
                    'descripcion': f"Legajo: {t_leg} | Email: S/D | Tel: S/D"
                }
                if registrar_estudiante(datos_m):
                    st.success("Estudiante guardado con éxito.")
                    st.rerun()
                else:
                    st.error("El DNI ingresado ya existe.")

st.divider()

# =========================================================================
# 📋 PLANILLA DE CONTROL DEFINITIVA (SINO AL DETALLE)
# =========================================================================
st.subheader(f"📋 Estudiantes grabados en la {st.session_state.global_comision}")
alumnos_db = obtener_estudiantes()

if alumnos_db:
    filas_comision = []
    for a in alumnos_db:
        if a.domicilio == st.session_state.global_comision:
            leg_val = a.descripcion.split("Legajo:")[1].split("|")[0].strip() if "Legajo:" in a.descripcion else "S/D"
            filas_comision.append({
                "Legajo": leg_val,
                "Alumno": f"{a.apellido}, {a.nombre}",
                "Documento": a.dni
            })
            
    if filas_comision:
        st.dataframe(pd.DataFrame(filas_comision), use_container_width=True, hide_index=True)
    else:
        st.info(f"No hay alumnos registrados en la {st.session_state.global_comision} todavía.")
else:
    st.info("La base de datos se encuentra vacía.")
