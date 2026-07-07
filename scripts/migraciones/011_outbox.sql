CREATE TABLE eventos_sync (
  uuid       TEXT PRIMARY KEY,
  local_id   TEXT NOT NULL,
  tipo       TEXT NOT NULL,
  payload    TEXT NOT NULL,            -- JSON (dinero como strings)
  creado_en  TEXT NOT NULL,
  enviado_en TEXT                      -- NULL = pendiente
);
CREATE INDEX ix_eventos_sync_pendientes ON eventos_sync (enviado_en) WHERE enviado_en IS NULL;
