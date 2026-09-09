---
name: cloud-integrations
description: Integraciones con la nube y APIs externas en Python: Supabase Storage, subida y descarga de archivos, consultas REST, manejo de credenciales y autenticacion. Usar cuando el usuario pida guardar, subir, bajar o sincronizar archivos en la nube, consumir APIs externas o gestionar credenciales de servicios en la nube.
license: Apache-2.0
compatibility: opencode
metadata:
  audience: jarvis
---

# Cloud Integrations — Nube y APIs externas

Guia para trabajar con servicios en la nube y APIs externas desde la PC del
usuario. Cubre lo que ya se usa (Supabase) y lo que pueda sumarse (Dropbox,
Google Drive, APIs REST, webhooks).

## Cuando usar esta skill

- Subir, listar, bajar o borrar archivos en la nube (Supabase y similares).
- Consumir una API externa (REST, JSON) desde Python.
- Guardar o recuperar credenciales de servicios en la nube.
- Sincronizar archivos entre la PC y un servicio remoto.
- Crear o gestionar buckets/carpetas en servicios de almacenamiento.

No activarla para tareas locales sin red: eso es python-dev o automation.

## Supabase Storage (lo que ya funciona)

- Proyecto: jarvis-cloud. URL y claves en la config del script supabase.py
  (url + apikey + bucket). La clave SECRET salta el RLS y permite gestion total.
- Script operativo: `C:\Users\wasc4\Documents\Default Project\Proyectos de asistente\manos\supabase.py`. Comandos:
  `subir <archivo> <carpeta/remota>`, `listar <prefijo>`, `bajar <ruta>`,
  `borrar <ruta>`, `crear-bucket <nombre>`.
- Detalles de la API actual (importantes, cambian seguido):
  * Listar es POST a `/storage/v1/object/list/<bucket>` con body
    `{"prefix":..., "limit":..., "offset":...}` (NO es GET).
  * Borrar es DELETE a `/storage/v1/object/<bucket>` con body
    `{"prefixes": ["ruta"]}`.
  * Subir es POST a `/storage/v1/object/<bucket>/<ruta>` con el binario como body.
  * Con clave publishable NO se puede crear bucket ni subir (viola RLS);
    usar la clave SECRET desde la PC.
- Al crear un bucket nuevo: crear tambien la carpeta con el nombre exacto en
  minusculas.

## Buenas practicas con APIs externas

- Credenciales NUNCA hardcodeadas: leerlas de un archivo config local
  (como supabase_config.json) o variables de entorno.
- Timeouts siempre en las peticiones (ej. requests timeout=15) y manejo de
  errores con log claro (codigo HTTP + cuerpo si es posible).
- Reintentos con backoff para errores transitorios (502, 429, timeout).
- No volcar respuestas gigantes a memoria: procesar o guardar a archivo.
- Verificar el estado HTTP antes de dar por buena una operacion.
- Si la API cambia, actualizar el script de `manos/` y esta skill.

## Verificacion (bucle de calidad)

1. Compilar el script: `python -m py_compile script.py`.
2. Probar con una operacion real pequena (subir un archivo de prueba,
   listarlo, bajarlo, borrarlo) antes de dar por bueno.
3. Confirmar en el log que la operacion respondio 200/OK.
4. Si falla: leer el error, corregir, repetir. Solo entregar cuando una
   operacion real completa el ciclo sin errores.
5. Rutas dentro de la skill con barra normal `/`.
