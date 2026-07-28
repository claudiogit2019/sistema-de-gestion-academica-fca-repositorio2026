import os
from pymongo import MongoClient
from bson.objectid import ObjectId

# 1. Conexión a MongoDB
# En desarrollo local usará una cadena por defecto; en Render leerá la Variable de Entorno
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

client = MongoClient(MONGO_URI)
db = client["sistema_academico"]

# Colecciones (Equivalente a tablas)
estudiantes_coll = db["estudiantes"]
notas_coll = db["calificaciones"]
config_coll = db["configuracion"]  # Para guardar comisiones y criterios

# =========================================================================
# LÓGICA DE ESTUDIANTES
# =========================================================================

def registrar_estudiante(datos):
    """
    Registra un estudiante en MongoDB.
    datos debe ser un diccionario: 
    {'nombre':..., 'apellido':..., 'dni':..., 'condicion':..., 'domicilio':..., 'descripcion':...}
    """
    try:
        # Verificamos si ya existe el DNI para no duplicar
        existente = estudiantes_coll.find_one({"dni": datos["dni"]})
        if existente:
            return False
        
        # Insertamos en la colección
        estudiantes_coll.insert_one(datos)
        return True
    except Exception as e:
        print(f"Error en MongoDB al registrar: {e}")
        return False

def obtener_estudiantes():
    """
    Retorna todos los estudiantes. Para mantener compatibilidad con el frontend de Streamlit,
    convertimos los documentos de Mongo a un objeto simulado o mapeamos sus propiedades.
    """
    try:
        cursor = estudiantes_coll.find()
        lista_alumnos = []
        for doc in cursor:
            # Creamos una clase rápida mapeada al vuelo para no romper tus "a.nombre", "a.dni", etc.
            class EstudianteMapeado:
                def __init__(self, d):
                    self.id = str(d["_id"])  # El ID de Mongo es un ObjectId, lo pasamos a string
                    self.nombre = d.get("nombre", "")
                    self.apellido = d.get("apellido", "")
                    self.dni = d.get("dni", "")
                    self.condicion = d.get("condicion", "Regular")
                    self.domicilio = d.get("domicilio", "")  # Usado para la comisión
                    self.descripcion = d.get("descripcion", "")
            
            lista_alumnos.append(EstudianteMapeado(doc))
        return lista_alumnos
    except Exception as e:
        print(f"Error al obtener estudiantes: {e}")
        return []

def eliminar_todos_los_estudiantes():
    """Vacía la colección completa de estudiantes"""
    try:
        estudiantes_coll.delete_many({})
        return True
    except Exception as e:
        print(f"Error al vaciar base de datos: {e}")
        return False

def eliminar_estudiantes_por_comision(comision):
    """
    NUEVA FUNCIÓN: Elimina únicamente los estudiantes de una comisión específica
    (identificada en la base de datos a través del campo 'domicilio').
    """
    try:
        resultado = estudiantes_coll.delete_many({"domicilio": comision})
        return True, resultado.deleted_count
    except Exception as e:
        print(f"Error al vaciar estudiantes de la comisión {comision}: {e}")
        return False, 0

# =========================================================================
# LÓGICA DE CALIFICACIONES Y CRITERIOS (Para persistir Evaluaciones.py)
# =========================================================================

def guardar_config_comision(comision, columnas, categorias_tipos, reglas_dinamicas):
    """Guarda la estructura de columnas y criterios de la comisión para que no se borre al reiniciar"""
    try:
        config_coll.update_one(
            {"comision": comision},
            {"$set": {
                "comision": comision,
                "columnas": columnas,
                "categorias_tipos": categorias_tipos,
                "reglas_dinamicas": reglas_dinamicas
            }},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error al guardar config: {e}")
        return False

def cargar_config_comision(comision):
    """Recupera la estructura de la comisión desde MongoDB"""
    try:
        return config_coll.find_one({"comision": comision})
    except Exception as e:
        print(f"Error al cargar config: {e}")
        return None
