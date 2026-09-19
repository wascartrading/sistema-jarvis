"""
whatsapp.py — Envia mensajes por WhatsApp Web abriendo el chat por URL
(wa.me) y tecleando con text_input. Portado del desmenuzado (version ligera).

Uso CLI:
  python cli.py whatsapp enviar "5215512345678" "hola jefe"
Nota: requiere WhatsApp Web con sesion activa en Brave.
"""
import time

from . import browser_control, text_input


def enviar(numero, mensaje, interval=0.03):
    """Abre el chat wa.me del numero y teclea el mensaje + Enter."""
    import urllib.parse
    url = f"https://wa.me/{numero}"
    ok, _msg = browser_control.go_to(url, interval=0.02)
    if not ok:
        return False, "No se pudo abrir WhatsApp Web"
    time.sleep(6)  # espera a que cargue el chat
    try:
        text_input.teclado_limpio()
        text_input.escribir(mensaje, interval=interval)
        time.sleep(0.3)
        browser_control.hotkey("enter")
        return True, f"Mensaje enviado a {numero}"
    except Exception as e:
        return False, f"Error tecleando: {e!r}"


def _main(argv):
    import sys
    if len(argv) < 3:
        print("Uso: whatsapp.py enviar <numero> <mensaje>")
        return 2
    accion = argv[1].lower()
    if accion != "enviar":
        print(f"Accion desconocida: {accion}")
        return 2
    numero = argv[2]
    mensaje = " ".join(argv[3:]) if len(argv) > 3 else ""
    ok, msg = enviar(numero, mensaje)
    print(msg)
    return 0 if ok else 2


if __name__ == "__main__":
    _main(sys.argv)