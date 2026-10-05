#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
servir_descarga.py - Pagina de descarga de la app JARVIS.

Sirve:
  /                 -> la pagina (index.html) con el boton de descarga.
  /app.apk          -> LA ULTIMA version del APK (se detecta sola).
  /version          -> el numero de version actual (texto plano).
  /JARVIS-x.y-arm64.apk -> cualquier APK concreto que exista.

La "ultima version" se detecta automaticamente mirando los archivos
JARVIS-<version>-arm64.apk en la carpeta padre (proyectos\\jarvis_app).
Asi, al soltar un APK nuevo (por ejemplo JARVIS-27.0-arm64.apk) el boton
ya entrega esa version, sin tocar nada.

Uso:
  python servir_descarga.py [puerto]     (por defecto 8099)

Creado por JARVIS para el senor Wascar.
"""

import glob
import os
import re
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))          # ...\jarvis_app\descarga
APP_DIR = os.path.dirname(BASE)                             # ...\jarvis_app
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
PAGINA = os.path.join(BASE, "index.html")


def ultima_apk():
    """Devuelve (version, ruta_del_apk) de la version mas alta, o (None, None)."""
    mejor = None
    for f in glob.glob(os.path.join(APP_DIR, "JARVIS-*-arm64.apk")):
        m = re.search(r"JARVIS-(\d+(?:\.\d+)+)-arm64\.apk$", os.path.basename(f))
        if not m:
            continue
        partes = tuple(int(x) for x in m.group(1).split("."))
        if mejor is None or partes > mejor[0]:
            mejor = (partes, m.group(1), f)
    if mejor is None:
        # Respaldo: un APK con nombre generico (por ejemplo en el kit).
        alterno = os.path.join(APP_DIR, "JARVIS.apk")
        if os.path.isfile(alterno):
            return ("actual", alterno)
        return (None, None)
    return (mejor[1], mejor[2])


def ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class Manejador(BaseHTTPRequestHandler):
    server_version = "JarvisDescarga/1.0"

    def _responder(self, codigo, tipo, cuerpo, extra=None):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(cuerpo)

    def do_GET(self):
        ruta = self.path.split("?")[0]

        # --- La pagina ---
        if ruta in ("/", "/index.html", "/descargar", "/descarga"):
            ver, _ = ultima_apk()
            try:
                with open(PAGINA, "r", encoding="utf-8") as fh:
                    html = fh.read()
            except OSError:
                self._responder(500, "text/plain; charset=utf-8",
                                b"Falta index.html"); return
            html = html.replace("{{VERSION}}", ver or "sin APK")
            self._responder(200, "text/html; charset=utf-8", html.encode("utf-8"))
            return

        # --- Version en texto ---
        if ruta == "/version":
            ver, _ = ultima_apk()
            self._responder(200, "text/plain; charset=utf-8",
                            (ver or "-").encode("utf-8"))
            return

        # --- El APK (siempre el ultimo) ---
        if ruta in ("/app.apk", "/JARVIS.apk", "/descargar/apk"):
            ver, apk = ultima_apk()
            if not apk:
                self._responder(404, "text/plain; charset=utf-8",
                                b"No hay ninguna APK en la carpeta."); return
            self._enviar_apk(apk, ver)
            return

        # --- Un APK concreto por nombre (compatibilidad) ---
        if ruta.lower().endswith(".apk"):
            nombre = os.path.basename(ruta)
            destino = os.path.join(APP_DIR, nombre)
            if os.path.isfile(destino) and nombre.lower().startswith("jarvis"):
                self._enviar_apk(destino, nombre.replace(".apk", "")); return
            self._responder(404, "text/plain; charset=utf-8",
                            b"Esa APK no existe."); return

        self._responder(404, "text/plain; charset=utf-8", b"No encontrado.")

    def do_HEAD(self):
        # Algunos gestores de descarga piden primero las cabeceras.
        self.do_GET()

    def _enviar_apk(self, ruta_apk, ver):
        tam = os.path.getsize(ruta_apk)
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.android.package-archive")
        nombre = ("JARVIS-%s-arm64.apk" % ver) if ver and ver != "actual" else "JARVIS.apk"
        self.send_header("Content-Disposition", 'attachment; filename="%s"' % nombre)
        self.send_header("Content-Length", str(tam))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(ruta_apk, "rb") as fh:
            while True:
                trozo = fh.read(65536)
                if not trozo:
                    break
                self.wfile.write(trozo)

    def log_message(self, *args):
        pass  # silencio: no llenar la consola


def main():
    ver, _ = ultima_apk()
    ip = ip_local()
    print("=" * 52)
    print("  PAGINA DE DESCARGA DE JARVIS")
    print("=" * 52)
    print("  Version detectada : %s" % (ver or "(no hay APK)"))
    print("  En esta PC        : http://127.0.0.1:%d/" % PUERTO)
    print("  En el celular     : http://%s:%d/" % (ip, PUERTO))
    print("  Abra esa direccion en el navegador del telefono.")
    print("  (Ctrl+C para detener)")
    print("=" * 52)
    try:
        servidor = ThreadingHTTPServer(("0.0.0.0", PUERTO), Manejador)
    except OSError as e:
        print("No se pudo abrir el puerto %d: %s" % (PUERTO, e))
        print("Puede que ya haya algo usando ese puerto.")
        sys.exit(1)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")
        servidor.server_close()


if __name__ == "__main__":
    main()
