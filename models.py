from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime, Boolean, Text, Float, UUID, JSON, ARRAY, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from database import Base

class EstadoExamen(str, enum.Enum):
    PENDIENTE = "Pendiente"
    REALIZADO = "Realizado"
    VALIDADO = "Validado"

class EstadoAdmision(str, enum.Enum):
    EN_CIRCUITO = "En Circuito"
    AUDITORIA = "Auditoria"
    CERRADO = "Cerrado"
    ANULADO = "Anulado"

class RolUsuario(str, enum.Enum):
    ADMIN = "admin"
    MEDICO = "medico"
    ADMISION = "admision"
    ENFERMERIA = "enfermeria"
    AUDITOR = "auditor"

class AptitudStatus(str, enum.Enum):
    APTO = "APTO"
    APTO_RESTRICCIONES = "APTO CON RESTRICCIONES"
    NO_APTO = "NO APTO"
    EVALUADO = "EVALUADO"
    OBSERVADO = "OBSERVADO"

class CatalogoExamenes(Base):
    __tablename__ = 'catalogo_examenes'
    
    id = Column(Integer, primary_key=True, index=True)
    codigo_interno = Column(String(20), unique=True)
    nombre = Column(String(100), nullable=False)
    categoria = Column(String(50))
    precio_base = Column(Float)
    activo = Column(Boolean, default=True)
    
    protocolo_detalles = relationship("ProtocoloDetalle", back_populates="examen")
    hoja_ruta_examenes = relationship("HojaRutaExamenes", back_populates="examen")
    resultados_clinicos = relationship("ResultadoClinico", back_populates="examen")

class Empresa(Base):
    __tablename__ = 'empresas'
    
    id = Column(Integer, primary_key=True, index=True)
    ruc = Column(String(11), unique=True, nullable=False)
    razon_social = Column(String(255), nullable=False)
    direccion = Column(Text)
    rubro = Column(String(100))
    contacto_nombre = Column(String(100))
    contacto_email = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    protocolos = relationship("Protocolo", back_populates="empresa")
    admisiones = relationship("Admision", back_populates="empresa")

class Protocolo(Base):
    __tablename__ = 'protocolos'
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey('empresas.id'))
    nombre_protocolo = Column(String(150))
    perfil_riesgo = Column(String(100))
    tipo_examen = Column(String(50))
    activo = Column(Boolean, default=True)
    
    empresa = relationship("Empresa", back_populates="protocolos")
    detalles = relationship("ProtocoloDetalle", back_populates="protocolo")
    admisiones = relationship("Admision", back_populates="protocolo")

class ProtocoloDetalle(Base):
    __tablename__ = 'protocolo_detalles'
    
    id = Column(Integer, primary_key=True, index=True)
    protocolo_id = Column(Integer, ForeignKey('protocolos.id'))
    examen_id = Column(Integer, ForeignKey('catalogo_examenes.id'))
    precio_acordado = Column(Float)
    
    protocolo = relationship("Protocolo", back_populates="detalles")
    examen = relationship("CatalogoExamenes", back_populates="protocolo_detalles")

class Usuario(Base):
    __tablename__ = 'usuarios'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String(255), unique=True, nullable=False)
    nombre_completo = Column(String(150))
    rol = Column(String(50))
    cmp_colegiatura = Column(String(20))
    firma_digital_url = Column(Text)
    especialidad = Column(String(100))
    activo = Column(Boolean, default=True)
    hashed_password = Column(String(128), nullable=True) 
    
    certificados = relationship("CertificadoAptitud", back_populates="medico")

class Paciente(Base):
    __tablename__ = 'pacientes'
    
    id = Column(Integer, primary_key=True, index=True)
    tipo_documento = Column(String(20), default='DNI')
    numero_documento = Column(String(20), unique=True, nullable=False)
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    genero = Column(String(20))
    grupo_sanguineo = Column(String(10))
    telefono = Column(String(20))
    email = Column(String(100))
    direccion_domicilio = Column(Text)
    estado_civil = Column(String(50))
    grado_instruccion = Column(String(50))
    foto_perfil_url = Column(Text)
    huella_digital_hash = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    admisiones = relationship("Admision", back_populates="paciente")
    antecedentes = relationship("AntecedenteOcupacional", back_populates="paciente")

class Admision(Base):
    __tablename__ = 'admisiones'
    
    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    empresa_id = Column(Integer, ForeignKey('empresas.id'))
    protocolo_id = Column(Integer, ForeignKey('protocolos.id'))
    fecha_ingreso = Column(DateTime(timezone=True), server_default=func.now())
    estado_global = Column(String(50), default='En Circuito')
    puesto_postula = Column(String(150))
    usuario_admision_id = Column(UUID(as_uuid=True), ForeignKey('usuarios.id'))
    
    paciente = relationship("Paciente", back_populates="admisiones")
    empresa = relationship("Empresa", back_populates="admisiones")
    protocolo = relationship("Protocolo", back_populates="admisiones")
    hoja_ruta = relationship("HojaRutaExamenes", back_populates="admision")
    resultados = relationship("ResultadoClinico", back_populates="admision")
    diagnosticos = relationship("DiagnosticoAtencion", back_populates="admision")
    certificados = relationship("CertificadoAptitud", back_populates="admision")

class HojaRutaExamenes(Base):
    __tablename__ = 'hoja_ruta_examenes'
    
    id = Column(Integer, primary_key=True, index=True)
    admision_id = Column(Integer, ForeignKey('admisiones.id'))
    examen_id = Column(Integer, ForeignKey('catalogo_examenes.id'))
    estado = Column(String(50), default='Pendiente')
    medico_evaluador_id = Column(UUID(as_uuid=True), ForeignKey('usuarios.id'))
    fecha_realizado = Column(DateTime(timezone=True))
    
    admision = relationship("Admision", back_populates="hoja_ruta")
    examen = relationship("CatalogoExamenes", back_populates="hoja_ruta_examenes")

class AntecedenteOcupacional(Base):
    __tablename__ = 'antecedentes_ocupacionales'
    
    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    empresa_anterior = Column(String(200))
    puesto = Column(String(100))
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
    riesgos_ocupacionales = Column(Text)
    epp_usado = Column(Text)
    
    paciente = relationship("Paciente", back_populates="antecedentes")

class ResultadoClinico(Base):
    __tablename__ = 'resultados_clinicos'
    
    id = Column(Integer, primary_key=True, index=True)
    admision_id = Column(Integer, ForeignKey('admisiones.id'))
    examen_id = Column(Integer, ForeignKey('catalogo_examenes.id'))
    datos_tecnicos = Column(JSON)
    observaciones = Column(Text)
    archivos_adjuntos_url = Column(ARRAY(Text))
    conclusiones_examen = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    admision = relationship("Admision", back_populates="resultados")
    examen = relationship("CatalogoExamenes", back_populates="resultados_clinicos")

class DiagnosticoAtencion(Base):
    __tablename__ = 'diagnosticos_atencion'
    
    id = Column(Integer, primary_key=True, index=True)
    admision_id = Column(Integer, ForeignKey('admisiones.id'))
    cie10_codigo = Column(String(10))
    cie10_descripcion = Column(String(255))
    tipo = Column(String(50))
    
    admision = relationship("Admision", back_populates="diagnosticos")

class CertificadoAptitud(Base):
    __tablename__ = 'certificados_aptitud'
    
    id = Column(Integer, primary_key=True, index=True)
    admision_id = Column(Integer, ForeignKey('admisiones.id'))
    medico_firmante_id = Column(UUID(as_uuid=True), ForeignKey('usuarios.id'))
    aptitud_status = Column(String(50))
    restricciones = Column(Text)
    recomendaciones = Column(Text)
    fecha_vencimiento = Column(Date)
    fecha_emision = Column(DateTime(timezone=True), server_default=func.now())
    uuid_documento = Column(UUID(as_uuid=True), server_default=func.gen_random_uuid())
    
    admision = relationship("Admision", back_populates="certificados")
    medico = relationship("Usuario", back_populates="certificados")