import streamlit as st
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models import Paciente, Empresa, Protocolo, Admision, HojaRutaExamenes, ProtocoloDetalle, CatalogoExamenes
from database import get_db, SessionLocal
from datetime import datetime, date
import logging
import time
import pandas as pd

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FUNCIONES DE BASE DE DATOS ---

def get_recent_patients_db():
    """Obtiene los últimos 20 pacientes registrados"""
    db = SessionLocal()
    try:
        patients = db.query(Paciente).order_by(desc(Paciente.id)).limit(20).all()
        return patients
    except Exception as e:
        logger.error(f"Error fetching recent patients: {e}")
        return []
    finally:
        db.close()

def search_patients_db(criterion, value):
    """Busca pacientes según el criterio seleccionado"""
    db = SessionLocal()
    try:
        query = db.query(Paciente)
        if criterion == "DNI":
            results = query.filter(Paciente.numero_documento.ilike(f"%{value}%")).limit(20).all()
        elif criterion == "Nombres":
            results = query.filter(Paciente.nombres.ilike(f"%{value}%")).limit(20).all()
        elif criterion == "Apellidos":
            results = query.filter(Paciente.apellidos.ilike(f"%{value}%")).limit(20).all()
        else:
            results = []
        return results
    except Exception as e:
        logger.error(f"Error buscando pacientes: {e}")
        return []
    finally:
        db.close()

def save_new_patient(data):
    """Guarda un nuevo paciente"""
    db = SessionLocal()
    try:
        new_patient = Paciente(**data)
        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)
        return new_patient
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def register_admission_db(patient_id, company_id, protocol_id, user_id):
    """Crea la admisión y la hoja de ruta"""
    db = SessionLocal()
    try:
        new_admission = Admision(
            paciente_id=patient_id,
            empresa_id=company_id,
            protocolo_id=protocol_id,
            fecha_ingreso=datetime.now(),
            estado_global="En Circuito",
            usuario_admision_id=user_id
        )
        db.add(new_admission)
        db.flush()
        
        protocol_details = db.query(ProtocoloDetalle).filter(ProtocoloDetalle.protocolo_id == protocol_id).all()
        
        count_exams = 0
        for detail in protocol_details:
            exam_route = HojaRutaExamenes(
                admision_id=new_admission.id,
                examen_id=detail.examen_id,
                estado="Pendiente"
            )
            db.add(exam_route)
            count_exams += 1
            
        db.commit()
        return new_admission, count_exams
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# --- UTILS ---

def calculate_age(born):
    if not born: return 0
    today = date.today() if isinstance(born, datetime) else datetime.now().date()
    born = born.date() if isinstance(born, datetime) else born
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

# --- UI COMPONENTS ---

def render_patient_card(patient):
    st.markdown("""---""")
    with st.container():
        col_img, col_info = st.columns([1, 4])
        with col_img:
            # Usamos un avatar genérico
            st.markdown("### 👤")
        
        with col_info:
            st.markdown(f"### {patient.nombres} {patient.apellidos}")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**🆔 DNI:** {patient.numero_documento}")
            c2.markdown(f"**🎂 Edad:** {calculate_age(patient.fecha_nacimiento)} años")
            c3.markdown(f"**📧 Email:** {patient.email or 'N/A'}")
            
            st.success(f"Paciente seleccionado correctamente")

def tab_search_patient():
    st.header("🔍 Directorio de Pacientes")
    
    with st.expander("📋 Ver últimos pacientes registrados", expanded=True):
        patients = get_recent_patients_db()
        if patients:
            data = []
            for p in patients:
                data.append({
                    "DNI": p.numero_documento,
                    "Apellidos": p.apellidos,
                    "Nombres": p.nombres,
                    "Edad": calculate_age(p.fecha_nacimiento)
                })
            df = pd.DataFrame(data)
            # CORRECCIÓN: width='stretch' elimina el warning de use_container_width
            st.dataframe(df, use_container_width=True) 
        else:
            st.info("No hay pacientes registrados aún.")

    st.divider()
    
    col_filter, col_input = st.columns([1, 3])
    with col_filter:
        search_criteria = st.selectbox("Buscar por:", ["DNI", "Apellidos", "Nombres"])
    
    with col_input:
        search_value = st.text_input(f"Escriba el {search_criteria}...", placeholder="Ej: 12345678")

    if len(search_value) > 1:
        results = search_patients_db(search_criteria, search_value)
        if results:
            patient_options = {f"{p.numero_documento} - {p.apellidos}, {p.nombres}": p for p in results}
            selected_label = st.selectbox("✅ Resultados encontrados:", options=list(patient_options.keys()), index=None)
            
            if selected_label:
                st.session_state.current_patient = patient_options[selected_label]
        else:
            st.warning("No se encontraron coincidencias.")

    if st.session_state.get('current_patient'):
        render_patient_card(st.session_state.current_patient)

def tab_new_patient():
    st.header("➕ Nuevo Paciente")
    with st.form("new_patient_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            dni = st.text_input("DNI *")
            nombres = st.text_input("Nombres *")
            fecha_nac = st.date_input("Fecha Nacimiento *", min_value=datetime(1950, 1, 1))
            civil = st.selectbox("Estado Civil", ["Soltero", "Casado", "Conviviente"])
        
        with col2:
            apellidos = st.text_input("Apellidos *")
            genero = st.selectbox("Género", ["M", "F"])
            email = st.text_input("Email")
            telefono = st.text_input("Teléfono")
        
        direccion = st.text_area("Dirección")
        
        # CORRECCIÓN: use_container_width=True para botones
        if st.form_submit_button("Guardar Paciente", use_container_width=True):
            if all([dni, nombres, apellidos]):
                try:
                    data = {
                        "numero_documento": dni, "nombres": nombres, "apellidos": apellidos,
                        "fecha_nacimiento": fecha_nac, "genero": genero, "email": email,
                        "telefono": telefono, "direccion_domicilio": direccion, "estado_civil": civil
                    }
                    new_p = save_new_patient(data)
                    st.success("Paciente registrado!")
                    st.session_state.current_patient = new_p
                    time.sleep(1)
                    st.rerun() # CORRECCIÓN: st.rerun() en lugar de experimental_rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Faltan campos obligatorios.")

def section_admission_process(patient):
    st.markdown("### 🏥 Crear Admisión")
    db = SessionLocal()
    try:
        companies = db.query(Empresa).all()
        if not companies:
            st.error("No hay empresas registradas.")
            return

        comp_dict = {f"{c.razon_social}": c.id for c in companies}
        
        col1, col2 = st.columns(2)
        with col1:
            c_label = st.selectbox("Empresa", list(comp_dict.keys()))
            c_id = comp_dict[c_label]
        
        with col2:
            protos = db.query(Protocolo).filter(Protocolo.empresa_id == c_id).all()
            if protos:
                p_dict = {p.nombre_protocolo: p.id for p in protos}
                p_label = st.selectbox("Protocolo", list(p_dict.keys()))
                p_id = p_dict[p_label]
            else:
                st.warning("Esta empresa no tiene protocolos activos.")
                p_id = None
        
        if p_id:
            st.markdown("---")
            # CORRECCIÓN: use_container_width=True
            if st.button("🚀 Generar Admisión", type="primary", use_container_width=True):
                user_id = st.session_state.user['id'] if st.session_state.user else None
                adm, count = register_admission_db(patient.id, c_id, p_id, user_id)
                st.success(f"¡Admisión creada con éxito! Se asignaron {count} exámenes.")
                time.sleep(2)
                st.session_state.current_patient = None
                st.rerun() # CORRECCIÓN: st.rerun()
            
    finally:
        db.close()

def main():
    st.title("Gestión de Admisiones")
    tab1, tab2 = st.tabs(["🔍 Directorio", "➕ Nuevo"])
    
    with tab1:
        tab_search_patient()
    with tab2:
        tab_new_patient()
        
    if st.session_state.get('current_patient'):
        section_admission_process(st.session_state.current_patient)

if __name__ == "__main__":
    main()