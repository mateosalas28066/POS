-- 015_origen_nombre_movimientos.sql — NUBE2 Ola B (POS).
-- Nombre del origen de un traslado, para la bandeja de pendientes del destino: la entrada
-- pendiente tiene origen_id NULL (el origen vive en la salida del grupo, que el destino no
-- sincroniza). El pull de la nube (/sync/inventario) lo resuelve y lo baja aquí.
ALTER TABLE movimientos_ubicacion ADD COLUMN origen_nombre TEXT;
