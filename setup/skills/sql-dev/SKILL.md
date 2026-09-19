---
name: sql-dev
description: SQL y bases de datos: PostgreSQL, SQLite, esquemas y queries.
---

# sql-dev

Guia practica de SQL moderno y bases de datos relacionales (2026). Objetivo:
disenar esquemas correctos, escribir consultas eficientes y elegir la base de
datos adecuada.

## Elegir la base de datos

- PostgreSQL 18: el estandar moderno para apps (ACID completo, jsonb,
  concurrencia robusta, uuidv7, columnas generadas virtuales). Para proyectos
  nuevos con criterio tecnico libre.
- SQLite 3.5x: embebida, la mas usada del mundo; para apps de escritorio/movil,
  prototipos, lectura embebida. STRICT tables, window functions.
- MySQL/MariaDB: solo ecosistema LAMP, WordPress, hosting compartido o equipos
  que ya lo operan. MariaDB > MySQL para nuevos despliegues en esa familia.

## SQL moderno (funciona en Postgres y SQLite)

- Window functions (no agrupan, calculan sobre una ventana):
  ```sql
  SELECT nombre, salario,
         ROW_NUMBER() OVER (PARTITION BY dept_id ORDER BY salario DESC) AS rango,
         LAG(salario) OVER (PARTITION BY dept_id ORDER BY salario) AS anterior,
         SUM(salario) OVER (PARTITION BY dept_id) AS total_dept
  FROM empleados;
  ```
  ROW_NUMBER = ranking unico; RANK = empates con huecos; DENSE_RANK = sin
  huecos; LAG/LEAD = fila previa/siguiente.
- CTEs con WITH para legibilidad y recursividad:
  ```sql
  WITH recientes AS (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY autor_id ORDER BY creado_at DESC) AS n
      FROM posts
  )
  SELECT * FROM recientes WHERE n = 1;  -- ultimo post por autor
  ```
- Joins EXPLICITOS siempre (JOIN ... ON ...), nunca joins implicitos en WHERE.
  LEFT JOIN para incluir sin match; COUNT(columna) no cuenta NULLs.
- Transacciones ACID: BEGIN; ... COMMIT; (o ROLLBACK si falla).
- JSON en Postgres (jsonb): `datos->>'pais'` (texto), `datos->'meta'` (objeto),
  contención `datos @> '{"tipo":"click"}'`, indice GIN.

## Indices

- Crear en columnas de WHERE/JOIN/ORDER BY frecuentes:
  `CREATE INDEX idx_ordenes_cliente ON ordenes (cliente_id);`
  `CREATE UNIQUE INDEX idx_clientes_email ON clientes (email);`
- B-tree para igualdad/rango; GIN para jsonb y busquedas; compuestos con el
  orden correcto de columnas.
- NO indexar todo (penaliza INSERT/UPDATE), NO indices en columnas de baja
  cardinalidad (booleanos). Verificar SIEMPRE con EXPLAIN ANALYZE.

## Normalizacion

- 1NF: celdas atomicas. 2NF: sin dependencias parciales de PK compuesta.
  3NF: sin dependencias transitivas. Normalizar a 3NF salvo excepcion
  deliberada y documentada (denormalizacion por rendimiento/JSON).

## Query plans

- `EXPLAIN ANALYZE` (en PG 18 incluye BUFFERS). Buscar Seq Scan sobre tablas
  grandes (falta indice), costes estimados vs reales, Nested Loop vs Hash Join.

## Buenas practicas

- Nombres: snake_case, tablas en plural (usuarios), columnas sin prefijos,
  PK `id`, FK `tabla_id`.
- Versionar el esquema con migraciones (EF Core, Laravel migrate, Flyway).
  Nunca tocar la BD "a mano" en produccion.
- Herramientas: psql (CLI), DBeaver (GUI), DB Browser (SQLite).
- EVITAR: SELECT * en produccion, concatenar SQL (inyeccion), transacciones
  largas, tipos imprecisos.
