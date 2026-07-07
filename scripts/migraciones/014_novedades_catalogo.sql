-- 014_novedades_catalogo.sql
-- NUBE2 Ola A: registro de precios que cambiaron desde la nube, para el aviso
-- no bloqueante del POS ("N precios actualizados desde la nube"). Append-only;
-- 'visto' pasa a 1 cuando el admin revisa el aviso.
CREATE TABLE IF NOT EXISTS novedades_catalogo (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id      INTEGER NOT NULL,
    nombre           TEXT NOT NULL,
    precio_anterior  DECIMAL,
    precio_nuevo     DECIMAL NOT NULL,
    detectado_en     TEXT NOT NULL,
    visto            INTEGER NOT NULL DEFAULT 0
);
