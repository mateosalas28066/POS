-- 007: movimientos manuales de efectivo (ingresos/egresos) dentro de una sesión de caja.
-- El runner (inventario.db.aplicar_migraciones) aplica cada archivo una sola vez.

CREATE TABLE IF NOT EXISTS caja_movimientos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    caja_sesion_id INTEGER NOT NULL REFERENCES caja_sesiones(id),
    usuario_id     INTEGER REFERENCES usuarios(id),
    tipo           TEXT NOT NULL,      -- 'ingreso' | 'egreso'
    monto          DECIMAL NOT NULL,   -- siempre positivo; el signo lo da el tipo
    motivo         TEXT NOT NULL,
    fecha          TEXT NOT NULL       -- ISO datetime
);
