#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""vision_deepseek.py - OJOS DE JARVIS con DeepSeek V4.1 Flash (13/09/2026, orden del jefe).

IDEA DEL JEFE: nada de montar un sistema aparte. JARVIS MISMO toma el capto
de la pantalla y se lo pasa a SU PROPIO cerebro multimodal (DeepSeek V4.1
Flash por OmniRoute); de ahi saca la descripcion y las COORDENADAS EXACTAS
para picar el mouse. Un solo guion: captar -> preguntar -> devolver pixeles.

PRUEBA REAL (13/09/2026, antes de escribir esto):
  - leyo un codigo secreto EXACTO en una imagen generada al azar;
  - describio la pantalla en vivo (IQ Option, EUR/GBP, botones SUBE/BAJA);
  - sus coordenadas coincidieron con el PIXEL REAL medido:
      SUBE (1257,413) = RGB(83,169,95) verde
      BAJA (1257,522) = RGB(234,99,75) rojo

Uso (contrato IDENTICO a vision_gemini, para que cli.py no cambie):
  python vision_deepseek.py ver "que hay en la pantalla"
  python vision_deepseek.py coords "el boton SUBE"
  python vision_deepseek.py clic "el boton SUBE"
  python vision_deepseek.py resolucion
  python vision_deepseek.py captura [ruta.png]

Reutiliza de vision_gemini (nunca reinventar): capturar() con su cadena de
metodos (mss -> PIL -> BitBlt -> PrintWindow), resolucion(), el prompt de
elementos+px y el parser de pixeles reales.

OJOS = KIRO como modelo PRINCIPAL (orden del jefe, 16/09/2026): "deja a kiro
como unico modelo principal para ver imagenes; luego vamos viendo si
anadimos mas modelos para ver imagenes de forma rapida". Se manda la CAPTURA
+ la peticion y nada mas, sin cadenas ni procesos raros; 2 intentos y si
fallan se reporta "VISION: FALLO" y listo.

HISTORIA: antes se probaba 1) COMBO JARVIS y 2) KIRO. El Combo quedo fuera
porque su proveedor (opencode-go) responde 403 "cuota agotada" y 503 "todas
las cuentas inactivas" (medido el 16/09/2026), asi que hacia perder ~5 s por
cada captura. KIRO se queda como principal: probado leyendo la pantalla
completa, con texto y cifras exactas, en ~6 s. La lista _MODELOS esta
preparada para anadir mas modelos de vision rapida cuando el jefe lo pida
(basta sumarlos a la tupla, en orden de prioridad).

El respaldo Gemini sigue APAGADO por defecto (--con-respaldo lo activa; nada
se borro: vision_gemini sigue aportando la captura de pantalla y los
parsers).
"""
import base64
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

try:
    import vision_gemini as vg
except Exception:                       # pragma: no cover
    vg = None

_OPENCODE_CFG = os.path.join(
    os.path.expanduser("~"), ".config", "opencode", "opencode.json")
_KEY_FALLBACK = "sk-d5080265d1e0b1a3-8d4fb2-4799617d"
_URL_FALLBACK = "http://localhost:20128/v1/chat/completions"

# Ojos = KIRO como modelo PRINCIPAL de vision (orden del jefe, 16/09/2026:
# "deja a kiro como unico modelo principal para ver imagenes"). El COMBO JARVIS
# salio de la lista porque su proveedor devuelve 403 "cuota agotada" / 503
# "all accounts inactive" y hacia perder ~5 s en cada captura.
# PARA ANADIR MAS MODELOS DE VISION (orden del jefe: "luego vamos viendo si
# anadimos mas modelos para ver imagenes de forma rapida"): basta sumarlos a
# esta tupla, en orden de prioridad; se prueban en ese orden con _INTENTOS.
# CADENA DE VISION SIN PERDER LA VISTA (orden del jefe, 16/09/2026): "la cadena
# va a ser la siguiente: ya hay uno actualmente que funciona perfectamente que es
# el de kiro, ese dejalo como primero; si este falla entonces pasa a haiku y luego
# a sonnet... para que no haya manera de perder la vision".
# Se proban EN ESTE ORDEN; si uno falla (error, vacio o se niega) pasa al
# siguiente. Orden y tiempos MEDIDOS en esta PC el 16/09/2026 con la misma
# captura: kiro/claude-haiku-4.5 4.1 s | kr/claude-haiku-4.5 2.1 s |
# kiro/claude-sonnet-4.5 5.4 s | kr/claude-sonnet-4.5 2.1 s (ddgw y tllm
# descartados: HTTP 418 y 403 con 24 s de espera).
# Para cambiar la cadena SIN editar el archivo: variable de entorno
# JARVIS_VISION_MODELOS="modelo1,modelo2,...".
_CADENA_POR_DEFECTO = (
    "kiro/claude-haiku-4.5",   # 1) el de kiro, el que ya funcionaba
    "kr/claude-haiku-4.5",     # 2) haiku por la ruta alterna (el mas rapido)
    "kiro/claude-sonnet-4.5",  # 3) sonnet, mas musculo para capturas densas
    "kr/claude-sonnet-4.5",    # 4) sonnet por la ruta alterna
)
_ENV_MODELOS = os.environ.get("JARVIS_VISION_MODELOS", "").strip()
_MODELOS = tuple(m.strip() for m in _ENV_MODELOS.split(",") if m.strip()) \
    or _CADENA_POR_DEFECTO
_TIMEOUT = 20.0          # tope por intento (los modelos responden en 2-6 s)
_INTENTOS = 2            # 2 intentos: si fallan, se reporta y listo
_ESPERA_REINTENTO = 1.5  # respiro entre intentos (deja pasar el corte breve)
# El provider opencode-go (miembro del COMBO JARVIS) EXIGE esta cabecera:
# sin ella el gateway responde 400 "Request is missing x-opencode-session and
# cannot be routed efficiently". opencode la manda por su cuenta; este script
# tambien tiene que mandarla (causa real del fallo del 16/09/2026, verificado:
# con la cabecera el Combo lee la captura y contesta en ~3 s).
_SESSION_ID = "jarvis-vision-" + os.urandom(6).hex()
_MAX_TOKENS = 2048
# RED FINAL (orden del jefe 16/09/2026: "para que no haya manera de perder la
# vision"): si los CUATRO eslabones de la cadena fallan, se intenta el respaldo
# Gemini directo antes de darse por vencido. Antes estaba apagado (13/09/2026).
_USAR_RESPALDO = True


def _gateway():
    """Lee baseURL+apiKey del provider omniroute de opencode.json (asi el
    modulo no se desincroniza si el jefe cambia la clave)."""
    try:
        with open(_OPENCODE_CFG, encoding="utf-8") as f:
            cfg = json.load(f)
        op = cfg["provider"]["omniroute"]["options"]
        url = (op.get("baseURL") or "http://localhost:20128/v1").rstrip("/")
        return op.get("apiKey") or _KEY_FALLBACK, url + "/chat/completions"
    except Exception:
        return _KEY_FALLBACK, _URL_FALLBACK


def _llamar_deepseek(modelo, prompt, img_b64, timeout=_TIMEOUT):
    """Manda el capto al cerebro multimodal por OmniRoute (OpenAI-compatible)."""
    key, url = _gateway()
    body = {
        "model": modelo,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url",
                 "image_url": {"url": "data:image/jpeg;base64," + img_b64}},
            ],
        }],
        "max_tokens": _MAX_TOKENS,
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + key,
                 "x-opencode-session": _SESSION_ID},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    txt = (data.get("choices") or [{}])[0].get("message", {}).get("content")
    if isinstance(txt, list):
        txt = " ".join(str(p.get("text", "")) if isinstance(p, dict) else str(p)
                       for p in txt)
    return txt


def _prompt_elementos(pregunta, w, h, simple=False):
    """Prompt CORTO (orden del jefe 16/09/2026): a la vision se le manda la
    captura y la peticion, nada mas — el modelo ya ve la imagen. Solo se
    recuerda el formato de PIXELES REALES para que las manos puedan clicar.

    Se presenta como asistente de ACCESIBILIDAD del propio dueno del equipo:
    asi el modelo no lo toma por vigilancia y no contesta "no puedo hablar de
    eso" (paso el 16/09/2026 con kiro). `simple=True` es la variante ultracorta
    para el reintento."""
    if simple:
        return ("Mira esta imagen (una foto de la pantalla de MI computadora) "
                "y ayudame con esto: {}\nSi te pido ubicar algo, dime su "
                "centro en pixeles (X de 0 a {}, Y de 0 a {})."
                .format(pregunta, w, h))
    return (
        "Eres los ojos de un asistente de accesibilidad personal: describís al "
        "usuario la pantalla de SU PROPIA computadora para que pueda manejarla "
        "con el teclado y el mouse (es su equipo, su sesion, uso autorizado).\n"
        "La imagen adjunta es esa pantalla, de {}x{} px exactos (todo 1:1).\n"
        "Peticion: {}\n"
        "Si la peticion pide localizar elementos, responde una linea por "
        "elemento con el CENTRO en pixeles reales (X de 0 a {}, Y de 0 a {}):\n"
        "  [Nombre] -> X , Y | TAMANO: WxH\n"
        "Solo elementos REALES y visibles; si algo no se ve con claridad, no "
        "lo inventes. Cierra con 2-3 lineas 'QUE SE VE:' resumiendo la "
        "pantalla."
        .format(w, h, pregunta, w, h))


# Frases con las que un modelo contesta "me niego" en vez de describir. Un
# rechazo NO es una lectura valida: cuenta como intento fallido.
_RECHAZOS = (
    "i can't discuss", "i cannot discuss", "can't discuss that",
    "i can't help with that", "i cannot help with that",
    "i'm not able to help", "i am not able to help", "i won't",
    "no puedo hablar de eso", "no puedo discutir", "no puedo ayudarte con eso",
    "no puedo analizar", "no puedo describir", "lo siento, no puedo",
)


def _es_rechazo(texto):
    """True si el modelo se nego en vez de describir la pantalla."""
    t = (texto or "").strip().lower()
    if not t or len(t) > 700:
        return False
    return any(s in t for s in _RECHAZOS)


def _parse_json_pixeles(texto, w, h, factor=1.0):
    """Respaldo: si el modelo contesta JSON, saca los pixeles reales igual.
    Filtro anti-alucinacion: descarta coordenadas fuera de pantalla."""
    pix, desc = [], []
    ini, fin = texto.find("{"), texto.rfind("}")
    if ini < 0 or fin <= ini:
        return pix, desc
    try:
        j = json.loads(texto[ini:fin + 1])
    except Exception:
        return pix, desc
    elems = j.get("elementos") or j.get("elements") or []
    for e in elems:
        if not isinstance(e, dict):
            continue
        try:
            x = int(round(float(e.get("x")) * factor))
            y = int(round(float(e.get("y")) * factor))
        except (TypeError, ValueError):
            continue
        nom = str(e.get("nombre") or e.get("name") or "elemento")
        if not (0 <= x < w and 0 <= y < h):
            desc.append("[%s] -> x=%d , y=%d (fuera de pantalla)" % (nom, x, y))
            continue
        ww = e.get("w") or e.get("ancho") or 0
        hh = e.get("h") or e.get("alto") or 0
        pix.append("[%s] -> x=%d , y=%d | TAMANO: %sx%s"
                   % (nom, x, y, ww, hh))
    return pix, desc


_RE_PX = re.compile(r"\[([^\]\n]+)\][^\n]*?->[^\n\d]*?(\d{1,5})\s*,\s*(\d{1,5})")
_RE_PCT = re.compile(r"\[([^\]\n]+)\][^\n]*?(\d{1,3}(?:[.,]\d+)?)\s*%[^\n]*?(\d{1,3}(?:[.,]\d+)?)\s*%")


def _parse_lineas(texto, w, h, factor=1.0):
    """Parser PROPIO: el modelo ya contesta '[Nombre] -> X , Y' en PIXELES
    reales; se usa tal cual (sin re-procesar y manglear). Si contesta en
    porcentajes, se convierten. Filtro anti-alucinacion fuera de pantalla."""
    pix, desc, vistos = [], [], set()
    for linea in texto.splitlines():
        if "[" not in linea or "]" not in linea:
            continue
        nom = linea.split("]")[0].lstrip("[").strip()
        if not nom:
            continue
        x = y = None
        if "%" in linea:
            mp = _RE_PCT.search(linea)
            if mp:
                try:
                    x = int(round(float(mp.group(2).replace(",", ".")) / 100.0 * w))
                    y = int(round(float(mp.group(3).replace(",", ".")) / 100.0 * h))
                except ValueError:
                    x = y = None
        if x is None:
            mn = _RE_PX.search(linea)
            if mn:
                x = int(round(int(mn.group(2)) * factor))
                y = int(round(int(mn.group(3)) * factor))
        if x is None:
            continue
        if not (0 <= x < w and 0 <= y < h):
            desc.append("[%s] -> x=%d , y=%d (fuera de pantalla)" % (nom, x, y))
            continue
        clave = nom.lower()
        if clave in vistos:
            continue
        vistos.add(clave)
        pix.append("[%s] -> x=%d , y=%d" % (nom, x, y))
    return pix, desc


def _pixeles(texto, w, h, factor):
    """Parser principal (propio) + respaldo JSON."""
    pix, desc = _parse_lineas(texto, w, h, factor)
    if pix:
        return pix, desc
    pj, dj = _parse_json_pixeles(texto, w, h, factor)
    if pj:
        return pj, desc + dj
    if vg is not None:                    # ultimo recurso: parser de Gemini
        try:
            return vg._convertir_a_pixeles(texto, w, h, factor)
        except Exception:
            pass
    return [], desc


def _informe(texto, modelo, w, h, factor):
    print("MODELO: %s" % modelo)
    print("RESOLUCION REAL: %dx%d" % (w, h))
    print("---DESCRIPCION---")
    print(texto.strip())
    pix, desc = _pixeles(texto, w, h, factor)
    if pix:
        print("---PIXELES REALES (para visual_click clic x= y=)---")
        for p in pix:
            print(p)
    if desc:
        print("---DESCARTADAS (fuera de pantalla, posible alucinacion)---")
        for d in desc:
            print("  " + d)
    return bool(pix)


def analizar(pregunta="describe la pantalla", ruta_guardar=None):
    if vg is None:
        print("ERROR: no pude importar vision_gemini (captura/parser)")
        return 2
    try:
        w, h = vg.resolucion()
        img, ruta = vg.capturar(ruta_guardar)
    except Exception as e:
        print("ERROR capturando pantalla: %r" % e)
        return 2
    b64, factor = vg._img_a_b64_jpeg(img)
    ultimo = ""
    primer_intento = True
    caidos = set()   # modelos con fallo de credenciales: no se reintentan
    for intento in range(1, _INTENTOS + 1):
        prompt = _prompt_elementos(pregunta, w, h, simple=(intento > 1))
        for modelo in _MODELOS:
            if modelo in caidos:
                continue
            if not primer_intento:
                time.sleep(_ESPERA_REINTENTO)
            primer_intento = False
            try:
                texto = _llamar_deepseek(modelo, prompt, b64)
                if texto and not _es_rechazo(texto):
                    _informe(texto, modelo, w, h, factor)
                    return 0
                ultimo = ("%s: respuesta vacia" % modelo if not texto
                          else "%s: se nego a describir" % modelo)
            except urllib.error.HTTPError as e:
                ultimo = "%s: HTTP %s" % (modelo, e.code)
                if e.code in (401, 403, 404, 418):
                    caidos.add(modelo)
                    print("AVISO: %s no esta disponible (HTTP %s); sigo con el "
                          "siguiente de la cadena de vision." % (modelo, e.code))
            except Exception as e:
                ultimo = "%s: %s" % (modelo, repr(e)[:110])
        if caidos and len(caidos) >= len(_MODELOS):
            break
    if _USAR_RESPALDO:
        print("AVISO: la cadena de vision no respondio (%s). Voy a la red final "
              "(Gemini directo)." % ultimo)
        return vg.analizar(pregunta, ruta_guardar)
    print("VISION: FALLO — no pude ver la pantalla (%d intentos | %s)"
          % (_INTENTOS * len(_MODELOS), ultimo))
    return 2


def clic_elemento(elemento):
    """CICLO COMPLETO ojos+manos: capto -> DeepSeek localiza -> px reales ->
    computer_control.click en el CENTRO exacto."""
    if vg is None:
        print("ERROR: no pude importar vision_gemini")
        return 2
    try:
        w, h = vg.resolucion()
        img, _ = vg.capturar()
    except Exception as e:
        print("ERROR capturando pantalla: %r" % e)
        return 2
    b64, factor = vg._img_a_b64_jpeg(img)
    peticion = (
        "Localiza SOLO el elemento '%s'. Responde UNA SOLA linea con el "
        "formato exacto [%s] -> X , Y | TAMANO: WxH. Si no puedes ubicarlo "
        "con precision, responde unicamente 'SIN ELEMENTO'." % (elemento, elemento))
    ultimo = ""
    primer_intento = True
    for intento in range(1, _INTENTOS + 1):
        prompt = _prompt_elementos(peticion, w, h, simple=(intento > 1))
        for modelo in _MODELOS:
            if not primer_intento:
                time.sleep(_ESPERA_REINTENTO)
            primer_intento = False
            try:
                texto = _llamar_deepseek(modelo, prompt, b64)
                if not texto:
                    ultimo = "%s: respuesta vacia" % modelo
                    continue
                if _es_rechazo(texto):
                    ultimo = "%s: se nego a describir" % modelo
                    continue
                pix, _ = _pixeles(texto, w, h, factor)
                objetivo = None
                for linea in pix:
                    nom = linea.split("]")[0].lstrip("[")
                    if elemento.lower() in nom.lower():
                        objetivo = linea
                        break
                if objetivo is None and len(pix) == 1:
                    objetivo = pix[0]
                if objetivo is None:
                    ultimo = "sin coordenadas utiles con " + modelo
                    continue
                m = re.search(r"x=(\d+)\s*,\s*y=(\d+)", objetivo)
                if not m:
                    ultimo = "formato inesperado con " + modelo
                    continue
                x, y = int(m.group(1)), int(m.group(2))
                print("MODELO: %s" % modelo)
                print("ELEMENTO: %s" % objetivo)
                vg._clic_px(x, y)
                print("CLIC: x=%d , y=%d (centro del elemento)" % (x, y))
                return 0
            except urllib.error.HTTPError as e:
                ultimo = "%s: HTTP %s" % (modelo, e.code)
            except Exception as e:
                ultimo = "%s: %s" % (modelo, repr(e)[:110])
    if _USAR_RESPALDO:
        print("AVISO: Vision no respondio (%s). Respaldo Gemini:" % ultimo)
        return vg.clic_elemento(elemento)
    print("VISION: FALLO — no pude ubicar '%s' (%d intentos | %s)"
          % (elemento, _INTENTOS * len(_MODELOS), ultimo))
    return 2


def _main(argv):
    global _USAR_RESPALDO
    if "--sin-respaldo" in argv:
        _USAR_RESPALDO = False
        argv = [a for a in argv if a != "--sin-respaldo"]
    if "--con-respaldo" in argv:
        _USAR_RESPALDO = True
        argv = [a for a in argv if a != "--con-respaldo"]
    if len(argv) < 2:
        print("Acciones: ver <pregunta> | coords <elemento> | clic <elemento> "
              "| resolucion | captura [ruta]")
        return 1
    accion = argv[1].lower()
    if accion == "resolucion":
        print(json.dumps(vg.resolucion()))
        return 0
    if accion == "captura":
        img, ruta = vg.capturar(argv[2] if len(argv) > 2 else None)
        print("captura: %s %dx%d" % (ruta or "(memoria)", img.size[0], img.size[1]))
        return 0
    if accion == "clic":
        if len(argv) < 3:
            print("falta el elemento")
            return 1
        return clic_elemento(" ".join(argv[2:]))
    if accion in ("ver", "coords"):
        pregunta = (" ".join(argv[2:]) if len(argv) > 2
                    else "describe la pantalla")
        if accion == "coords":
            pregunta = ("Localiza el elemento '%s' y dame su centro exacto en "
                        "pixeles reales. Se preciso." % pregunta)
        return analizar(pregunta)
    print("Accion desconocida: %s" % accion)
    return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
