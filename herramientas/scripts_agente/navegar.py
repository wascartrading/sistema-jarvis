#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===================================================================
navegar.py  --  Herramienta GENERAL de navegacion de JARVIS
===================================================================
Automatiza el NAVEGADOR REAL (Brave del jefe) usando Playwright,
para navegar por CUALQUIER pagina web (HBO, YouTube, otros), buscar
elementos por texto real y ASEGURAR de verdad que la accion se hizo
(no clics a ciegas): espera, detecta, confirma y reporta.

Usa el PERFIL real de Brave del jefe (logins, historial, sesion HBO)
via launch_persistent_context + ejecutable de Brave.

COMO SE USA (modo peticion JSON - el mas flexible):
  python navegar.py --instruccion '{
     "navegar": "https://play.max.com",
     "buscar": "Red John's Footsteps",
     "clic_en": "Red John's Footsteps",
     "esperar": 5,
     "confirmar_busqueda": "play-button|Reproducir|Play",
     "iniciar_reproduccion": true,
     "pantalla_completa": true,
     "reportar": true
  }'

Acciones disponibles (todas opcionales, se ejecutan en orden):
  - navegar:       URL a abrir (str)
  - buscar_texto:  texto a localizar/validar que existe (str)
  - clic_en:       texto del elemento sobre el que hacer clic (str)
  - clic_en_rol:   hacer clic por rol/etiqueta, ej. {"rol":"button","nombre":"Play"}
  - teclear:       texto a escribir (str, opcional con clic_en para campos)
  - esperar:       segundos a pausar (float)
  - confirmar:     texto o regex que debe aparecer para dar por bueno (str)
  - pantalla_completa: true para F11 de verdad
  - salir_pantalla:     true para salir de pantalla completa
  - header_visible: true/false oculta la barra superior con solo teclas
  - reportar:      true para imprimir un informe de lo hecho/confirmado

EL SCRIPT SIEMPRE IMPRIME UN INFORME FINAL: que navego, que encontro,
que clico y si confirmo la accion. JARVIS lee ese informe.
===================================================================
"""
import sys, json, time, argparse
from playwright.sync_api import sync_playwright

BRAVE_EXE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
PERFIL    = r"C:\Users\wasc4\AppData\Local\BraveSoftware\Brave-Browser\User Data"


def reporte(puntos):
    print("\n===== INFORME DE NAVEGACION (JARVIS) =====")
    for k, v in puntos.items():
        print(f"  {k}: {v}")
    print("==========================================")


def normalizar(texto):
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def contiene(contenido, patron):
    """True si patron (normalizado) aparece en el contenido normalizado."""
    return normalizar(patron) in normalizar(contenido)


def buscar_y_clic(page, texto, rol=None, timeout=15000):
    """Busca un elemento por su texto (visible) y hace clic. Devuelve True si lo hizo."""
    try:
        if rol:
            page.get_by_role(rol, name=texto, exact=False).first.click(timeout=timeout)
        else:
            page.get_by_text(texto, exact=False).first.click(timeout=timeout)
        return True
    except Exception as e:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instruccion", type=str, required=True,
                    help="JSON con las acciones a realizar")
    args = ap.parse_args()

    try:
        ins = json.loads(args.instruccion)
    except Exception as e:
        print(f"ERROR: instruccion JSON invalida: {e}")
        sys.exit(1)

    puntos = {"estado": "ejecutado", "navego": ins.get("navegar", "-"),
              "encontro": None, "clico": None, "confirmado": None, "nota": ""}

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            PERFIL,
            executable_path=BRAVE_EXE,
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
            ],
            no_viewport=True,
        )
        page = context.pages[0] if context.pages else context.new_page()

        # 1) Navegar
        if ins.get("navegar"):
            page.goto(ins["navegar"], wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

        # 2) Buscar texto (validar que existe)
        if ins.get("buscar"):
            hay = True
            try:
                page.get_by_text(ins["buscar"], exact=False).first.wait_for(timeout=8000)
            except Exception:
                hay = False
            puntos["encontro"] = f"{ins['buscar']} -> {'SI' if hay else 'NO'}"
            if not hay:
                puntos["nota"] += " No se encontro el texto buscado."

        # 3) Hacer clic en elemento por texto
        if ins.get("clic_en"):
            hecho = buscar_y_clic(page, ins["clic_en"])
            puntos["clico"] = f"{ins['clic_en']} -> {'SI' if hecho else 'NO/fallo'}"
            time.sleep(1)

        # 4) Hacer clic por rol/etiqueta
        if ins.get("clic_en_rol"):
            ce = ins["clic_en_rol"]
            hecho = buscar_y_clic(page, ce.get("nombre", ""), rol=ce.get("rol", "button"))
            puntos["clico"] = f"[{ce.get('rol')}] {ce.get('nombre')} -> {'SI' if hecho else 'NO/fallo'}"
            time.sleep(1)

        # 5) Escribir texto (si se pide en un campo)
        if ins.get("teclear") and ins.get("clic_en"):
            page.keyboard.type(ins["teclear"], delay=40)
            page.keyboard.press("Enter")
            time.sleep(1)

        # 6) Esperar
        if ins.get("esperar"):
            time.sleep(float(ins["esperar"]))

        # 7) Pantalla completa / salir
        if ins.get("pantalla_completa"):
            page.keyboard.press("F11")
            time.sleep(1)
            puntos["nota"] += " Pantalla completa (F11) activada."
        if ins.get("salir_pantalla"):
            page.keyboard.press("F11")
            time.sleep(1)

        # 8) Iniciar reproduccion (tecla espacio en el player enfocado)
        if ins.get("iniciar_reproduccion"):
            page.keyboard.press(" ")
            time.sleep(0.5)
            page.keyboard.press(" ")
            puntos["nota"] += " Se pulso barra para reanudar."

        # 9) Confirmar que aparecio algo
        if ins.get("confirmar"):
            encontrado = False
            try:
                page.get_by_text(ins["confirmar"], exact=False).first.wait_for(timeout=15000)
                encontrado = True
            except Exception:
                # intentar con regex
                try:
                    page.wait_for_selector(f"text=/{ins['confirmar']}/i", timeout=8000)
                    encontrado = True
                except Exception:
                    encontrado = False
            puntos["confirmado"] = f"{ins['confirmar']} -> {'SI' if encontrado else 'NO'}"
            if encontrado:
                puntos["nota"] += " Accion confirmada en pantalla."
            else:
                puntos["nota"] += " NO se confirmo (revisar estado)."

        # Cerrar sin matar el perfil (deja la sesion viva en pantalla para el jefe)
        if ins.get("reportar", True):
            reporte(puntos)


if __name__ == "__main__":
    main()
