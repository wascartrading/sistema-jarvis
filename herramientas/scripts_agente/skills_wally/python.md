# SKILL: Crear programas en Python

Guia rapida para crear programas Python cuando el jefe lo pida.

## Estructura basica

# -*- coding: utf-8 -*-
import os
import sys

def main():
    # Logica principal aqui
    print("Hola desde Python")

if __name__ == "__main__":
    main()

## Reglas

1. Crea SIEMPRE un archivo .py con la extension correcta usando write.
2. Usa funciones para organizar el codigo (def main(): ...).
3. Maneja errores con try/except cuando haya operaciones riesgosas
   (archivos, red, comandos).
4. Usa rutas absolutas o relativas claras; en Windows usa barras
   invertidas o r strings (r"C:\ruta").
5. Despues de crear, ejecuta con bash: python "ruta\archivo.py"
6. Verifica la salida y confirma al jefe que funciono.
7. Si el programa necesita librerias externas, verifica si estan
   instaladas (import) y avisa si falta alguna.

## Ejemplos utiles

- Leer archivo: with open(ruta, "r", encoding="utf-8") as f: contenido = f.read()
- Escribir archivo: with open(ruta, "w", encoding="utf-8") as f: f.write(texto)
- Listar carpeta: os.listdir(ruta)
- Ejecutar comando: import subprocess; subprocess.run(cmd, shell=True)
- Descargar: import urllib.request; urllib.request.urlretrieve(url, destino)

## Buenas practicas

- Nombres claros en espanol o ingles (variables, funciones).
- Comentarios breves explicando lo importante.
- El programa debe ser completo y ejecutable tal cual.