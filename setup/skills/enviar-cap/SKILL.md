---
name: enviar-cap
description: Capturar la pantalla y enviarla al chat de Telegram.
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

## TODAS LAS VENTANAS (orden permanente del jefe, 15/09/2026)

Cuando el jefe pida "un cap", lo que quiere es **una captura de CADA ventana
abierta** (Brave, WhatsApp, OpenCode...), no solo del escritorio:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\wasc4\.config\opencode\skills\enviar-cap\enviar_caps_todas.ps1"
```

- Enumera las ventanas de nivel superior con titulo y llama al script de una
  ventana por cada una (reutiliza `enviar_cap_telegram.ps1`).
- `-Max 8` limite de ventanas (por defecto 8) · `-Escritorio` solo el
  escritorio completo · `-IncluirGlobal` añade el escritorio al final.
- Devuelve JSON: `{"ok":true,"enviadas_total":N,"enviadas":[...],"fallidas":[...]}`.
- Cada ventana se captura con PrintWindow: funciona **aunque el monitor este
  en reposo** (el cap global no).


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