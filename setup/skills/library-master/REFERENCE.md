# REFERENCE — Catalogo de librerias modernas 2026

Indice:
1. Frameworks web y HTTP
2. Asincronia, validacion y datos
3. Bases de datos
4. Dataframes y analitica
5. ML y ciencia de datos
6. IA, LLMs y agentes
7. Embeddings y vector search
8. Voz y audio (TTS/STT)
9. CLIs y TUIs
10. Automatizacion de sistema (Windows)
11. Procesos, tareas y archivos
12. Red, descargas, networking y MQTT
13. Seguridad y secretos
14. Empaquetado y tooling
15. Node.js / JavaScript
16. Bots Telegram/Discord
17. Frontend y desktop
18. Tabla resumen por categoria

---

## 1. Frameworks web y HTTP

RECOMENDACION: FastAPI + httpx.

- FastAPI (v0.141, verificada 15/08/2026): estandar moderno para APIs. Type hints, validacion Pydantic v2,
  docs OpenAPI gratis, async nativo. Para cualquier API/backend nuevo.
- Starlette: toolkit ASGI base (lo usa FastAPI). Solo si quieres minimo control directo.
- Litestar (v2.2x): alternativa full-stack ASGI con DI y serializacion integradas.
- Flask (v3.1): micro-framework sincrono clasico. Solo apps pequenas o legacy.
- Django (v6.1): full-stack (admin, ORM, auth). Para sitios web completos, requiere Py 3.12+.
- httpx (v0.28.1, verificada 15/08/2026): cliente HTTP de nueva generacion. API compatible con requests pero
  sync Y async, HTTP/2, timeouts estrictos. Usar para TODO cliente HTTP nuevo.
- requests (v2.3x): en modo mantenimiento. Solo legacy.
- aiohttp (v3.1x): solo si necesitas servidor HTTP/WebSocket async.

## 2. Asincronia, validacion y datos

RECOMENDACION: asyncio + anyio, pydantic v2.

- asyncio: base oficial del lenguaje.
- anyio (v4.1x): capa de abstraccion sobre asyncio/trio; la usan FastAPI, httpx,
  Litestar. Para librerias, usar anyio como API publica.
- uvloop (v0.2x): acelera el event loop ~2x (uvicorn lo usa en produccion).
- trio: buen diseno pero ecosistema pequeno. Solo si se prefiere.
- pydantic v2 (v2.1x): validacion+serializacion, motor Rust (5-50x mas rapido que v1).
  Estandar de facto (FastAPI, OpenAI SDK, SQLModel). Para fronteras de datos (API, config, LLM).
- msgspec (v0.2x): serializacion ultrarapida (JSON/MessagePack/YAML/TOML). Si necesitas
  maxima velocidad de serializacion.
- attrs (v26.x): clases de dominio interno, mas ligero que pydantic, con slots.
- dataclasses (stdlib): contenedores simples sin validacion.

## 3. Bases de datos

RECOMENDACION: SQLAlchemy 2.0 + psycopg3; SQLite nativo para prototipos.

- SQLAlchemy 2.0 (v2.0.5x): ORM estandar, API tipada, sesiones async. Por defecto.
- SQLModel (v0.0.3x): SQLAlchemy + Pydantic, solo dentro del ecosistema FastAPI.
- psycopg (psycopg3, v3.3): driver oficial de Postgres, sync y async. El que recomienda SQLAlchemy.
- asyncpg (v0.3x): driver async puro de Postgres, maximo rendimiento sin ORM.
- sqlite3 (stdlib, SQLite 3.4x): embebido; usar autocommit, check_same_thread=False, URIs.
- TinyDB (v4.9): mini-BBDD JSON para prototipos, no produccion.
- Redis: cache/colas (redis-py). MongoDB: pymongo o Beanie (ODM async).
- DuckDB: OLAP analitico embebido sobre ficheros/Parquet.

## 4. Dataframes y analitica

RECOMENDACION: Polars para codigo nuevo; DuckDB para SQL analitico; pandas 3.0 por compatibilidad.

- Polars (v1.43, verificada 15/08/2026): Rust, 3-11x mas rapido que pandas, evaluacion perezosa, streaming, API 1.x estable.
  Para proyectos nuevos y datos grandes.
- pandas 3.0 (abril 2026): backend Arrow por defecto, copy-on-write, mas rapido.
  Para proyectos existentes e interoperar con scikit-learn/geopandas.
- DuckDB: SQL OLAP in-process superrapido sobre Parquet/CSV; zero-copy con Polars/pandas.
- PyArrow: formato columnar, la infraestructura de interoperabilidad estandar.

## 5. ML y ciencia de datos

RECOMENDACION: scikit-learn para pipelines, LightGBM para tabular en produccion.

- scikit-learn (v1.7): API estandar de ML clasico.
- LightGBM (serie 4.x): el GBDT mas rapido, default para tabular en produccion.
- XGBoost (3.x): excelente, compatibilidad/distribuido.
- CatBoost: manejo nativo de categoricas sin preprocesado.
- TabPFN: modelo fundacional para tabulares, SOTA en datasets pequenos/medianos
  (pesos v3 bajo licencia no comercial).

## 6. IA, LLMs y agentes

RECOMENDACION: LiteLLM (acceso a modelos) + Pydantic AI (agente validado);
LangGraph si el flujo es complejo, durable y multi-paso. MCP como estandar de herramientas.

- LiteLLM: una API estilo OpenAI para 100+ proveedores. Capa base de portabilidad.
- Pydantic AI (v1.0): agente type-safe, valida cada respuesta contra tu schema,
  mas barato que CrewAI. Single-agent. El recomendado para Python de produccion.
- LangGraph (v1.0): grafo de estado con checkpoints (SQLite/Postgres), crash recovery,
  human-in-the-loop. El mas descargado. Para flujos complejos.
- OpenAI Agents SDK: minimalista (5 primitivas), sin persistencia de estado.
- Anthropic Claude Agent SDK: harness de Claude Code, MCP nativo, atado a Claude.
- agno (antes phidata): ligero, alternativa simple a LangChain.
- smolagents (HuggingFace): ultra-ligero, agente que escribe codigo.
- DSPy: programar, no hacer prompt; optimiza pipelines automaticamente.
- PASARON DE MODA: AutoGen (modo mantenimiento, heredero AG2), LangChain clasico,
  CrewAI (costos altos y control cuestionado).

## 7. Embeddings y vector search

RECOMENDACION: sentence-transformers + pgvector si ya hay Postgres; Qdrant para
servicio dedicado; Chroma para prototipos.

- sentence-transformers: embeddings y rerankers, 15k+ modelos en HuggingFace.
- pgvector: extension de Postgres, vectores + datos relacionales en una BD. Default si ya hay Postgres.
- qdrant-client: servidor vectorial en Rust, filtros complejos, busqueda hibrida. Produccion a escala.
- Weaviate: BD vectorial con modulos LLM integrados, mas pesada.
- ChromaDB: embebida, "el SQLite de las vectoriales", ideal para desarrollo.
- FAISS: libreria de indices en memoria (no es una BD; sin persistencia).

## 8. Voz y audio (TTS/STT)

RECOMENDACION: Kokoro (TTS local) + faster-whisper (STT).

- Kokoro (v0.9.4, verificada 15/08/2026): TTS local, 82M params, Apache-2.0, calidad top, multilingue (espanol incluido).
  Default moderno para TTS local. `pip install kokoro`. Tambien kokoro.js en navegador.
- Piper: repo archivado en oct 2025; sigue valido para embebidos pero ya no es la de moda.
- faster-whisper: STT hasta 4x mas rapido que openai-whisper, menos memoria, VAD integrado,
  sin FFmpeg. Default para transcripcion.
- whisper.cpp: Whisper en C++, para edge/CPU minima.
- openai-whisper: la implementacion original, lenta. Solo referencia.
- Vosk: STT offline ligero, calidad inferior a Whisper.
- edge-tts: TTS online gratis con voces neurales Microsoft, sin API key, requiere red.

## 9. CLIs y TUIs

RECOMENDACION: Typer + Rich para el 95% de CLIs; Textual para apps TUI.

- Typer (v0.27): CLIs desde type hints, genera --help y validacion. Depende de Rich.
  Default para CLIs nuevos.
- Click (8.x): base de Typer, mas verboso. Para proyectos existentes.
- argparse (stdlib): scripts de 1 archivo sin dependencias.
- Rich (v15): tablas, progreso, paneles, colores. Estandar de output bonito.
- Textual (v8.x): TUIs interactivas (apps de terminal tipo htop).

## 10. Automatizacion de sistema (Windows)

RECOMENDACION: pywinauto (backend uia) + pyautogui + psutil.

- pywinauto (v0.6.9): automatizar ventanas y controles GUI de Windows. Backends win32
  (nativas) y uia (modernas: WinUI, .NET, Electron). Capa principal de GUI automation.
- pyautogui (v0.9.54): raton/teclado global + screenshots + locateOnScreen.
  Mantenimiento casi parado pero funcional; para macros simples.
- pygetwindow: gestionar ventanas (buscar, activar, redimensionar). Complemento de pyautogui.
- pydirectinput: raton/teclado por DirectInput (juegos).
- pywin32 / comtypes: automatizacion COM (Excel, Word, Outlook, Office).
- psutil (v7.x): procesos y sistema (CPU/RAM/disco, matar procesos). Cross-platform.
- keyboard/mouse: hotkeys globales (pueden requerir admin y alertar al antivirus).
- wmi: consultas WMI avanzadas (psutil ya cubre lo comun).

## 11. Procesos, tareas y archivos

RECOMENDACION: APScheduler 3.x dentro de la app; arq para colas async; subprocess+psutil para procesos.

- subprocess (stdlib) + psutil: lanzar y controlar procesos.
- schedule (v1.2): cron simple en el mismo proceso, sin persistencia.
- APScheduler (v3.11): scheduler en-proceso con cron e intervalos, jobs persistentes.
  Usar 3.x (la v4 sigue en alpha).
- Celery (v5.6): cola distribuida madura (Redis/RabbitMQ), pesado, sincroniza mal con asyncio.
- arq (v0.28): cola async + Redis, del autor de pydantic. La opcion moderna para stack asyncio.
- dramatiq (v2.2): cola simple sin el peso de Celery.
- pathlib (stdlib): rutas, EL estandar. Siempre.
- watchfiles (v1.2): vigilar archivos, reescritura Rust del autor de pydantic, async nativa. Moderna.
- watchdog (v6.0): mas clasico, API sincrona.
- send2trash: borrar a la papelera (borrado reversible).
- shutil (stdlib): copiar/mover/zip arboles.

## 12. Red, descargas, networking y MQTT

RECOMENDACION: httpx, yt-dlp, websockets, paho-mqtt.

- httpx: cliente HTTP sync y async (ver seccion 1).
- requests: solo legacy.
- yt-dlp (v2026.x): descargar audio/video de 1000+ sitios, releases casi semanales. Usar como libreria tambien.
- aiofiles (v25.x): E/S de archivos async sin bloquear el loop.
- paramiko: SFTP (estandar de facto).
- websockets: cliente/servidor WebSocket estandar.
- paho-mqtt (v2.1): MQTT 3.1.1/5.0, estandar de facto (IoT, domotica).
- gmqtt: MQTT asyncio puro pero con adopcion minima.

## 13. Seguridad y secretos

RECOMENDACION: argon2-cffi para passwords; cryptography para cifrado; keyring para secretos del SO; pydantic-settings para .env.

- argon2-cffi (v25.x): Argon2, el algoritmo recomendado hoy (mejor que bcrypt). Passwords nuevas.
- bcrypt (v5.0): clasico, mantenido, pero Argon2 es superior.
- cryptography (v50.x): cifrado simetrico, TLS, firmas, KDFs. El estandar moderno (~1500 M/mes).
- keyring (v25.x): guarda secretos en el almacen del SO (Credential Manager en Windows).
- pydantic-settings (v2.15): config tipada desde .env/entorno con validacion. La opcion moderna.
- python-dotenv (v1.2): solo cargar .env, sin validacion. Base de pydantic-settings.

## 14. Empaquetado y tooling

RECOMENDACION: uv + ruff + pyright + pytest.

- uv (v0.12.5, verificada 15/08/2026): reemplaza pip, pip-tools, pipx, poetry, pyenv y virtualenv. 10-100x mas rapido,
  lockfile universal, gestiona versiones de Python. TODO proyecto nuevo.
- ruff (v0.16): linter + formateador en Rust, reemplaza flake8+black+isort. Siempre.
- pyright: chequeo de tipos (Microsoft), mas rapido que mypy. Proyectos nuevos.
- mypy: el clasico, mas lento. Proyectos existentes.
- pytest: estandar de testing (con pytest-asyncio, pytest-cov).
- hatch (v1.18): project management + build backend hatchling.
- poetry (v2.4): sigue vivo pero perdio traccion frente a uv.
- pip-tools: solo workflows legacy con requirements.txt.

## 15. Node.js / JavaScript

RECOMENDACION: Node 24 LTS + Fastify (o Hono para edge) + Drizzle + zod + pino + pnpm + Biome + bun.

- Node LTS 24 "Krypton" (produccion); Node 26 Current; Node 20 EOL (marzo 2026).
- Bun: runtime + bundler + test runner + package manager en un binario, muy rapido en dev.
- Deno: TS nativo, menos adopcion.
- Fastify: estandar moderno para APIs Node clasicas, plugin-based, type-safe.
- Hono: ultrafast, basado en Web Standards, corre en Workers/Deno/Bun/Lambda/Node. De moda para edge.
- Express: legacy (sin TS de primera clase). No para nuevo.
- NestJS: arquitectura empresarial (DI, modulos) para equipos grandes.
- Drizzle: headless ORM, type-safe total, 0 dependencias, serverless-ready. Ganador moderno.
- Prisma: mas usado por DX tipo framework, pero pesado y con capa de indireccion.
- Kysely: query builder type-safe sin ORM.
- zod (v4): validacion de esquemas, estandar de facto.
- pino: logger JSON de alto rendimiento.
- Node 20+ tiene --env-file nativo; Bun lee .env solo.
- pnpm: 2x mas rapido, almacen content-addressable, ideal monorepos. npm para cero setup.
- Biome: formateador + linter en Rust, 97% compatible con Prettier. eslint+prettier si necesitas plugins.
- npx/bunx: ejecutar binarios sin instalar.

## 16. Bots Telegram/Discord

RECOMENDACION: Python -> aiogram 3 o python-telegram-bot v21+; Node -> grammY; Discord -> discord.js / discord.py.

- aiogram 3 (v3.30, verificada 15/08/2026): async, Blueprints, FSM, magic filters, middlewares. Framework moderno.
- python-telegram-bot v21+: async desde v20, gran comunidad, madurez, type-safe.
- grammY: TypeScript, plugins oficiales, corre en Node/Deno/Cloudflare Workers. Moderno.
- telegraf: fue el estandar, pierde mantenimiento frente a grammY.
- node-telegram-bot-api: viejo, callback style, mantenimiento minimo.
- discord.js (Node) / discord.py (Python): Discord.

## 17. Frontend y desktop

RECOMENDACION: Astro (simple/estatico), SvelteKit o Vue+Vite (medio), Next.js/React (complejo); Tauri 2 para desktop.

- React 19 / Next.js: Server Components, Actions, compilador automatico. Ecosistema mas grande,
  pero el mas pesado para apps simples.
- Svelte 5 / SvelteKit: runes, compila a poco JS, curva suave. Simple a mediana.
- Vue 3 / Vite: equilibrio facil y popular.
- Astro: cero JS por defecto + islands; para blogs, docs, landing. Puede embeker React/Svelte/Vue.
- Solid: maximo rendimiento reactivo, ecosistema pequeno (nicho).
- Vite: build tool universal (salvo Next).
- Electron: maduro (VS Code, Slack) pero 100-200 MB y alto consumo RAM.
- Tauri 2: webview del sistema, binarios ~10 MB, backend Rust, soporta movil. La opcion moderna
  para apps ligeras. Requiere Rust para backend nativo.

## 18. Tabla resumen por categoria

- Web API: FastAPI. HTTP: httpx. Async: asyncio+anyio.
- Validacion: pydantic v2. Config: pydantic-settings.
- ORM: SQLAlchemy 2.0. Postgres driver: psycopg3.
- Dataframes: Polars. SQL analitico: DuckDB.
- ML tabular: LightGBM. Pipelines: scikit-learn.
- Agentes/IA: LiteLLM + Pydantic AI (+ LangGraph si complejo).
- Embeddings: sentence-transformers. Vector DB: pgvector/Qdrant/Chroma.
- TTS local: Kokoro. STT: faster-whisper. TTS online: edge-tts.
- CLI: Typer+Rich. TUI: Textual.
- Windows GUI automation: pywinauto (uia). Raton/teclado: pyautogui. Procesos: psutil.
- Scheduler: APScheduler 3.x. Colas async: arq. Colas clasicas: Celery.
- File watching: watchfiles. Papelera: send2trash.
- Descargas: yt-dlp. MQTT: paho-mqtt. WebSocket: websockets.
- Passwords: argon2-cffi. Cifrado: cryptography. Secretos: keyring.
- Empaquetado: uv. Lint: ruff. Tipos: pyright. Tests: pytest.
- Node: Fastify/Hono + Drizzle + zod + pino + pnpm + Biome.
- Bots: aiogram 3 / PTB v21 (Python), grammY (Node).
- Desktop: Tauri 2.
