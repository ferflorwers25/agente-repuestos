"""Genera datos de ejemplo y los carga en PostgreSQL.

Uso:
    uv run scripts/cargar_datos.py

Cada ejecución borra y recrea las tablas, así que siempre deja la base
en el mismo estado (la semilla aleatoria es fija).
"""

import math
import os
import random
import sys
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from dotenv import load_dotenv
from psycopg import sql

import catalogo as cat

RAIZ = Path(__file__).resolve().parent.parent
SEMILLA = 42
TOTAL_REPUESTOS = 200
FECHA_INICIO = date(2026, 4, 1)
FECHA_FIN = date(2026, 9, 30)
PARES_PROBLEMA = 30  # pares repuesto/sucursal que dejan de reabastecerse al final
ZONA = ZoneInfo("America/Managua")


def redondear_5(valor: float) -> Decimal:
    """Redondea a múltiplos de 5 córdobas, como en una lista de precios."""
    return (Decimal(valor) / 5).quantize(Decimal(1), rounding=ROUND_HALF_UP) * 5


def poisson(rng: random.Random, lam: float) -> int:
    """Muestra de una distribución de Poisson (algoritmo de Knuth, λ pequeño)."""
    limite, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limite:
            return k
        k += 1


def momento(rng: random.Random, dia: date, desde: float, hasta: float) -> datetime:
    """Hora aleatoria dentro del horario indicado (en horas decimales)."""
    minutos = rng.randint(int(desde * 60), int(hasta * 60))
    return datetime.combine(dia, time(minutos // 60, minutos % 60), ZONA)


# ---------------------------------------------------------------- catálogo


def generar_repuestos(rng: random.Random) -> list[dict]:
    candidatos = []
    for categoria, nombre, grupos, cmin, cmax, demanda in cat.PLANTILLAS:
        for g in grupos:
            candidatos.append((categoria, nombre, [g], cmin, cmax, demanda, False))
    for categoria, nombre, grupos, cmin, cmax, demanda in cat.UNIVERSALES:
        candidatos.append((categoria, nombre, grupos, cmin, cmax, demanda, True))

    # Los universales siempre entran; el resto se elige al azar hasta llegar a 200.
    universales = [c for c in candidatos if c[6]]
    especificos = [c for c in candidatos if not c[6]]
    rng.shuffle(especificos)
    elegidos = universales + especificos[: TOTAL_REPUESTOS - len(universales)]
    elegidos.sort(key=lambda c: (c[0], c[1], c[2][0]))

    prefijos = {nombre: prefijo for nombre, prefijo, _ in cat.CATEGORIAS}
    repuestos = []
    for n, (categoria, nombre, grupos, cmin, cmax, demanda, universal) in enumerate(elegidos, start=1):
        grupo = cat.GRUPOS[grupos[0]]
        if universal:
            nombre_completo, codigo_grupo, mult, popularidad = nombre, "UNI", 1.0, 1.5
            marca = rng.choice(cat.MARCAS_POR_CATEGORIA[categoria])
        else:
            clase = cat.CLASES[grupo["clase"]]
            nombre_completo = f"{nombre} – {grupo['etiqueta']}"
            codigo_grupo, mult = grupos[0], clase["costo"]
            popularidad = grupo["popularidad"] * clase["demanda"]
            pesada = grupo["clase"] in ("camion", "maquinaria")
            alternativas = (cat.MARCAS_PESADAS.get(categoria) if pesada else None) or cat.MARCAS_POR_CATEGORIA[categoria]
            # Mitad original de fábrica, mitad alternativo (cuando hay marca original).
            marca = grupo["oem"] if grupo["oem"] and rng.random() < 0.5 else rng.choice(alternativas)

        costo = redondear_5(rng.uniform(cmin, cmax) * mult)
        precio = redondear_5(float(costo) * rng.uniform(1.25, 1.60))
        repuestos.append({
            "id": n,
            "codigo": f"{prefijos[categoria]}-{codigo_grupo}-{1000 + n}",
            "nombre": nombre_completo,
            "marca": marca,
            "categoria": categoria,
            "proveedor": cat.PROVEEDOR_POR_MARCA.get(marca, "Autopartes del Pacífico S.A."),
            "precio": precio,
            "costo": costo,
            "demanda": demanda,
            "popularidad": popularidad,
            "grupos": grupos,
        })
    return repuestos


# ------------------------------------------------------------- movimientos


def simular_par(rng, repuesto, sucursal_id, peso_sucursal, lead_min, lead_max, dia_corte):
    """Simula 6 meses de un repuesto en una sucursal.

    Devuelve (stock_final, stock_minimo, movimientos). La política es la de un
    almacén típico: cuando el stock baja del punto de reorden se pide al
    proveedor, y el pedido llega después del tiempo de entrega.
    """
    d = cat.DEMANDA[repuesto["demanda"]]
    trans_semana = d["transacciones"] * repuesto["popularidad"] * peso_sucursal * rng.uniform(0.6, 1.4)
    unidades_semana = trans_semana * (1 + d["cantidad_max"]) / 2
    lead_promedio = (lead_min + lead_max) / 2

    stock_minimo = max(1, math.ceil(unidades_semana * 2))
    punto_reorden = stock_minimo + math.ceil(unidades_semana * lead_promedio / 7 * 2)
    cantidad_pedido = max(stock_minimo * 2, math.ceil(unidades_semana * 6), 2)
    stock = punto_reorden + rng.randint(0, cantidad_pedido)

    movs = [(repuesto["id"], sucursal_id, "entrada", "inventario_inicial", stock,
             repuesto["costo"], datetime.combine(FECHA_INICIO, time(7, 0), ZONA))]
    llegada_pedido = None
    pedido = 0

    dia = FECHA_INICIO
    while dia <= FECHA_FIN:
        domingo = dia.weekday() == 6
        if llegada_pedido and dia >= llegada_pedido and not domingo:
            stock += pedido
            movs.append((repuesto["id"], sucursal_id, "entrada", "compra", pedido,
                         repuesto["costo"], momento(rng, dia, 8.5, 11)))
            llegada_pedido = None

        if not domingo:
            cierre = 12 if dia.weekday() == 5 else 17.5
            for _ in range(poisson(rng, trans_semana / 6)):
                cantidad = min(rng.randint(1, d["cantidad_max"]), stock)
                if cantidad == 0:
                    continue  # venta perdida por falta de stock
                stock -= cantidad
                movs.append((repuesto["id"], sucursal_id, "salida", "venta", cantidad,
                             repuesto["precio"], momento(rng, dia, 8, cierre)))
            if stock > 0 and rng.random() < 0.0005:  # merma o daño
                stock -= 1
                movs.append((repuesto["id"], sucursal_id, "salida", "ajuste", 1,
                             repuesto["costo"], momento(rng, dia, 16, 17.5)))

        sin_reabastecer = dia_corte is not None and dia >= dia_corte
        if sin_reabastecer:
            llegada_pedido = None  # el proveedor no entrega lo pendiente
        elif llegada_pedido is None and stock <= punto_reorden:
            pedido = cantidad_pedido
            llegada_pedido = dia + timedelta(days=rng.randint(lead_min, lead_max))
        dia += timedelta(days=1)

    return stock, stock_minimo, movs


def generar_inventario(rng, repuestos):
    proveedores = {p[0]: p for p in cat.PROVEEDORES}
    pares = [(r, s) for r in repuestos for s in range(1, len(cat.SUCURSALES) + 1)]

    # Algunos pares de demanda media/alta quedan sin reabastecer las últimas semanas.
    candidatos = [p for p in pares if p[0]["demanda"] != "baja"]
    problema = {(r["id"], s) for r, s in rng.sample(candidatos, PARES_PROBLEMA)}

    inventario, movimientos = [], []
    for repuesto, sucursal_id in pares:
        _, _, _, _, _, lead_min, lead_max = proveedores[repuesto["proveedor"]]
        peso = cat.SUCURSALES[sucursal_id - 1][6]
        corte = None
        if (repuesto["id"], sucursal_id) in problema:
            corte = FECHA_FIN - timedelta(days=rng.randint(35, 80))
        stock, minimo, movs = simular_par(rng, repuesto, sucursal_id, peso, lead_min, lead_max, corte)
        inventario.append((sucursal_id, repuesto["id"], stock, minimo))
        movimientos.extend(movs)

    movimientos.sort(key=lambda m: m[6])
    return inventario, numerar_referencias(movimientos)


def numerar_referencias(movimientos):
    """Asigna números de factura (ventas) y de orden de compra (entradas)."""
    codigos = {i: s[1] for i, s in enumerate(cat.SUCURSALES, start=1)}
    facturas = {i: 0 for i in codigos}
    ordenes = 0
    resultado = []
    for rep, suc, tipo, motivo, cant, precio, fecha in movimientos:
        if motivo == "venta":
            facturas[suc] += 1
            ref = f"FAC-{codigos[suc]}-{facturas[suc]:06d}"
        elif motivo == "compra":
            ordenes += 1
            ref = f"OC-2026-{ordenes:05d}"
        elif motivo == "ajuste":
            ref = "AJUSTE-MERMA"
        else:
            ref = "INV-INICIAL-2026"
        resultado.append((rep, suc, tipo, motivo, cant, precio, fecha, ref))
    return resultado


# --------------------------------------------------------------- base de datos


def conectar(usuario=None, clave=None):
    return psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=usuario or os.environ["POSTGRES_USER"],
        password=clave or os.environ["POSTGRES_PASSWORD"],
    )


def insertar(cur, repuestos, inventario, movimientos):
    cur.executemany(
        "INSERT INTO categorias (nombre, descripcion) VALUES (%s, %s)",
        [(nombre, desc) for nombre, _, desc in cat.CATEGORIAS],
    )
    cur.executemany(
        "INSERT INTO proveedores (nombre, pais, contacto, telefono, email) VALUES (%s, %s, %s, %s, %s)",
        [p[:5] for p in cat.PROVEEDORES],
    )
    cur.executemany(
        "INSERT INTO sucursales (nombre, ciudad, departamento, direccion, telefono) VALUES (%s, %s, %s, %s, %s)",
        [(s[0], s[2], s[3], s[4], s[5]) for s in cat.SUCURSALES],
    )

    modelos = []
    for codigo_grupo, grupo in cat.GRUPOS.items():
        for m in grupo["modelos"]:
            modelos.append((codigo_grupo, *m))
    cur.executemany(
        "INSERT INTO modelos_vehiculo (marca, modelo, anio_desde, anio_hasta, tipo) VALUES (%s, %s, %s, %s, %s)",
        [m[1:] for m in modelos],
    )
    ids_por_grupo = {}
    for modelo_id, m in enumerate(modelos, start=1):
        ids_por_grupo.setdefault(m[0], []).append(modelo_id)

    ids_categoria = {n: i for i, (n, _, _) in enumerate(cat.CATEGORIAS, start=1)}
    ids_proveedor = {p[0]: i for i, p in enumerate(cat.PROVEEDORES, start=1)}
    cur.executemany(
        """INSERT INTO repuestos (codigo, nombre, marca, categoria_id, proveedor_id, precio_nio, costo_nio)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        [(r["codigo"], r["nombre"], r["marca"], ids_categoria[r["categoria"]],
          ids_proveedor[r["proveedor"]], r["precio"], r["costo"]) for r in repuestos],
    )
    cur.executemany(
        "INSERT INTO repuesto_modelo (repuesto_id, modelo_id) VALUES (%s, %s)",
        [(r["id"], mid) for r in repuestos for g in r["grupos"] for mid in ids_por_grupo[g]],
    )
    cur.executemany(
        "INSERT INTO inventario (sucursal_id, repuesto_id, stock_actual, stock_minimo) VALUES (%s, %s, %s, %s)",
        inventario,
    )
    columnas = "repuesto_id, sucursal_id, tipo, motivo, cantidad, precio_unitario, fecha, referencia"
    with cur.copy(f"COPY movimientos ({columnas}) FROM STDIN") as copia:
        for m in movimientos:
            copia.write_row(m)


def configurar_rol_lectura(cur):
    """Crea (o actualiza) el rol de solo lectura que usará el agente."""
    usuario = os.environ["AGENTE_DB_USER"]
    rol = sql.Identifier(usuario)
    clave = sql.Literal(os.environ["AGENTE_DB_PASSWORD"])

    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (usuario,))
    accion = "ALTER" if cur.fetchone() else "CREATE"
    cur.execute(sql.SQL(accion + " ROLE {} WITH LOGIN PASSWORD {}").format(rol, clave))
    # Segunda barrera: aunque tuviera permisos, sus transacciones son de solo lectura.
    cur.execute(sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(rol))
    cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
        sql.Identifier(os.environ["POSTGRES_DB"]), rol))
    cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(rol))
    # Incluye la vista v_stock_bajo_minimo. Las tablas se recrean en cada
    # carga, por eso el permiso se vuelve a otorgar aquí.
    cur.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(rol))


def main():
    load_dotenv(RAIZ / ".env")
    faltantes = [v for v in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER",
                             "POSTGRES_PASSWORD", "AGENTE_DB_USER", "AGENTE_DB_PASSWORD")
                 if not os.environ.get(v)]
    if faltantes:
        sys.exit(f"Faltan variables en .env: {', '.join(faltantes)} (ver .env.example)")

    rng = random.Random(SEMILLA)
    print("Generando datos…")
    repuestos = generar_repuestos(rng)
    inventario, movimientos = generar_inventario(rng, repuestos)

    print("Cargando en PostgreSQL…")
    with conectar() as conn, conn.cursor() as cur:  # una sola transacción
        cur.execute((RAIZ / "db" / "schema.sql").read_text(encoding="utf-8"))
        insertar(cur, repuestos, inventario, movimientos)
        configurar_rol_lectura(cur)

        cur.execute("SELECT count(*) FROM repuesto_modelo")
        compatibilidades = cur.fetchone()[0]
        cur.execute("SELECT count(*), count(*) FILTER (WHERE stock_actual = 0) FROM v_stock_bajo_minimo")
        bajo_minimo, en_cero = cur.fetchone()

    print(f"""Listo:
  {len(cat.SUCURSALES)} sucursales, {len(cat.PROVEEDORES)} proveedores, {len(cat.CATEGORIAS)} categorías
  {sum(len(g['modelos']) for g in cat.GRUPOS.values())} modelos de vehículo
  {len(repuestos)} repuestos, {compatibilidades} compatibilidades repuesto-modelo
  {len(movimientos)} movimientos ({FECHA_INICIO} a {FECHA_FIN})
  {bajo_minimo} pares repuesto/sucursal bajo el stock mínimo ({en_cero} en cero)
  Rol de solo lectura: {os.environ['AGENTE_DB_USER']}""")


if __name__ == "__main__":
    main()
