from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# CORRECCIÓN: connect_args es necesario para SQLite en entornos multihilo como Streamlit
engine = create_engine(
    'sqlite:///data/estudiantes.db', 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELOS DE TABLAS ---

class Estudiante(Base):
    __tablename__ = "estudiantes"
    id = Column(Integer, primary_key=True, index=True)
    dni = Column(String, unique=True, index=True)
    nombre = Column(String)
    apellido = Column(String)
    domicilio = Column(String)
    condicion = Column(String) # Ingresante o Recursante
    descripcion = Column(String)
    
    # Notas principales
    parcial = Column(Float, default=0.0)
    recuperatorio = Column(Float, default=0.0)
    flotante = Column(Float, default=0.0)

class Asistencia(Base):
    __tablename__ = "asistencia"
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    fecha = Column(String) # YYYY-MM-DD
    presente = Column(Boolean, default=False)

class NotaParticipacion(Base):
    __tablename__ = "notas_participacion"
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"))
    nro_clase = Column(Integer) # Del 1 al 15
    nota = Column(Float, default=0.0)

# --- CREACIÓN DE TABLAS ---
# Esta línea se encarga de generar el archivo .db y las tablas si no existen
Base.metadata.create_all(bind=engine)
