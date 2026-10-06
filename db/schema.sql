-- Esquema de inventario de repuestos
-- Se aplica desde scripts/cargar_datos.py: borra y recrea todo (base limpia en cada carga).

DROP VIEW  IF EXISTS v_stock_bajo_minimo;
DROP TABLE IF EXISTS movimientos, inventario, repuesto_modelo, repuestos,
                     modelos_vehiculo, sucursales, proveedores, categorias CASCADE;

CREATE TABLE categorias (
    id          SERIAL PRIMARY KEY,
    nombre      TEXT NOT NULL UNIQUE,
    descripcion TEXT
);

CREATE TABLE proveedores (
    id        SERIAL PRIMARY KEY,
    nombre    TEXT NOT NULL UNIQUE,
    pais      TEXT NOT NULL,
    contacto  TEXT,
    telefono  TEXT,
    email     TEXT
);

CREATE TABLE repuestos (
    id           SERIAL PRIMARY KEY,
    codigo       TEXT NOT NULL UNIQUE,
    nombre       TEXT NOT NULL,
    marca        TEXT NOT NULL,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    proveedor_id INTEGER NOT NULL REFERENCES proveedores(id),
    precio_nio   NUMERIC(12,2) NOT NULL CHECK (precio_nio >= 0),
    costo_nio    NUMERIC(12,2) NOT NULL CHECK (costo_nio >= 0),
    activo       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE modelos_vehiculo (
    id         SERIAL PRIMARY KEY,
    marca      TEXT NOT NULL,
    modelo     TEXT NOT NULL,
    anio_desde SMALLINT NOT NULL,
    anio_hasta SMALLINT NOT NULL,
    tipo       TEXT NOT NULL CHECK (tipo IN ('vehiculo', 'maquinaria', 'motocicleta')),
    CHECK (anio_hasta >= anio_desde),
    UNIQUE (marca, modelo, anio_desde)
);

-- Relación muchos a muchos: un repuesto sirve para varios modelos y viceversa.
CREATE TABLE repuesto_modelo (
    repuesto_id INTEGER NOT NULL REFERENCES repuestos(id) ON DELETE CASCADE,
    modelo_id   INTEGER NOT NULL REFERENCES modelos_vehiculo(id) ON DELETE CASCADE,
    PRIMARY KEY (repuesto_id, modelo_id)
);
CREATE INDEX ON repuesto_modelo (modelo_id);

CREATE TABLE sucursales (
    id           SERIAL PRIMARY KEY,
    nombre       TEXT NOT NULL UNIQUE,
    ciudad       TEXT NOT NULL,
    departamento TEXT NOT NULL,
    direccion    TEXT,
    telefono     TEXT
);

CREATE TABLE inventario (
    sucursal_id  INTEGER NOT NULL REFERENCES sucursales(id),
    repuesto_id  INTEGER NOT NULL REFERENCES repuestos(id),
    stock_actual INTEGER NOT NULL CHECK (stock_actual >= 0),
    stock_minimo INTEGER NOT NULL CHECK (stock_minimo >= 0),
    PRIMARY KEY (sucursal_id, repuesto_id)
);
CREATE INDEX ON inventario (repuesto_id);

-- cantidad siempre positiva; el campo tipo indica la dirección.
CREATE TABLE movimientos (
    id              BIGSERIAL PRIMARY KEY,
    repuesto_id     INTEGER NOT NULL REFERENCES repuestos(id),
    sucursal_id     INTEGER NOT NULL REFERENCES sucursales(id),
    tipo            TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida')),
    motivo          TEXT NOT NULL CHECK (motivo IN ('inventario_inicial', 'compra', 'venta', 'ajuste')),
    cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(12,2) NOT NULL CHECK (precio_unitario >= 0), -- costo si es entrada, precio de venta si es salida
    fecha           TIMESTAMPTZ NOT NULL,
    referencia      TEXT
);
CREATE INDEX ON movimientos (repuesto_id, sucursal_id);
CREATE INDEX ON movimientos (fecha);

CREATE VIEW v_stock_bajo_minimo AS
SELECT s.nombre                       AS sucursal,
       r.codigo,
       r.nombre                       AS repuesto,
       r.marca,
       c.nombre                       AS categoria,
       i.stock_actual,
       i.stock_minimo,
       i.stock_minimo - i.stock_actual AS faltante
FROM inventario i
JOIN sucursales s ON s.id = i.sucursal_id
JOIN repuestos  r ON r.id = i.repuesto_id
JOIN categorias c ON c.id = r.categoria_id
WHERE i.stock_actual < i.stock_minimo;
