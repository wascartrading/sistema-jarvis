---
name: voice-audio
description: Voz y audio del asistente: TTS, STT, volumen y dispositivos.
---

# Voice & Audio — La voz de JARVIS

Guia para todo lo relacionado con la voz y el audio del asistente: motores
actuales (Kokoro y Piper), integracion de Moshi como capa conversacional, y
el manejo de audio en la PC del usuario.

## Cuando usar esta skill

- Modificar la voz, el tono, la velocidad o el motor de sintesis del asistente.
- Trabajar con Moshi u otro motor de voz conversacional.
- Diagnosticar problemas de audio: sin sonido, micrófono, dispositivo equivocado.
- Cambiar el dispositivo de salida (altavoz, audifonos, HDMI).
- Implementar reconocimiento de voz (dictado) o mejorar la narracion.
- Ajustar fades, pausas, volumen o naturalidad de la voz.

No activarla para tareas que no tocan voz/audio: eso es python-dev o jarvis.

## Motores de voz actuales del asistente

- Kokoro (voz principal, suave): `voz_kokoro/models/kokoro-v1.0.onnx` +
  `voices-v1.0.bin`. Voz actual: em_alex, VELOCIDAD 1.15, IDIOMA es.
- Piper (respaldo): `voz_kokoro/piper/es_MX-ald-medium.onnx`.
- Parametros en `asistente_voz.py` (seccion CONFIGURACION): MOTOR, VOZ,
  IDIOMA, VELOCIDAD, DISPOSITIVO, PAUSA_ENTRE_ORACIONES.
- Flujo de audio: sintesis en hilo aparte (Kokoro/Piper) -> cola -> reproduccion
  con fades (rampa de entrada 15 ms, salida en curva coseno, cola de silencio
  final) para que suene natural.

## Dispositivos de audio (leccion aprendida)

- Comparar dispositivos por TOKENS significativos (palabras >= 4 letras, sin
  genericos como audio/output/high/definition/2nd), no por nombre completo.
- El usuario alterna entre SAMSUNG (HDMI, tokens: samsung, nvidia) y
  Headphones Realtek (tokens: headphones, realtek).
- Consultar el dispositivo por defecto actual de Windows en cada reproduccion
  (`sd.default._default_device`) para seguir el switch de la barra de tareas.

## Moshi (capa de voz conversacional futura)

- Moshi NO reemplaza al modelo de IA: es la boca y los oidos en tiempo real.
  Detras sigue el orquestador (JARVIS + opencode) que hace el trabajo real.
- La RTX 3070 (8 GB VRAM) corre Moshi CUANTIZADO (GGUF 4-bit aprox), no el
  completo (7B fp16 pide 14-24 GB). Ver plan en memoria_jarvis.md.
- Arquitectura objetivo: Moshi corre como servidor de voz local por un puerto
  propio, y el asistente alterna entre Moshi y Kokoro segun el modo activo.
- La implementacion se hace por opencode, NO editando el archivo mientras el
  asistente de voz esta hablando (riesgo de colgarse).

## Buenas practicas de audio

- Todo cambio de voz se compila: `python -m py_compile asistente_voz.py`.
- Cambios UNO a UNO y reiniciar el asistente para probar cada uno.
- Si el audio falla: revisar `asistente.log` (lineas "audio:") y verificar el
  dispositivo por defecto actual de Windows.
- Cortes al final de oracion: aplicar fades (rampa de salida suave + silencio).
- No bloquear el hilo de la interfaz con sintesis: siempre hilos aparte.

## Verificacion (bucle de calidad)

1. Compilar el archivo modificado.
2. Reiniciar el asistente y probar la voz con una frase real.
3. Probar el cambio de dispositivo (altavoz/audifonos) si se toco audio.
4. Si falla o suena mal: corregir, compilar, reiniciar y repetir.
5. Solo entregar cuando la voz suena correcta y el asistente responde.
