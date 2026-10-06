"""El servidor MCP de punta a punta: proceso real por stdio, igual que Claude Code."""

import asyncio
import json

import psycopg
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from agente_repuestos.db import RAIZ, conectar

HERRAMIENTAS = {"buscar_repuestos", "stock_bajo_minimo", "resumen_movimientos", "consulta_sql"}


@pytest.fixture(scope="module", autouse=True)
def requiere_base():
    try:
        conectar().close()
    except psycopg.OperationalError:
        pytest.skip("La base no está disponible")


def test_servidor_por_stdio():
    async def probar():
        params = StdioServerParameters(command="uv", args=["run", "agente-repuestos-mcp"], cwd=RAIZ)
        async with Client(params) as cliente:
            herramientas = (await cliente.list_tools()).tools
            assert {h.name for h in herramientas} == HERRAMIENTAS
            assert all(h.annotations.read_only_hint for h in herramientas)

            ok = await cliente.call_tool("stock_bajo_minimo", {"sucursal": "León"})
            assert not ok.is_error
            assert json.loads(ok.content[0].text)["total"] > 0

            rechazo = await cliente.call_tool("consulta_sql", {"sql": "DELETE FROM movimientos"})
            assert rechazo.is_error
            assert "solo" in rechazo.content[0].text.lower()

    asyncio.run(probar())
