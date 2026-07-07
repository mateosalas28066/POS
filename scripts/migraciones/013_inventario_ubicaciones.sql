-- 013_inventario_ubicaciones.sql — NUBE2 Ola B (POS).
CREATE TABLE IF NOT EXISTS ubicaciones (
    id       INTEGER PRIMARY KEY,
    nombre   TEXT NOT NULL,
    tipo     TEXT NOT NULL DEFAULT 'local',   -- 'bodega'|'local'
    local_id TEXT,
    activo   INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS movimientos_ubicacion (
    uuid           TEXT PRIMARY KEY,
    tipo           TEXT NOT NULL,             -- entrada|salida|ajuste|traslado|conversion
    producto_id    INTEGER NOT NULL,
    cantidad       DECIMAL NOT NULL,
    origen_id      INTEGER,
    destino_id     INTEGER,
    estado         TEXT NOT NULL DEFAULT 'confirmado',  -- confirmado|pendiente
    grupo_uuid     TEXT,
    lote_id        INTEGER,
    ref            TEXT,
    fecha          TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_mov_ubic_dest ON movimientos_ubicacion (destino_id);
CREATE INDEX IF NOT EXISTS ix_mov_ubic_orig ON movimientos_ubicacion (origen_id);
