import streamlit as st
from sqlalchemy import func, extract, case, and_
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
import pandas as pd
import plotly.express as px
from database import SessionLocal
from models import Admision, Empresa, HojaRutaExamenes, Paciente
from typing import List, Dict, Any
import logging
from fpdf import FPDF

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CLASE PARA GENERAR PDF ---
class PDFReport(FPDF):
    def header(self):
        # Título
        self.set_font('Helvetica', 'B', 15)
        self.cell(0, 10, 'SisoAI - Reporte Gerencial', 0, 1, 'C')
        self.ln(5)
        
        # Fecha del reporte
        self.set_font('Helvetica', 'I', 10)
        self.cell(0, 10, f'Generado el: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'R')
        self.line(10, 30, 200, 30)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, label):
        self.set_font('Helvetica', 'B', 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 10, label, 0, 1, 'L', fill=True)
        self.ln(4)

    def kpi_grid(self, kpis):
        self.set_font('Helvetica', '', 10)
        # Fila 1
        self.cell(90, 10, f"Total Admisiones Hoy: {kpis['total_admisiones_hoy']}", 1)
        self.cell(90, 10, f"Pacientes en Circuito: {kpis['atenciones_circuito']}", 1)
        self.ln()
        # Fila 2
        self.cell(90, 10, f"Empresas Activas: {kpis['total_empresas']}", 1)
        self.cell(90, 10, f"Examenes Realizados Hoy: {kpis['examenes_hoy']}", 1)
        self.ln(10)

    def add_table(self, df, title):
        self.chapter_title(title)
        self.set_font('Helvetica', 'B', 10)
        
        # Headers dinámicos
        cols = df.columns
        if len(cols) > 0:
            col_width = 190 / len(cols)
            
            for col in cols:
                # Limpiar caracteres especiales básicos para FPDF simple
                header_text = str(col).encode('latin-1', 'replace').decode('latin-1')
                self.cell(col_width, 10, header_text, 1, 0, 'C')
            self.ln()
            
            # Data
            self.set_font('Helvetica', '', 9)
            for index, row in df.iterrows():
                for col in cols:
                    # Convertir a string y limpiar
                    raw_text = str(row[col])
                    # Reemplazo básico de caracteres problemáticos para 'latin-1'
                    clean_text = raw_text.encode('latin-1', 'replace').decode('latin-1')
                    self.cell(col_width, 10, clean_text[:25], 1, 0, 'C') # Truncar a 25 chars
                self.ln()
        else:
            self.cell(0, 10, "Sin datos para mostrar", 1, 1, 'C')
        self.ln(10)

# --- LÓGICA DE BASE DE DATOS ---

def get_db() -> Session:
    """Obtener sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_kpis() -> Dict[str, Any]:
    db = next(get_db())
    today = date.today()
    try:
        total_admisiones_hoy = db.query(func.count(Admision.id)).filter(
            func.date(Admision.fecha_ingreso) == today
        ).scalar() or 0
        
        atenciones_circuito = db.query(func.count(Admision.id)).filter(
            Admision.estado_global == "En Circuito"
        ).scalar() or 0
        
        total_empresas = db.query(func.count(Empresa.id)).scalar() or 0
        
        examenes_hoy = db.query(func.count(HojaRutaExamenes.id)).filter(
            and_(
                HojaRutaExamenes.estado == "Realizado",
                func.date(HojaRutaExamenes.fecha_realizado) == today
            )
        ).scalar() or 0
        
        return {
            "total_admisiones_hoy": total_admisiones_hoy,
            "atenciones_circuito": atenciones_circuito,
            "total_empresas": total_empresas,
            "examenes_hoy": examenes_hoy
        }
    except Exception:
        return {"total_admisiones_hoy": 0, "atenciones_circuito": 0, "total_empresas": 0, "examenes_hoy": 0}
    finally:
        db.close()

def get_admisiones_por_empresa() -> pd.DataFrame:
    db = next(get_db())
    try:
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        query = db.query(
            Empresa.razon_social.label("Empresa"),
            func.count(Admision.id).label("Admisiones")
        ).join(Admision, Empresa.id == Admision.empresa_id).filter(
            extract('month', Admision.fecha_ingreso) == current_month,
            extract('year', Admision.fecha_ingreso) == current_year
        ).group_by(Empresa.razon_social).order_by(func.count(Admision.id).desc()).limit(5)
        
        result = query.all()
        return pd.DataFrame([{"Empresa": r.Empresa, "Admisiones": r.Admisiones} for r in result])
    except Exception:
        return pd.DataFrame(columns=["Empresa", "Admisiones"])
    finally:
        db.close()

def get_estado_admisiones() -> pd.DataFrame:
    db = next(get_db())
    try:
        query = db.query(
            Admision.estado_global.label("estado"),
            func.count(Admision.id).label("total")
        ).group_by(Admision.estado_global)
        result = query.all()
        
        if not result:
            return pd.DataFrame({"estado": ["En Circuito", "Cerrado"], "total": [0, 0]})
            
        df = pd.DataFrame([{"estado": r.estado, "total": r.total} for r in result])
        return df
    except Exception:
        return pd.DataFrame({"estado": ["Error"], "total": [0]})
    finally:
        db.close()

def get_flujo_pacientes() -> pd.DataFrame:
    db = next(get_db())
    try:
        today = date.today()
        horas = [f"{h:02d}:00" for h in range(24)]
        
        query = db.query(
            func.extract('hour', Admision.fecha_ingreso).label('hora'),
            func.count(Admision.id).label('total')
        ).filter(func.date(Admision.fecha_ingreso) == today).group_by('hora').order_by('hora')
        
        result = query.all()
        datos = {f"{int(r.hora):02d}:00": r.total for r in result}
        
        return pd.DataFrame({"Hora": horas, "Pacientes": [datos.get(h, 0) for h in horas]})
    except Exception:
        return pd.DataFrame({"Hora": [], "Pacientes": []})
    finally:
        db.close()

def get_ultimos_ingresos() -> pd.DataFrame:
    db = next(get_db())
    try:
        query = db.query(
            Paciente.nombres, Paciente.apellidos, Empresa.razon_social, Admision.fecha_ingreso
        ).join(Admision, Paciente.id == Admision.paciente_id).join(
            Empresa, Admision.empresa_id == Empresa.id
        ).order_by(Admision.fecha_ingreso.desc()).limit(10)
        
        result = query.all()
        data = [{
            "Paciente": f"{r.nombres} {r.apellidos}",
            "Empresa": r.razon_social,
            "Hora": r.fecha_ingreso.strftime("%H:%M")
        } for r in result]
        
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame(columns=["Paciente", "Empresa", "Hora"])
    finally:
        db.close()

# --- FUNCIÓN GENERADORA DE PDF ---
def create_downloadable_report(kpis, df_empresas, df_ultimos):
    # CORRECCIÓN: Instancia FPDF sin argumentos complejos
    pdf = PDFReport()
    pdf.add_page()
    
    # 1. KPIs
    pdf.chapter_title("1. Indicadores del Dia (KPIs)")
    pdf.kpi_grid(kpis)
    
    # 2. Tabla Top Empresas
    if not df_empresas.empty:
        pdf.add_table(df_empresas, "2. Top Empresas del Mes")
    else:
        pdf.chapter_title("2. Top Empresas")
        pdf.set_font('Helvetica', 'I', 10)
        pdf.cell(0, 10, "No hay datos registrados este mes.", 0, 1)
        pdf.ln(5)

    # 3. Tabla Últimos Ingresos
    if not df_ultimos.empty:
        pdf.add_table(df_ultimos, "3. Registro de Ultimos Ingresos")
    
    # CORRECCIÓN: Devolver bytes directamente (sin encode)
    return bytes(pdf.output())

# --- VISTA PRINCIPAL ---
def show_dashboard():
    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.title("📊 Panel Gerencial")
    
    kpis = get_kpis()
    df_empresas = get_admisiones_por_empresa()
    df_ultimos = get_ultimos_ingresos()
    df_estados = get_estado_admisiones()
    df_flujo = get_flujo_pacientes()

    with col_btn:
        st.write("") 
        if st.button("📥 Descargar Reporte PDF"):
            try:
                pdf_bytes = create_downloadable_report(kpis, df_empresas, df_ultimos)
                st.download_button(
                    label="Confirmar Descarga",
                    data=pdf_bytes,
                    file_name=f"Reporte_SisoAI_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    key="download_pdf_final"
                )
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")

    st.markdown("---")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Admisiones Hoy", kpis["total_admisiones_hoy"])
    c2.metric("En Circuito", kpis["atenciones_circuito"])
    c3.metric("Empresas", kpis["total_empresas"])
    c4.metric("Exámenes Hoy", kpis["examenes_hoy"])
    
    st.markdown("---")
    
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.subheader("Top Empresas (Mes Actual)")
        if not df_empresas.empty:
            fig = px.bar(df_empresas, x="Empresa", y="Admisiones", color="Empresa")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos.")

    with c_right:
        st.subheader("Estado de Atenciones")
        if not df_estados.empty and df_estados['total'].sum() > 0:
            fig2 = px.pie(df_estados, names="estado", values="total", hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Sin datos.")

    st.subheader("Flujo por Hora")
    if not df_flujo.empty:
        st.area_chart(df_flujo.set_index("Hora"))

    st.subheader("Últimos Ingresos")
    if not df_ultimos.empty:
        st.dataframe(df_ultimos, use_container_width=True, hide_index=True)
    else:
        st.info("No hay ingresos recientes.")

if __name__ == "__main__":
    if 'user' not in st.session_state or not st.session_state.get('authenticated'):
        st.warning("🔒 Inicie sesión.")
    else:
        show_dashboard()