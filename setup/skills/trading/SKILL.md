---
name: trading
description: Trading y APIs de trading en Python: plataformas de opciones binarias (IQ Option), datos de mercado, velas, latencia, indicadores, gestion de riesgo y bots de trading. Usar cuando el usuario pida trabajar con trading, analizar mercado, crear o arreglar bots de trading o consumir APIs de corredores.
license: Apache-2.0
compatibility: opencode
metadata:
  audience: jarvis
---

# Trading — Trading y APIs de mercado

Guia para el trabajo de trading del usuario: plataformas como IQ Option,
datos de mercado, velas, indicadores, latencia, gestion de riesgo y bots.
Base para el proyecto IQ-ULTIMATE y futuros desarrollos.

## Cuando usar esta skill

- Analizar velas, tendencias, indicadores o datos de mercado.
- Crear, ampliar o arreglar un bot de trading (IQ Option u otro corredor).
- Trabajar con la API de una plataforma de trading (iqoptionapi y similares).
- Optimizar latencia, tiempos de entrada o gestion de riesgo.
- Auditar modulos de un bot de trading (velas, señales, ejecucion).

No activarla para trading general sin codigo ni para bots de Telegram: eso es
python-dev o bot-builder.

## Plataformas y librerias

- IQ Option: paquete `iqoptionapi` (en el Python 3.12 del usuario). Es una
  API no oficial: verificar siempre la conexion y los estados de sesion.
- Proyecto conocido del usuario: `IQ-ULTIMATE` en el Escritorio (bot de velas
  y latencia). Estructura: config.py, requirements.txt, modulos de velas.
- Otras librerias disponibles: pandas, numpy, scipy, websockets, requests.

## Principios de un bot de trading

1. Datos de mercado primero: velas limpias y sincronizadas antes de operar.
2. Latencia controlada: medir y registrar tiempos de ida y vuelta.
3. Riesgo gestionado: nunca apostar mas de lo definido por operacion.
4. Estados claros: el bot sabe si esta conectado, esperando, o en operacion.
5. Log completo: cada decision (entrada, salida, error) queda registrada.
6. Fallo seguro: si pierde conexion, no abrir posiciones a ciegas.

## Buenas practicas

- Credenciales de la cuenta NUNCA hardcodeadas: config aparte o variables.
- Usar timeouts y reintentos en las conexiones websocket/API.
- Validar cada vela antes de usarla (timestamp, precio, formato).
- Probar en modo demo/paper antes de operar con dinero real.
- Documentar cada bot creado en `memoria_jarvis.md` y guardar scripts
  reutilizables en `voz_kokoro/manos/`.
- Al auditar codigo de trading: compilar y revisar logica de riesgo primero.

## Verificacion (bucle de calidad)

1. Compilar el script: `python -m py_compile script.py`.
2. Probar la conexion con la plataforma y verificar que llegan datos reales.
3. Probar en demo/paper una pasada completa (entrada, espera, salida).
4. Revisar el log: sin errores de conexion ni posiciones raras.
5. Si falla: corregir, compilar, probar de nuevo. Solo entregar cuando una
   pasada real completa funciona sin errores y el riesgo esta controlado.
6. Rutas dentro de la skill con barra normal `/`.
