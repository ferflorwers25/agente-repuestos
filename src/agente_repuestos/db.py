"""Conexión a PostgreSQL con el rol de solo lectura del agente."""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

RAIZ = Path(__file__).resolve().parents[2]
TIEMPO_MAXIMO_MS = 5000


class ErrorConsulta(Exception):
    """Error con un mensaje pensado para que el modelo lo lea y se corrija."""


def conectar() -> psycopg.Connection:
    """Abre una conexión nueva como agente_lectura.

    Nunca usa las credenciales del administrador. Cada transacción es de solo
    lectura y cada sentencia se corta a los TIEMPO_MAXIMO_MS milisegundos.
    """
    load_dotenv(RAIZ / ".env")
    conn = psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["AGENTE_DB_USER"],
        password=os.environ["AGENTE_DB_PASSWORD"],
        options=f"-c statement_timeout={TIEMPO_MAXIMO_MS} -c TimeZone=America/Managua",
        connect_timeout=5,
        row_factory=dict_row,
    )
    conn.read_only = True
    return conn
