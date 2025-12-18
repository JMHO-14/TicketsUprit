import streamlit as st
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from models import (
    Empresa, Protocolo, CatalogoExamenes, ProtocoloDetalle,
    Usuario, RolUsuario
)
from database import get_db, SessionLocal
from datetime import datetime
import logging
import time

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- GESTIÓN DE EMPRESAS ---
def manage_companies(db: Session):
    st.header("🏢 Empresas y Clientes")
    
    # Métricas
    total = db.query(Empresa).count()
    col_metric, col_space = st.columns([1, 3])
    col_metric.metric("Total de Empresas", total)
    st.divider()

    # 1. CREAR NUEVA
    with st.expander("➕ Registrar Nueva Empresa", expanded=False):
        with st.form("company_form", clear_on_submit=True):
            st.markdown("##### Datos de la Empresa")
            col1, col2 = st.columns(2)
            with col1:
                ruc = st.text_input("RUC *", max_chars=11)
                razon_social = st.text_input("Razón Social *")
            with col2:
                rubro = st.text_input("Rubro / Sector")
                email = st.text_input("Email de Contacto")
            
            direccion = st.text_area("Dirección Fiscal")
            
            if st.form_submit_button("💾 Guardar Empresa", type="primary", use_container_width=True):
                if not ruc or not razon_social:
                    st.error("RUC y Razón Social son obligatorios.")
                else:
                    try:
                        new_company = Empresa(
                            ruc=ruc, razon_social=razon_social, 
                            rubro=rubro, contacto_email=email, direccion=direccion
                        )
                        db.add(new_company)
                        db.commit()
                        st.success(f"Empresa {razon_social} creada!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # 2. LISTADO Y EDICIÓN
    st.subheader("Listado de Empresas")
    search = st.text_input("🔍 Buscar empresa por nombre o RUC:", "")
    
    query = db.query(Empresa)
    if search:
        query = query.filter(or_(
            Empresa.razon_social.ilike(f"%{search}%"),
            Empresa.ruc.ilike(f"%{search}%")
        ))
    
    companies = query.order_by(Empresa.razon_social).all()

    if not companies:
        st.info("No se encontraron empresas.")
        return

    for comp in companies:
        with st.expander(f"🏢 {comp.razon_social} (RUC: {comp.ruc})"):
            with st.form(f"edit_company_{comp.id}"):
                c1, c2 = st.columns(2)
                with c1:
                    new_rs = st.text_input("Razón Social", comp.razon_social)
                    new_ruc = st.text_input("RUC", comp.ruc)
                with c2:
                    new_rubro = st.text_input("Rubro", comp.rubro)
                    new_mail = st.text_input("Email", comp.contacto_email)
                
                new_dir = st.text_area("Dirección", comp.direccion)
                
                col_save, col_del = st.columns([1, 1])
                with col_save:
                    if st.form_submit_button("Actualizar Datos", use_container_width=True):
                        comp.razon_social = new_rs
                        comp.ruc = new_ruc
                        comp.rubro = new_rubro
                        comp.contacto_email = new_mail
                        comp.direccion = new_dir
                        db.commit()
                        st.success("Actualizado!")
                        time.sleep(0.5)
                        st.rerun()
                
                with col_del:
                    st.markdown("") # Espaciador

# --- GESTIÓN DE EXÁMENES ---
def manage_exams(db: Session):
    st.header("🧪 Catálogo de Exámenes")
    
    total = db.query(CatalogoExamenes).count()
    col_m, _ = st.columns([1,3])
    col_m.metric("Exámenes en Catálogo", total)
    st.divider()

    # CREAR
    with st.expander("➕ Nuevo Examen", expanded=False):
        with st.form("exam_form", clear_on_submit=True):
            st.markdown("##### Datos del Examen")
            c1, c2, c3 = st.columns(3)
            with c1:
                codigo = st.text_input("Código Interno *")
            with c2:
                nombre = st.text_input("Nombre del Examen *")
            with c3:
                precio = st.number_input("Precio Base (S/.)", min_value=0.0)
            
            categoria = st.selectbox("Categoría", ["Laboratorio", "Imagenología", "Medicina", "Audiología", "Oftalmología", "Psicología", "Otros"])
            
            if st.form_submit_button("💾 Guardar Examen", type="primary", use_container_width=True):
                if codigo and nombre:
                    try:
                        new_ex = CatalogoExamenes(
                            codigo_interno=codigo, nombre=nombre, 
                            precio_base=precio, categoria=categoria, activo=True
                        )
                        db.add(new_ex)
                        db.commit()
                        st.success("Examen creado.")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Faltan datos.")

    # LISTAR
    st.subheader("Listado de Exámenes")
    search = st.text_input("🔍 Buscar examen:", "")
    
    query = db.query(CatalogoExamenes)
    if search:
        query = query.filter(CatalogoExamenes.nombre.ilike(f"%{search}%"))
    
    exams = query.order_by(CatalogoExamenes.nombre).all()

    for ex in exams:
        status_icon = "🟢" if ex.activo else "🔴"
        with st.expander(f"{status_icon} {ex.nombre} ({ex.codigo_interno}) - S/ {ex.precio_base}"):
            with st.form(f"edit_exam_{ex.id}"):
                c1, c2 = st.columns(2)
                with c1:
                    n_nom = st.text_input("Nombre", ex.nombre)
                    n_cat = st.selectbox("Categoría", ["Laboratorio", "Imagenología", "Medicina", "Audiología", "Oftalmología", "Psicología", "Otros"], index=0)
                with c2:
                    n_pre = st.number_input("Precio", value=float(ex.precio_base))
                    n_act = st.checkbox("Activo", value=ex.activo)
                
                if st.form_submit_button("Actualizar Examen", use_container_width=True):
                    ex.nombre = n_nom
                    ex.categoria = n_cat
                    ex.precio_base = n_pre
                    ex.activo = n_act
                    db.commit()
                    st.success("Examen actualizado")
                    time.sleep(0.5)
                    st.rerun()

# --- GESTIÓN DE PROTOCOLOS ---
def manage_protocols(db: Session):
    st.header("📋 Protocolos Médicos")
    st.info("Los protocolos definen qué exámenes se aplican a los trabajadores de una empresa.")

    # Filtro Principal
    companies = db.query(Empresa).all()
    if not companies:
        st.warning("Primero registre empresas.")
        return
        
    comp_opts = {c.razon_social: c.id for c in companies}
    
    # CREAR NUEVO
    with st.expander("➕ Crear Nuevo Protocolo", expanded=False):
        with st.form("new_proto_form"):
            st.markdown("##### Configuración del Protocolo")
            c1, c2 = st.columns(2)
            with c1:
                c_name = st.selectbox("Empresa Cliente", list(comp_opts.keys()))
                p_name = st.text_input("Nombre (Ej: Admin, Operario)")
            with c2:
                p_riesgo = st.text_input("Perfil de Riesgo (Ej: Altura)")
            
            st.divider()
            st.markdown("##### Selección de Exámenes")
            
            all_exams = db.query(CatalogoExamenes).filter(CatalogoExamenes.activo==True).all()
            if not all_exams:
                st.error("No hay exámenes en el catálogo.")
            else:
                exam_opts = {e.nombre: e for e in all_exams}
                selected_exam_names = st.multiselect("Agregar exámenes:", list(exam_opts.keys()))
                
                # Precios dinámicos
                custom_prices = {}
                if selected_exam_names:
                    st.caption("Ajuste de precios para este cliente:")
                    cols = st.columns(3)
                    for i, ex_name in enumerate(selected_exam_names):
                        exam_obj = exam_opts[ex_name]
                        with cols[i % 3]:
                            val = st.number_input(f"S/. {ex_name}", value=float(exam_obj.precio_base), key=f"p_{i}")
                            custom_prices[exam_obj.id] = val
                
                if st.form_submit_button("💾 Guardar Protocolo", type="primary", use_container_width=True):
                    if p_name and selected_exam_names:
                        try:
                            new_prot = Protocolo(
                                empresa_id=comp_opts[c_name],
                                nombre_protocolo=p_name,
                                perfil_riesgo=p_riesgo,
                                tipo_examen="Ocupacional"
                            )
                            db.add(new_prot)
                            db.flush()
                            
                            for eid, price in custom_prices.items():
                                det = ProtocoloDetalle(
                                    protocolo_id=new_prot.id,
                                    examen_id=eid,
                                    precio_acordado=price
                                )
                                db.add(det)
                            
                            db.commit()
                            st.success("Protocolo Creado!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"Error: {e}")
                    else:
                        st.error("Complete el nombre y seleccione exámenes.")

    # LISTAR
    st.divider()
    st.subheader("Protocolos Existentes")
    
    sel_comp_filter = st.selectbox("Filtrar por Empresa:", ["Todas"] + list(comp_opts.keys()))
    
    q_prot = db.query(Protocolo)
    if sel_comp_filter != "Todas":
        q_prot = q_prot.filter(Protocolo.empresa_id == comp_opts[sel_comp_filter])
    
    protocols = q_prot.all()
    
    if not protocols:
        st.info("No hay protocolos registrados.")
    
    for p in protocols:
        with st.expander(f"📄 {p.nombre_protocolo} - {p.empresa.razon_social}"):
            st.write(f"**Riesgo:** {p.perfil_riesgo}")
            
            details = db.query(ProtocoloDetalle).filter(ProtocoloDetalle.protocolo_id == p.id).all()
            data = []
            for d in details:
                data.append({"Examen": d.examen.nombre, "Precio Acordado": f"S/ {d.precio_acordado}"})
            st.table(data)
            
            if st.button(f"🗑️ Eliminar Protocolo {p.id}", key=f"del_p_{p.id}"):
                try:
                    db.query(ProtocoloDetalle).filter(ProtocoloDetalle.protocolo_id == p.id).delete()
                    db.delete(p)
                    db.commit()
                    st.warning("Protocolo eliminado.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error("No se puede eliminar (posiblemente ya tiene admisiones vinculadas).")

# --- GESTIÓN DE USUARIOS ---
def manage_users(db: Session):
    st.header("👥 Usuarios del Sistema")
    
    # CREAR
    with st.expander("➕ Nuevo Usuario", expanded=False):
        with st.form("new_user"):
            st.markdown("##### Crear Credenciales")
            c1, c2 = st.columns(2)
            with c1:
                u_email = st.text_input("Correo / Usuario *")
                u_pass = st.text_input("Contraseña *", type="password")
            with c2:
                u_name = st.text_input("Nombre Completo")
                u_rol = st.selectbox("Rol", ["admin", "medico", "admision", "enfermeria"])
            
            if st.form_submit_button("Crear Usuario", type="primary", use_container_width=True):
                if u_email and u_pass:
                    try:
                        hashed = f"hashed_{u_pass}" if not u_pass.startswith("hashed_") else u_pass
                        new_u = Usuario(
                            email=u_email, hashed_password=hashed,
                            nombre_completo=u_name, rol=u_rol, activo=True
                        )
                        db.add(new_u)
                        db.commit()
                        st.success("Usuario creado")
                        time.sleep(1)
                        st.rerun()
                    except:
                        st.error("Error: El correo ya existe.")
    
    # LISTAR
    users = db.query(Usuario).order_by(Usuario.email).all()
    
    st.markdown("### Directorio")
    for u in users:
        with st.container():
            c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
            c1.write(f"**{u.nombre_completo}**")
            c2.caption(u.email)
            c3.write(f"`{u.rol}`")
            # Mostrar estado sin checkbox editable para simplificar
            status = "✅ Activo" if u.activo else "❌ Inactivo"
            c4.write(status)
            st.divider()

# --- MAIN ---
def main():
    # Validar Admin
    if 'user' not in st.session_state or not st.session_state.authenticated:
        st.warning("Acceso restringido.")
        return
        
    if st.session_state.user.get("rol") != "admin":
        st.error("⛔ Acceso denegado: Se requieren permisos de Administrador.")
        return

    st.title("⚙️ Configuración")
    
    # NAVEGACIÓN POR PESTAÑAS
    tab1, tab2, tab3, tab4 = st.tabs(["🏢 Empresas", "📋 Protocolos", "🧪 Exámenes", "👥 Usuarios"])
    
    db = SessionLocal()
    try:
        with tab1:
            manage_companies(db)
        with tab2:
            manage_protocols(db)
        with tab3:
            manage_exams(db)
        with tab4:
            manage_users(db)
    finally:
        db.close()

if __name__ == "__main__":
    main()