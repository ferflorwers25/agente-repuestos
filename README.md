# Agente de repuestos

Agente de IA que responde preguntas sobre el inventario de repuestos de un distribuidor de vehículos y maquinaria en Nicaragua.

**Estado:** Fase 1, base de datos con datos de ejemplo. Todos los datos (repuestos, proveedores, precios) son ficticios.

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (con Docker Compose)
- [uv](https://docs.astral.sh/uv/) para manejar Python 3.12 y las dependencias (`brew install uv`)

## Puesta en marcha

```bash
cp .env.example .env          # y cambiá las dos contraseñas
docker compose up -d --wait   # levanta PostgreSQL 17
uv sync                       # crea .venv e instala dependencias
uv run scripts/cargar_datos.py
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

## Estructura

```
├── docker-compose.yml      # PostgreSQL 17 en Docker
├── .env.example            # plantilla de variables (el .env real no va a git)
├── db/schema.sql           # tablas, restricciones, índices y vista
├── scripts/
│   ├── catalogo.py         # catálogos fijos: categorías, marcas, modelos, plantillas
│   └── cargar_datos.py     # genera los datos y los carga
└── pyproject.toml / uv.lock
```

## Comandos útiles

```bash
docker compose stop        # detener la base (los datos se conservan)
docker compose start       # volver a levantarla
docker compose down -v     # borrar contenedor Y datos (volumen)
```
