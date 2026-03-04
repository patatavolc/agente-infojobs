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

-- Indices para optmizar búsquedas
CREATE INDEX idx_job_offers_portal_id ON job_offers(portal_id);
CREATE INDEX idx_job_offers_city ON job_offers(city);
CREATE INDEX idx_job_offers_province ON job_offers(province);
CREATE INDEX idx_job_offers_scrapped ON job_offers(scraped_at DESC);
CREATE INDEX idx_job_offers_title_search ON job_offers USING GIN (to_tsvector('spanish', title));
CREATE INDEX idx_job_offers_company ON job_offers(company);
CREATE INDEX idx_raw_data ON job_offers USING GIN (raw_data);

COMMENT ON INDEX idx_job_offers_title_search IS 'Índice para búsqueda rápida por título de oferta';

-- Funciones y triggers

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_column() IS 'Actualiza automáticamente el campo updated_at antes de cada UPDATE';

CREATE TRIGGER update_job_offers_updated_at
  BEFORE UPDATE ON job_offers
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_job_portals_updated_at
  BEFORE UPDATE ON job_portals
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();


-- Vistas utiles
-- Vista simplificada de ofertas con nombre del portal
CREATE OR REPLACE VIEW v_job_offers_with_portal AS
SELECT
  jo.id,
  jo.external_id,
  jp.name AS portal_name,
  jo.title,
  jo.company,
  jo.city,
  jo.province,
  jo.salary,
  jo.published_at
FROM job_offers jo
JOIN job_portals jp ON jo.portal_id = jp.id
WHERE jp.is_active = TRUE
ORDER BY jo.scraped_at DESC;

COMMENT ON VIEW v_job_offers_with_portal IS 'Vista que muestra ofertas de empleo junto con el nombre del portal de origen, filtrando solo portales activos';

-- Vista de estadisticas por portal
CREATE OR REPLACE VIEW v_stats_by_portal AS
SELECT
  jp.name AS portal,
  jp.is_active,
  COUNT(jo.id) AS total_offers,
  COUNT(DISTINCT jo.city) AS unique_cities,
  COUNT(DISTINCT jo.company) AS unique_companies,
  MAX(jo.scraped_at) AS last_scraped,
  MIN(jo.scraped_at) AS first_scraped
FROM job_portals jp
LEFT JOIN job_offers jo ON jp.id = jo.portal_id
GROUP BY jp.id, jp.name, jp.is_active
ORDER BY total_offers DESC;

COMMENT ON VIEW v_stats_by_portal IS 'Vista que muestra estadísticas de ofertas por portal, incluyendo número total de ofertas, ciudades únicas, empresas únicas y fechas de última y primera captura';