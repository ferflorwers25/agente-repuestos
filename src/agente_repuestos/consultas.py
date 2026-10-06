"""Operaciones de consulta del inventario.

Son funciones normales que reciben una conexión y devuelven estructuras
serializables a JSON. No saben nada de MCP, así se pueden probar solas.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import psycopg

from .db import ErrorConsulta

LIMITE_BUSQUEDA_MAXIMO = 50


def a_json(valor):
    """Convierte los tipos de PostgreSQL a tipos que JSON entiende."""
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {k: a_json(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [a_json(v) for v in valor]
    return valor


def _patron(texto: str) -> str:
    """Patrón ILIKE que busca el texto en cualquier parte, escapando comodines."""
    escapado = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado}%"


def _limpiar(texto: str | None) -> str | None:
    texto = (texto or "").strip()
    return texto or None


def buscar_repuestos(
    conn: psycopg.Connection,
    texto: str | None = None,
    marca_vehiculo: str | None = None,
    modelo: str | None = None,
    anio: int | None = None,
    limite: int = 20,
) -> dict:
    texto, marca_vehiculo, modelo = _limpiar(texto), _limpiar(marca_vehiculo), _limpiar(modelo)
    if not any([texto, marca_vehiculo, modelo, anio]):
        raise ErrorConsulta("Indicá al menos un criterio: texto, marca_vehiculo, modelo o anio.")
    if anio is not None and not 1950 <= anio <= 2100:
        raise ErrorConsulta(f"El año {anio} no es válido.")
    if not 1 <= limite <= LIMITE_BUSQUEDA_MAXIMO:
        raise ErrorConsulta(f"El límite debe estar entre 1 y {LIMITE_BUSQUEDA_MAXIMO}.")

    palabras = [_patron(p) for p in texto.split()] if texto else []
    filtra_vehiculo = any([marca_vehiculo, modelo, anio])
    filas = conn.execute(
        """
        SELECT r.codigo, r.nombre, r.marca, c.nombre AS categoria, r.precio_nio,
               (SELECT sum(i.stock_actual) FROM inventario i WHERE i.repuesto_id = r.id) AS stock_total,
               (SELECT json_agg(json_build_object('sucursal', s.nombre, 'stock', i.stock_actual,
                                                  'stock_minimo', i.stock_minimo) ORDER BY s.id)
                  FROM inventario i JOIN sucursales s ON s.id = i.sucursal_id
                 WHERE i.repuesto_id = r.id) AS stock_por_sucursal,
               (SELECT json_agg(mv.marca || ' ' || mv.modelo || ' ' || mv.anio_desde || '-' || mv.anio_hasta
                                ORDER BY mv.marca, mv.modelo, mv.anio_desde)
                  FROM repuesto_modelo rm JOIN modelos_vehiculo mv ON mv.id = rm.modelo_id
                 WHERE rm.repuesto_id = r.id) AS compatible_con
        FROM repuestos r
        JOIN categorias c ON c.id = r.categoria_id
        WHERE r.activo
          -- Cada palabra del texto debe aparecer en el nombre, código, marca o categoría.
          AND NOT EXISTS (
                SELECT 1 FROM unnest(%(palabras)s::text[]) AS p
                 WHERE unaccent(r.nombre || ' ' || r.codigo || ' ' || r.marca || ' ' || c.nombre)
                       NOT ILIKE unaccent(p))
          AND (NOT %(filtra_vehiculo)s OR EXISTS (
                SELECT 1 FROM repuesto_modelo rm JOIN modelos_vehiculo mv ON mv.id = rm.modelo_id
                 WHERE rm.repuesto_id = r.id
                   AND (%(marca)s::text IS NULL OR unaccent(mv.marca) ILIKE unaccent(%(marca)s))
                   AND (%(modelo)s::text IS NULL OR unaccent(mv.modelo) ILIKE unaccent(%(modelo)s))
                   AND (%(anio)s::int IS NULL OR %(anio)s::int BETWEEN mv.anio_desde AND mv.anio_hasta)))
        ORDER BY c.nombre, r.nombre
        LIMIT %(limite)s
        """,
        {
            "palabras": palabras,
            "filtra_vehiculo": filtra_vehiculo,
            "marca": _patron(marca_vehiculo) if marca_vehiculo else None,
            "modelo": _patron(modelo) if modelo else None,
            "anio": anio,
            "limite": limite + 1,
        },
    ).fetchall()

    return {
        "total": min(len(filas), limite),
        "hay_mas_resultados": len(filas) > limite,
        "moneda": "NIO",
        "repuestos": a_json(filas[:limite]),
    }


def _validar_sucursal(conn: psycopg.Connection, sucursal: str) -> None:
    sucursales = [f["nombre"] for f in conn.execute("SELECT nombre FROM sucursales ORDER BY id")]
    coincide = conn.execute(
        "SELECT 1 FROM sucursales WHERE unaccent(nombre) ILIKE unaccent(%s)", (_patron(sucursal),)
    ).fetchone()
    if not coincide:
        raise ErrorConsulta(f"No existe la sucursal '{sucursal}'. Sucursales válidas: {', '.join(sucursales)}.")


def stock_bajo_minimo(conn: psycopg.Connection, sucursal: str | None = None) -> dict:
    sucursal = _limpiar(sucursal)
    if sucursal:
        _validar_sucursal(conn, sucursal)
    filas = conn.execute(
        """
        SELECT sucursal, codigo, repuesto, marca, categoria, stock_actual, stock_minimo, faltante
        FROM v_stock_bajo_minimo
        WHERE %(sucursal)s::text IS NULL OR unaccent(sucursal) ILIKE unaccent(%(sucursal)s)
        ORDER BY stock_actual = 0 DESC, faltante DESC, sucursal, codigo
        """,
        {"sucursal": _patron(sucursal) if sucursal else None},
    ).fetchall()
    return {
        "total": len(filas),
        "en_cero": sum(1 for f in filas if f["stock_actual"] == 0),
        "repuestos": a_json(filas),
    }


def resumen_movimientos(
    conn: psycopg.Connection,
    codigo: str,
    sucursal: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> dict:
    codigo, sucursal = (_limpiar(codigo) or "").upper(), _limpiar(sucursal)
    repuesto = conn.execute(
        "SELECT id, codigo, nombre, marca FROM repuestos WHERE upper(codigo) = %s", (codigo,)
    ).fetchone()
    if not repuesto:
        raise ErrorConsulta(
            f"No existe el repuesto con código '{codigo}'. Usá buscar_repuestos para encontrar el código."
        )
    if sucursal:
        _validar_sucursal(conn, sucursal)
    if desde and hasta and desde > hasta:
        raise ErrorConsulta("La fecha 'desde' es posterior a 'hasta'.")

    filas = conn.execute(
        """
        SELECT s.nombre AS sucursal,
               coalesce(sum(m.cantidad) FILTER (WHERE m.tipo = 'entrada'), 0)              AS unidades_entrada,
               coalesce(sum(m.cantidad) FILTER (WHERE m.motivo = 'inventario_inicial'), 0) AS unidades_inventario_inicial,
               coalesce(sum(m.cantidad) FILTER (WHERE m.motivo = 'compra'), 0)             AS unidades_compradas,
               coalesce(sum(m.cantidad) FILTER (WHERE m.tipo = 'salida'), 0)               AS unidades_salida,
               coalesce(sum(m.cantidad) FILTER (WHERE m.motivo = 'venta'), 0)              AS unidades_vendidas,
               coalesce(sum(m.cantidad) FILTER (WHERE m.motivo = 'ajuste'), 0)             AS unidades_ajuste,
               count(*) FILTER (WHERE m.motivo = 'venta')                                  AS numero_ventas,
               coalesce(sum(m.cantidad * m.precio_unitario) FILTER (WHERE m.motivo = 'venta'), 0) AS monto_vendido_nio,
               max(m.fecha)                                                                AS ultimo_movimiento,
               i.stock_actual
        FROM sucursales s
        JOIN inventario i ON i.sucursal_id = s.id AND i.repuesto_id = %(repuesto_id)s
        LEFT JOIN movimientos m ON m.sucursal_id = s.id AND m.repuesto_id = %(repuesto_id)s
                               AND (%(desde)s::date IS NULL OR m.fecha >= %(desde)s::date)
                               AND (%(hasta)s::date IS NULL OR m.fecha < %(hasta)s::date + 1)
        WHERE %(sucursal)s::text IS NULL OR unaccent(s.nombre) ILIKE unaccent(%(sucursal)s)
        GROUP BY s.id, s.nombre, i.stock_actual
        ORDER BY s.id
        """,
        {
            "repuesto_id": repuesto["id"],
            "desde": desde,
            "hasta": hasta,
            "sucursal": _patron(sucursal) if sucursal else None,
        },
    ).fetchall()

    campos_suma = ["unidades_entrada", "unidades_salida", "unidades_vendidas", "numero_ventas", "monto_vendido_nio"]
    total = {campo: sum(f[campo] for f in filas) for campo in campos_suma}
    return {
        "repuesto": {k: repuesto[k] for k in ("codigo", "nombre", "marca")},
        "periodo": {"desde": desde, "hasta": hasta} if desde or hasta else "todo el historial",
        "moneda": "NIO",
        "por_sucursal": a_json(filas),
        "total": a_json(total),
    }
