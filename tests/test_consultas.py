"""Herramientas contra la base real. Los datos son reproducibles (semilla fija)."""

from datetime import date

import pytest

from agente_repuestos import consultas
from agente_repuestos.db import ErrorConsulta

SUCURSALES = ["Managua Central", "León", "Granada", "Chinandega", "Estelí"]


def test_buscar_filtro_aceite_hilux_2018(conn):
    r = consultas.buscar_repuestos(conn, texto="filtro aceite", modelo="hilux", anio=2018)
    codigos = [x["codigo"] for x in r["repuestos"]]
    assert "FIL-TGD-1031" in codigos
    filtro = r["repuestos"][codigos.index("FIL-TGD-1031")]
    assert [s["sucursal"] for s in filtro["stock_por_sucursal"]] == SUCURSALES
    assert filtro["stock_total"] == sum(s["stock"] for s in filtro["stock_por_sucursal"])
    assert any("Hilux 2016-2024" in m for m in filtro["compatible_con"])


def test_buscar_respeta_el_anio(conn):
    # El filtro de la plataforma GD (2016 en adelante) no sirve para una Hilux 2010.
    r = consultas.buscar_repuestos(conn, texto="filtro aceite", modelo="hilux", anio=2010)
    assert "FIL-TGD-1031" not in [x["codigo"] for x in r["repuestos"]]


def test_buscar_ignora_tildes_y_mayusculas(conn):
    r = consultas.buscar_repuestos(conn, texto="SUSPENSION", limite=5)
    assert r["total"] == 5
    assert all(x["categoria"] == "Suspensión y dirección" for x in r["repuestos"])


def test_buscar_por_marca_de_vehiculo(conn):
    r = consultas.buscar_repuestos(conn, marca_vehiculo="john deere", texto="filtro aire")
    assert r["total"] >= 1
    assert all(any("John Deere" in m for m in x["compatible_con"]) for x in r["repuestos"])


def test_buscar_sin_criterios_da_error(conn):
    with pytest.raises(ErrorConsulta, match="al menos un criterio"):
        consultas.buscar_repuestos(conn)


def test_buscar_marca_hay_mas_resultados(conn):
    r = consultas.buscar_repuestos(conn, marca_vehiculo="Toyota", limite=3)
    assert r["total"] == 3 and r["hay_mas_resultados"]


def test_stock_bajo_minimo_total(conn):
    r = consultas.stock_bajo_minimo(conn)
    assert r["total"] == 30 and r["en_cero"] == 7
    assert all(x["stock_actual"] < x["stock_minimo"] for x in r["repuestos"])


def test_stock_bajo_minimo_por_sucursal_sin_tilde(conn):
    r = consultas.stock_bajo_minimo(conn, sucursal="esteli")
    assert r["total"] > 0
    assert {x["sucursal"] for x in r["repuestos"]} == {"Estelí"}


def test_sucursal_inexistente(conn):
    with pytest.raises(ErrorConsulta, match="Sucursales válidas"):
        consultas.stock_bajo_minimo(conn, sucursal="Rivas")


def test_resumen_cuadra_con_el_stock(conn):
    # Sin fechas, entradas - salidas debe dar exactamente el stock actual.
    r = consultas.resumen_movimientos(conn, codigo="fil-tgd-1031")
    assert len(r["por_sucursal"]) == 5
    for s in r["por_sucursal"]:
        assert s["unidades_entrada"] - s["unidades_salida"] == s["stock_actual"]


def test_resumen_con_rango_de_fechas(conn):
    sept = consultas.resumen_movimientos(conn, codigo="FIL-TGD-1031", sucursal="Managua",
                                          desde=date(2026, 9, 1), hasta=date(2026, 9, 30))
    todo = consultas.resumen_movimientos(conn, codigo="FIL-TGD-1031", sucursal="Managua")
    assert len(sept["por_sucursal"]) == 1
    assert 0 < sept["total"]["unidades_vendidas"] < todo["total"]["unidades_vendidas"]
    assert sept["por_sucursal"][0]["unidades_inventario_inicial"] == 0


def test_resumen_codigo_inexistente(conn):
    with pytest.raises(ErrorConsulta, match="buscar_repuestos"):
        consultas.resumen_movimientos(conn, codigo="NO-EXISTE-1")
