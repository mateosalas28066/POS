-- 009: cuentas por cobrar (fiado). Medio de pago Crédito/Fiado + abonos de cliente.
INSERT OR IGNORE INTO medios_pago (id, nombre) VALUES (4, 'Crédito/Fiado');

CREATE TABLE IF NOT EXISTS abonos_cliente (
    id            INTEGER PRIMARY KEY,
    cliente_id    INTEGER NOT NULL REFERENCES clientes(id),
    monto         DECIMAL NOT NULL,
    fecha         TEXT NOT NULL,
    medio_pago_id INTEGER NOT NULL REFERENCES medios_pago(id),
    caja_sesion_id INTEGER REFERENCES caja_sesiones(id),
    usuario_id    INTEGER REFERENCES usuarios(id)
);
