---
name: library-master
description: Elegir librerias y herramientas modernas y mantenidas.
---

# library-master

Catalogo viviente de las librerias y herramientas mas modernas y funcionales
(actualizado a 2026). Objetivo: nunca usar una libreria vieja o abandonada
cuando existe una opcion moderna, mantenida y mejor.

## Como usar esta skill

1. Antes de crear codigo, buscar la categoria del problema en `REFERENCE.md`.
2. Tomar la RECOMENDACION PRINCIPAL de esa categoria (es la opcion moderna).
3. Si la categoria no esta, consultar el Stack por defecto (abajo) o investigar
   en Internet: awesome lists de GitHub (vinta/awesome-python, sindresorhus/awesome),
   PyPI (pypi.org), npm (npmjs.com) y pypistats para descargas. Criterio de
   seleccion: mantenimiento activo (releases recientes), descargas altas,
   ecosistema vivo, y que resuelva el problema sin friccion.
4. Verificar version actual con `pip index versions <paquete>` o `npm view <paquete> version`.
5. Al elegir, preferir lo que ya este instalado o sea mas simple si la tarea es trivial.

## Criterios para considerar una libreria "moderna"

- Releases recientes (ultimos 6 meses) y proyecto activo en GitHub.
- Altas descargas mensuales (pypistats.org / npm trends).
- API moderna: type hints, async nativo, sin dependencias muertas.
- Reemplaza a una alternativa vieja (ej. httpx reemplaza requests; uv reemplaza pip+poetry).
- Cuidado con librerias en "modo mantenimiento" o archivadas: requests, piper,
  pyautogui (casi parada), AutoGen (modo mantenimiento), LangChain clasico.

## Stack por defecto 2026 (decision rapida)

- Gestor de proyectos/entornos: uv (reemplaza pip, poetry, virtualenv).
- Lint y formato: ruff. Tipos: pyright. Testing: pytest.
- HTTP: httpx (sync y async). Web API: FastAPI.
- Datos: Polars (+ DuckDB para SQL analitico, pandas 3.0 solo por compatibilidad).
- Validacion: pydantic v2. Config: pydantic-settings.
- ORM: SQLAlchemy 2.0 (SQLModel solo en ecosistema FastAPI). Postgres: psycopg3.
- IA/agentes: LiteLLM + Pydantic AI; LangGraph si el flujo es complejo y durable.
- Voz local: Kokoro (TTS) + faster-whisper (STT).
- Bots Telegram Python: aiogram 3 o python-telegram-bot v21+. Node: grammY.
- CLI Python: Typer + Rich. Automatizacion Windows: pywinauto (backend uia) + pyautogui.
- Node: runtime Node LTS 24, backend Fastify o Hono, ORM Drizzle, validacion zod,
  logger pino, gestor pnpm, linter Biome.
- Desktop moderno: Tauri 2 (no Electron, salvo necesidad de Chromium completo).

## Reglas

- Para detalles, versiones, alternativas y "cuando usar cada una", leer `REFERENCE.md`.
- Si la tarea necesita una categoria no cubierta, investigar en Internet antes de
  inventar; el catalogo se actualiza con los hallazgos verificados.
- No inventar versiones: si no se puede verificar, indicar el nombre del paquete
  correcto y recomendar verificar con pip/npm.
- Esta skill se combina con python-dev, bot-builder y automation: usar el
  conocimiento de librerias aqui documentado dentro de esas tareas.
