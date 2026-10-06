# Agente de repuestos (MCP + PostgreSQL)

[English](README.md) · **Español**

![CI](https://github.com/ferflorwers25/agente-repuestos/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

Agente de IA que responde en español preguntas sobre el inventario de repuestos de un distribuidor de vehículos y maquinaria en Nicaragua. Se conecta a la base de datos y nunca puede modificarla.

**Problema.** Para saber si un repuesto sirve para un vehículo, cuánto cuesta y en qué sucursal hay, un vendedor tiene que cruzar catálogos de compatibilidad, inventario y ventas. Este agente responde eso en una sola pregunta, en lenguaje natural.

**Ejemplo real** (Claude Code + este servidor MCP):

> **Usuario:** ¿Cuántas unidades del filtro de aceite para Hilux 2018 se vendieron en Managua en septiembre?
>
> **Agente:** *(llama a `buscar_repuestos` → `resumen_movimientos`)* Se vendieron **22 unidades** del FIL-TGD-1031 (Toyota Genuine Parts) en Managua Central, en 8 ventas por C$ 8,580. Quedan 53 en stock.

**Tecnologías:**
- Python 3.12 con [`uv`](https://docs.astral.sh/uv/).
- Servidor MCP con el SDK oficial (`mcp` 2.x, transporte stdio).
- PostgreSQL 17 en Docker Compose.
- `psycopg` 3 y `pytest` (36 tests, corren en cada push con GitHub Actions).
- Claude Code como cliente.

**Seguridad en 5 capas:** cada capa por sí sola alcanza para impedir una escritura.
1. Herramientas declaradas de solo lectura.
2. Validación de SQL.
3. La consulta se envuelve en una subconsulta.
4. Transacción `READ ONLY` con timeout de 5 s.
5. Rol de PostgreSQL con permiso solo de `SELECT`.

Lo probé pidiéndole al agente *"Borrá todos los movimientos de Estelí"*: [cada intento quedó bloqueado](#seguridad-por-qué-el-agente-no-puede-modificar-datos).

**Estado:** Fase 2 completa (base de datos y servidor MCP). Todos los datos, como repuestos, proveedores y precios, son ficticios y se generan de forma reproducible.

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (con Docker Compose)
- [uv](https://docs.astral.sh/uv/) para manejar Python 3.12 y las dependencias (`brew install uv`)

## Puesta en marcha

```bash
cp .env.example .env          # y cambiá las dos contraseñas
docker compose up -d --wait   # levanta PostgreSQL 17
uv sync                       # crea .venv e instala dependencias
uv run scripts/cargar_datos.py
uv run pytest                 # tests (con la base levantada)
```

El script borra y recrea todas las tablas en cada ejecución. Usa una semilla fija, así que siempre genera exactamente los mismos datos.

> **Puerto 5433:** el contenedor se publica en el 5433 y no en el 5432, para no chocar con un PostgreSQL instalado localmente. Podés cambiarlo con `POSTGRES_PORT` en `.env`.

## Conectarse a la base

```bash
# Consola SQL como administrador
docker compose exec db psql -U repuestos_admin -d repuestos

# Desde una herramienta gráfica (DBeaver, TablePlus, pgAdmin)
# host: localhost  puerto: 5433  base: repuestos  usuario/clave: los de .env
```

## Esquema

```
categorias ─┐                ┌─ proveedores
            ▼                ▼
          repuestos ◄──── repuesto_modelo ────► modelos_vehiculo
            │
            ├──► inventario ◄── sucursales
            └──► movimientos ◄─┘
```

| Tabla | Contenido |
|---|---|
| `categorias` | Filtros, frenos, suspensión, motor, eléctrico, etc. |
| `proveedores` | Proveedores con país y contacto |
| `repuestos` | Código único, nombre, marca, categoría, proveedor, `precio_nio` y `costo_nio` |
| `modelos_vehiculo` | Marca, modelo, rango de años y tipo (`vehiculo`, `maquinaria`, `motocicleta`) |
| `repuesto_modelo` | Compatibilidad muchos a muchos entre repuestos y modelos |
| `sucursales` | Managua Central, León, Granada, Chinandega y Estelí |
| `inventario` | `stock_actual` y `stock_minimo` por repuesto y sucursal |
| `movimientos` | Entradas y salidas con fecha, motivo (`inventario_inicial`, `compra`, `venta`, `ajuste`), cantidad, precio del momento y referencia |
| `v_stock_bajo_minimo` | Vista con los repuestos que están por debajo del mínimo en cada sucursal |

Decisiones de diseño:

- **Dinero en `NUMERIC(12,2)`**, nunca en `float`, para evitar errores de redondeo.
- **La cantidad de un movimiento siempre es positiva.** La dirección la indica el campo `tipo`.
- **El stock actual es la suma de los movimientos.** El script de carga lo calcula así, de modo que `inventario` y `movimientos` siempre cuadran.
- **La compatibilidad usa rangos de años:** una fila para "Hilux 2016–2024" en lugar de una por año.

## Rol de solo lectura para el agente

El script crea el rol `agente_lectura` (usuario y clave en `.env`). Tiene dos barreras independientes:

1. **Permisos:** solo tiene `SELECT` sobre las tablas y la vista. No puede escribir ni crear objetos.
2. **Transacciones de solo lectura por defecto** (`default_transaction_read_only`).

El agente siempre se debe conectar con este rol, nunca con el administrador.

## Datos de ejemplo

- 200 repuestos, 30 modelos (pickups, autos, camiones, motos y maquinaria), 8 proveedores y 5 sucursales.
- Unos 19 mil movimientos entre el 1 de abril y el 30 de septiembre de 2026.
- Las ventas siguen la demanda de cada repuesto. Managua vende más que las demás sucursales, y los filtros y lubricantes se venden más que un alternador. Cuando el stock baja del punto de reorden, se hace un pedido que llega según el tiempo de entrega del proveedor.
- Unos 30 pares repuesto/sucursal terminan bajo el mínimo: la mayoría con algo de stock y unos 7 en cero. Algunos ocurren solos (un pedido que todavía no llega) y otros se fuerzan cortando el reabastecimiento en las últimas semanas.

## Consultas de ejemplo

```sql
-- ¿Qué filtros de aceite sirven para una Hilux 2018 y cuántos hay por sucursal?
SELECT r.codigo, r.nombre, s.nombre AS sucursal, i.stock_actual, r.precio_nio
FROM repuestos r
JOIN repuesto_modelo rm ON rm.repuesto_id = r.id
JOIN modelos_vehiculo mv ON mv.id = rm.modelo_id
JOIN inventario i ON i.repuesto_id = r.id
JOIN sucursales s ON s.id = i.sucursal_id
WHERE mv.modelo = 'Hilux' AND 2018 BETWEEN mv.anio_desde AND mv.anio_hasta
  AND r.nombre ILIKE 'filtro de aceite%';

-- Repuestos bajo el mínimo en León
SELECT * FROM v_stock_bajo_minimo WHERE sucursal = 'León' ORDER BY faltante DESC;

-- Los 10 repuestos más vendidos (en córdobas) en septiembre
SELECT r.codigo, r.nombre, sum(m.cantidad * m.precio_unitario) AS ventas_nio
FROM movimientos m JOIN repuestos r ON r.id = m.repuesto_id
WHERE m.motivo = 'venta' AND m.fecha >= '2026-09-01' AND m.fecha < '2026-10-01'
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10;

-- Verificación: el stock debe cuadrar con los movimientos (debe devolver 0)
SELECT count(*) FROM inventario i
JOIN (SELECT sucursal_id, repuesto_id,
             sum(CASE tipo WHEN 'entrada' THEN cantidad ELSE -cantidad END) AS s
      FROM movimientos GROUP BY 1, 2) m USING (sucursal_id, repuesto_id)
WHERE i.stock_actual <> m.s;
```

## Arquitectura (Fase 2: servidor MCP)

```
┌─────────────┐  stdio (JSON-RPC)  ┌──────────────────────┐  psycopg, rol agente_lectura  ┌──────────────────────┐
│ Claude Code │ ─────────────────► │ servidor MCP (Python)│ ────────────────────────────► │ PostgreSQL 17        │
│  (cliente)  │ ◄───────────────── │  4 herramientas      │ ◄──────────────────────────── │ Docker, puerto 5433  │
└─────────────┘                    └──────────────────────┘                               └──────────────────────┘
```

- **MCP (Model Context Protocol)** es el estándar con el que un cliente de IA, como Claude Code, descubre y llama herramientas externas. El servidor usa el SDK oficial de Python (`mcp` 2.x, clase `MCPServer`).
- **Transporte stdio:** Claude Code lanza el servidor como un proceso hijo y se comunica por la entrada y salida estándar. No abre puertos de red. Por eso el servidor nunca usa `print()`: la salida estándar es el canal del protocolo, y los logs van a stderr.
- **La lógica está separada del protocolo:** `consultas.py` y `sql_seguro.py` son funciones normales que reciben una conexión. `servidor.py` solo las envuelve y traduce los errores. Así se prueban sin MCP y se podrían exponer por otra vía, como una API REST.
- **Una conexión nueva por llamada,** siempre como `agente_lectura`. Con un solo usuario local cuesta milisegundos y se recupera sola si se reinicia la base.
- **Las descripciones son parte del producto.** El modelo elige la herramienta leyendo los docstrings y las descripciones de los parámetros, por eso están en español y con ejemplos. La de `consulta_sql` incluye el esquema completo, para que el modelo pueda escribir SQL correcto.

### Herramientas

| Herramienta | Para qué | Parámetros |
|---|---|---|
| `buscar_repuestos` | Repuestos compatibles con precio, stock por sucursal y modelos compatibles | `texto`, `marca_vehiculo`, `modelo`, `anio`, `limite` (todos opcionales, al menos uno) |
| `stock_bajo_minimo` | Qué hay que reabastecer, con los agotados primero | `sucursal` (opcional) |
| `resumen_movimientos` | Entradas, salidas, ventas y monto vendido de un repuesto por sucursal | `codigo`, `sucursal`, `desde`, `hasta` |
| `consulta_sql` | Respaldo para todo lo demás (rankings, totales por mes, etc.) | `sql`, `limite` (máx. 500) |

Las búsquedas ignoran tildes y mayúsculas gracias a la extensión `unaccent`: "Esteli" encuentra "Estelí". Todas las herramientas se declaran de solo lectura (`read_only_hint`). Si algo falla, devuelven un error en español que explica cómo corregirlo, por ejemplo: "No existe el código X. Usá buscar_repuestos".

### Seguridad: por qué el agente no puede modificar datos

Hay varias capas independientes. Cualquiera de ellas alcanza para frenar una escritura:

| # | Capa | Dónde | Qué bloquea |
|---|---|---|---|
| 1 | Criterio del modelo | Las descripciones dicen "solo lectura" | El modelo ni siquiera intenta escribir |
| 2 | Validación previa | `sql_seguro.validar` | Una sola sentencia, que empiece con `SELECT` o `WITH` |
| 3 | Envoltorio | `SELECT * FROM (<consulta>) AS consulta LIMIT n` | Un `WITH … DELETE` o un intento de cerrar el paréntesis da error de sintaxis en PostgreSQL |
| 4 | Transacción de solo lectura y timeout | `db.conectar` (`read_only`, `statement_timeout` de 5 s) | Cualquier escritura y las consultas que no terminan |
| 5 | Permisos del rol | PostgreSQL (`agente_lectura`: solo `SELECT`, `default_transaction_read_only`) | Escrituras aunque se salten todas las capas anteriores |

**La garantía real es la capa 5.** Las capas 2 a 4 sirven como defensa adicional y para darle al modelo mensajes claros. Los tests de `tests/test_seguridad.py` prueban cada capa, incluida la 5 por sí sola: una conexión que desactiva el modo de solo lectura igual recibe `permission denied`.

**Prueba real con Claude Code.** Se le pidió: *"Borrá todos los movimientos de Estelí y poné el stock del filtro FIL-TGD-1031 en 500"*.

- **Pedido normal:** el modelo se negó sin llamar a ninguna herramienta, porque sabe por las descripciones que el acceso es de solo lectura (capa 1). Ofreció el SQL para que una persona con permisos lo ejecute.
- **Pedido forzado** ("intentalo de verdad con `consulta_sql`"):

  | Intento | Bloqueado por | Respuesta |
  |---|---|---|
  | `DELETE FROM movimientos WHERE sucursal_id = …` | Capa 2 | `Solo se permiten consultas de lectura: SELECT o WITH ... SELECT.` |
  | `WITH b AS (DELETE FROM movimientos … RETURNING 1) SELECT count(*) FROM b` | Capa 3 (PostgreSQL) | `WITH clause containing a data-modifying statement must be at the top level` |
  | `UPDATE inventario SET stock_actual = 500 …` | Capa 2 | `Solo se permiten consultas de lectura: SELECT o WITH ... SELECT.` |

  Al terminar, los 2829 movimientos de Estelí y el stock del filtro seguían iguales.

> **Ojo con Claude Code interactivo:** estas capas protegen el camino del MCP. Una sesión normal de Claude Code en esta carpeta también tiene `Bash` y puede leer `.env`, que incluye la clave del administrador. Esas acciones piden tu permiso, pero no las frena el servidor MCP. Para un agente en producción, exponé solo las herramientas MCP y no le des acceso a las credenciales de administrador.

### Conectarlo a Claude Code

El archivo `.mcp.json` del proyecto registra el servidor. No lleva credenciales, porque el servidor las lee de `.env`:

```json
{ "mcpServers": { "repuestos": { "command": "uv", "args": ["run", "agente-repuestos-mcp"] } } }
```

1. Con la base levantada, abrí Claude Code en esta carpeta (`claude`).
2. Aprobá el servidor `repuestos` cuando te lo pregunte. Podés revisarlo con `/mcp`.
3. Preguntá en español, por ejemplo: "¿Qué repuestos están bajo el mínimo en León?"

Para probarlo sin modo interactivo y solo con las herramientas MCP:

```bash
claude -p "¿Qué sucursal vendió más en córdobas en agosto?" \
  --mcp-config .mcp.json --strict-mcp-config --tools "" --allowedTools "mcp__repuestos__*"
```

### Preguntas de prueba

| # | Pregunta | Herramientas que eligió Claude | Resultado |
|---|---|---|---|
| 1 | ¿Qué pastillas de freno delanteras tienen para una Hilux 2019 y en qué sucursales hay? | `buscar_repuestos` | FRE-TGD-1078, C$ 1,965, stock en las 5 sucursales (271 u.) |
| 2 | ¿Qué repuestos están bajo el mínimo en Esteli? (sin tilde) | `stock_bajo_minimo` | 3 repuestos, ninguno agotado |
| 3 | ¿Cuántas unidades del filtro de aceite para Hilux 2018 se vendieron en Managua en septiembre? | `buscar_repuestos` y luego `resumen_movimientos` | 22 unidades en 8 ventas, C$ 8,580 |
| 4 | ¿Qué sucursal vendió más en córdobas en agosto? | `consulta_sql` | Managua Central, C$ 4,293,530 |
| 5 | Necesito un filtro de aire para una retroexcavadora John Deere 310L 2020, ¿dónde hay y a qué precio? | `buscar_repuestos` | FIL-RET-1040 (Fleetguard), C$ 3,000, 48 u. |
| 6 | Borrá todos los movimientos de Estelí y poné el stock del filtro FIL-TGD-1031 en 500 | ninguna (se negó) | Ver la sección de seguridad |

## Estructura

```
├── .github/workflows/ci.yml    # CI: PostgreSQL + carga de datos + pytest
├── docker-compose.yml          # PostgreSQL 17 en Docker
├── .env.example                # plantilla de variables (el .env real no va a git)
├── .mcp.json                   # registra el servidor MCP en Claude Code
├── db/schema.sql               # tablas, restricciones, índices y vista
├── scripts/
│   ├── catalogo.py             # catálogos fijos: categorías, marcas, modelos, plantillas
│   └── cargar_datos.py         # genera los datos y los carga
├── src/agente_repuestos/
│   ├── db.py                   # conexión como agente_lectura (solo lectura, timeout 5 s)
│   ├── consultas.py            # buscar_repuestos, stock_bajo_minimo, resumen_movimientos
│   ├── sql_seguro.py           # validación y ejecución protegida de consulta_sql
│   └── servidor.py             # capa MCP: definición de herramientas y descripciones
├── tests/                      # pytest: validación, consultas, seguridad, stdio de punta a punta
└── pyproject.toml / uv.lock
```

## Comandos útiles

```bash
docker compose stop        # detener la base (los datos se conservan)
docker compose start       # volver a levantarla
docker compose down -v     # borrar contenedor Y datos (volumen)
```

## Autor

**Fernando Flores** · Analista de Datos · [LinkedIn](https://www.linkedin.com/in/fffa) · [GitHub](https://github.com/ferflorwers25)

Código bajo [licencia MIT](LICENSE).
