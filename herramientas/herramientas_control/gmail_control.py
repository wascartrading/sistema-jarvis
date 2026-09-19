# -*- coding: utf-8 -*-
"""
gmail_control.py — Gmail para JARVIS (Telegram).
API oficial de Google (OAuth). Portado del desmenuzado JARVIS-HRZ
(actions/gmail_control) con codigo limpio.

PASOS PARA ACTIVAR (una sola vez):
  1) Tener google_credentials.json (OAuth de escritorio de Google Cloud)
     en la carpeta:  herramientas_control\.gmail\
  2) Autorizar:  python cli.py gmail auth   (abre el navegador)

Acciones:
  python cli.py gmail auth
  python cli.py gmail inbox [N]
  python cli.py gmail leer <id>
  python cli.py gmail buscar "<consulta>"
  python cli.py gmail enviar <para> <asunto> <cuerpo>
  python cli.py gmail responder <id> <texto>
  python cli.py gmail archivar <id>
  python cli.py gmail borrar <id>
  python cli.py gmail leido <id>
  python cli.py gmail etiquetas
"""
import base64
import os
import re
import sys
from email.mime.text import MIMEText

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gmail")
_CRED = os.path.join(_DIR, "google_credentials.json")
_TOKEN = os.path.join(_DIR, "google_token.json")

_ACENTOS = str.maketrans(
    "ÁÉÍÓÚáéíóúÑñ", "AEIOUaeiouNn")


def _sin_acentos(t):
    return t.translate(_ACENTOS) if t else t


def _get_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(_TOKEN):
        creds = Credentials.from_authorized_user_file(_TOKEN, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None
    if creds and creds.valid:
        return build("gmail", "v1", credentials=creds)
    return None


def _pedir_token():
    """Flujo OAuth local: abre el navegador para autorizar."""
    if not os.path.exists(_CRED):
        return ("FALTA google_credentials.json en:\n"
                f"{_DIR}\n\nTramitalo en Google Cloud Console "
                "(credencial OAuth de escritorio) y vuelve a intentar.")
    from google_auth_oauthlib.flow import InstalledAppFlow

    os.makedirs(_DIR, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(_CRED, SCOPES)
    try:
        creds = flow.run_local_server(port=0, prompt="consent")
    except Exception:
        creds = flow.run_console()
    from google.auth.transport.requests import Request
    creds.refresh(Request())
    with open(_TOKEN, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    return "Autorizado. Tu correo quedo conectado a JARVIS."


def _fecha(ms):
    from datetime import datetime, timezone
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%d/%m %H:%M")
    except Exception:
        return ""


def _cabecera(msg, nombre):
    for h in msg.get("payload", {}).get("headers", []):
        if h.get("name", "").lower() == nombre:
            return h.get("value", "")
    return ""


def _texto_plano(msg):
    """Extrae el cuerpo en texto plano de un mensaje (con multipart)."""
    payload = msg.get("payload", {})
    def walk(p):
        mime = p.get("mimeType", "")
        if mime == "text/plain" and p.get("body", {}).get("data"):
            try:
                return base64.urlsafe_b64decode(p["body"]["data"]).decode("utf-8", "replace")
            except Exception:
                return ""
        for part in p.get("parts", []) or []:
            r = walk(part)
            if r:
                return r
        return ""
    return walk(payload)


def _accion_inbox(service, n):
    res = service.users().messages().list(userId="me", q="in:inbox",
                                          maxResults=n).execute()
    msgs = res.get("messages", [])
    if not msgs:
        return "Bandeja de entrada vacia. Todo al dia."
    lineas = ["Bandeja de entrada:"]
    for i, m in enumerate(msgs, 1):
        det = service.users().messages().get(userId="me", id=m["id"],
                                             format="metadata",
                                             metadataHeaders=["From", "Subject", "Date"]).execute()
        de = _cabecera(det, "From") or "?"
        asunto = _cabecera(det, "Subject") or "(sin asunto)"
        fecha = _fecha(det.get("internalDate"))
        # de: "Nombre <correo>"
        de_corto = re.sub(r"\s*<[^>]+>\s*$", "", de)
        if len(de_corto) > 28:
            de_corto = de_corto[:25] + "..."
        asunto_c = asunto if len(asunto) <= 70 else asunto[:67] + "..."
        lineas.append(f"{i}) {de_corto} · {fecha}\n   {asunto_c} · id:{m['id'][:10]}")
    return "\n".join(lineas)


def _accion_leer(service, mid):
    msg = service.users().messages().get(userId="me", id=mid, format="full").execute()
    de = _cabecera(msg, "From") or "?"
    asunto = _cabecera(msg, "Subject") or "(sin asunto)"
    cuerpo = _texto_plano(msg).strip()
    if len(cuerpo) > 1500:
        cuerpo = cuerpo[:1500] + "\n... (truncado)"
    return f"De: {de}\nAsunto: {asunto}\nFecha: {_fecha(msg.get('internalDate'))}\n\n{cuerpo}"


def _crear_mime(para, asunto, cuerpo):
    m = MIMEText(cuerpo, "plain", "utf-8")
    m["to"] = para
    m["subject"] = asunto
    return base64.urlsafe_b64encode(m.as_bytes()).decode()


def _accion_enviar(service, para, asunto, cuerpo):
    raw = _crear_mime(para, asunto, cuerpo)
    res = service.users().messages().send(userId="me",
                                          body={"raw": raw}).execute()
    return f"Enviado a {para} (id {res.get('id', '')[:10]})."


def _accion_responder(service, mid, texto):
    orig = service.users().messages().get(userId="me", id=mid, format="metadata",
                                          metadataHeaders=["From", "Subject", "Message-ID", "References"]).execute()
    de = _cabecera(orig, "From") or ""
    asunto = _cabecera(orig, "Subject") or ""
    mid_orig = _cabecera(orig, "Message-ID") or ""
    refs = _cabecera(orig, "References") or ""
    m = MIMEText(texto, "plain", "utf-8")
    if asunto and not asunto.lower().startswith("re:"):
        m["Subject"] = "Re: " + asunto
    else:
        m["Subject"] = asunto
    m["To"] = de
    if mid_orig:
        m["In-Reply-To"] = mid_orig
        m["References"] = (refs + " " + mid_orig).strip()
    raw = base64.urlsafe_b64encode(m.as_bytes()).decode()
    res = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return f"Respuesta enviada a {de} (id {res.get('id', '')[:10]})."


def _modify(service, mid, add=None, remove=None):
    body = {}
    if add:
        body["addLabelIds"] = add
    if remove:
        body["removeLabelIds"] = remove
    service.users().messages().modify(userId="me", id=mid, body=body).execute()


def _main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    accion = _sin_acentos(argv[1].lower())
    args = argv[2:]

    if accion == "auth":
        print(_pedir_token())
        return 0

    service = _get_service()
    if service is None:
        print("Gmail no autorizado. Ejecuta primero:  python cli.py gmail auth")
        return 1

    try:
        if accion in ("inbox", "bandeja", "correos"):
            n = int(args[1]) if len(args) > 1 else 10
            print(_accion_inbox(service, max(1, min(n, 25))))
        elif accion in ("leer", "ver", "abrir"):
            if len(args) < 2:
                print("Uso: python cli.py gmail leer <id>")
                return 2
            print(_accion_leer(service, args[1]))
        elif accion in ("buscar", "search"):
            q = " ".join(args[1:]) if len(args) > 1 else ""
            if not q:
                print("Uso: python cli.py gmail buscar \"consulta\"")
                return 2
            res = service.users().messages().list(userId="me", q=q, maxResults=8).execute()
            msgs = res.get("messages", [])
            if not msgs:
                print(f"Sin resultados para: {q}")
                return 0
            for i, m in enumerate(msgs, 1):
                det = service.users().messages().get(userId="me", id=m["id"],
                                                     format="metadata",
                                                     metadataHeaders=["From", "Subject"]).execute()
                de = _cabecera(det, "From") or "?"
                asunto = _cabecera(det, "Subject") or "(sin asunto)"
                print(f"{i}) {de} · {asunto} · id:{m['id'][:10]}")
        elif accion in ("enviar", "send"):
            if len(args) < 4:
                print("Uso: python cli.py gmail enviar <para> <asunto> <cuerpo>")
                return 2
            print(_accion_enviar(service, args[1], args[2], args[3]))
        elif accion in ("responder", "reply"):
            if len(args) < 3:
                print("Uso: python cli.py gmail responder <id> <texto>")
                return 2
            print(_accion_responder(service, args[1], args[2]))
        elif accion in ("archivar", "archive"):
            if len(args) < 2:
                print("Uso: python cli.py gmail archivar <id>")
                return 2
            _modify(service, args[1], remove=["INBOX"])
            print("Archivado.")
        elif accion in ("borrar", "trash", "eliminar"):
            if len(args) < 2:
                print("Uso: python cli.py gmail borrar <id>")
                return 2
            service.users().messages().trash(userId="me", id=args[1]).execute()
            print("Movido a la papelera.")
        elif accion in ("leido", "read", "marcar"):
            if len(args) < 2:
                print("Uso: python cli.py gmail leido <id>")
                return 2
            _modify(service, args[1], remove=["UNREAD"])
            print("Marcado como leido.")
        elif accion in ("etiquetas", "labels"):
            labs = service.users().labels().list(userId="me").execute().get("labels", [])
            print("Etiquetas: " + ", ".join(l["name"] for l in labs))
        elif accion in ("ayuda", "help"):
            print(__doc__)
        else:
            print(f"Accion desconocida: {accion}")
            return 2
        return 0
    except Exception as e:
        print(f"Error de Gmail: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv))