"""Validación previa de consulta_sql (no necesita base de datos)."""

import pytest

from agente_repuestos.db import ErrorConsulta
from agente_repuestos.sql_seguro import validar


@pytest.mark.parametrize("consulta", [
    "SELECT 1",
    "  select * from repuestos;  ",
    "WITH t AS (SELECT 1) SELECT * FROM t",
    "SELECT 1 -- comentario al final",
])
def test_acepta_lecturas(consulta):
    assert validar(consulta)


@pytest.mark.parametrize("consulta", [
    "",
    "   ;  ",
    "DELETE FROM movimientos",
    "UPDATE inventario SET stock_actual = 500",
    "INSERT INTO categorias (nombre) VALUES ('x')",
    "DROP TABLE movimientos",
    "SELECT 1; DELETE FROM movimientos",
    "TRUNCATE movimientos",
])
def test_rechaza_lo_demas(consulta):
    with pytest.raises(ErrorConsulta):
        validar(consulta)


def test_quita_punto_y_coma_final():
    assert validar("SELECT 1;") == "SELECT 1"
