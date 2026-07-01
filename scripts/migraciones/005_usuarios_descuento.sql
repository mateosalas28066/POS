-- 005: unicidad de login (usuarios.nombre) + descuento porcentual (cliente y venta).
-- El runner (inventario.db.aplicar_migraciones) aplica cada archivo una sola vez.

CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_nombre ON usuarios(nombre);

-- Descuento porcentual del cliente (fracción 0..1; 0 = sin descuento).
ALTER TABLE clientes ADD COLUMN descuento_pct DECIMAL NOT NULL DEFAULT '0';

-- Descuento porcentual aplicado a la venta (cliente o manual). Para recibo/reportes.
ALTER TABLE ventas ADD COLUMN descuento_pct DECIMAL NOT NULL DEFAULT '0';
