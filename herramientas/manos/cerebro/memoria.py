"""memoria.py - Persistencia del cerebro de JARVIS.

Guarda en disco: checkpoints (config.json + modelo.pt), diario.json,
experiencia.pt (replay + fisher + pesos previos POR TAREA) e historial.
"""
import json
import os

import torch

RAIZ = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(RAIZ, "datos")
CHECKPOINTS = os.path.join(DATOS, "checkpoints")
DIARIO = os.path.join(DATOS, "diario.json")


def _asegurar_carpetas():
    os.makedirs(CHECKPOINTS, exist_ok=True)


def ruta_checkpoint(nombre):
    return os.path.join(CHECKPOINTS, str(nombre))


def existe(nombre):
    return os.path.isdir(ruta_checkpoint(nombre))


def guardar_checkpoint(nombre, modelo, config):
    """Guarda pesos del modelo y configuracion del cerebro."""
    _asegurar_carpetas()
    carpeta = ruta_checkpoint(nombre)
    os.makedirs(carpeta, exist_ok=True)
    torch.save(modelo.state_dict(), os.path.join(carpeta, "modelo.pt"))
    with open(os.path.join(carpeta, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2, default=str)


def torch_save(modelo, ruta):
    torch.save(modelo.state_dict(), ruta)


def cargar_config(nombre):
    with open(os.path.join(ruta_checkpoint(nombre), "config.json"),
              "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_pesos(modelo, nombre, clases_por_tarea=None):
    ruta = os.path.join(ruta_checkpoint(nombre), "modelo.pt")
    estado = torch.load(ruta, weights_only=True, map_location="cpu")
    # Recrear las cabezas de salida que existan en el checkpoint
    for k in estado:
        if k.startswith("cabezas.") and k.endswith(".weight"):
            tarea = k.split(".")[1]
            if tarea not in modelo.cabezas:
                n_sal = None
                if clases_por_tarea and tarea in clases_por_tarea:
                    n_sal = clases_por_tarea[tarea]
                modelo._nueva_cabeza(tarea, n_sal)
    modelo.load_state_dict(estado)
    return modelo


def listar():
    """Lista los cerebros guardados (por nombre y fecha de modificacion)."""
    _asegurar_carpetas()
    cerebros = []
    for nombre in sorted(os.listdir(CHECKPOINTS)):
        carpeta = os.path.join(CHECKPOINTS, nombre)
        if os.path.isdir(carpeta):
            ruta_m = os.path.join(carpeta, "modelo.pt")
            mod = os.path.getmtime(ruta_m) if os.path.exists(ruta_m) else 0
            cerebros.append({"nombre": nombre, "modificado": mod})
    return cerebros


def registrar_diario(entrada):
    """Anade una entrada al diario de aprendizaje."""
    _asegurar_carpetas()
    diario = []
    if os.path.exists(DIARIO):
        try:
            with open(DIARIO, "r", encoding="utf-8") as f:
                diario = json.load(f)
        except Exception:
            diario = []
    diario.append(entrada)
    with open(DIARIO, "w", encoding="utf-8") as f:
        json.dump(diario, f, ensure_ascii=False, indent=2, default=str)


def leer_diario():
    if os.path.exists(DIARIO):
        with open(DIARIO, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def guardar_experiencia(nombre, tarea, X, y, fisher, theta_prev):
    """Guarda la experiencia de UNA tarea: muestras (replay), fisher y pesos.

    La experiencia se acumula por tarea dentro de experiencia.pt, de modo que
    el cerebro conserva el replay de TODAS las tareas aprendidas.
    X se guarda en espacio CRUDO (des-normalizado).
    """
    _asegurar_carpetas()
    ruta = os.path.join(ruta_checkpoint(nombre), "experiencia.pt")
    experiencia = {}
    if os.path.exists(ruta):
        try:
            experiencia = torch.load(ruta, weights_only=False)
        except Exception:
            experiencia = {}
    experiencia[tarea] = {
        "X": X.detach().cpu(),
        "y": y.detach().cpu(),
        "fisher": {k: v.detach().cpu() for k, v in fisher.items()},
        "theta_prev": {k: v.detach().cpu() for k, v in theta_prev.items()},
    }
    torch.save(experiencia, ruta)


def cargar_experiencia(nombre):
    """Carga la experiencia acumulada (dict tarea -> datos) o None."""
    ruta = os.path.join(ruta_checkpoint(nombre), "experiencia.pt")
    if not os.path.exists(ruta):
        return None
    try:
        return torch.load(ruta, weights_only=False)
    except Exception:
        return None


def guardar_historial(nombre, historial):
    _asegurar_carpetas()
    ruta = os.path.join(ruta_checkpoint(nombre), "historial.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2, default=str)