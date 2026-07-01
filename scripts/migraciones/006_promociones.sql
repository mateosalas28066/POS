-- 006: promociones por producto + vínculo de la línea de venta a la promo aplicada.
-- El runner (inventario.db.aplicar_migraciones) aplica cada archivo una sola vez.

CREATE TABLE IF NOT EXISTS promociones (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id        INTEGER NOT NULL REFERENCES productos(id),
    tipo_valor         TEXT NOT NULL,          -- 'precio_fijo' | 'porcentaje'
    valor              DECIMAL NOT NULL,       -- pesos (fijo) o fracción (porcentaje)
    tipo_duracion      TEXT NOT NULL,          -- 'tiempo' | 'unidades' | 'manual'
    activa             INTEGER NOT NULL DEFAULT 1,
    desde              TEXT,                   -- ISO datetime (tipo 'tiempo')
    hasta              TEXT,                   -- ISO datetime (tipo 'tiempo')
    unidades_limite    DECIMAL,
    unidades_restantes DECIMAL
);

ALTER TABLE venta_lineas ADD COLUMN promocion_id INTEGER REFERENCES promociones(id);
