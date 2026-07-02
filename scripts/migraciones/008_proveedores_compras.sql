-- 008: proveedores y compras (primera parte — solo tabla proveedores).
-- El runner (inventario.db.aplicar_migraciones) aplica cada archivo una sola vez.

CREATE TABLE IF NOT EXISTS proveedores (
    id                INTEGER PRIMARY KEY,
    identificacion    TEXT NOT NULL UNIQUE,
    nombre            TEXT NOT NULL,
    contacto          TEXT,
    bloqueado_edicion INTEGER NOT NULL DEFAULT 0
);
