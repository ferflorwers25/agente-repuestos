"""Servidor MCP del inventario de repuestos (transporte stdio).

Importante: en stdio la salida estándar es el canal del protocolo, así que
este proceso nunca debe usar print(). Los logs van a stderr.
"""

import logging
import sys
from datetime import date
from typing import Annotated, Any

import psycopg
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import Field

from . import consultas, sql_seguro
from .db import ErrorConsulta, conectar

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

servidor = MCPServer(
    "repuestos",
    instructions=(
        "Inventario de repuestos de un distribuidor de vehículos y maquinaria en Nicaragua. "
        "Precios en córdobas (NIO). Sucursales: Managua Central, León, Granada, Chinandega y Estelí. "
        "Los datos llegan hasta el 30 de septiembre de 2026. "
        "Acceso de solo lectura: no se pueden modificar datos. "
        "Usá buscar_repuestos para encontrar repuestos y sus códigos; resumen_movimientos necesita el código. "
        "Usá consulta_sql solo cuando ninguna otra herramienta cubra la pregunta."
    ),
)

SOLO_LECTURA = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)


def _ejecutar(funcion, **parametros) -> dict[str, Any]:
    """Abre una conexión, ejecuta la consulta y traduce los errores para el modelo."""
    try:
        with conectar() as conn:
            return funcion(conn, **parametros)
    except ErrorConsulta as e:
        raise ToolError(str(e)) from e
    except psycopg.OperationalError as e:
        logging.exception("Error de conexión")
        raise ToolError(
            "No se pudo conectar a la base de datos. Verificá que el contenedor esté levantado "
            "(docker compose up -d)."
        ) from e


@servidor.tool(annotations=SOLO_LECTURA)
def buscar_repuestos(
    texto: Annotated[str | None, Field(
        description="Palabras a buscar en nombre, código, marca del repuesto o categoría. "
                    "Todas deben aparecer, en cualquier orden. Ej.: 'pastillas delanteras', 'filtro aire', 'Bosch'.")] = None,
    marca_vehiculo: Annotated[str | None, Field(
        description="Marca del vehículo o máquina. Ej.: 'Toyota', 'Yamaha', 'John Deere'.")] = None,
    modelo: Annotated[str | None, Field(
        description="Modelo del vehículo o máquina. Ej.: 'Hilux', 'Corolla', 'FZ 150', '310L'.")] = None,
    anio: Annotated[int | None, Field(description="Año del vehículo. Ej.: 2019.")] = None,
    limite: Annotated[int, Field(description="Máximo de repuestos a devolver (1 a 50).")] = 20,
) -> dict[str, Any]:
    """Busca repuestos y devuelve precio en córdobas, stock por sucursal y modelos compatibles.

    Usala para preguntas como "¿qué pastillas de freno hay para una Hilux 2019?" o
    "¿hay filtro de aire para una retroexcavadora 310L?". Combiná texto (qué repuesto)
    con marca_vehiculo, modelo y anio (para qué vehículo). Se ignoran tildes y mayúsculas.
    """
    return _ejecutar(consultas.buscar_repuestos, texto=texto, marca_vehiculo=marca_vehiculo,
                     modelo=modelo, anio=anio, limite=limite)


@servidor.tool(annotations=SOLO_LECTURA)
def stock_bajo_minimo(
    sucursal: Annotated[str | None, Field(
        description="Nombre (o parte) de la sucursal. Ej.: 'León', 'Managua'. Vacío = todas.")] = None,
) -> dict[str, Any]:
    """Lista los repuestos cuyo stock actual está por debajo del stock mínimo.

    Devuelve sucursal, código, repuesto, stock actual, stock mínimo y faltante, con los
    agotados (stock 0) primero. Usala para preguntas sobre qué hay que reabastecer.
    """
    return _ejecutar(consultas.stock_bajo_minimo, sucursal=sucursal)


@servidor.tool(annotations=SOLO_LECTURA)
def resumen_movimientos(
    codigo: Annotated[str, Field(description="Código exacto del repuesto, ej.: 'FIL-TGD-1031'. "
                                             "Si no lo sabés, buscalo antes con buscar_repuestos.")],
    sucursal: Annotated[str | None, Field(description="Nombre (o parte) de la sucursal. Vacío = todas.")] = None,
    desde: Annotated[date | None, Field(description="Fecha inicial inclusive (AAAA-MM-DD).")] = None,
    hasta: Annotated[date | None, Field(description="Fecha final inclusive (AAAA-MM-DD).")] = None,
) -> dict[str, Any]:
    """Resume entradas y salidas de un repuesto por sucursal en un rango de fechas.

    Por sucursal devuelve unidades que entraron (compras e inventario inicial), unidades
    que salieron (ventas y ajustes por merma), número de ventas, monto vendido en córdobas,
    fecha del último movimiento y stock actual. Sin fechas, resume todo el historial
    (1 de abril al 30 de septiembre de 2026).
    """
    return _ejecutar(consultas.resumen_movimientos, codigo=codigo, sucursal=sucursal, desde=desde, hasta=hasta)


@servidor.tool(annotations=SOLO_LECTURA)
def consulta_sql(
    sql: Annotated[str, Field(description="Una sola consulta SELECT (o WITH ... SELECT) de PostgreSQL.")],
    limite: Annotated[int, Field(description="Máximo de filas a devolver (1 a 500).")] = sql_seguro.LIMITE_POR_DEFECTO,
) -> dict[str, Any]:
    """Ejecuta una consulta SELECT de solo lectura. Es el respaldo para preguntas que las otras
    herramientas no cubren (rankings, totales por mes, comparaciones entre sucursales, etc.).

    Límites: una sola sentencia, solo lectura, máximo 500 filas y 5 segundos.

    Esquema (PostgreSQL, montos en córdobas):
    - categorias(id, nombre, descripcion)
    - proveedores(id, nombre, pais, contacto, telefono, email)
    - repuestos(id, codigo, nombre, marca, categoria_id, proveedor_id, precio_nio, costo_nio, activo)
    - modelos_vehiculo(id, marca, modelo, anio_desde, anio_hasta, tipo: 'vehiculo'|'maquinaria'|'motocicleta')
    - repuesto_modelo(repuesto_id, modelo_id)  -- compatibilidad muchos a muchos
    - sucursales(id, nombre, ciudad, departamento, direccion, telefono)
    - inventario(sucursal_id, repuesto_id, stock_actual, stock_minimo)
    - movimientos(id, repuesto_id, sucursal_id, tipo: 'entrada'|'salida',
                  motivo: 'inventario_inicial'|'compra'|'venta'|'ajuste',
                  cantidad (siempre positiva), precio_unitario, fecha timestamptz, referencia)
      precio_unitario es el precio de venta en ventas y el costo en entradas y ajustes.
    - v_stock_bajo_minimo(sucursal, codigo, repuesto, marca, categoria, stock_actual, stock_minimo, faltante)
    Para ignorar tildes usá unaccent(), ej.: unaccent(nombre) ILIKE unaccent('%estelí%').
    Movimientos: 2026-04-01 a 2026-09-30, zona horaria America/Managua.
    """
    return _ejecutar(sql_seguro.ejecutar, consulta=sql, limite=limite)


def main() -> None:
    servidor.run()


if __name__ == "__main__":
    main()
