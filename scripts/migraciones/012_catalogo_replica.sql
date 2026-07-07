-- 012_catalogo_replica.sql
-- NUBE2 Ola A: espejo RO del catálogo que el POS baja por snapshot y contra el que vende.
CREATE TABLE IF NOT EXISTS catalogo_replica (
    producto_id       INTEGER PRIMARY KEY,
    codigo_barras     TEXT,
    nombre            TEXT NOT NULL,
    unidad            TEXT NOT NULL DEFAULT 'und',
    vendido_por_peso  INTEGER NOT NULL DEFAULT 0,
    categoria_id      INTEGER,
    categoria_nombre  TEXT,
    impuesto_id       INTEGER,
    tarifa_impuesto   DECIMAL,
    precio            DECIMAL NOT NULL,
    costo             DECIMAL NOT NULL DEFAULT '0',
    activo            INTEGER NOT NULL DEFAULT 1,
    actualizado_en    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS promo_replica (
    id                 INTEGER PRIMARY KEY,
    producto_id        INTEGER NOT NULL,
    tipo_valor         TEXT NOT NULL,
    valor              DECIMAL NOT NULL,
    tipo_duracion      TEXT NOT NULL,
    activa             INTEGER NOT NULL DEFAULT 1,
    desde              TEXT,
    hasta              TEXT,
    unidades_limite    DECIMAL,
    unidades_restantes DECIMAL,
    actualizado_en     TEXT NOT NULL
);

-- Cursor genérico de sync (catálogo: última bajada; inventario: por ubicación en Ola B).
CREATE TABLE IF NOT EXISTS sync_cursor (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
