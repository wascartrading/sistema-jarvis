# -*- coding: utf-8 -*-
"""apuente_cerebro.py - Puente entre JARVIS y su cerebro neuronal LOCAL.

La fusion del cerebro neuronal con el flujo diario de JARVIS (20/08/2026,
regla del usuario: "fusionate para que vayas aprendiendo a dia a dia y dejes
de depender de modelos externos, con DeepSeek de respaldo").

QUE HACE este modulo:
  1. INTENCION LOCAL (red_neuronal/cerebro.pt): detecta la intencion de un
     pedido en espanol SIN gastar el modelo externo (abrir_app, buscar_web,
     reproducir_musica, crear_proyecto, modificar_codigo, automatizar,
     informacion, memoria, trading, sistema, saludo, despedida...).
  2. MEMORIA DE LARGO PLAZO (cerebro 'memoria' / lecciones): registra y
     aprende gustos, estilo, trabajo y habitos del usuario en una red
     neuronal, y los RECUERDA para usarlos en el dia a dia.
  3. APRENDIZAJE CONTINUO: consolida las lecciones acumuladas (reentrena la
     red) para que JARVIS mejore con el tiempo.

SEGURIDAD:
  - Todo es OPCIONAL y con fallback: si el cerebro local falla (falta torch,
    checkpoint corrupto, cualquier error), este puente devuelve None o False
    y JARVIS sigue con su flujo normal (modelo externo). NUNCA lanza hacia
    arriba.
  - Carga PEREZOSA (lazy): los checkpoints (60 MB) solo se cargan cuando se
    llama a una funcion que los necesita, no al importar el modulo.
  - RUTA de datos: las mismas del laboratorio (manos/cerebro/datos).
"""
import os
import sys

# Directorios del laboratorio
CARPETA_CEREBRO = os.path.dirname(os.path.abspath(__file__))
DATOS_CEREBRO = os.path.join(CARPETA_CEREBRO, "datos")
RUTA_LECCIONES = os.path.join(DATOS_CEREBRO, "lecciones.json")

# Interruptor global de la inteligencia local (False = desactivada).
# Se puede poner en False para volver al comportamiento 100% externo.
ACTIVO = True

# Categorias validas de lecciones (mismas que inventario del cerebro 'memoria')
CATEGORIAS_VALIDAS = ("gustos", "estilo", "trabajo", "habitos", "preferencias",
                      "datos", "reglas")

# UMBRAL de confianza para que una intencion local se considere "clara" y se
# pueda actuar sin el modelo externo. Debajo de esto, se delega al externo.
UMBRAL_CONFIANZA = 0.80

# Categorias/heuristicas para inferir la categoria de una leccion nueva
_CATEGORIA_PISTAS = {
    "gustos": ["gusta", "gustan", "prefiere", "me gusta", "me encanta",
               "favorito", "no me gusta", "odio", "amo"],
    "habitos": ["trabaja", "duerme", "madrug", "noche", "manana", "tarde",
                "diario", "cada dia", "habitual", "acostumbra"],
    "estilo": ["respuesta", "directo", "breve", "corto", "humor", "usted",
               "tuteo", "formal", "informal", "conciso", "habla"],
    "trabajo": ["trading", "iq", "opciones", "bot", "programa", "python",
                "proyecto", "trabaja", "negocio", "empresa", "cobro", "codigo"],
    "datos": ["nombre", "cumple", "correo", "telefono", "direccion", "numero",
              "fecha", "nacimiento", "edad", "equipo"],
    "reglas": ["nunca", "siempre", "prohibido", "no hagas", "no uses",
               "recuerda que", "regla", "aprende que"],
}


def _disponible():
    """True si la fusion esta activa y torch + el checkpoint base existen."""
    if not ACTIVO:
        return False
    try:
        import torch  # noqa: F401
        cp = os.path.join(DATOS_CEREBRO, "checkpoints", "cerebro.pt")
        return os.path.exists(cp)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# INTENCION LOCAL
# ---------------------------------------------------------------------------
_cerebro_intencion = None          # instancia unica de CerebroJarvis (lazy)
_cerebro_intencion_error = None


def _obtener_cerebro_intencion():
    """Carga (una sola vez) el cerebro de intenciones local. No lanza."""
    global _cerebro_intencion, _cerebro_intencion_error
    if _cerebro_intencion is not None:
        return _cerebro_intencion
    if _cerebro_intencion_error is not None:
        return None
    try:
        sys.path.insert(0, CARPETA_CEREBRO)
        from red_neuronal import CerebroJarvis
        _cerebro_intencion = CerebroJarvis()
    except Exception as e:
        _cerebro_intencion_error = repr(e)
        return None
    return _cerebro_intencion


def predecir_intencion(texto):
    """Detecta la intencion local de 'texto'. Devuelve (intencion, confianza)
    de la mejor, o (None, 0.0) si no hay cerebro/falla. Nunca lanza.

    Ej: predecir_intencion("abre youtube") -> ("abrir_app", 0.97)
    """
    if not texto or not _disponible():
        return None, 0.0
    try:
        cb = _obtener_cerebro_intencion()
        if cb is None:
            return None, 0.0
        resultados = cb.predecir(texto, top_k=1)
        if not resultados:
            return None, 0.0
        intencion, confianza = resultados[0]
        return intencion, confianza
    except Exception:
        return None, 0.0


def intencion_clara(texto):
    """True si el cerebro local detecta una intencion CONFIABLE (>= umbral).
    Es la puerta que permite actuar sin el modelo externo."""
    intencion, confianza = predecir_intencion(texto)
    return intencion is not None and confianza >= UMBRAL_CONFIANZA


# ---------------------------------------------------------------------------
# MEMORIA DE LARGO PLAZO (lecciones)
# ---------------------------------------------------------------------------
def _cargar_lecciones():
    if os.path.exists(RUTA_LECCIONES):
        try:
            with open(RUTA_LECCIONES, "r", encoding="utf-8") as f:
                import json
                return json.load(f)
        except Exception:
            pass
    return []


def _guardar_lecciones(lecciones):
    import json
    os.makedirs(os.path.dirname(RUTA_LECCIONES), exist_ok=True)
    with open(RUTA_LECCIONES, "w", encoding="utf-8") as f:
        json.dump(lecciones, f, ensure_ascii=False, indent=2)


def _inferir_categoria(texto, categoria=None):
    """Si no se dio categoria, la infiere por palabras clave. Fallback 'gustos'."""
    if categoria and categoria in CATEGORIAS_VALIDAS:
        return categoria
    if categoria and categoria not in CATEGORIAS_VALIDAS:
        categoria = None
    t = (texto or "").lower()
    if not categoria:
        mejor, mayor = None, 0
        for c, pistas in _CATEGORIA_PISTAS.items():
            n = sum(1 for p in pistas if p in t)
            if n > mayor:
                mayor, mejor = n, c
        if mejor:
            return mejor
    return "gustos"


def registrar_leccion(texto, categoria=None):
    """Registra una leccion nueva en lecciones.json (memoria del usuario).

    Devuelve True si se guardo, False si no. NUNCA lanza. JARVIS llama a esto
    cuando el usuario revela un gusto/preferencia/habito ("recuerda que...",
    "aprende que...", o simplemente lo menciona).
    """
    if not ACTIVO or not texto:
        return False
    try:
        texto_limpio = (texto or "").strip()
        if len(texto_limpio) < 4:
            return False
        import datetime
        cat = _inferir_categoria(texto_limpio, categoria)
        lecciones = _cargar_lecciones()
        # Evitar duplicados casi exactos
        for l in lecciones:
            if l.get("texto", "").strip().lower() == texto_limpio.lower():
                return False
        lecciones.append({
            "texto": texto_limpio,
            "categoria": cat,
            "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        _guardar_lecciones(lecciones)
        return True
    except Exception:
        return False


def recordar_por_categoria(categoria=None):
    """Devuelve las lecciones guardadas (opcionalmente filtradas por categoria).
    Ej: recordar_por_categoria("estilo") -> todas las de estilo."""
    if not ACTIVO:
        return []
    try:
        lecciones = _cargar_lecciones()
        if categoria:
            return [l for l in lecciones if l.get("categoria") == categoria]
        return lecciones
    except Exception:
        return []


def recordar_relevante(texto, top=5):
    """Recupera las lecciones MAS RELEVANTES para 'texto' por coincidencia de
    palabras. Sirve para que JARVIS recuerde gustos/habitos al responder.

    Devuelve una lista de dicts {'texto', 'categoria'}.
    """
    if not ACTIVO or not texto:
        return []
    try:
        import re
        palabras = set(re.findall(r"[a-záéíóúñü]+", (texto or "").lower()))
        palabras -= {"que", "como", "cuando", "donde", "para", "una", "unos",
                     "unas", "me", "te", "el", "la", "los", "las", "de", "y"}
        lecciones = _cargar_lecciones()
        puntuadas = []
        for l in lecciones:
            lp = set(re.findall(r"[a-záéíóúñü]+", (l.get("texto") or "").lower()))
            comunes = lp & palabras
            if comunes:
                puntuadas.append((len(comunes), l))
        puntuadas.sort(key=lambda x: -x[0])
        return [{"texto": l.get("texto"), "categoria": l.get("categoria")}
                for _, l in puntuadas[:top]]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# APRENDIZAJE CONTINUO (consolidar)
# ---------------------------------------------------------------------------
def consolidar(epocas=40):
    """Reentrena el cerebro 'memoria' con TODAS las lecciones acumuladas
    (aprendizaje continuo sin olvidar lo anterior). Devuelve (ok, detalle).
    Suele llamarse al final del dia o cuando se acumulan varias lecciones.

    Es lento (CPU) y puede tardar segundos; por eso se llama fueroa del hilo
    critico de respuesta (idea: un hilo o una tarea al cierre).
    """
    if not ACTIVO:
        return False, "cerebro local desactivado"
    try:
        sys.path.insert(0, CARPETA_CEREBRO)
        import lecciones as mod_lecciones
        lecciones = mod_lecciones._cargar_lecciones()
        if not lecciones:
            return False, "no hay lecciones que consolidar"
        cats = mod_lecciones._categorias(lecciones)
        # El cerebro 'memoria' ya existe (verificado); aprende la tarea
        # 'lecciones' de forma incremental.
        mod_lecciones.cmd_entrenar(_Args(epocas=epocas, lr=1e-3, batch=32,
                                         umbral=0.90, semilla=0, lam_ewc=2.0,
                                         silencioso=True))
        return True, "consolidado: %d lecciones en %d categorias" % (
            len(lecciones), len(cats))
    except Exception as e:
        return False, repr(e)


class _Args:
    """Mini-namespace para llamar a lecciones.cmd_entrenar sin argparse."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


def estado():
    """Resumen de la fusion del cerebro local. No lanza."""
    try:
        lecciones = _cargar_lecciones()
        cats = {}
        for l in lecciones:
            cats[l.get("categoria", "?")] = cats.get(l.get("categoria", "?"), 0) + 1
        intencion, conf = None, 0.0
        # Probamos con una frase de ejemplo para ver si el cerebro responde
        ok = _disponible()
        return {
            "activo": ACTIVO,
            "disponible": ok,
            "lecciones": len(lecciones),
            "categorias": cats,
        }
    except Exception:
        return {"activo": ACTIVO, "disponible": False}


if __name__ == "__main__":
    import json
    print("=== Estado de la fusion ===")
    print(json.dumps(estado(), ensure_ascii=False, indent=2))
    print("\n=== Intencion local (frases de prueba) ===")
    for t in ["abre youtube", "busca el clima", "reproduce musica",
              "hazme un juego", "recuerda que me gusta el cafe", "hola"]:
        i, c = predecir_intencion(t)
        print(f"  '{t}' -> {i} ({c:.0%})")
    print("\n=== Lecciones guardadas ===")
    for l in recordar_por_categoria():
        print(f"  [{l['categoria']}] {l['texto']}")
