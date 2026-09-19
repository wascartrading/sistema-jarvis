"""continuo.py - Aprendizaje continuo del cerebro de JARVIS.

El cerebro aprende tareas una tras otra SIN olvidar las anteriores, usando:
1. Cabezas por tarea: cada dominio tiene su propia capa de salida, asi las
   tareas no se pisan entre si (solucion estandar en aprendizaje continuo).
2. Replay de experiencia: guarda muestras de cada tarea y las reentrena.
3. Consolidacion elastica (EWC): ancla los pesos importantes de tareas viejas
   con el Fisher, para que aprender lo nuevo no los destruya.
4. Destilacion (Learning without Forgetting): el modelo nuevo imita al viejo
   en las tareas anteriores, conservando su comportamiento.
5. Crecimiento autonomo: si la precision no alcanza el umbral, la red inserta
   una capa nueva (profundiza) y sigue entrenando.
"""
import copy
import os

import torch

import datos as mod_datos
import entrenamiento as mod_entrenamiento
import memoria as mod_memoria
from red import crear_red


def crear_cerebro(nombre, entrada=2, salida=2, capas=6, ancho=64,
                  activacion="relu", dropout=0.05, semilla=42):
    """Crea un cerebro nuevo (red profunda) y lo guarda en disco."""
    if mod_memoria.existe(nombre):
        raise ValueError(f"Ya existe un cerebro llamado '{nombre}'")
    modelo = crear_red(entrada, salida, [ancho] * int(capas), activacion, dropout, semilla)
    config = {
        "nombre": nombre,
        "entrada": entrada,
        "salida": salida,
        "capas_ocultas": [ancho] * int(capas),
        "activacion": activacion,
        "dropout": dropout,
        "semilla": semilla,
        "creado": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tareas": [],
        "crecimientos": 0,
        "normalizacion": {"media": [0.0] * entrada, "std": [1.0] * entrada},
    }
    mod_memoria.guardar_checkpoint(nombre, modelo, config)
    return modelo, config


def cargar_cerebro(nombre):
    """Carga un cerebro guardado (pesos + config)."""
    if not mod_memoria.existe(nombre):
        raise ValueError(f"No existe el cerebro '{nombre}'")
    config = mod_memoria.cargar_config(nombre)
    modelo = crear_red(config["entrada"], config["salida"], config["capas_ocultas"],
                       config["activacion"], config["dropout"], config["semilla"])
    mod_memoria.cargar_pesos(modelo, nombre, config.get("clases_por_tarea"))
    return modelo, config


def _replay_por_tarea(experiencia, media, std, max_replay=1500):
    """Arma replay y validacion vieja agrupados por tarea (normalizados).

    Devuelve (replay_dict, val_dict): cada dict mapea tarea -> (X, y).
    """
    replay = {}
    val = {}
    if not experiencia:
        return replay, val
    for tarea, datos in experiencia.items():
        X = datos["X"]
        y = datos["y"]
        if X.shape[0] == 0:
            continue
        Xn = (X - media) / std
        n_v = min(X.shape[0], 500)
        perm = torch.randperm(X.shape[0])
        replay[tarea] = (Xn[perm][:max_replay], y[perm][:max_replay])
        val[tarea] = (Xn[perm][n_v:], y[perm][n_v:])
    return replay, val


def aprender_tarea(nombre, tarea, epocas=60, lr=1e-3, batch=64, umbral=0.90,
                   crecer=True, max_crecimientos=3, semilla=0, silencioso=False,
                   n_puntos=2000, lam_ewc=2.0, max_replay=1500):
    """Entrena una tarea sintetica (por nombre) sobre el cerebro."""
    X, y = mod_datos.generar_tarea(tarea, n_puntos=n_puntos, semilla=semilla)
    return aprender_datos(nombre, tarea, X, y, epocas=epocas, lr=lr, batch=batch,
                          umbral=umbral, crecer=crecer,
                          max_crecimientos=max_crecimientos, semilla=semilla,
                          silencioso=silencioso, lam_ewc=lam_ewc,
                          max_replay=max_replay)


def aprender_datos(nombre, tarea, X, y, epocas=60, lr=1e-3, batch=64,
                   umbral=0.90, crecer=True, max_crecimientos=3, semilla=0,
                   silencioso=False, lam_ewc=2.0, max_replay=1500):
    """Entrena una tarea con DATOS REALES (tensores X, y) sobre el cerebro.

    Es la puerta para que JARVIS le ensene al cerebro lo que aprende del
    usuario (gustos, habitos, preferencias): cada dominio nuevo es una tarea
    con su propia cabeza de salida, y las anteriores se conservan con replay
    equitativo + EWC + destilacion.

    Devuelve (modelo, config, metricas). Si crecer=True y la precision no
    llega al umbral, la red inserta capas nuevas automaticamente.
    """
    modelo, config = cargar_cerebro(nombre)
    if X.dim() == 1:
        X = X.unsqueeze(0)
    # y debe quedar 1D (n,): si viene (1, n) o (n, 1), aplanar
    if y.dim() == 2:
        y = y.reshape(-1)
    y = y.long()
    if os.environ.get("DEBUG_CEREBRO"):
        print(f"[debug] X {X.shape} y {y.shape}")
    # Con pocas muestras, validacion minima (1) y el resto para entrenar
    n_total = X.shape[0]
    if n_total < 20:
        Xtr, ytr, Xva, yva = X, y, X[:1], y[:1]
    else:
        Xtr, ytr, Xva, yva = mod_datos.dividir(X, y, semilla=semilla)
    if os.environ.get("DEBUG_CEREBRO"):
        print(f"[debug] Xtr {Xtr.shape} ytr {ytr.shape} Xva {Xva.shape} yva {yva.shape}")

    # Normalizacion GLOBAL consistente entre tareas: la primera fija media/std.
    normalizacion = config.get("normalizacion_global")
    if normalizacion is None:
        media = Xtr.mean(dim=0)
        std = Xtr.std(dim=0).clamp_min(1e-6)
        normalizacion = {"media": media.tolist(), "std": std.tolist()}
        config["normalizacion_global"] = normalizacion
        config["normalizacion"] = normalizacion
    media = torch.tensor(normalizacion["media"])
    std = torch.tensor(normalizacion["std"]).clamp_min(1e-6)
    Xtr = (Xtr - media) / std
    Xva = (Xva - media) / std

    # Numero de clases de la tarea (cada tarea puede tener el suyo)
    n_clases = int(y.max().item()) + 1

    # Cabeza de salida para esta tarea (si no existe todavia). Si ya existe
    # pero con MENOS salidas que clases (aparecieron categorias nuevas), se
    # recrea con el tamano correcto: solo se pierde esa cabeza, las demas
    # tareas del cerebro se conservan.
    if tarea not in modelo.cabezas:
        modelo._nueva_cabeza(tarea, n_clases)
    elif modelo.cabezas[tarea].out_features < n_clases:
        del modelo.cabezas[tarea]
        modelo._nueva_cabeza(tarea, n_clases)
    config.setdefault("clases_por_tarea", {})[tarea] = n_clases

    experiencia = mod_memoria.cargar_experiencia(nombre) or {}
    ewc = None
    destilacion = None
    X_viejo = None
    y_viejo = None
    Xva_viejo = None
    tareas_viejas = None
    replay_prev, val_prev = _replay_por_tarea(experiencia, media, std, max_replay)
    hay_viejas = bool(replay_prev)
    if hay_viejas:
        # Con conocimiento previo, ajustar mas fino (menos destructivo)
        lr = lr * 0.4
        # Replay: muestras de TODAS las tareas viejas (cada una con su tarea
        # para usar su cabeza). Se entrena por separado de las nuevas: las
        # nuevas con la cabeza de la tarea actual, las viejas con la suya.
        partes_x = [v[0] for v in replay_prev.values()]
        partes_y = [v[1] for v in replay_prev.values()]
        X_viejo = torch.cat(partes_x)
        y_viejo = torch.cat(partes_y)
        tareas_viejas = []
        for t, (xv, yv) in replay_prev.items():
            tareas_viejas.extend([t] * xv.shape[0])
        # EWC consolidado: suma de fishers de todas las tareas anteriores
        fisher_total = None
        for t, datos in experiencia.items():
            f = datos["fisher"]
            if fisher_total is None:
                fisher_total = {k: v.clone() for k, v in f.items()}
            else:
                for k in fisher_total:
                    if k in f:
                        fisher_total[k] = fisher_total[k] + f[k]
        theta_prev = {}
        for t, datos in experiencia.items():
            for k, v in datos["theta_prev"].items():
                theta_prev[k] = v
        ewc = {"fisher": fisher_total, "theta_prev": theta_prev, "lam": lam_ewc}
        # Destilacion: copia congelada del modelo ANTES de esta tarea. Al
        # imitar sus salidas en las tareas viejas, el comportamiento previo
        # se conserva.
        modelo_viejo = copy.deepcopy(modelo)
        modelo_viejo.eval()
        destilacion = {"modelo_viejo": modelo_viejo, "T": 2.0, "lam": 0.5}
        # Validacion de tareas viejas (dict tarea -> (X, y)) para elegir el
        # checkpoint sin sacrificar lo ya aprendido.
        Xva_viejo = {t: v for t, v in val_prev.items()}

    if not silencioso:
        print(f"Cerebro '{nombre}' aprendiendo tarea '{tarea}' "
              f"({Xtr.shape[0]} muestras, {modelo.profundidad()} capas)")

    metricas = None
    crecimientos = 0
    epocas_actuales = epocas
    while True:
        modelo, metricas, historial = mod_entrenamiento.entrenar(
            modelo, Xtr, ytr, Xva, yva, epocas=epocas_actuales, lr=lr, batch=batch,
            ewc=ewc, destilacion=destilacion, silencioso=silencioso,
            Xva_viejo=Xva_viejo,
            X_viejo=X_viejo, y_viejo=y_viejo, tarea_actual=tarea,
            tareas_viejas=tareas_viejas,
            parada_por_nueva=hay_viejas)
        precision = metricas.get("precision_va", 0.0)
        if (crecer and precision < umbral and crecimientos < max_crecimientos
                and modelo.profundidad() < 12):
            crecimientos += 1
            modelo.insertar_capa()
            config["capas_ocultas"] = [c.out_features for c in modelo.capas]
            config["crecimientos"] = config.get("crecimientos", 0) + 1
            if not silencioso:
                print(f"  precision {precision:.2%} < umbral {umbral:.0%}: "
                      f"insertando capa {crecimientos} (ahora {modelo.profundidad()} capas)")
            epocas_actuales = max(15, epocas // 2)
            lr = lr * 0.5
            continue
        break

    # Guardar experiencia de esta tarea para el futuro (replay + EWC).
    # Se guarda en espacio CRUDO (des-normalizado).
    n_guardar = min(Xtr.shape[0], max_replay)
    perm = torch.randperm(Xtr.shape[0])[:n_guardar]
    X_guardar = Xtr[perm].detach().cpu()
    y_guardar = ytr[perm].detach().cpu()
    fisher = mod_entrenamiento.calcular_fisher(modelo, X_guardar, y_guardar, tarea=tarea)
    theta_prev = {k: v.detach().clone() for k, v in modelo.state_dict().items()}
    X_crudo = X_guardar * std + media
    mod_memoria.guardar_experiencia(nombre, tarea, X_crudo, y_guardar, fisher, theta_prev)

    # Registrar en config y diario (sin duplicar si la tarea ya existia)
    entrada_tarea = {
        "tarea": tarea,
        "semilla": semilla,
        "precision_va": round(metricas.get("precision_va", 0.0), 4),
        "perdida_va": round(metricas.get("perdida_va", 0.0), 4),
        "epocas": epocas,
        "crecimientos": crecimientos,
        "capas": modelo.profundidad(),
    }
    tareas = config.get("tareas", [])
    # Eliminar TODAS las entradas previas de esta tarea (evita duplicados)
    tareas = [t for t in tareas if t.get("tarea") != tarea]
    tareas.append(entrada_tarea)
    config["tareas"] = tareas
    mod_memoria.guardar_checkpoint(nombre, modelo, config)
    mod_memoria.guardar_historial(nombre, historial)
    mod_memoria.registrar_diario({
        "cerebro": nombre,
        "tarea": tarea,
        "precision_va": round(metricas.get("precision_va", 0.0), 4),
        "perdida_va": round(metricas.get("perdida_va", 0.0), 4),
        "capas": modelo.profundidad(),
        "parametros": modelo.contar_parametros(),
        "crecimientos": crecimientos,
    })
    return modelo, config, metricas


def evaluar_tarea(nombre, tarea, semilla=0, n_puntos=2000):
    """Evalua el cerebro en una tarea (usa la cabeza de esa tarea)."""
    modelo, config = cargar_cerebro(nombre)
    if tarea not in modelo.cabezas:
        raise ValueError(f"El cerebro '{nombre}' no conoce la tarea '{tarea}'")
    X, y = mod_datos.generar_tarea(tarea, n_puntos=n_puntos, semilla=semilla)
    media = torch.tensor(config["normalizacion"]["media"])
    std = torch.tensor(config["normalizacion"]["std"]).clamp_min(1e-6)
    X = (X - media) / std
    perdida, precision, _ = mod_entrenamiento.evaluar(modelo, X, y, tarea=tarea)
    return precision, perdida


def predecir(nombre, x, y, tarea=None):
    """Predice la clase de un punto (x, y) con la cabeza de 'tarea' (o la
    primera disponible si no se indica)."""
    modelo, config = cargar_cerebro(nombre)
    modelo.eval()
    if tarea is None:
        tarea = next(iter(modelo.cabezas))
    if tarea not in modelo.cabezas:
        raise ValueError(f"El cerebro '{nombre}' no conoce la tarea '{tarea}'")
    media = torch.tensor(config["normalizacion"]["media"])
    std = torch.tensor(config["normalizacion"]["std"]).clamp_min(1e-6)
    punto = (torch.tensor([x, y], dtype=torch.float32) - media) / std
    return predecir_vector(nombre, punto, tarea)


def predecir_vector(nombre, vector, tarea=None):
    """Predice la clase de un VECTOR (ya en el espacio de la tarea) con la
    cabeza indicada (o la primera disponible). Devuelve (clase, probs)."""
    modelo, config = cargar_cerebro(nombre)
    modelo.eval()
    if tarea is None:
        tarea = next(iter(modelo.cabezas))
    if tarea not in modelo.cabezas:
        raise ValueError(f"El cerebro '{nombre}' no conoce la tarea '{tarea}'")
    if not isinstance(vector, torch.Tensor):
        vector = torch.tensor(vector, dtype=torch.float32)
    if vector.dim() == 1:
        vector = vector.unsqueeze(0)
    media = torch.tensor(config["normalizacion"]["media"])
    std = torch.tensor(config["normalizacion"]["std"]).clamp_min(1e-6)
    punto = (vector - media) / std
    with torch.no_grad():
        salida = modelo(punto, tarea)
        prob = torch.softmax(salida, dim=1)[0]
        clase = int(prob.argmax().item())
    return clase, prob.tolist()


def evaluar_datos(nombre, tarea, X, y):
    """Evalua el cerebro con datos REALES (tensores X, y) en una tarea."""
    modelo, config = cargar_cerebro(nombre)
    if tarea not in modelo.cabezas:
        raise ValueError(f"El cerebro '{nombre}' no conoce la tarea '{tarea}'")
    if X.dim() == 1:
        X = X.unsqueeze(0)
    if y.dim() == 2:
        y = y.reshape(-1)
    y = y.long()
    media = torch.tensor(config["normalizacion"]["media"])
    std = torch.tensor(config["normalizacion"]["std"]).clamp_min(1e-6)
    X = (X - media) / std
    perdida, precision, _ = mod_entrenamiento.evaluar(modelo, X, y, tarea=tarea)
    return precision, perdida


def estado(nombre):
    """Resumen del estado de un cerebro."""
    modelo, config = cargar_cerebro(nombre)
    return {
        "nombre": nombre,
        "arquitectura": modelo.arquitectura(),
        "capas": modelo.profundidad(),
        "parametros": modelo.contar_parametros(),
        "tareas": config.get("tareas", []),
        "crecimientos": config.get("crecimientos", 0),
        "creado": config.get("creado", ""),
    }