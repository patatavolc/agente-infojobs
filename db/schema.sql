DROP TABLE IF EXISTS job_offers CASCADE;
DROP TABLE IF EXISTS job_portals CASCADE;


CREATE TABLE job_portals (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  base_url VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE job_portals IS 'Catalogo de portales de empleo integrados (InfoJobs, Jooble, Adzuna, etc)';
COMMENT ON COLUMN job_portals.name IS 'Nombre del portal de empleo';
COMMENT ON COLUMN job_portals.base_url IS 'URL base del portal de empleo';
COMMENT ON COLUMN job_portals.is_active IS 'Indica si el portal de empleo está activo para busquedas';

CREATE TABLE job_offers (
  id SERIAL PRIMARY KEY,
  portal_id INTEGER NOT NULL REFERENCES job_portals(id) ON DELETE CASCADE,
  external_id VARCHAR(255) NOT NULL,
  title VARCHAR(255) NOT NULL,
  company VARCHAR(255),
  city VARCHAR(255),
  province VARCHAR(255),
  country VARCHAR(255) DEFAULT 'España',
  salary VARCHAR(255),
  description TEXT,
  url VARCHAR(1000),
  published_at TIMESTAMP,
  scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  raw_data JSONB,

  CONSTRAINT unique_offer_per_portal UNIQUE (portal_id, external_id)
);

COMMENT ON TABLE job_offers IS 'Ofertas de empleo recopiladas de múltiples portales';
COMMENT ON COLUMN job_offers.portal_id IS 'Referencia al portal de origen';
COMMENT ON COLUMN job_offers.external_id IS 'ID de la oferta en el portal original';
COMMENT ON COLUMN job_offers.title IS 'Título de la oferta';
COMMENT ON COLUMN job_offers.company IS 'Nombre de la empresa';
COMMENT ON COLUMN job_offers.city IS 'Ciudad del puesto';
COMMENT ON COLUMN job_offers.province IS 'Provincia del puesto';
COMMENT ON COLUMN job_offers.salary IS 'Salario ofrecido (puede ser rango o "No especificado")';
COMMENT ON COLUMN job_offers.description IS 'Descripción completa de la oferta';
COMMENT ON COLUMN job_offers.url IS 'URL directa a la oferta en el portal';
COMMENT ON COLUMN job_offers.published_date IS 'Fecha de publicación original';
COMMENT ON COLUMN job_offers.scraped_at IS 'Fecha en que se guardó en nuestra BD';
COMMENT ON COLUMN job_offers.updated_at IS 'Última actualización del registro';
COMMENT ON COLUMN job_offers.raw_data IS 'JSON con la respuesta completa del portal (para análisis)';

