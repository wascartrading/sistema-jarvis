---
name: python-dev
description: Programar en Python profesional: scripts, APIs y herramientas.
---

# Python Dev — Scripts y codigo Python de calidad

Esta skill guia la creacion y mejora de codigo Python para el usuario, que
trabaja con scripts, programacion general y bots. El objetivo es codigo
limpio, mantenible y que funcione a la primera.

## Cuando usar esta skill

Activar SIEMPRE que el trabajo involucre codigo Python:

- Crear un script nuevo o una herramienta CLI.
- Revisar, depurar o mejorar codigo existente (incluido asistente_voz.py).
- Escribir pruebas o diagnosticar errores de ejecucion.
- Manejar dependencias, entornos virtuales o paquetes.
- Compilar/verificar un archivo antes de darlo por bueno.

No activarla para tareas que no tocan Python (por ejemplo, abrir programas,
ver la pantalla o conversacion general: eso es la skill jarvis).

## Reglas de estilo

- Python 3.8+ compatible; usar type hints donde aporten claridad.
- Nombres descriptivos en ingles o espanol, consistentes dentro del proyecto.
- Funciones pequenas y con un solo proposito; evitar monolitos.
- Usar `if __name__ == '__main__':` para separar definiciones de ejecucion.
- Manejar excepciones de forma especifica (nunca `except:` pelado sin log).
- Preferir `pathlib.Path` sobre `os.path` para rutas modernas.
- Logging con el modulo `logging` en vez de prints cuando haya flujo largo.
- Constantes sin valores magicos: cada numero se justifica con un comentario.

## Estructura recomendada para un script

```
mi_script.py
├── imports (stdlib, luego terceros)
├── constantes en MAYUSCULAS
├── funciones auxiliares
├── funcion main()
└── if __name__ == '__main__': main()
```

Para proyectos: carpeta con `__init__.py`, `requirements.txt` y, si aplica,
un `README.md` corto con uso.

## Entornos virtuales y dependencias

- Crear venv: `python -m venv .venv`
- Activar en Windows: `.venv\Scripts\activate`
- Congelar deps: `pip freeze > requirements.txt`
- Para el asistente, el usuario usa `C:\Users\wasc4\AppData\Local\Programs\Python\Python312\python.exe`
  (a veces `python` falla con acceso denegado; usar la ruta completa).

## Verificacion (bucle de calidad obligatorio)

1. Compilar siempre: `python -m py_compile archivo.py` (o la ruta completa).
2. Probar el script en un entorno controlado antes de darlo por bueno.
3. Si el codigo toca archivos del usuario (rutas), usar rutas explicitas y
   comprobarlas con Test-Path / pathlib.exists() antes de abrir.
4. Si hay errores: corregir, compilar de nuevo y repetir hasta que pase.
   Solo entregar el codigo cuando py_compile devuelve OK.

## Ejemplos tipicos del usuario

- Scripts de automatizacion de tareas en su PC (Windows).
- Creacion de bots de Telegram (ver skill bot-builder).
- Herramientas CLI simples para su flujo diario.
- Modificaciones al asistente de voz (asistente_voz.py): aplicar UN cambio
  puntual por vez y compilar tras cada uno (regla de la skill jarvis).

