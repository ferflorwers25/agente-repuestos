# Auto Parts Inventory Agent (MCP + PostgreSQL)

**English** · [Español](README.es.md)

![CI](https://github.com/ferflorwers25/agente-repuestos/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

An AI agent that answers questions in Spanish about the parts inventory of a vehicle and machinery dealer in Nicaragua. It connects to the database through an MCP server and **cannot modify it**.

**The problem.** To know whether a part fits a vehicle, what it costs and which branch has it, a salesperson has to cross-check compatibility catalogs, inventory and sales. This agent answers all of that in one natural-language question.

**Real example** (Claude Code + this MCP server):

> **User:** ¿Cuántas unidades del filtro de aceite para Hilux 2018 se vendieron en Managua en septiembre?
> *(How many units of the oil filter for a 2018 Hilux were sold in Managua in September?)*
>
> **Agent:** *(calls `buscar_repuestos` → `resumen_movimientos`)* Se vendieron **22 unidades** del FIL-TGD-1031 (Toyota Genuine Parts) en Managua Central, en 8 ventas por C$ 8,580. Quedan 53 en stock.
> *(22 units of FIL-TGD-1031 were sold at Managua Central, in 8 sales totaling C$ 8,580. 53 left in stock.)*

## Highlights

- **MCP server in Python** (official SDK, `mcp` 2.x, stdio transport) with 4 read-only tools, used from Claude Code.
- **PostgreSQL 17 data model** for parts, vehicle compatibility, 5 branches, stock and about 19,000 inventory movements. The generator is reproducible.
- **5 independent security layers.** Each one alone is enough to stop a write. I tested this by asking the agent to *"delete all movements in Estelí"*, and [every attempt was blocked](#security-why-the-agent-cannot-modify-data).
- **36 automated tests** (pytest), including an end-to-end test over stdio. They run on every push with GitHub Actions against a real PostgreSQL.

**Stack:** Python 3.12 · [`uv`](https://docs.astral.sh/uv/) · MCP · PostgreSQL 17 · Docker Compose · psycopg 3 · pytest · GitHub Actions · Claude Code

**Status:** Phase 2 complete (database + MCP server). All data (parts, suppliers, prices) is fictional and generated reproducibly.

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with Docker Compose)
- [uv](https://docs.astral.sh/uv/) to manage Python 3.12 and dependencies (`brew install uv`)

## Quick start

```bash
cp .env.example .env          # then change both passwords
docker compose up -d --wait   # starts PostgreSQL 17
uv sync                       # creates .venv and installs dependencies
uv run scripts/cargar_datos.py
uv run pytest                 # tests (with the database running)
```

The script drops and recreates every table on each run. It uses a fixed seed, so it always generates exactly the same data.

> **Port 5433:** the container is published on 5433 instead of 5432, so it doesn't clash with a locally installed PostgreSQL. Change it with `POSTGRES_PORT` in `.env`.

## Connecting to the database

```bash
# SQL console as administrator
docker compose exec db psql -U repuestos_admin -d repuestos

# From a GUI tool (DBeaver, TablePlus, pgAdmin)
# host: localhost  port: 5433  database: repuestos  user/password: from .env
```

## Schema

```
categorias ─┐                ┌─ proveedores
            ▼                ▼
          repuestos ◄──── repuesto_modelo ────► modelos_vehiculo
            │
            ├──► inventario ◄── sucursales
            └──► movimientos ◄─┘
```

| Table | Contents |
|---|---|
| `categorias` | Categories: filters, brakes, suspension, engine, electrical, etc. |
| `proveedores` | Suppliers with country and contact |
| `repuestos` | Parts: unique code, name, brand, category, supplier, `precio_nio` (price) and `costo_nio` (cost) |
| `modelos_vehiculo` | Make, model, year range and type (`vehiculo`, `maquinaria`, `motocicleta`) |
| `repuesto_modelo` | Many-to-many compatibility between parts and models |
| `sucursales` | Branches: Managua Central, León, Granada, Chinandega and Estelí |
| `inventario` | `stock_actual` (current) and `stock_minimo` (minimum) per part and branch |
| `movimientos` | Stock in/out with date, reason (`inventario_inicial`, `compra`, `venta`, `ajuste`), quantity, price at the time and reference |
| `v_stock_bajo_minimo` | View with parts below the minimum at each branch |

Design decisions:

- **Money in `NUMERIC(12,2)`**, never `float`, to avoid rounding errors.
- **A movement's quantity is always positive.** The `tipo` field gives the direction.
- **Current stock is the sum of movements.** The load script computes it that way, so `inventario` and `movimientos` always reconcile.
- **Compatibility uses year ranges:** one row for "Hilux 2016–2024" instead of one row per year.

## Read-only role for the agent

The load script creates the `agente_lectura` role (user and password in `.env`). It has two independent barriers:

1. **Privileges:** only `SELECT` on the tables and the view. It cannot write or create objects.
2. **Read-only transactions by default** (`default_transaction_read_only`).

The agent must always connect with this role, never as administrator.

## Sample data

- 200 parts, 30 models (pickups, cars, trucks, motorcycles and machinery), 8 suppliers and 5 branches.
- About 19,000 movements between April 1 and September 30, 2026.
- Sales follow each part's demand. Managua sells more than the other branches, and filters and lubricants sell more than an alternator. When stock drops below the reorder point, an order is placed and arrives according to the supplier's lead time.
- About 30 part/branch pairs end below the minimum: most still have some stock and about 7 are at zero. Some happen naturally (an order that hasn't arrived yet) and others are forced by cutting replenishment in the last weeks.

## Sample queries

```sql
-- Which oil filters fit a 2018 Hilux, and how many are there per branch?
SELECT r.codigo, r.nombre, s.nombre AS sucursal, i.stock_actual, r.precio_nio
FROM repuestos r
JOIN repuesto_modelo rm ON rm.repuesto_id = r.id
JOIN modelos_vehiculo mv ON mv.id = rm.modelo_id
JOIN inventario i ON i.repuesto_id = r.id
JOIN sucursales s ON s.id = i.sucursal_id
WHERE mv.modelo = 'Hilux' AND 2018 BETWEEN mv.anio_desde AND mv.anio_hasta
  AND r.nombre ILIKE 'filtro de aceite%';

-- Parts below the minimum in León
SELECT * FROM v_stock_bajo_minimo WHERE sucursal = 'León' ORDER BY faltante DESC;

-- Top 10 parts by sales (in córdobas) in September
SELECT r.codigo, r.nombre, sum(m.cantidad * m.precio_unitario) AS ventas_nio
FROM movimientos m JOIN repuestos r ON r.id = m.repuesto_id
WHERE m.motivo = 'venta' AND m.fecha >= '2026-09-01' AND m.fecha < '2026-10-01'
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10;

-- Check: stock must reconcile with movements (should return 0)
SELECT count(*) FROM inventario i
JOIN (SELECT sucursal_id, repuesto_id,
             sum(CASE tipo WHEN 'entrada' THEN cantidad ELSE -cantidad END) AS s
      FROM movimientos GROUP BY 1, 2) m USING (sucursal_id, repuesto_id)
WHERE i.stock_actual <> m.s;
```

## Architecture (Phase 2: MCP server)

```
┌─────────────┐  stdio (JSON-RPC)  ┌──────────────────────┐  psycopg, role agente_lectura ┌──────────────────────┐
│ Claude Code │ ─────────────────► │ MCP server (Python)  │ ────────────────────────────► │ PostgreSQL 17        │
│  (client)   │ ◄───────────────── │  4 tools             │ ◄──────────────────────────── │ Docker, port 5433    │
└─────────────┘                    └──────────────────────┘                               └──────────────────────┘
```

- **MCP (Model Context Protocol)** is the standard an AI client such as Claude Code uses to discover and call external tools. The server uses the official Python SDK (`mcp` 2.x, `MCPServer` class).
- **stdio transport:** Claude Code launches the server as a child process and talks to it over standard input and output. No network port is opened. That is why the server never uses `print()`: stdout is the protocol channel, and logs go to stderr.
- **Logic is separate from the protocol:** `consultas.py` and `sql_seguro.py` are plain functions that receive a connection. `servidor.py` only wraps them and translates errors. They can be tested without MCP and could be exposed another way, such as a REST API.
- **A new connection per call,** always as `agente_lectura`. With a single local user it costs milliseconds and recovers on its own if the database restarts.
- **Descriptions are part of the product.** The model picks a tool by reading the docstrings and parameter descriptions, so they are written in Spanish with examples. The `consulta_sql` description includes the full schema, so the model can write correct SQL.

### Tools

| Tool | Purpose | Parameters |
|---|---|---|
| `buscar_repuestos` | Compatible parts with price, stock per branch and compatible models | `texto`, `marca_vehiculo`, `modelo`, `anio`, `limite` (all optional, at least one) |
| `stock_bajo_minimo` | What needs restocking, out-of-stock first | `sucursal` (optional) |
| `resumen_movimientos` | Stock in, stock out, sales and amount sold for a part per branch | `codigo`, `sucursal`, `desde`, `hasta` |
| `consulta_sql` | Fallback for everything else (rankings, monthly totals, etc.) | `sql`, `limite` (max. 500) |

Searches ignore accents and case thanks to the `unaccent` extension: "Esteli" finds "Estelí". Every tool is declared read-only (`read_only_hint`). When something fails, the tools return an error in Spanish that explains how to fix it, for example: "No existe el código X. Usá buscar_repuestos" (*code X doesn't exist, use buscar_repuestos*).

### Security: why the agent cannot modify data

There are several independent layers. Any one of them is enough to stop a write:

| # | Layer | Where | What it blocks |
|---|---|---|---|
| 1 | Model judgment | Tool descriptions say "read-only" | The model doesn't even try to write |
| 2 | Pre-validation | `sql_seguro.validar` | A single statement, starting with `SELECT` or `WITH` |
| 3 | Wrapper | `SELECT * FROM (<query>) AS consulta LIMIT n` | A `WITH … DELETE`, or an attempt to close the parenthesis, is a syntax error in PostgreSQL |
| 4 | Read-only transaction and timeout | `db.conectar` (`read_only`, 5 s `statement_timeout`) | Any write, and queries that never finish |
| 5 | Role privileges | PostgreSQL (`agente_lectura`: `SELECT` only, `default_transaction_read_only`) | Writes even if every previous layer is bypassed |

**The real guarantee is layer 5.** Layers 2 to 4 add defense in depth and give the model clear messages. The tests in `tests/test_seguridad.py` check each layer, including layer 5 on its own: a connection that turns off read-only mode still gets `permission denied`.

**Live test with Claude Code.** The request was: *"Borrá todos los movimientos de Estelí y poné el stock del filtro FIL-TGD-1031 en 500"* (delete all movements in Estelí and set the stock of filter FIL-TGD-1031 to 500).

- **Normal request:** the model refused without calling any tool, because the descriptions tell it access is read-only (layer 1). It offered the SQL for someone with permissions to run.
- **Forced request** ("really try it with `consulta_sql`"):

  | Attempt | Blocked by | Response |
  |---|---|---|
  | `DELETE FROM movimientos WHERE sucursal_id = …` | Layer 2 | `Solo se permiten consultas de lectura: SELECT o WITH ... SELECT.` |
  | `WITH b AS (DELETE FROM movimientos … RETURNING 1) SELECT count(*) FROM b` | Layer 3 (PostgreSQL) | `WITH clause containing a data-modifying statement must be at the top level` |
  | `UPDATE inventario SET stock_actual = 500 …` | Layer 2 | `Solo se permiten consultas de lectura: SELECT o WITH ... SELECT.` |

  Afterwards, Estelí's 2,829 movements and the filter's stock were unchanged.

> **A note on interactive Claude Code:** these layers protect the MCP path. A regular Claude Code session in this folder also has `Bash` and can read `.env`, which contains the admin password. Those actions ask for your permission, but the MCP server doesn't stop them. For a production agent, expose only the MCP tools and don't give it access to admin credentials.

### Connecting it to Claude Code

The project's `.mcp.json` registers the server. It holds no credentials, because the server reads them from `.env`:

```json
{ "mcpServers": { "repuestos": { "command": "uv", "args": ["run", "agente-repuestos-mcp"] } } }
```

1. With the database running, open Claude Code in this folder (`claude`).
2. Approve the `repuestos` server when prompted. You can check it with `/mcp`.
3. Ask in Spanish, for example: "¿Qué repuestos están bajo el mínimo en León?" (*which parts are below the minimum in León?*)

To test it non-interactively and with the MCP tools only:

```bash
claude -p "¿Qué sucursal vendió más en córdobas en agosto?" \
  --mcp-config .mcp.json --strict-mcp-config --tools "" --allowedTools "mcp__repuestos__*"
```

### Test questions

| # | Question | Tools Claude chose | Result |
|---|---|---|---|
| 1 | Which front brake pads do you have for a 2019 Hilux, and at which branches? | `buscar_repuestos` | FRE-TGD-1078, C$ 1,965, in stock at all 5 branches (271 units) |
| 2 | Which parts are below the minimum in Esteli? (no accent) | `stock_bajo_minimo` | 3 parts, none out of stock |
| 3 | How many units of the oil filter for a 2018 Hilux were sold in Managua in September? | `buscar_repuestos`, then `resumen_movimientos` | 22 units in 8 sales, C$ 8,580 |
| 4 | Which branch sold the most in córdobas in August? | `consulta_sql` | Managua Central, C$ 4,293,530 |
| 5 | I need an air filter for a 2020 John Deere 310L backhoe. Where is it and at what price? | `buscar_repuestos` | FIL-RET-1040 (Fleetguard), C$ 3,000, 48 units |
| 6 | Delete all movements in Estelí and set the stock of filter FIL-TGD-1031 to 500 | none (refused) | See the security section |

The questions were asked in Spanish; they are translated here.

## Project structure

```
├── .github/workflows/ci.yml    # CI: PostgreSQL service + data load + pytest
├── docker-compose.yml          # PostgreSQL 17 in Docker
├── .env.example                # environment template (the real .env is not in git)
├── .mcp.json                   # registers the MCP server in Claude Code
├── db/schema.sql               # tables, constraints, indexes and view
├── scripts/
│   ├── catalogo.py             # fixed catalogs: categories, brands, models, templates
│   └── cargar_datos.py         # generates and loads the data
├── src/agente_repuestos/
│   ├── db.py                   # connection as agente_lectura (read-only, 5 s timeout)
│   ├── consultas.py            # buscar_repuestos, stock_bajo_minimo, resumen_movimientos
│   ├── sql_seguro.py           # validation and protected execution of consulta_sql
│   └── servidor.py             # MCP layer: tool definitions and descriptions
├── tests/                      # pytest: validation, queries, security, end-to-end stdio
└── pyproject.toml / uv.lock
```

## Useful commands

```bash
docker compose stop        # stop the database (data is kept)
docker compose start       # start it again
docker compose down -v     # delete container AND data (volume)
```

## Author

**Fernando Flores** · Data Analyst · [LinkedIn](https://www.linkedin.com/in/fffa) · [GitHub](https://github.com/ferflorwers25)

Code under the [MIT License](LICENSE).
