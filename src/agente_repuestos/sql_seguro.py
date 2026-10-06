"""Ejecución protegida de consultas SQL libres (herramienta consulta_sql).

Capas de protección, de la más fuerte a la más débil:
1. El rol agente_lectura solo tiene permiso SELECT y transacciones de solo lectura.
2. La conexión abre cada transacción como READ ONLY y corta a los 5 segundos.
3. La consulta se envuelve como subconsulta: SELECT * FROM (<consulta>) LIMIT n.
   Un DELETE, varias sentencias o un WITH ... DELETE dan error de sintaxis.
4. Una revisión previa rechaza lo obvio con un mensaje claro.
"""

import psycopg
from psycopg import errors, sql
from psycopg.rows import tuple_row

from .consultas import a_json
from .db import TIEMPO_MAXIMO_MS, ErrorConsulta

LIMITE_POR_DEFECTO = 100
LIMITE_MAXIMO = 500


def validar(consulta: str) -> str:
    """Revisión previa: una sola sentencia que empiece con SELECT o WITH."""
    limpia = (consulta or "").strip().rstrip(";").strip()
    if not limpia:
        raise ErrorConsulta("La consulta está vacía.")
    if ";" in limpia:
        raise ErrorConsulta("Solo se permite una sentencia (sin ';' en medio de la consulta).")
    if limpia.split(None, 1)[0].lower() not in ("select", "with"):
        raise ErrorConsulta("Solo se permiten consultas de lectura: SELECT o WITH ... SELECT.")
    return limpia


def ejecutar(conn: psycopg.Connection, consulta: str, limite: int = LIMITE_POR_DEFECTO) -> dict:
    if not 1 <= limite <= LIMITE_MAXIMO:
        raise ErrorConsulta(f"El límite debe estar entre 1 y {LIMITE_MAXIMO}.")
    limpia = validar(consulta)
    # Los saltos de línea evitan que un comentario '--' al final se coma el cierre.
    envuelta = sql.SQL("SELECT * FROM (\n{}\n) AS consulta LIMIT {}").format(sql.SQL(limpia), sql.Literal(limite + 1))

    try:
        with conn.cursor(row_factory=tuple_row) as cur:
            cur.execute(envuelta)
            columnas = [c.name for c in cur.description]
            filas = cur.fetchmany(limite + 1)
    except errors.QueryCanceled:
        raise ErrorConsulta(f"La consulta superó el tiempo máximo de {TIEMPO_MAXIMO_MS // 1000} segundos.")
    except (errors.InsufficientPrivilege, errors.ReadOnlySqlTransaction) as e:
        raise ErrorConsulta(f"Operación no permitida: este acceso es de solo lectura. ({e.diag.message_primary})")
    except psycopg.Error as e:
        raise ErrorConsulta(f"Error de PostgreSQL: {e.diag.message_primary or e}")

    return {
        "columnas": columnas,
        "filas": a_json(filas[:limite]),
        "total_filas": min(len(filas), limite),
        "recortado": len(filas) > limite,
    }
