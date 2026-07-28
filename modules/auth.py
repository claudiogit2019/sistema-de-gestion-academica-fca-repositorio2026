import streamlit as st
import os

def requiere_login():
    """
    Verifica la sesión activa. Si no está autenticado, detiene la ejecución
    y dibuja el formulario de login en la página donde sea invocada.
    """
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.title("🔐 Acceso al Sistema de Gestión Académica - FCA UNJu")
        
        with st.form("form_login"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            
            if submit:
                # Intentamos leer de st.secrets de forma segura o de os.getenv/valores por defecto
                try:
                    USER_OK = st.secrets.get("ADMIN_USER", "admin")
                    PASS_OK = st.secrets.get("ADMIN_PASS", "fca2026")
                except Exception:
                    USER_OK = os.getenv("ADMIN_USER", "admin")
                    PASS_OK = os.getenv("ADMIN_PASS", "Academica@2026")
                
                if usuario == USER_OK and password == PASS_OK:
                    st.session_state.autenticado = True
                    st.success("¡Bienvenido/a!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
        
        # Detiene la renderización de la página actual hasta que se autentique
        st.stop()

    # Si está autenticado, agrega la opción de cerrar sesión en la barra lateral
    with st.sidebar:
        st.write("👤 **Usuario:** Admin")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()
