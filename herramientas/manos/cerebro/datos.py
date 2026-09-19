"""datos.py - Generadores de tareas de aprendizaje para el cerebro de JARVIS.

Tareas sinteticas clasicas de clasificacion 2D: espiral, lunas, circulos y
gaussianas. Cada tarea puede variarse con una semilla distinta para crear
problemas nuevos cada vez, de modo que la red siempre tenga algo que aprender.
"""
import math

import torch


def espiral(n_puntos, clases=2, ruido=0.15, semilla=0):
    """Espiral multiclase: el clasico para probar redes profundas."""
    g = torch.Generator().manual_seed(semilla)
    n = n_puntos // clases
    X = torch.zeros(n * clases, 2)
    y = torch.zeros(n * clases, dtype=torch.long)
    for c in range(clases):
        t = torch.arange(n, dtype=torch.float32) / n
        ang = t * 2 * math.pi * 2 + (c * 2 * math.pi) / clases
        r = t * 2.2 + 0.2
        X[c * n:(c + 1) * n, 0] = r * torch.cos(ang) + torch.randn(n, generator=g) * ruido
        X[c * n:(c + 1) * n, 1] = r * torch.sin(ang) + torch.randn(n, generator=g) * ruido
        y[c * n:(c + 1) * n] = c
    return X, y


def lunas(n_puntos, ruido=0.1, semilla=0):
    """Dos medias lunas: problema de frontera no lineal."""
    g = torch.Generator().manual_seed(semilla)
    n = n_puntos // 2
    t = torch.linspace(0, math.pi, n)
    x1 = torch.cos(t) + torch.randn(n, generator=g) * ruido
    y1 = torch.sin(t) + torch.randn(n, generator=g) * ruido
    x2 = 1 - torch.cos(t) + torch.randn(n, generator=g) * ruido
    y2 = 0.3 - torch.sin(t) + torch.randn(n, generator=g) * ruido
    X = torch.stack([torch.cat([x1, x2]), torch.cat([y1, y2])], dim=1)
    y = torch.cat([torch.zeros(n, dtype=torch.long), torch.ones(n, dtype=torch.long)])
    return X, y


def circulos(n_puntos, ruido=0.12, semilla=0):
    """Anillo interior vs exterior: problema de concentracion."""
    g = torch.Generator().manual_seed(semilla)
    n = n_puntos // 2
    t1 = torch.rand(n, generator=g) * 2 * math.pi
    t2 = torch.rand(n, generator=g) * 2 * math.pi
    r1 = 0.6 + torch.rand(n, generator=g) * 0.4
    r2 = 1.6 + torch.rand(n, generator=g) * 0.6
    x1 = r1 * torch.cos(t1) + torch.randn(n, generator=g) * ruido
    y1 = r1 * torch.sin(t1) + torch.randn(n, generator=g) * ruido
    x2 = r2 * torch.cos(t2) + torch.randn(n, generator=g) * ruido
    y2 = r2 * torch.sin(t2) + torch.randn(n, generator=g) * ruido
    X = torch.stack([torch.cat([x1, x2]), torch.cat([y1, y2])], dim=1)
    y = torch.cat([torch.zeros(n, dtype=torch.long), torch.ones(n, dtype=torch.long)])
    return X, y


def gaussianas(n_puntos, semilla=0):
    """Dos nubes de puntos separadas."""
    g = torch.Generator().manual_seed(semilla)
    n = n_puntos // 2
    c1 = torch.tensor([-1.5, -1.0])
    c2 = torch.tensor([1.5, 1.0])
    X = torch.cat([
        c1 + torch.randn(n, 2, generator=g) * 0.5,
        c2 + torch.randn(n, 2, generator=g) * 0.5,
    ])
    y = torch.cat([torch.zeros(n, dtype=torch.long), torch.ones(n, dtype=torch.long)])
    return X, y


def cuatro_gaussianas(n_puntos, semilla=0):
    """Cuatro nubes: tarea mas exigente (4 clases)."""
    g = torch.Generator().manual_seed(semilla)
    n = n_puntos // 4
    centros = [(-2.0, 2.0), (2.0, 2.0), (-2.0, -2.0), (2.0, -2.0)]
    X, y = [], []
    for c, (cx, cy) in enumerate(centros):
        X.append(torch.tensor([cx, cy]) + torch.randn(n, 2, generator=g) * 0.6)
        y.append(torch.full((n,), c, dtype=torch.long))
    return torch.cat(X), torch.cat(y)


TAREAS = {
    "espiral": espiral,
    "lunas": lunas,
    "circulos": circulos,
    "gaussianas": gaussianas,
    "4gaussianas": cuatro_gaussianas,
}


def generar_tarea(nombre, n_puntos=2000, semilla=0, ruido=None):
    """Genera (X, y) para una tarea por nombre."""
    if nombre not in TAREAS:
        raise ValueError(f"Tarea desconocida: {nombre}. Disponibles: {list(TAREAS)}")
    if ruido is None:
        ruido = {"espiral": 0.15, "lunas": 0.1, "circulos": 0.12}.get(nombre)
    fn = TAREAS[nombre]
    if nombre in ("gaussianas", "4gaussianas"):
        return fn(n_puntos, semilla)
    if nombre == "espiral":
        return fn(n_puntos, 2, ruido, semilla)
    return fn(n_puntos, ruido, semilla)


def dividir(X, y, fraccion_validacion=0.2, semilla=0):
    """Divide en entrenamiento y validacion mezclando con semilla fija."""
    g = torch.Generator().manual_seed(semilla)
    n = X.shape[0]
    perm = torch.randperm(n, generator=g)
    n_val = int(n * fraccion_validacion)
    return X[perm[n_val:]], y[perm[n_val:]], X[perm[:n_val]], y[perm[:n_val]]
