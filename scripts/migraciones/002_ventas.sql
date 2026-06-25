-- scripts/migraciones/002_ventas.sql
-- Esquema de caja/venta (E1). DECIMAL declarado para Decimal exacto y portabilidad PostgreSQL.

-- Esquema ahora, repositorio diferido (E8 usuarios / E3 caja). Permite FK de ventas.
CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY,
    nombre        TEXT NOT NULL,
    rol           TEXT NOT NULL DEFAULT 'cajero',
    hash_password TEXT
);

CREATE TABLE IF NOT EXISTS clientes (
    id                   INTEGER PRIMARY KEY,
    identificacion       TEXT NOT NULL UNIQUE,
    nombre               TEXT NOT NULL,
    contacto             TEXT,
    bloqueado_edicion    INTEGER NOT NULL DEFAULT 0,  -- BOOL 0/1
    tipo_documento       TEXT,                        -- reservado DIAN
    regimen              TEXT,                        -- reservado DIAN
    tipo_responsabilidad TEXT                         -- reservado DIAN
);

CREATE TABLE IF NOT EXISTS medios_pago (
    id     INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

INSERT OR IGNORE INTO medios_pago (id, nombre) VALUES
    (1, 'Efectivo'), (2, 'Tarjeta'), (3, 'Transferencia');

-- Esquema ahora, repositorio diferido (E3 cierre/arqueo). Permite FK de ventas.
CREATE TABLE IF NOT EXISTS caja_sesiones (
    id             INTEGER PRIMARY KEY,
    usuario_id     INTEGER REFERENCES usuarios(id),
    apertura_fecha TEXT NOT NULL,
    monto_inicial  DECIMAL NOT NULL DEFAULT '0',
    cierre_fecha   TEXT,
    monto_contado  DECIMAL,
    estado         TEXT NOT NULL DEFAULT 'abierta'
);

CREATE TABLE IF NOT EXISTS ventas (
    id              INTEGER PRIMARY KEY,
    fecha           TEXT NOT NULL,                        -- ISO-8601
    usuario_id      INTEGER REFERENCES usuarios(id),      -- NULLABLE (E8)
    caja_sesion_id  INTEGER REFERENCES caja_sesiones(id), -- NULLABLE (E3)
    cliente_id      INTEGER REFERENCES clientes(id),      -- NULLABLE (consumidor final)
    total           DECIMAL NOT NULL,
    total_impuestos DECIMAL NOT NULL,
    estado          TEXT NOT NULL DEFAULT 'pagada'
);

CREATE TABLE IF NOT EXISTS venta_lineas (
    id              INTEGER PRIMARY KEY,
    venta_id        INTEGER NOT NULL REFERENCES ventas(id),
    producto_id     INTEGER NOT NULL REFERENCES productos(id),
    descripcion     TEXT NOT NULL,        -- snapshot del nombre para el recibo
    cantidad_o_peso DECIMAL NOT NULL,
    precio_unit     DECIMAL NOT NULL,
    impuesto        DECIMAL NOT NULL,
    subtotal        DECIMAL NOT NULL
);

CREATE TABLE IF NOT EXISTS pagos (
    id            INTEGER PRIMARY KEY,
    venta_id      INTEGER NOT NULL REFERENCES ventas(id),
    medio_pago_id INTEGER NOT NULL REFERENCES medios_pago(id),
    monto         DECIMAL NOT NULL,
    referencia    TEXT
);
