---
name: enviar-cap
description: Toma una captura de la pantalla (o de una ventana concreta) y la envia INMEDIATAMENTE al chat de Telegram del jefe. Usar cuando el jefe pida "enviame un cap", "captura la pantalla", "manda una foto de la pantalla", "manda un screenshot", o quiera ver que hay en pantalla. Detecta pantallas en reposo/bloqueadas y usa PrintWindow de respaldo para no mandar caps en negro.
---

# Enviar Cap — Captura de pantalla directa a Telegram

Habilidad permanente de JARVIS para mandar al jefe una foto de lo que hay
en la pantalla (o de una ventana concreta) con UN solo comando.

## Cuando usar

- El jefe pide: "enviame un cap", "manda un cap", "captura la pantalla",
  "mándame una foto de..." o quiere ver qué hay abierto en el PC.
- Necesitas mostrar visualmente algo (una app, un error, una página) sin
  depender del navegador.

## Ejecucion

El script vive en este mismo directorio:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\wasc4\.config\opencode\skills\enviar-cap\enviar_cap_telegram.ps1"
```

Variantes:

```powershell
# Cap de la ventana activa (si no hay ventana, intenta pantalla global)
powershell -NoProfile -ExecutionPolicy Bypass -File "...\enviar_cap_telegram.ps1"

# Cap de una ventana concreta por parte del titulo
powershell -NoProfile -ExecutionPolicy Bypass -File "...\enviar_cap_telegram.ps1" -Ventana "IQ Option"

# Forzar captura global (todo el escritorio)
powershell -NoProfile -ExecutionPolicy Bypass -File "...\enviar_cap_telegram.ps1" -ForzarGlobal
```

## Que hace por dentro (anti-cap-negro)

1. Despierta la pantalla (SetThreadExecutionState + nudge de mouse).
2. Intenta captura GLOBAL con CopyFromScreen.
3. Si falla o sale plana (monitor en reposo), usa PrintWindow con
   PW_RENDERFULLCONTENT sobre la ventana objetivo, que funciona aunque la
   pantalla física esté apagada.
4. Verifica que la imagen no sea un bloque de un solo color.
5. Envia el PNG por Telegram con la API sendPhoto del bot.
6. Responde JSON corto: `{"ok":true,"metodo":"global"|"ventana","bytes":N,"ventana":"..."}`.

## Salidas de error (importante para responder al jefe)

- `ok:false, motivo:ventana_no_encontrada` — no existe ventana con ese título.
- `ok:false, motivo:pantalla_no_capturable` — ni global ni ventana funcionaron:
  el escritorio está en reposo/apagado o sin superficie visible. Se responde
  al jefe: "La pantalla está dormida/nocapturable ahora mismo; toca una tecla
  o enciende el monitor y reintento" — NUNCA mandar un cap en negro.
- `ok:false, motivo:telegram_fallo` — la API de Telegram rechazó el envío.

## Reglas de uso

- Siempre confirmar el resultado en UNA frase al jefe ("Cap enviado, jefe")
  o el error con la recomendación.
- Si el jefe pide el cap para mostrar una app concreta, usar `-Ventana`.
- El cap temporal se borra solo. Si se quiere conservar, usar `-SinLimpiar`.