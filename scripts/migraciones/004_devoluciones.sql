-- scripts/migraciones/004_devoluciones.sql
-- Devoluciones con reembolso (E6). La venta original queda inmutable; aquí vive el documento
-- de devolución (cabecera + líneas devueltas + reembolsos por medio de pago).

CREATE TABLE IF NOT EXISTS devoluciones (
    id              INTEGER PRIMARY KEY,
    venta_id        INTEGER NOT NULL REFERENCES ventas(id),
    fecha           TEXT NOT NULL,                        -- ISO-8601
    caja_sesion_id  INTEGER REFERENCES caja_sesiones(id), -- sesión del reembolso (NULLABLE)
    usuario_id      INTEGER REFERENCES usuarios(id),
    total           DECIMAL NOT NULL,
    total_impuestos DECIMAL NOT NULL,
    estado          TEXT NOT NULL DEFAULT 'emitida',
    cufe_nota       TEXT                                  -- reservado DIAN (nota crédito), sin uso fiscal hoy
);

CREATE TABLE IF NOT EXISTS devolucion_lineas (
    id              INTEGER PRIMARY KEY,
    devolucion_id   INTEGER NOT NULL REFERENCES devoluciones(id),
    venta_linea_id  INTEGER REFERENCES venta_lineas(id),
    producto_id     INTEGER NOT NULL REFERENCES productos(id),
    cantidad_o_peso DECIMAL NOT NULL,
    impuesto        DECIMAL NOT NULL,
    subtotal        DECIMAL NOT NULL
);

CREATE TABLE IF NOT EXISTS devolucion_reembolsos (
    id            INTEGER PRIMARY KEY,
    devolucion_id INTEGER NOT NULL REFERENCES devoluciones(id),
    medio_pago_id INTEGER NOT NULL REFERENCES medios_pago(id),
    monto         DECIMAL NOT NULL,
    referencia    TEXT
);
