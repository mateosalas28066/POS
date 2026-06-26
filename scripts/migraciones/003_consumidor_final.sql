-- Cliente bien-conocido para ventas sin cliente identificado (requisito DIAN).
-- Idempotente gracias al UNIQUE sobre clientes.identificacion.
INSERT OR IGNORE INTO clientes (identificacion, nombre)
VALUES ('222222222222', 'Consumidor final');
