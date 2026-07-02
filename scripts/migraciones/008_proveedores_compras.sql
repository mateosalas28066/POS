-- 008: proveedores y compras (primera parte — solo tabla proveedores).
-- El runner (inventario.db.aplicar_migraciones) aplica cada archivo una sola vez.

CREATE TABLE IF NOT EXISTS proveedores (
    id                INTEGER PRIMARY KEY,
    identificacion    TEXT NOT NULL UNIQUE,
    nombre            TEXT NOT NULL,
    contacto          TEXT,
    bloqueado_edicion INTEGER NOT NULL DEFAULT 0
);

-- Despiece: encabezado + líneas (prorrateo del costo del canal entre cortes).
CREATE TABLE IF NOT EXISTS despieces (
    id                INTEGER PRIMARY KEY,
    producto_canal_id INTEGER NOT NULL REFERENCES productos(id),
    peso_canal        DECIMAL NOT NULL,
    costo_canal       DECIMAL NOT NULL,
    fecha             TEXT NOT NULL,
    usuario_id        INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS despiece_lineas (
    id               INTEGER PRIMARY KEY,
    despiece_id      INTEGER NOT NULL REFERENCES despieces(id),
    producto_corte_id INTEGER NOT NULL REFERENCES productos(id),
    peso             DECIMAL NOT NULL,
    costo_asignado   DECIMAL NOT NULL,
    costo_unit       DECIMAL NOT NULL
);

-- Compras: encabezado + líneas. estado 'pagada'|'credito' (crédito lo lee CxP en Fase 3).
CREATE TABLE IF NOT EXISTS compras (
    id           INTEGER PRIMARY KEY,
    proveedor_id INTEGER NOT NULL REFERENCES proveedores(id),
    fecha        TEXT NOT NULL,
    total        DECIMAL NOT NULL,
    estado       TEXT NOT NULL DEFAULT 'pagada',
    usuario_id   INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS compra_lineas (
    id          INTEGER PRIMARY KEY,
    compra_id   INTEGER NOT NULL REFERENCES compras(id),
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    descripcion TEXT NOT NULL,
    cantidad    DECIMAL NOT NULL,
    costo_unit  DECIMAL NOT NULL,
    subtotal    DECIMAL NOT NULL
);
