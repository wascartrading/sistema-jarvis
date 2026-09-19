---
name: automation
description: Automatizacion en Windows: tareas programadas, vigilar carpetas, encadenar pasos y agentes autonomos.
---

# Automation — Sistemas autonomos y automatizacion en Windows

Esta skill guia la construccion de sistemas autonomos y automatizaciones en
la PC del usuario (Windows 10/11). El asistente debe poder crear agentes que
trabajen solos y encadenar tareas utiles.

## Cuando usar esta skill

- Automatizar una tarea repetitiva en la PC (programar, copiar, vigilar).
- Programar procesos con el Programador de tareas de Windows o schtasks.
- Vigilar carpetas y procesar archivos nuevos automaticamente.
- Crear agentes que trabajan solos y avisan al terminar.
- Montar el arranque automatico de algo al encender la PC.

No activarla para tareas sueltas de una sola vez (eso es python-dev o jarvis):
la automatizacion implica un proceso que corre solo o en bucle.

## Principios de un sistema autonomo

1. Tarea clara y comprobable: el sistema sabe cuando termino y que fallo.
2. Registro (logging): todo queda en un log para poder revisar.
3. Reinicio seguro: si falla, reintenta o avisa, no muere en silencio.
4. Ciclo controlado: loop con pausas para no saturar la CPU.
5. Estado persistente: guarda progreso en un archivo para retomar.

## Patron base de agente autonomo (Python)

```python
import time, logging, pathlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger('agente')

ESTADO = pathlib.Path('estado.txt')

def tarea():
    # la accion que el agente repite o procesa
    return True

def main():
    while True:
        try:
            if tarea():
                logger.info('tarea OK')
            else:
                logger.warning('tarea sin trabajo')
        except Exception as e:
            logger.error('fallo: %s', e)
        time.sleep(60)  # pausa del ciclo

if __name__ == '__main__':
    main()
```

## Automatizaciones utiles en su PC

- **Programar tareas**: `schtasks /create /tn Nombre /tr "ruta" /sc daily /st 09:00`
  (o usar el Programador de tareas de Windows).
- **Vigilar carpetas**: observar una carpeta y procesar archivos nuevos
  (watchdog en Python).
- **Ejecutar comandos**: `subprocess.run([...])` con rutas absolutas y
  captura de errores.
- **Iniciar con Windows**: clave Run en el registro (HKCU) apuntando al
  script con pythonw.exe (sin ventana).

## Integracion con JARVIS

- El usuario ya tiene a JARVIS como asistente de voz sobre opencode. Un
  sistema autonomo puede ser un script que JARVIS lanza, o un proceso que
  corre aparte y le avisa por voz cuando termina.
- Guardar scripts reutilizables en `C:\Users\wasc4\Documents\Default Project\Proyectos de asistente\scripts_agente\` con nombre descriptivo.
- Documentar en `memoria_jarvis.md` los sistemas autonomos creados para
  recordar como funcionan entre sesiones.

## Verificacion (bucle de calidad)

- Compilar el script antes de dejarlo correr: `python -m py_compile script.py`.
- Probar el ciclo en una pasada corta antes de dejarlo corriendo en bucle.
- Comprobar que el script no pide entrada de teclado (mueren en background).
- Si es un servicio largo, usar pythonw.exe (sin consola) o schtasks.
- Avisar siempre que un proceso queda corriendo en segundo plano.
- Si algo falla en la prueba: corregir, compilar y probar de nuevo. Solo
  entregar el sistema autonomo cuando completa una pasada real sin errores.
- Rutas dentro de la skill SIEMPRE con barra normal `/`; los comandos reales
  de Windows (schtasks, pythonw.exe) usan backslash.
