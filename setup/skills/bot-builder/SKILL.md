---
name: bot-builder
description: Crear y arreglar bots de Telegram/Discord en Python.
---

# Bot Builder — Bots de Telegram (y otros) en Python

Esta skill guia la creacion de bots para el usuario, que trabaja
principalmente con Telegram. El asistente debe poder generar un bot
funcional desde cero con plantillas reutilizables.

## Cuando usar esta skill

- Crear un bot nuevo (Telegram u otro canal) desde cero.
- Anadir comandos, teclados o conversaciones a un bot existente.
- Arreglar un bot que falla (no responde, muere, token invalido).
- Desplegar o correr un bot local en la PC del usuario.

No activarla para tareas que no sean bots: para Python en general usar
python-dev, para sistemas autonomos usar automation.

## Librerias recomendadas

- `python-telegram-bot` (v20+, asyncio) — la mas completa y moderna.
- `aiogram` (asyncio) — alternativa rapida y ligera.
- Para bots simples de script: `python-telegram-bot` con Application.

## Plantilla base (python-telegram-bot v20)

```python
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = 'TU_TOKEN_AQUI'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hola! Soy un bot de ejemplo.')

async def eco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, eco))
    app.run_polling()

if __name__ == '__main__':
    main()
```

## Estructura recomendada para bots medianos

```
bot/
├── bot.py            # punto de entrada (Application + handlers)
├── handlers/         # modulos por area (comandos, mensajes, callbacks)
├── config.py         # token y constantes (nunca token en el codigo duro)
├── services/         # logica de negocio (API, base de datos)
└── requirements.txt
```

## Buenas practicas

- El token NUNCA va hardcodeado en el codigo: usar variable de entorno o
  archivo config separado (que no se suba a git).
- Manejar errores de red con reintentos y logs.
- Usar `ContextTypes.DEFAULT_TYPE` y type hints en los handlers.
- Para teclados: `ReplyKeyboardMarkup` (teclado de respuesta) o
  `InlineKeyboardMarkup` (botones en el mensaje).
- Para conversaciones de varios pasos: `ConversationHandler` con estados.
- Registrar un `error_handler` global para que el bot no muera en silencio.
- Rutas y rutas de archivos SIEMPRE con barra normal `/` dentro de la skill;
  los comandos de Windows reales (venv, pythonw) usan backslash.

## Como probar (bucle de verificacion)

- Obtener token con @BotFather en Telegram.
- Crear venv e instalar la libreria.
- Compilar antes de correr: `python -m py_compile bot.py`.
- Correr `python bot.py` y probar con /start.
- Logs claros: logging.basicConfig(level=logging.INFO).
- Si falla: leer el log, corregir, compilar de nuevo y repetir. Solo
  entregar el bot cuando responde correctamente en una prueba real.

## Nota

Si el usuario pide otro tipo de bot (Discord, webhook, escritorio), adaptar
la estructura manteniendo estas mismas buenas practicas.
