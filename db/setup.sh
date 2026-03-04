#!/bin/bash

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DB_NAME="jobsdb"
DB_USER="postgres"

echo -e "${YELLOW}🗄️  Configurando base de datos para el agente InfoJobs...${NC}\n"

# 1. Crear la base de datos si no existe
echo -e "${YELLOW}📦 Paso 1: Creando base de datos '${DB_NAME}'...${NC}"
psql -U $DB_USER -c "CREATE DATABASE $DB_NAME;" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Base de datos creada exitosamente${NC}\n"
else
    echo -e "${YELLOW}⚠️  La base de datos ya existe (continuando...)${NC}\n"
fi

# 2. Ejecutar el schema
echo -e "${YELLOW}📋 Paso 2: Ejecutando schema.sql...${NC}"
psql -U $DB_USER -d $DB_NAME -f schema.sql

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Schema ejecutado exitosamente${NC}\n"
else
    echo -e "${RED}❌ Error ejecutando schema.sql${NC}\n"
    exit 1
fi

# 3. Cargar datos iniciales
echo -e "${YELLOW}🌱 Paso 3: Cargando datos iniciales...${NC}"
psql -U $DB_USER -d $DB_NAME -f seed_data.sql

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Datos iniciales cargados${NC}\n"
else
    echo -e "${RED}❌ Error cargando datos iniciales${NC}\n"
    exit 1
fi

# 4. Verificar instalación
echo -e "${YELLOW}🔍 Verificando instalación...${NC}"
psql -U $DB_USER -d $DB_NAME -c "\dt" -c "SELECT * FROM job_portals;"

echo -e "\n${GREEN}🎉 ¡Base de datos configurada correctamente!${NC}"
echo -e "${GREEN}   Tablas creadas: job_portals, job_offers${NC}"
echo -e "${GREEN}   Portales cargados: 3 (InfoJobs, Jooble, Adzuna)${NC}"