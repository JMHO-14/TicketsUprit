import sys
import os
from pathlib import Path
import random
from datetime import datetime, timedelta
from faker import Faker
import json

# Configuración de rutas para importar models y database
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import (
    Usuario, CatalogoExamenes, Empresa, Protocolo, ProtocoloDetalle,
    Paciente, Admision, HojaRutaExamenes, ResultadoClinico, 
    CertificadoAptitud, AntecedenteOcupacional, 
    EstadoExamen, EstadoAdmision, RolUsuario, AptitudStatus
)

# Configurar Faker en español
fake = Faker(['es_ES', 'es_MX']) # Mezcla para variedad de apellidos latinos

def reset_db():
    """Limpia la base de datos para empezar de cero"""
    print("🗑️  Limpiando base de datos...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos recreada.")

def create_catalog(db: Session):
    print("🏥 Creando Catálogo de Exámenes...")
    exams_data = [
        {"nombre": "Audiometría Ocupacional", "cat": "Audiología", "precio": 45.00, "cod": "AUDIO-001"},
        {"nombre": "Espirometría", "cat": "Neumología", "precio": 50.00, "cod": "NEUMO-001"},
        {"nombre": "Radiografía de Tórax OIT", "cat": "Imagenología", "precio": 80.00, "cod": "RAYOS-001"},
        {"nombre": "Hemograma Completo", "cat": "Laboratorio", "precio": 25.00, "cod": "LAB-001"},
        {"nombre": "Examen Oftalmológico", "cat": "Oftalmología", "precio": 40.00, "cod": "OFT-001"},
        {"nombre": "Evaluación Psicológica", "cat": "Psicología", "precio": 35.00, "cod": "PSICO-001"},
        {"nombre": "Examen Médico Musculoesquelético", "cat": "Medicina General", "precio": 60.00, "cod": "MED-001"},
        {"nombre": "EKG (Electrocardiograma)", "cat": "Cardiología", "precio": 55.00, "cod": "CARD-001"},
        {"nombre": "Prueba de Esfuerzo", "cat": "Cardiología", "precio": 120.00, "cod": "CARD-002"},
        {"nombre": "Tamizaje de Drogas", "cat": "Laboratorio", "precio": 30.00, "cod": "LAB-002"},
    ]
    
    exams_objs = []
    for ex in exams_data:
        new_ex = CatalogoExamenes(
            nombre=ex["nombre"],
            categoria=ex["cat"],
            precio_base=ex["precio"],
            codigo_interno=ex["cod"],
            activo=True
        )
        db.add(new_ex)
        exams_objs.append(new_ex)
    db.commit()
    return db.query(CatalogoExamenes).all()

def create_users(db: Session):
    print("👥 Creando Usuarios del Sistema...")
    # Admin
    admin = Usuario(
        email="admin@sisoai.com",
        nombre_completo="Administrador Principal",
        rol=RolUsuario.ADMIN,
        activo=True,
        hashed_password="admin123"
    )
    db.add(admin)

    # Médicos
    medicos = []
    especialidades = ["Neumología", "Medicina Ocupacional", "Cardiología", "Medicina General"]
    for _ in range(5):
        m = Usuario(
            email=fake.unique.email(),
            nombre_completo=f"Dr. {fake.first_name()} {fake.last_name()}",
            rol=RolUsuario.MEDICO,
            cmp_colegiatura=str(random.randint(10000, 99999)),
            especialidad=random.choice(especialidades),
            activo=True,
            hashed_password="medico123"
        )
        db.add(m)
        medicos.append(m)
    
    db.commit()
    # Recargar admins y medicos
    return admin, db.query(Usuario).filter(Usuario.rol == RolUsuario.MEDICO).all()

def create_companies_and_protocols(db: Session, exams):
    print("🏭 Creando Empresas y Protocolos...")
    companies = []
    protocols = []
    
    rubros = ["Minería", "Construcción", "Industrial", "Administrativo", "Transporte"]
    
    for _ in range(8): # 8 Empresas
        comp = Empresa(
            ruc=str(random.randint(10000000000, 20999999999)),
            razon_social=f"{fake.company()} S.A.C.",
            rubro=random.choice(rubros),
            direccion=fake.address(),
            contacto_nombre=fake.name(),
            contacto_email=fake.company_email()
        )
        db.add(comp)
        db.flush() # Para obtener ID
        companies.append(comp)

        # Crear 2 protocolos por empresa (Uno Operativo, Uno Administrativo)
        # Protocolo Operativo (Más exámenes)
        proto_op = Protocolo(
            empresa_id=comp.id,
            nombre_protocolo="Protocolo Operativo - Ingreso",
            perfil_riesgo="Alto Riesgo",
            tipo_examen="Pre-Ocupacional",
            activo=True
        )
        db.add(proto_op)
        db.flush()
        
        # Asignar 5 exámenes aleatorios al protocolo operativo
        selected_exams = random.sample(exams, k=5)
        for ex in selected_exams:
            det = ProtocoloDetalle(
                protocolo_id=proto_op.id,
                examen_id=ex.id,
                precio_acordado=ex.precio_base * 0.9 # 10% descuento
            )
            db.add(det)
        protocols.append(proto_op)

        # Protocolo Administrativo (Menos exámenes)
        proto_adm = Protocolo(
            empresa_id=comp.id,
            nombre_protocolo="Protocolo Administrativo - Anual",
            perfil_riesgo="Bajo Riesgo",
            tipo_examen="Periodico",
            activo=True
        )
        db.add(proto_adm)
        db.flush()
        
        selected_exams_adm = random.sample(exams, k=3)
        for ex in selected_exams_adm:
            det = ProtocoloDetalle(
                protocolo_id=proto_adm.id,
                examen_id=ex.id,
                precio_acordado=ex.precio_base
            )
            db.add(det)
        protocols.append(proto_adm)

    db.commit()
    return companies, protocols

def generate_patients_flow(db: Session, protocols, medicos, admin_user):
    print("🚶 Generando Flujo de Pacientes (Admisiones, Exámenes, Resultados)...")
    
    # Crear 50 pacientes
    for i in range(50):
        # 1. Crear Paciente
        paciente = Paciente(
            tipo_documento="DNI",
            numero_documento=str(random.randint(10000000, 99999999)),
            nombres=fake.first_name(),
            apellidos=f"{fake.last_name()} {fake.last_name()}",
            fecha_nacimiento=fake.date_of_birth(minimum_age=18, maximum_age=60),
            genero=random.choice(["M", "F"]),
            telefono=fake.phone_number(),
            email=fake.email(),
            direccion_domicilio=fake.address(),
            estado_civil=random.choice(["Soltero", "Casado", "Conviviente"]),
            grado_instruccion=random.choice(["Secundaria", "Técnico", "Universitario"]),
            grupo_sanguineo=random.choice(["O+", "A+", "B+", "O-"])
        )
        db.add(paciente)
        db.flush()

        # 2. Crear Antecedente Ocupacional
        antecedente = AntecedenteOcupacional(
            paciente_id=paciente.id,
            empresa_anterior=fake.company(),
            puesto="Operario General",
            fecha_inicio=fake.date_between(start_date='-5y', end_date='-2y'),
            fecha_fin=fake.date_between(start_date='-1y', end_date='today'),
            riesgos_ocupacionales="Ruido, Polvo, Carga Física"
        )
        db.add(antecedente)

        # 3. Crear Admisión (Elegir protocolo al azar)
        protocolo_elegido = random.choice(protocols)
        estado_random = random.choice([EstadoAdmision.EN_CIRCUITO, EstadoAdmision.CERRADO])
        
        admision = Admision(
            paciente_id=paciente.id,
            empresa_id=protocolo_elegido.empresa_id,
            protocolo_id=protocolo_elegido.id,
            fecha_ingreso=fake.date_time_between(start_date='-1M', end_date='now'),
            estado_global=estado_random,
            puesto_postula="Asistente",
            usuario_admision_id=admin_user.id
        )
        db.add(admision)
        db.flush()

        # 4. Generar Hoja de Ruta y Resultados (Basado en el protocolo)
        detalles_protocolo = db.query(ProtocoloDetalle).filter(ProtocoloDetalle.protocolo_id == protocolo_elegido.id).all()
        
        all_exams_passed = True
        
        for detalle in detalles_protocolo:
            # Estado del examen individual
            if estado_random == EstadoAdmision.CERRADO:
                status_ex = EstadoExamen.VALIDADO
            else:
                status_ex = random.choice([EstadoExamen.PENDIENTE, EstadoExamen.REALIZADO])

            # Hoja de ruta
            hoja = HojaRutaExamenes(
                admision_id=admision.id,
                examen_id=detalle.examen_id,
                estado=status_ex,
                medico_evaluador_id=random.choice(medicos).id if status_ex != EstadoExamen.PENDIENTE else None,
                fecha_realizado=datetime.now() if status_ex != EstadoExamen.PENDIENTE else None
            )
            db.add(hoja)

            # Si está realizado o validado, crear resultado clínico dummy
            if status_ex in [EstadoExamen.REALIZADO, EstadoExamen.VALIDADO]:
                resultado = ResultadoClinico(
                    admision_id=admision.id,
                    examen_id=detalle.examen_id,
                    datos_tecnicos={"valor": random.randint(80, 120), "unidad": "mg/dL"},
                    observaciones=fake.sentence(),
                    conclusiones_examen="Normal" if random.random() > 0.1 else "Observado"
                )
                db.add(resultado)
                if resultado.conclusiones_examen == "Observado":
                    all_exams_passed = False

        # 5. Si la admisión está cerrada, emitir certificado
        if estado_random == EstadoAdmision.CERRADO:
            aptitud = AptitudStatus.APTO if all_exams_passed else AptitudStatus.OBSERVADO
            cert = CertificadoAptitud(
                admision_id=admision.id,
                medico_firmante_id=random.choice(medicos).id,
                aptitud_status=aptitud,
                restricciones="Uso de lentes correctores" if aptitud == AptitudStatus.OBSERVADO else "Ninguna",
                fecha_vencimiento=datetime.now() + timedelta(days=365)
            )
            db.add(cert)
        
    db.commit()
    print(f"✅ Se han generado 50 pacientes con historiales completos.")

def main():
    print("🚀 INICIANDO GENERACIÓN DE DATA REALISTA...")
    reset_db()
    
    db = SessionLocal()
    try:
        exams = create_catalog(db)
        admin_user, medicos = create_users(db)
        companies, protocols = create_companies_and_protocols(db, exams)
        generate_patients_flow(db, protocols, medicos, admin_user)
        
        print("\n✨ ¡PROCESO COMPLETADO! ✨")
        print("Ahora tienes:")
        print("- 10 Tipos de exámenes")
        print("- 1 Usuario Admin (admin@sisoai.com / admin123)")
        print("- 5 Médicos con especialidades")
        print("- 8 Empresas reales")
        print("- 16 Protocolos médicos")
        print("- 50 Pacientes con datos demográficos completos")
        print("- 50 Admisiones con hojas de ruta y resultados vinculados")
        
    except Exception as e:
        print(f"❌ Error durante el seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()