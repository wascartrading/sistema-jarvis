---
name: skill-authoring
description: Crea y mejora skills de opencode siguiendo el estandar Agent Skills y las mejores practicas de autor (basado en la guia oficial de Anthropic y la documentacion de opencode). Usar cuando se vaya a crear, redisenar, fusionar, depurar o auditar cualquier skill, incluidas las de este proyecto.
license: Apache-2.0
compatibility: opencode
---

# Autor de Skills

Guia maestra para crear skills de calidad. Se aplica a CUALQUIER skill de este
proyecto (jarvis, python-dev, bot-builder, automation y las nuevas).

## 1. Formato obligatorio

Cada skill es una carpeta con `SKILL.md` dentro, en `.opencode/skills/<nombre>/`.
El archivo empieza con frontmatter YAML. Campos reconocidos:

- `name` (obligatorio): 1-64 caracteres, minusculas alfanumericas con guiones
  simples, sin guiones al inicio/final ni `--` consecutivos. Debe coincidir con
  el nombre de la carpeta. Regex: `^[a-z0-9]+(-[a-z0-9]+)*$`
- `description` (obligatorio): 1-1024 caracteres. Debe decir QUE hace la skill
  y CUANDO usarla. En TERCERA persona (nunca "yo puedo" ni "tu puedes").
- `license`, `compatibility`, `metadata` (opcionales).

## 2. Reglas de la descripcion (clave para que me activen)

La description es lo unico que veo al arrancar para decidir si cargo la skill.
Debe ser especifica e incluir terminos de disparo.

Ejemplo bueno: "Analiza hojas de Excel, crea tablas dinamicas y genera graficos.
Usar al analizar archivos .xlsx o datos tabulares."
Ejemplo malo: "Ayuda con documentos" / "Procesa datos" / "Hace cosas con archivos".

NUNCA en primera persona: es texto que se inyecta en el system prompt.

## 3. Principio de concision

Solo anade contexto que yo no tenga ya. Desafiar cada linea:
- "Realmente necesito esta explicacion?"
- "Puedo asumir que ya lo se?"
- "Esta parrafo justifica su costo de tokens?"

SKILL.md debe quedar bajo 500 lineas. Si se pasa, dividir en archivos de
referencia que se cargan solo cuando se necesitan (progressive disclosure).

## 4. Grados de libertad (cuanto detalle)

Ajustar la especificidad al riesgo de la tarea:

- ALTA libertad (instrucciones de texto): tareas con varias soluciones validas
  o que dependen del contexto. Ej: revision de codigo.
- MEDIA libertad (pseudocodigo o plantillas con parametros): hay un patron
  preferido pero se adapta. Ej: generar reportes.
- BAJA libertad (scripts exactos, pocos parametros): operaciones fragiles que
  deben hacerse SIEMPRE igual. Ej: migraciones de BD, comandos de despliegue.

Analogia: puente angosto con precipicios -> instrucciones exactas y
guardarrailes; campo abierto sin peligros -> direccion general.

## 5. Progressive disclosure (cargar solo lo necesario)

SKILL.md es el indice; los detalles viven en archivos que se leen bajo demanda.

Estructura recomendada:
```
mi-skill/
├── SKILL.md          # indice + guia rapida (se carga al activar)
├── REFERENCE.md      # API completa / detalles (bajo demanda)
├── EXAMPLES.md       # ejemplos (bajo demanda)
└── scripts/          # codigo ejecutable (se ejecuta, no se lee)
```

Reglas:
- Referencias UN NIVEL de profundidad desde SKILL.md (nada de enlazar a un
  archivo que enlaza a otro: puedo leerlo a medias).
- Archivos de referencia largos (>100 lineas): indice/tabla de contenidos arriba.
- Nombres descriptivos: `form_validation_rules.md`, no `doc2.md`.
- Rutas SIEMPRE con barra normal `/` (nunca backslash, ni en Windows).
- Scripts para operaciones deterministicas: ejecutar en vez de generar codigo.

## 6. Flujo de trabajo y bucles de retroalimentacion

- Tareas complejas: pasos secuenciales claros + checklist que puedo copiar y
  marcar mientras avanzo.
- Patron "validar-corregir-repetir": ejecutar validador, arreglar errores,
  volver a ejecutar. Solo seguir cuando pasa.

## 7. Lo que se debe EVITAR

- Info sensible al tiempo que quedara desactualizada (usar seccion "Patrones
  antiguos" si hace falta contexto historico).
- Terminologia inconsistente: elegir un termino y usarlo siempre.
- Demasiadas opciones: dar UNO por defecto con escape hatch.
- Nombres vagos: `helper`, `utils`, `tools`, `documents`, `data`.
- Constantes magicas sin justificar (Ousterhout): cada numero debe explicarse.
- Asumir paquetes instalados: escribir el paso de instalacion si hace falta.
- Referencias MCP sin nombre completo del servidor: usar `Servidor:herramienta`.
- Asumir que las tools existen: declarar dependencias explicitamente.

## 8. Ciclo de creacion/mejora (Claude A / Claude B)

1. Completar una tarea SIN skill y anotar que contexto repeti.
2. Identificar el patron reutilizable (tablas, convenciones, reglas, filtros).
3. Crear la skill que capture ese patron (yo la escribo directamente).
4. Revisar concision: quitar explicaciones que yo ya se.
5. Probar con tareas reales similares y observar si encuentro la info, aplico
   las reglas y completo el trabajo.
6. Iterar con observaciones concretas: si olvido algo, hacer la regla mas
   prominente o usar lenguaje fuerte ("DEBE filtrar por fecha").
7. Evaluar con al menos tres escenarios representativos antes de dar por buena.

## 9. Checklist final antes de publicar una skill

- [ ] name valido (minusculas + guiones, coincide con carpeta)
- [ ] description especifica, con terminos de disparo, en tercera persona
- [ ] SKILL.md bajo 500 lineas
- [ ] Detalles extra en archivos separados, un nivel de profundidad
- [ ] Sin info desactualizada ni fechas de caducidad
- [ ] Terminologia consistente
- [ ] Ejemplos concretos, no abstractos
- [ ] Flujo con pasos claros y validacion cuando la tarea es critica
- [ ] Rutas con barra normal
- [ ] Scripts que resuelven (con manejo de errores), no que difieren
- [ ] Probada con tareas reales antes de confiar en ella

## 10. Context engineering (lecciones de Anthropic, 15/08/2026)

Principios aplicados a skills y al asistente, basados en "Effective context
engineering for AI agents" (Anthropic):

- El contexto es un recurso FINITO: cada token compite con el resto. Buscar
  SIEMPRE el conjunto minimo de tokens de alta senal que produzca el resultado
  deseado. Menos contexto bien curado supera a mas contexto desordenado.
- Descripcion de skill = el "disparador": debe decidir por si sola si activar
  o no la skill. Si dudo, es descripcion pobre.
- Progressive disclosure: mantener identificadores ligeros (rutas, nombres,
  consultas) y cargar datos solo cuando se necesitan (just-in-time), como
  CLAUDE.md de Claude Code: lo esencial arriba, el detalle bajo demanda.
- Notas estructuradas fuera del contexto (memoria_jarvis.md, NOTES.md):
  persisten entre sesiones sin gastar tokens. Es lo que hace el memory tool
  de Anthropic. El asistente ya lo implementa con memoria_jarvis.md.
- Compaction: cuando una conversacion se acerca al limite, resumir lo
  esencial (decisiones, bugs, progreso) y descartar salidas de tools viejas.
  opencode ya compacta automaticamente; el asistente ademas rota sesiones.
- Evaluator-optimizer: para tareas criticas, generar y luego verificar con
  criterios claros en un bucle, en vez de entregar la primera version.
- Los ejemplos valen mas que mil reglas: curar ejemplos canonicos diversos
  en vez de listas interminables de casos borde.
- Herramientas: pocas, claras y sin solaparse. Cada tool debe tener un
  proposito distinto y devolver SOLO informacion de alta senal (nada de
  UUIDs ni basura tecnica). Descripciones como para un recien llegado.
- Simplificar: empezar simple y anadir complejidad solo si mejora resultados.

## 11. Patrones de diseno de agentes (Andrew Ng + OpenAI + Anthropic)

Los patrones de DeepLearning.AI (Andrew Ng), OpenAI y Anthropic para construir
agentes efectivos. Aplicarlos segun la tarea:

- REFLECTION (auto-critica): generar una version, criticarla con criterios
  claros y reescribirla. Aplica a respuestas importantes, codigo y textos.
  En la practica: despues de generar algo critico, revisarlo con ojos de
  critico antes de entregar (que falta, que sobra, que puede fallar).
- TOOL USE: dar al agente herramientas especificas (buscar, ejecutar, abrir).
  Es la base del asistente: manos/ + scripts + ver_pantalla.
- PLANNING: para tareas de varios pasos, primero un plan (outline) y luego
  ejecutar paso a paso. El asistente ya usa todowrite para esto.
- MULTI-AGENT / ORCHESTRATOR-WORKERS: dividir tareas complejas entre agentes
  especializados y sintetizar. opencode ya lo soporta con subagentes; usarlos
  cuando la tarea lo amerite (explorar codigo, auditar, investigar).
- GUARDRAILS (OpenAI): validar entradas y salidas antes de acciones riesgosas.
  El asistente ya tiene blindaje; extenderlo a validar pedidos peligrosos.
- HANDOFFS (OpenAI): delegar la propiedad de una tarea al agente correcto.
  Equivale a elegir la skill adecuada por descripcion de disparo.
- DECOUPLE BRAIN/HANDS (Anthropic Managed Agents): separar el cerebro
  (instrucciones) de las manos (herramientas/scripts) para poder cambiar
  cualquiera sin romper el otro. Ya es la estructura de JARVIS: asistente
  (cerebro) + manos/ (herramientas) + skills (conocimiento).

## 12. Norma para ESTE proyecto

- Todas las skills del proyecto (jarvis, python-dev, bot-builder, automation,
  skill-authoring y futuras) se redactan o auditan con esta guia.
- JARVIS sigue siendo la skill predominante: identidad, voz, permisos, memoria
  y forma de trabajar. Las demas son companeras especializadas.
- Al crear una skill nueva, decidir si es de dominio general (reutilizable) o
  propia del asistente, y guardar las que sean herramientas en `manos/`.
