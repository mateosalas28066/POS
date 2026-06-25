-- scripts/migraciones/001_inventario.sql
-- Esquema inicial de inventario (E2). Tipos DECLARADOS para portabilidad SQLite->PostgreSQL.

CREATE TABLE IF NOT EXISTS categorias (
    id     INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS impuestos (
    id          INTEGER PRIMARY KEY,
    nombre      TEXT NOT NULL,
    tarifa      DECIMAL NOT NULL,
    codigo_dian TEXT            -- reservado DIAN
);

CREATE TABLE IF NOT EXISTS productos (
    id               INTEGER PRIMARY KEY,
    codigo_barras    TEXT NOT NULL UNIQUE,
    nombre           TEXT NOT NULL,
    precio           DECIMAL NOT NULL,
    costo            DECIMAL NOT NULL DEFAULT '0',
    categoria_id     INTEGER REFERENCES categorias(id),
    impuesto_id      INTEGER REFERENCES impuestos(id),
    vendido_por_peso INTEGER NOT NULL DEFAULT 0,  -- BOOL: 0/1
    unidad           TEXT NOT NULL DEFAULT 'und'
);

-- Definida ahora (carnicería/fruver la exigirá); código diferido (sin repositorio aún).
CREATE TABLE IF NOT EXISTS lotes (
    id                INTEGER PRIMARY KEY,
    producto_id       INTEGER NOT NULL REFERENCES productos(id),
    lote              TEXT NOT NULL,
    fecha_vencimiento TEXT,                        -- ISO-8601
    cantidad          DECIMAL NOT NULL DEFAULT '0'
);

CREATE TABLE IF NOT EXISTS inventario_movimientos (
    id          INTEGER PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    lote_id     INTEGER REFERENCES lotes(id),
    tipo        TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida')),
    cantidad    DECIMAL NOT NULL,
    fecha       TEXT NOT NULL,                     -- ISO-8601
    ref         TEXT
);
