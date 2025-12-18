import sys
import os
from pathlib import Path
from datetime import datetime, date
import logging

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from database import SessionLocal, engine, Base
from models import (
    Usuario, Paciente, Empresa, CatalogoExamenes, 
    Protocolo, ProtocoloDetalle, RolUsuario
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    """Create all database tables"""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully!")

def seed_admin_user():
    """Create admin user"""
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(Usuario).filter(Usuario.email == "admin@sisoai.com").first()
        
        if not admin:
            admin = Usuario(
                email="admin@sisoai.com",
                hashed_password="hashed_admin123",  # In production, use proper password hashing
                rol=RolUsuario.ADMIN,
                especialidad="Administración"
            )
            db.add(admin)
            db.commit()
            logger.info("Admin user created successfully!")
        else:
            logger.info("Admin user already exists, skipping...")
            
        return admin
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating admin user: {str(e)}")
        raise
    finally:
        db.close()

def seed_companies():
    """Create test companies"""
    db = SessionLocal()
    try:
        companies = [
            {
                "ruc": "20123456781",
                "razon_social": "Tecnologías Avanzadas S.A.",
                "rubro": "Tecnología",
                "contacto_email": "contacto@tecnologias-avanzadas.com"
            },
            {
                "ruc": "20234567892",
                "razon_social": "Construcciones Modernas S.A.C.",
                "rubro": "Construcción",
                "contacto_email": "rrhh@constru-moderna.com"
            }
        ]
        
        created_companies = []
        
        for company_data in companies:
            # Check if company exists
            company = db.query(Empresa).filter(
                Empresa.ruc == company_data["ruc"]
            ).first()
            
            if not company:
                company = Empresa(**company_data)
                db.add(company)
                db.flush()  # Get the ID
                created_companies.append(company)
                logger.info(f"Created company: {company.razon_social}")
            else:
                created_companies.append(company)
                logger.info(f"Company already exists: {company.razon_social}")
        
        db.commit()
        return created_companies
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating companies: {str(e)}")
        raise
    finally:
        db.close()

def seed_exams():
    """Create test exams"""
    db = SessionLocal()
    try:
        exams = [
            {
                "codigo_interno": "AUDIO",
                "nombre": "Audiometría",
                "categoria": "Otorrinolaringología",
                "precio_base": 80.00,
                "activo": True
            },
            {
                "codigo_interno": "ESPIRO",
                "nombre": "Espirometría",
                "categoria": "Neumología",
                "precio_base": 90.00,
                "activo": True
            },
            {
                "codigo_interno": "RXTORAX",
                "nombre": "Radiografía de Tórax",
                "categoria": "Radiología",
                "precio_base": 120.00,
                "activo": True
            },
            {
                "codigo_interno": "OFTALMO",
                "nombre": "Examen Oftalmológico",
                "categoria": "Oftalmología",
                "precio_base": 70.00,
                "activo": True
            },
            {
                "codigo_interno": "PSICO",
                "nombre": "Evaluación Psicológica",
                "categoria": "Psicología",
                "precio_base": 100.00,
                "activo": True
            }
        ]
        
        created_exams = []
        
        for exam_data in exams:
            # Check if exam exists
            exam = db.query(CatalogoExamenes).filter(
                CatalogoExamenes.codigo_interno == exam_data["codigo_interno"]
            ).first()
            
            if not exam:
                exam = CatalogoExamenes(**exam_data)
                db.add(exam)
                db.flush()  # Get the ID
                created_exams.append(exam)
                logger.info(f"Created exam: {exam.nombre}")
            else:
                created_exams.append(exam)
                logger.info(f"Exam already exists: {exam.nombre}")
        
        db.commit()
        return created_exams
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating exams: {str(e)}")
        raise
    finally:
        db.close()

def seed_protocol(company_id: int, exams: list):
    """Create a test protocol for a company"""
    db = SessionLocal()
    try:
        # Create protocol
        protocol = Protocolo(
            empresa_id=company_id,
            nombre_protocolo="Protocolo General de Salud Ocupacional",
            perfil_riesgo="Riesgo Medio"
        )
        db.add(protocol)
        db.flush()  # Get the protocol ID
        
        # Add exam details
        for exam in exams:
            detail = ProtocoloDetalle(
                protocolo_id=protocol.id,
                examen_id=exam.id,
                precio_acordado=exam.precio_base * 0.9  # 10% discount
            )
            db.add(detail)
        
        db.commit()
        logger.info(f"Created protocol for company ID {company_id}")
        return protocol
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating protocol: {str(e)}")
        raise
    finally:
        db.close()

def seed_test_patient():
    """Create a test patient"""
    db = SessionLocal()
    try:
        patient_data = {
            "numero_documento": "12345678",
            "nombres": "Juan",
            "apellidos": "Pérez González",
            "fecha_nacimiento": date(1990, 5, 15),
            "genero": "Masculino",
            "email": "juan.perez@example.com",
            "foto_perfil_url": "https://randomuser.me/api/portraits/men/1.jpg"
        }
        
        # Check if patient exists
        patient = db.query(Paciente).filter(
            Paciente.numero_documento == patient_data["numero_documento"]
        ).first()
        
        if not patient:
            patient = Paciente(**patient_data)
            db.add(patient)
            db.commit()
            logger.info(f"Created test patient: {patient.nombres} {patient.apellidos}")
        else:
            logger.info(f"Test patient already exists: {patient.nombres} {patient.apellidos}")
        
        return patient
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating test patient: {str(e)}")
        raise
    finally:
        db.close()

def main():
    """Main function to seed the database"""
    try:
        logger.info("Starting database seeding...")
        
        # Create tables if they don't exist
        create_tables()
        
        # Seed admin user
        admin = seed_admin_user()
        
        # Seed companies
        companies = seed_companies()
        
        # Seed exams
        exams = seed_exams()
        
        # Create a protocol for the first company
        if companies and exams:
            seed_protocol(companies[0].id, exams)
        
        # Create a test patient
        seed_test_patient()
        
        logger.info("Database seeding completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during database seeding: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
