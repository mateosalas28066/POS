-- 010: gastos. Categorías (lista fija administrable con seed) + gastos.
CREATE TABLE IF NOT EXISTS categorias_gasto (
    id     INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

INSERT OR IGNORE INTO categorias_gasto (id, nombre) VALUES
    (1, 'Arriendo'), (2, 'Servicios'), (3, 'Transporte'), (4, 'Nómina'), (5, 'Otros');

CREATE TABLE IF NOT EXISTS gastos (
    id                INTEGER PRIMARY KEY,
    fecha             TEXT NOT NULL,
    categoria_gasto_id INTEGER NOT NULL REFERENCES categorias_gasto(id),
    monto             DECIMAL NOT NULL,
    descripcion       TEXT,
    medio_pago_id     INTEGER NOT NULL REFERENCES medios_pago(id),
    caja_sesion_id    INTEGER REFERENCES caja_sesiones(id),
    usuario_id        INTEGER REFERENCES usuarios(id)
);
