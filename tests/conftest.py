import psycopg
import pytest

from agente_repuestos.db import conectar


@pytest.fixture
def conn():
    """Conexión como agente_lectura. Salta el test si la base no está levantada."""
    try:
        conexion = conectar()
    except psycopg.OperationalError:
        pytest.skip("La base no está disponible (docker compose up -d y cargar_datos.py)")
    with conexion:
        yield conexion
