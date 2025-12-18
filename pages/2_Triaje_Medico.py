import streamlit as st
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from models import Paciente, Admision, HojaRutaExamenes, CatalogoExamenes, ResultadoClinico, Usuario, EstadoExamen
from database import get_db, SessionLocal
from datetime import datetime
import logging
import time
import json

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FUNCIONES DE LÓGICA Y BD ---

def search_patient_triage(search_term):
    """Busca pacientes por DNI o Nombre"""
    db = SessionLocal()
    try:
        patients = db.query(Paciente).filter(
            or_(
                Paciente.numero_documento.ilike(f"%{search_term}%"),
                Paciente.nombres.ilike(f"%{search_term}%"),
                Paciente.apellidos.ilike(f"%{search_term}%")
            )
        ).limit(10).all()
        return patients
    finally:
        db.close()

def get_patient_active_admission(patient_id):
    """Busca la admisión activa del paciente"""
    db = SessionLocal()
    try:
        admission = db.query(Admision).filter(
            Admision.paciente_id == patient_id,
            Admision.estado_global == "En Circuito"
        ).order_by(desc(Admision.fecha_ingreso)).first()
        return admission
    finally:
        db.close()

def get_existing_triage_data(admission_id):
    """Recupera los datos de triaje guardados previamente para mostrarlos en el formulario"""
    db = SessionLocal()
    try:
        # Buscar cualquier examen que parezca de triaje/medicina
        target_exam = db.query(HojaRutaExamenes).join(CatalogoExamenes).filter(
            HojaRutaExamenes.admision_id == admission_id,
            (CatalogoExamenes.nombre.ilike("%Triaje%")) | 
            (CatalogoExamenes.nombre.ilike("%Medicina%")) |
            (CatalogoExamenes.nombre.ilike("%Musculo%"))
        ).first()

        # Fallback si no encuentra examen específico
        if not target_exam:
            target_exam = db.query(HojaRutaExamenes).filter(
                HojaRutaExamenes.admision_id == admission_id
            ).first()

        if target_exam:
            result = db.query(ResultadoClinico).filter(
                ResultadoClinico.admision_id == admission_id,
                ResultadoClinico.examen_id == target_exam.examen_id
            ).first()
            
            if result and result.datos_tecnicos:
                return result.datos_tecnicos
                
        return {} # Retorna vacío si no hay datos
    finally:
        db.close()

def save_vital_signs(admission_id, vitals_data, user_id):
    """Guarda los signos vitales en la base de datos"""
    db = SessionLocal()
    try:
        # 1. Buscar examen destino
        target_exam = db.query(HojaRutaExamenes).join(CatalogoExamenes).filter(
            HojaRutaExamenes.admision_id == admission_id,
            (CatalogoExamenes.nombre.ilike("%Triaje%")) | 
            (CatalogoExamenes.nombre.ilike("%Medicina%")) |
            (CatalogoExamenes.nombre.ilike("%Musculo%"))
        ).first()

        if not target_exam:
            target_exam = db.query(HojaRutaExamenes).filter(
                HojaRutaExamenes.admision_id == admission_id
            ).first()

        if not target_exam:
            return False, "Error crítico: No hay exámenes asociados a esta admisión."

        # 2. Crear o Actualizar Resultado
        existing_result = db.query(ResultadoClinico).filter(
            ResultadoClinico.admision_id == admission_id,
            ResultadoClinico.examen_id == target_exam.examen_id
        ).first()

        if existing_result:
            current_data = existing_result.datos_tecnicos or {}
            current_data.update(vitals_data)
            existing_result.datos_tecnicos = current_data
            existing_result.conclusiones_examen = f"Triaje actualizado. IMC: {vitals_data.get('imc')}"
        else:
            new_result = ResultadoClinico(
                admision_id=admission_id,
                examen_id=target_exam.examen_id,
                datos_tecnicos=vitals_data,
                observaciones="Signos vitales registrados en módulo de Triaje.",
                conclusiones_examen=f"Evaluado. IMC: {vitals_data.get('imc')}",
                created_at=datetime.now()
            )
            db.add(new_result)

        # 3. Marcar como Realizado
        target_exam.estado = EstadoExamen.REALIZADO
        target_exam.fecha_realizado = datetime.now()
        target_exam.medico_evaluador_id = user_id

        db.commit()
        return True, "Signos vitales guardados correctamente."

    except Exception as e:
        db.rollback()
        return False, f"Error: {str(e)}"
    finally:
        db.close()

# --- UI ---

def calculate_imc_ui(peso, talla_cm):
    if peso > 0 and talla_cm > 0:
        talla_m = talla_cm / 100
        imc = round(peso / (talla_m ** 2), 2)
        
        if imc < 18.5: return imc, "Bajo Peso", "blue"
        elif 18.5 <= imc < 25: return imc, "Normal", "green"
        elif 25 <= imc < 30: return imc, "Sobrepeso", "orange"
        else: return imc, "Obesidad", "red"
    return 0, "Pendiente", "gray"

def render_triage_dashboard(patient, admission):
    st.markdown(f"### 🩺 Triaje: {patient.nombres} {patient.apellidos}")
    st.caption(f"Admisión #{admission.id} | Fecha: {admission.fecha_ingreso.strftime('%d/%m/%Y')}")
    
    st.divider()

    # --- CARGAR DATOS EXISTENTES ---
    saved_data = get_existing_triage_data(admission.id)
    
    # Valores por defecto inteligentes (Si no hay datos, usa promedios normales, si hay, usa lo guardado)
    # Nota: Los floats deben coincidir con el step del input
    def_peso = float(saved_data.get("peso", 70.0))
    def_talla = int(saved_data.get("talla", 170))
    def_temp = float(saved_data.get("temperatura", 36.5))
    def_sat = int(saved_data.get("saturacion", 98))
    def_pas = int(saved_data.get("pa_sistolica", 120))
    def_pad = int(saved_data.get("pa_diastolica", 80))
    def_fc = int(saved_data.get("frecuencia_cardiaca", 75))
    def_fr = int(saved_data.get("frecuencia_respiratoria", 16))
    def_alergias = saved_data.get("alergias", "")
    def_obs = saved_data.get("observaciones", "")

    with st.form("vital_signs_form"):
        st.subheader("1. Signos Vitales (Adultos)")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            # Rango Peso: 30kg a 200kg
            peso = st.number_input("Peso (kg)", min_value=30.0, max_value=200.0, value=def_peso, step=0.1, format="%.1f")
        with c2:
            # Rango Talla: 100cm a 230cm
            talla = st.number_input("Talla (cm)", min_value=100, max_value=230, value=def_talla, step=1)
        with c3:
            # Rango Temp: 35°C a 42°C
            temp = st.number_input("Temp (°C)", min_value=35.0, max_value=42.0, value=def_temp, step=0.1, format="%.1f")
        with c4:
            # Rango SatO2: 70% a 100%
            sat = st.number_input("Sat O2 (%)", min_value=70, max_value=100, value=def_sat, step=1)

        c5, c6, c7, c8 = st.columns(4)
        with c5:
            # Rango PAS: 60 a 250
            pas = st.number_input("P.A. Sistólica", min_value=60, max_value=250, value=def_pas)
        with c6:
            # Rango PAD: 30 a 150
            pad = st.number_input("P.A. Diastólica", min_value=30, max_value=150, value=def_pad)
        with c7:
            # Rango FC: 40 a 200
            fc = st.number_input("Frec. Cardíaca", min_value=40, max_value=200, value=def_fc)
        with c8:
            # Rango FR: 10 a 60
            fr = st.number_input("Frec. Respiratoria", min_value=10, max_value=60, value=def_fr)

        imc_val, imc_txt, imc_color = calculate_imc_ui(peso, talla)
        st.info(f"📊 **IMC Calculado:** {imc_val} - :{imc_color}[{imc_txt}]")

        st.subheader("2. Observaciones")
        alergias = st.text_input("Alergias Conocidas", value=def_alergias, placeholder="Ninguna conocida")
        obs = st.text_area("Notas de Enfermería", value=def_obs, height=100)
        
        submit = st.form_submit_button("💾 Actualizar Triaje", type="primary")

        if submit:
            user_id = st.session_state.user['id'] if st.session_state.user else None
            
            vitals_data = {
                "peso": peso, "talla": talla, "imc": imc_val, "imc_diag": imc_txt,
                "temperatura": temp, "saturacion": sat,
                "pa_sistolica": pas, "pa_diastolica": pad,
                "frecuencia_cardiaca": fc, "frecuencia_respiratoria": fr,
                "alergias": alergias, "observaciones": obs
            }
            
            success, msg = save_vital_signs(admission.id, vitals_data, user_id)
            if success:
                st.success(msg)
                time.sleep(1)
                st.rerun() # Recargamos para que los datos se asienten en el formulario
            else:
                st.error(msg)

def main():
    if 'user' not in st.session_state or not st.session_state.authenticated:
        st.warning("🔒 Inicie sesión para acceder.")
        st.stop()

    st.title("👨‍⚕️ Módulo de Triaje Médico")

    patient = st.session_state.get('current_patient')

    if not patient:
        st.info("👋 Busque un paciente para comenzar la evaluación.")
        
        col_search, col_res = st.columns([2, 3])
        with col_search:
            search = st.text_input("🔍 Buscar por DNI o Nombre:", placeholder="Ej: Perez")
        
        with col_res:
            if len(search) > 2:
                results = search_patient_triage(search)
                if results:
                    opts = {f"{p.numero_documento} | {p.apellidos} {p.nombres}": p for p in results}
                    sel = st.selectbox("Seleccionar:", list(opts.keys()), index=None)
                    if sel:
                        st.session_state.current_patient = opts[sel]
                        st.rerun()
                else:
                    st.warning("No se encontraron pacientes.")
    else:
        if st.button("⬅️ Cambiar Paciente"):
            st.session_state.current_patient = None
            st.rerun()

        admission = get_patient_active_admission(patient.id)
        
        if admission:
            render_triage_dashboard(patient, admission)
        else:
            st.error(f"⚠️ El paciente {patient.nombres} no tiene una admisión 'En Circuito'.")
            st.info("Vaya al módulo **Admisiones** para registrarlo.")

if __name__ == "__main__":
    main()