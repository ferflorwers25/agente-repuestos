"""consulta_sql y el rol agente_lectura no deben permitir modificar nada."""

import time

import psycopg
import pytest

from agente_repuestos import sql_seguro
from agente_repuestos.db import ErrorConsulta, conectar


def contar_movimientos(conn):
    return conn.execute("SELECT count(*) AS n FROM movimientos").fetchone()["n"]


@pytest.mark.parametrize("consulta", [
    "DELETE FROM movimientos",
    "SELECT 1; DELETE FROM movimientos",
    "UPDATE inventario SET stock_actual = 500",
    # Un WITH que modifica datos pasa la revisión previa, pero el envoltorio lo rechaza.
    "WITH borrados AS (DELETE FROM movimientos RETURNING *) SELECT count(*) FROM borrados",
    # Intento de cerrar el envoltorio desde adentro.
    "SELECT 1) AS x; DELETE FROM movimientos; SELECT * FROM (SELECT 1",
])
def test_consultas_que_modifican_se_rechazan(conn, consulta):
    antes = contar_movimientos(conn)
    with pytest.raises(ErrorConsulta):
        sql_seguro.ejecutar(conn, consulta)
    conn.rollback()
    assert contar_movimientos(conn) == antes


def test_limite_de_filas(conn):
    r = sql_seguro.ejecutar(conn, "SELECT id FROM movimientos ORDER BY id", limite=10)
    assert r["total_filas"] == 10 and r["recortado"]
    assert len(r["filas"]) == 10


def test_limite_fuera_de_rango(conn):
    with pytest.raises(ErrorConsulta):
        sql_seguro.ejecutar(conn, "SELECT 1", limite=10_000)


def test_tiempo_maximo(conn):
    inicio = time.monotonic()
    with pytest.raises(ErrorConsulta, match="tiempo máximo"):
        sql_seguro.ejecutar(conn, "SELECT pg_sleep(10)")
    assert time.monotonic() - inicio < 8


def test_comentario_final_no_rompe_el_envoltorio(conn):
    r = sql_seguro.ejecutar(conn, "SELECT 1 AS uno -- comentario")
    assert r["filas"] == [[1]]


def test_rol_sin_permisos_aunque_desactive_solo_lectura():
    """Aun saltándose todas las capas de la aplicación, PostgreSQL niega la escritura."""
    try:
        conexion = conectar()
    except psycopg.OperationalError:
        pytest.skip("La base no está disponible")
    with conexion:
        conexion.read_only = False  # psycopg abre la transacción como READ WRITE
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conexion.execute("DELETE FROM movimientos")
