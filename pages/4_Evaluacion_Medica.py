import streamlit as st
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from models import (
    Paciente, Admision, HojaRutaExamenes, 
    ResultadoClinico, CatalogoExamenes, Usuario
)
from database import SessionLocal
from datetime import datetime
import json
import logging
from typing import Dict, Any, Optional

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_patient() -> Optional[Paciente]:
    """Search for a patient by document number or name"""
    st.subheader("Buscar Paciente")
    
    search_term = st.text_input(
        "Ingrese DNI o nombre del paciente:",
        key="patient_search"
    )
    
    if search_term:
        db = SessionLocal()
        try:
            # Search by document number or name
            patients = db.query(Paciente).filter(
                or_(
                    Paciente.numero_documento.ilike(f"%{search_term}%"),
                    Paciente.nombres.ilike(f"%{search_term}%"),
                    Paciente.apellidos.ilike(f"%{search_term}%")
                )
            ).limit(10).all()
            
            if patients:
                if len(patients) == 1:
                    return patients[0]
                else:
                    # Show selection if multiple patients found
                    patient_options = {
                        f"{p.nombres} {p.apellidos} (DNI: {p.numero_documento})": p 
                        for p in patients
                    }
                    selected = st.selectbox(
                        "Seleccione el paciente:",
                        options=list(patient_options.keys())
                    )
                    return patient_options[selected]
            else:
                st.warning("No se encontraron pacientes con ese criterio de búsqueda")
                return None
                
        except Exception as e:
            st.error(f"Error al buscar paciente: {str(e)}")
            logger.exception("Error searching for patient:")
            return None
        finally:
            db.close()
    return None

def get_pending_exams(patient_id: int) -> list:
    """Get pending exams for a patient's active admission"""
    db = SessionLocal()
    try:
        # Get active admission
        admission = db.query(Admision).filter(
            Admision.paciente_id == patient_id,
            Admision.estado_global == "En Circuito"
        ).order_by(Admision.fecha_ingreso.desc()).first()
        
        if not admission:
            st.warning("No se encontró una admisión activa para este paciente")
            return []
        
        # Get pending exams
        exams = db.query(
            HojaRutaExamenes,
            CatalogoExamenes.nombre
        ).join(
            CatalogoExamenes,
            HojaRutaExamenes.examen_id == CatalogoExamenes.id
        ).filter(
            HojaRutaExamenes.admision_id == admission.id,
            HojaRutaExamenes.estado != "Realizado"
        ).all()
        
        return exams
        
    except Exception as e:
        st.error(f"Error al obtener exámenes pendientes: {str(e)}")
        logger.exception("Error getting pending exams:")
        return []
    finally:
        db.close()

def show_exam_form(exam_route_id: int, exam_name: str, admission_id: int):
    """Show the appropriate form based on exam type"""
    st.markdown(f"### 🩺 Evaluación: {exam_name}")
    st.info("Complete los datos clínicos del examen.")
    
    # Initialize form data
    form_data = {}
    conclusion = ""
    
    # Get existing result if it exists
    db = SessionLocal()
    try:
        existing_result = db.query(ResultadoClinico).filter(
            ResultadoClinico.admision_id == admission_id,
            ResultadoClinico.examen_id == db.query(HojaRutaExamenes.examen_id)
            .filter(HojaRutaExamenes.id == exam_route_id).scalar_subquery()
        ).first()
        
        if existing_result:
            form_data = existing_result.datos_tecnicos or {}
            conclusion = existing_result.conclusiones_examen or ""
    except Exception as e:
        st.error(f"Error al cargar resultados previos: {str(e)}")
    finally:
        db.close()
    
    # Show appropriate form based on exam name
    if "audiometr" in exam_name.lower():
        st.write("#### 🎧 Audiometría")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Oído Derecho (dB HL)**")
            form_data["od_500"] = st.number_input("500 Hz", min_value=0, max_value=120, value=int(form_data.get("od_500", 0)))
            form_data["od_1000"] = st.number_input("1000 Hz", min_value=0, max_value=120, value=int(form_data.get("od_1000", 0)))
            form_data["od_2000"] = st.number_input("2000 Hz", min_value=0, max_value=120, value=int(form_data.get("od_2000", 0)))
            form_data["od_4000"] = st.number_input("4000 Hz", min_value=0, max_value=120, value=int(form_data.get("od_4000", 0)))
            form_data["od_8000"] = st.number_input("8000 Hz", min_value=0, max_value=120, value=int(form_data.get("od_8000", 0)))
            
        with col2:
            st.write("**Oído Izquierdo (dB HL)**")
            form_data["oi_500"] = st.number_input("500 Hz ", min_value=0, max_value=120, value=int(form_data.get("oi_500", 0)))
            form_data["oi_1000"] = st.number_input("1000 Hz ", min_value=0, max_value=120, value=int(form_data.get("oi_1000", 0)))
            form_data["oi_2000"] = st.number_input("2000 Hz ", min_value=0, max_value=120, value=int(form_data.get("oi_2000", 0)))
            form_data["oi_4000"] = st.number_input("4000 Hz ", min_value=0, max_value=120, value=int(form_data.get("oi_4000", 0)))
            form_data["oi_8000"] = st.number_input("8000 Hz ", min_value=0, max_value=120, value=int(form_data.get("oi_8000", 0)))
        
    elif "oftalmol" in exam_name.lower():
        st.write("#### 👁️ Oftalmología")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Agudeza Visual Lejos**")
            form_data["av_lejos_od"] = st.text_input("OD (Ojo Derecho)", value=form_data.get("av_lejos_od", "20/20"))
            form_data["av_lejos_oi"] = st.text_input("OI (Ojo Izquierdo)", value=form_data.get("av_lejos_oi", "20/20"))
            
            st.write("**Agudeza Visual Cerca**")
            form_data["av_cerca_od"] = st.text_input("OD Cerca", value=form_data.get("av_cerca_od", "J1"))
            form_data["av_cerca_oi"] = st.text_input("OI Cerca", value=form_data.get("av_cerca_oi", "J1"))
            
        with col2:
            vc_opts = ["Normal", "Anomalía leve", "Anomalía moderada", "Anomalía severa", "Acromatopsia"]
            vc_idx = vc_opts.index(form_data.get("vision_colores", "Normal")) if form_data.get("vision_colores") in vc_opts else 0
            form_data["vision_colores"] = st.selectbox("Visión de Colores", options=vc_opts, index=vc_idx)
            
            est_opts = ["Normal (40-60 seg)", "Reducida (60-100)", "Muy reducida (>100)", "Ausente"]
            est_idx = est_opts.index(form_data.get("estereopsis", "Normal (40-60 seg)")) if form_data.get("estereopsis") in est_opts else 0
            form_data["estereopsis"] = st.selectbox("Estereopsis", options=est_opts, index=est_idx)
    
    elif "espirometr" in exam_name.lower():
        st.write("#### 🌬️ Espirometría")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            form_data["fvc"] = st.number_input("FVC (L)", min_value=0.0, max_value=10.0, step=0.1, value=float(form_data.get("fvc", 0.0)))
            
        with col2:
            form_data["fev1"] = st.number_input("FEV1 (L)", min_value=0.0, max_value=10.0, step=0.1, value=float(form_data.get("fev1", 0.0)))
            
        with col3:
            form_data["fev1_fvc"] = st.number_input("FEV1/FVC (%)", min_value=0, max_value=100, value=int(form_data.get("fev1_fvc", 0)))
        
        if form_data["fvc"] > 0:
            st.caption(f"FVC Predicho (aprox): {round(form_data['fvc'] * 1.1, 1)} L")
    
    elif "laboratorio" in exam_name.lower():
        st.write("#### 🧪 Laboratorio Clínico")
        col1, col2 = st.columns(2)
        
        with col1:
            form_data["hemoglobina"] = st.number_input("Hemoglobina (g/dL)", min_value=0.0, max_value=30.0, step=0.1, value=float(form_data.get("hemoglobina", 0.0)))
            form_data["glucosa"] = st.number_input("Glucosa (mg/dL)", min_value=0, max_value=1000, value=int(form_data.get("glucosa", 0)))
            
        with col2:
            form_data["colesterol"] = st.number_input("Colesterol Total (mg/dL)", min_value=0, max_value=500, value=int(form_data.get("colesterol", 0)))
            
            gs_opts = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
            gs_idx = gs_opts.index(form_data.get("grupo_sanguineo", "O+")) if form_data.get("grupo_sanguineo") in gs_opts else 6
            form_data["grupo_sanguineo"] = st.selectbox("Grupo Sanguíneo", options=gs_opts, index=gs_idx)
    
    elif "musculoesquel" in exam_name.lower():
        st.write("#### 🦴 Examen Musculoesquelético")
        col1, col2 = st.columns(2)
        
        with col1:
            form_data["phallen"] = st.checkbox("Maniobra de Phallen positiva", value=form_data.get("phallen", False))
            form_data["tinel"] = st.checkbox("Signo de Tinel positivo", value=form_data.get("tinel", False))
            
        with col2:
            form_data["lasegue"] = st.checkbox("Maniobra de Lasegue positivo", value=form_data.get("lasegue", False))
            
    elif "psicol" in exam_name.lower():
        st.write("#### 🧠 Evaluación Psicológica")
        form_data["observaciones"] = st.text_area("Observaciones / Aptitud Psicológica", value=form_data.get("observaciones", ""), height=150)
    else:
        st.write("#### Examen General")
        form_data["resultado"] = st.text_area("Resultados del examen", value=form_data.get("resultado", ""), height=200)
    
    st.markdown("---")
    conclusion = st.text_area("Conclusión del examen (Normal / Observado / Patológico)", value=conclusion, height=100)
    
    if st.button("💾 Guardar Resultado", type="primary"):
        save_exam_result(
            exam_route_id=exam_route_id,
            exam_name=exam_name,
            admission_id=admission_id,
            form_data=form_data,
            conclusion=conclusion
        )

def save_exam_result(exam_route_id: int, exam_name: str, admission_id: int, form_data: Dict[str, Any], conclusion: str):
    """Save exam results to the database"""
    db = SessionLocal()
    try:
        exam_route = db.query(HojaRutaExamenes).get(exam_route_id)
        if not exam_route:
            st.error("No se encontró la ruta del examen")
            return
        
        result = db.query(ResultadoClinico).filter(
            ResultadoClinico.admision_id == admission_id,
            ResultadoClinico.examen_id == exam_route.examen_id
        ).first()
        
        if not result:
            result = ResultadoClinico(
                admision_id=admission_id,
                examen_id=exam_route.examen_id,
                datos_tecnicos=form_data,
                conclusiones_examen=conclusion,
            )
            db.add(result)
        else:
            result.datos_tecnicos = form_data
            result.conclusiones_examen = conclusion
        
        exam_route.estado = "Realizado"
        exam_route.fecha_realizado = datetime.now()
        exam_route.medico_evaluador_id = st.session_state.user["id"]
        
        db.commit()
        st.success("¡Resultado guardado exitosamente!")
        st.balloons()
        st.rerun()
        
    except Exception as e:
        db.rollback()
        st.error(f"Error al guardar el resultado: {str(e)}")
        logger.exception("Error saving exam result:")
    finally:
        db.close()

def main():
    st.title("👩‍⚕️ Módulo de Evaluación Médica")
    
    if 'user' not in st.session_state or not st.session_state.authenticated:
        st.warning("Por favor inicie sesión para acceder a esta página.")
        return
    
    user_role = st.session_state.user.get("rol", "").lower()
    if user_role not in ["medico", "admin"]:
        st.error("No tiene permisos para acceder a este módulo.")
        return
    
    if 'current_patient' not in st.session_state or not st.session_state.current_patient:
        patient = search_patient()
        if patient:
            st.session_state.current_patient = {
                "id": patient.id,
                "nombre": f"{patient.nombres} {patient.apellidos}",
                "documento": patient.numero_documento
            }
            st.rerun()
    else:
        patient = st.session_state.current_patient
        col_info, col_btn = st.columns([3, 1])
        with col_info:
            st.success(f"Paciente: **{patient['nombre']}** (DNI: {patient['documento']})")
        with col_btn:
             if st.button("🔄 Cambiar Paciente"):
                del st.session_state.current_patient
                st.rerun()
        
        db = SessionLocal()
        try:
            admission = db.query(Admision).filter(
                Admision.paciente_id == patient["id"],
                Admision.estado_global == "En Circuito"
            ).order_by(Admision.fecha_ingreso.desc()).first()
            
            if not admission:
                st.warning("El paciente no tiene una admisión 'En Circuito'.")
                return
            
            # --- CORRECCIÓN DEL ERROR AQUÍ ---
            # Obtenemos la tupla (ObjetoHojaRuta, NombreString)
            pending_exams = db.query(
                HojaRutaExamenes,
                CatalogoExamenes.nombre
            ).join(
                CatalogoExamenes,
                HojaRutaExamenes.examen_id == CatalogoExamenes.id
            ).filter(
                HojaRutaExamenes.admision_id == admission.id,
                HojaRutaExamenes.estado != "Realizado"
            ).all()
            
            if not pending_exams:
                st.info("✅ ¡Todos los exámenes han sido completados!")
                return
                
            # Desempaquetamos correctamente la tupla en el bucle
            exam_options = {}
            for hoja_ruta, nombre_examen in pending_exams:
                key = f"{nombre_examen} ({hoja_ruta.estado})"
                exam_options[key] = hoja_ruta.id

            selected_label = st.selectbox(
                "Seleccione un examen pendiente:",
                options=list(exam_options.keys())
            )
            
            if selected_label:
                exam_route_id = exam_options[selected_label]
                # Extraemos solo el nombre para saber qué form mostrar
                exam_name = selected_label.split(" (")[0]
                
                st.markdown("---")
                show_exam_form(
                    exam_route_id=exam_route_id,
                    exam_name=exam_name,
                    admission_id=admission.id
                )
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            logger.exception("Error in main evaluation function:")
        finally:
            db.close()

if __name__ == "__main__":
    main()