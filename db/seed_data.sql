-- Datoss iniciales - Portales de Empleo

INSERT INTO job_portals (name, url) VALUES
  ('InfoJobs', 'https://api.infojobs.net/api/9'),
  ('Jooble', 'https://jooble.org/api'),
  ('Adzuna', 'https://api.adzuna.com/v1/api')
ON CONFLICT (name) DO NOTHING;

-- Verificar los portales insertados
SELECT
  id,
  name,
  base_url,
  is_active,
  created_at,
FROM job_portals
ORDER BY id;
