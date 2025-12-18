import streamlit as st
import time
import logging
from database import get_db
from models import Usuario

# --- CONFIGURACIÓN INICIAL (Debe ir primero) ---
st.set_page_config(
    page_title="SisoAI - Salud Ocupacional",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Configurar logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ESTILOS CSS PARA OCULTAR/MOSTRAR MENÚ ---
def inject_css(authenticated):
    if not authenticated:
        # Ocultar sidebar en Login
        st.markdown("""
            <style>
                [data-testid="stSidebar"] {display: none;}
                [data-testid="collapsedControl"] {display: none;}
                .main {padding-top: 2rem;}
            </style>
        """, unsafe_allow_html=True)
    else:
        # Mostrar sidebar limpia (ocultando navegación nativa de archivos)
        st.markdown("""
            <style>
                .main {padding: 1rem;}
                div[data-testid="stSidebarNav"] {display: none;} 
            </style>
        """, unsafe_allow_html=True)

# --- GESTIÓN DE ESTADO ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

inject_css(st.session_state.authenticated)

# --- LOGIN ---
def login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🏥 SisoAI</h1>", unsafe_allow_html=True)
        st.divider()
        with st.form("login_form"):
            st.subheader("Iniciar Sesión")
            email = st.text_input("Correo", value="admin@sisoai.com")
            password = st.text_input("Contraseña", type="password", value="admin123")
            
            if st.form_submit_button("Ingresar", use_container_width=True):
                db = next(get_db())
                try:
                    user_db = db.query(Usuario).filter(Usuario.email == email).first()
                    if user_db and user_db.hashed_password == password:
                        st.session_state.authenticated = True
                        st.session_state.user = {
                            "id": str(user_db.id),
                            "email": user_db.email,
                            "rol": user_db.rol,
                            "nombre": user_db.nombre_completo
                        }
                        st.success(f"Bienvenido {user_db.nombre_completo}")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas")
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    db.close()

# --- MENÚ LATERAL ---
def sidebar_menu():
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=50)
        st.title("SisoAI")
        st.write(f"Hola, **{st.session_state.user['nombre']}**")
        st.caption(f"Rol: {st.session_state.user['rol']}")
        st.divider()
        
        opcion = st.radio(
            "Ir a:", 
            [
                "📊 Dashboard",          # Opción 0
                "📋 Admisiones",         # Opción 1
                "👨‍⚕️ Triaje Médico",     # Opción 2
                "🩺 Evaluación Médica",  # Opción 3 (Nueva)
                "⚙️ Configuración"       # Opción 4
            ],
            index=0
        )
        
        st.divider()
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
            
    return opcion

# --- MAIN ---
def main():
    if not st.session_state.authenticated:
        login()
    else:
        seleccion = sidebar_menu()
        
        try:
            # LÓGICA DE NAVEGACIÓN (Router)
            if seleccion == "📊 Dashboard":
                st.switch_page("pages/0_Dashboard.py")
            
            elif seleccion == "📋 Admisiones":
                st.switch_page("pages/1_Admision.py")
                
            elif seleccion == "👨‍⚕️ Triaje Médico":
                st.switch_page("pages/2_Triaje_Medico.py")
            
            elif seleccion == "🩺 Evaluación Médica":
                st.switch_page("pages/4_Evaluacion_Medica.py")
                
            elif seleccion == "⚙️ Configuración":
                st.switch_page("pages/3_Configuracion.py")
                
        except Exception as e:
            if "switch_page" in str(e):
                st.error("Error crítico: Actualice Streamlit (`pip install streamlit --upgrade`)")
            else:
                st.error(f"No se pudo cargar el módulo: {e}")

if __name__ == "__main__":
    main()