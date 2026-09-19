"""entrenamiento.py - Entrenamiento y evaluacion de la red profunda de JARVIS.

Incluye: bucle de entrenamiento con AdamW, reduccion de tasa por meseta,
parada temprana por validacion, calculo de Fisher (para consolidacion elastica
EWC contra el olvido), destilacion (Learning without Forgetting) y evaluacion.
"""
import torch
import torch.nn as nn


def entrenar(modelo, Xtr, ytr, Xva, yva, epocas=60, lr=1e-3, batch=64,
             peso_decay=1e-4, paciencia=10, ewc=None, destilacion=None,
             silencioso=False, semilla=42, Xva_viejo=None, yva_viejo=None,
             peso_viejo=1.0, X_viejo=None, y_viejo=None,
             seleccion_por_precision=False, parada_por_nueva=False,
             proporcion_viejas=0.5, tarea_actual=None, tareas_viejas=None):
    """Entrena por epocas y devuelve el mejor modelo segun validacion.

    ewc es opcional: dict con 'fisher', 'theta_prev' y 'lam'. Ancla los pesos
    importantes de tareas viejas para no destruirlos al aprender lo nuevo.

    destilacion es opcional: dict con 'modelo_viejo' (copia congelada antes de
    esta tarea), 'T' (temperatura) y 'lam'. Iguala las salidas del modelo
    actual con las del viejo en las muestras VIEJAS (X_viejo/y_viejo), de modo
    que el comportamiento previo se conserva sin frenar la tarea nueva.

    X_viejo/y_viejo: muestras de tareas anteriores (replay), entrenadas con CE
    + destilacion. Xva_viejo/yva_viejo: validacion de tareas anteriores para
    elegir el checkpoint sin sacrificar lo ya aprendido. Cuando hay tarea
    nueva y parada_por_nueva=True, la parada temprana la decide SOLO la tarea
    nueva (la vieja ya esta en su optimo y no mejora, cortar por ella no deja
    converger lo nuevo).
    """
    torch.manual_seed(semilla)
    dispositivo = next(modelo.parameters()).device
    Xtr, ytr = Xtr.to(dispositivo), ytr.to(dispositivo)
    Xva, yva = Xva.to(dispositivo), yva.to(dispositivo)
    if Xva_viejo is not None:
        # dict {tarea: (X, y)}: mover cada tensor al dispositivo
        Xva_viejo = {t: (x.to(dispositivo), y.to(dispositivo))
                     for t, (x, y) in Xva_viejo.items()}
    if X_viejo is not None:
        X_viejo = X_viejo.to(dispositivo)
        y_viejo = y_viejo.to(dispositivo)
    n = Xtr.shape[0]
    batch = min(batch, max(n, 1))
    mejor_perdida = float("inf")
    mejor_precision = -1.0
    mejor_precision_nueva = -1.0
    espera_nueva = 0
    mejor_estado = None
    mejores_metricas = {}
    espera = 0
    historial = []
    optimizador = torch.optim.AdamW(modelo.parameters(), lr=lr, weight_decay=peso_decay)
    programador = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizador, mode="min", factor=0.5, patience=4, min_lr=1e-6)
    criterio = nn.CrossEntropyLoss()
    if destilacion is not None:
        modelo_viejo = destilacion["modelo_viejo"].to(dispositivo)
        modelo_viejo.eval()
        T = destilacion.get("T", 2.0)
        lam_kd = destilacion.get("lam", 0.5)
        criterio_kd = nn.KLDivLoss(reduction="batchmean")

    for epoca in range(1, epocas + 1):
        modelo.train()
        perdida_total = 0.0
        n_batchs = 0
        if X_viejo is not None:
            # Batches MEZCLADOS: proporcion_viejas de viejas, el resto nuevas.
            # Las nuevas usan la cabeza de la tarea actual; las viejas usan la
            # cabeza de SU tarea (tareas_viejas alineado con X_viejo). Cada
            # grupo hace su propio forward para no mezclar dimensiones de
            # salida. Las viejas se reparten EQUITATIVAMENTE entre las tareas
            # anteriores: si hay 4 tareas viejas, cada una aporta la misma
            # cantidad, para que ninguna se diluya (leccion: la espiral se
            # olvidaba al competir con muchas tareas).
            n_v = max(1, int(batch * proporcion_viejas))
            n_n = batch - n_v
            # Agrupar indices viejos por tarea
            tareas_unicas = []
            for t_v in tareas_viejas:
                if t_v not in tareas_unicas:
                    tareas_unicas.append(t_v)
            idx_por_tarea = {t: [] for t in tareas_unicas}
            for j, t_v in enumerate(tareas_viejas):
                idx_por_tarea[t_v].append(j)
            for t_v in tareas_unicas:
                torch.manual_seed(semilla + epoca + len(tareas_unicas))
                idx_por_tarea[t_v] = torch.tensor(idx_por_tarea[t_v])[
                    torch.randperm(len(idx_por_tarea[t_v]))].tolist()
            perm = torch.randperm(n)
            n_pares = min(n // n_n, min(len(v) for v in idx_por_tarea.values()) // 1)
            n_por_tarea = max(1, n_v // len(tareas_unicas))
            for k in range(n_pares):
                idx = perm[k * n_n:(k + 1) * n_n]
                xb_n, yb_n = Xtr[idx], ytr[idx]
                optimizador.zero_grad()
                perdida = 0.0
                # Nuevas: CE con la cabeza de la tarea actual
                salida_n = modelo(xb_n, tarea_actual)
                perdida = perdida + criterio(salida_n, yb_n)
                # Viejas: CE + destilacion, una porcion de CADA tarea anterior
                for t_v in tareas_unicas:
                    lista = idx_por_tarea[t_v]
                    ini = k * n_por_tarea
                    fin = min(ini + n_por_tarea, len(lista))
                    if fin <= ini:
                        continue
                    idx_v = torch.tensor(lista[ini:fin])
                    xb_v, yb_v = X_viejo[idx_v], y_viejo[idx_v]
                    salida_v = modelo(xb_v, t_v)
                    perdida = perdida + criterio(salida_v, yb_v)
                    if destilacion is not None:
                        with torch.no_grad():
                            salida_vieja = modelo_viejo(xb_v, t_v)
                        log_p_nueva = torch.log_softmax(salida_v / T, dim=1)
                        p_vieja = torch.softmax(salida_vieja / T, dim=1)
                        perdida = perdida + lam_kd * criterio_kd(log_p_nueva, p_vieja) * (T * T)
                if ewc is not None:
                    perdida = perdida + _penalizacion_ewc(modelo, ewc)
                perdida.backward()
                optimizador.step()
                perdida_total += perdida.item()
                n_batchs += 1
        else:
            perm = torch.randperm(n)
            for i in range(0, n, batch):
                idx = perm[i:i + batch]
                xb, yb = Xtr[idx], ytr[idx]
                optimizador.zero_grad()
                salida = modelo(xb, tarea_actual)
                perdida = criterio(salida, yb)
                if ewc is not None:
                    perdida = perdida + _penalizacion_ewc(modelo, ewc)
                perdida.backward()
                optimizador.step()
                perdida_total += perdida.item()
                n_batchs += 1

        perdida_va, precision_va, precision_tr = evaluar(
            modelo, Xva, yva, Xtr, ytr, batch, tarea=tarea_actual)
        perdida_combinada = perdida_va
        precision_combinada = precision_va
        if Xva_viejo is not None:
            # Xva_viejo es dict {tarea: (X, y)}: cada tarea vieja se evalua
            # con SU cabeza y se promedian las metricas.
            perdidas_v, precisiones_v = [], []
            for t_v, (Xv, yv) in Xva_viejo.items():
                pv_, pr_, _ = evaluar(modelo, Xv, yv, batch=batch, tarea=t_v)
                perdidas_v.append(pv_)
                precisiones_v.append(pr_)
            perdida_vieja = sum(perdidas_v) / len(perdidas_v)
            precision_vieja = sum(precisiones_v) / len(precisiones_v)
            perdida_combinada = (perdida_va + peso_viejo * perdida_vieja) / (1.0 + peso_viejo)
            precision_combinada = (precision_va + peso_viejo * precision_vieja) / (1.0 + peso_viejo)
        perdida_prom = perdida_total / max(n_batchs, 1)
        historial.append({"epoca": epoca, "perdida_tr": perdida_prom,
                          "perdida_va": perdida_va, "precision_va": precision_va})
        if not silencioso:
            print(f"  epoca {epoca}/{epocas} | perdida {perdida_prom:.4f} "
                  f"| validacion {perdida_va:.4f} | precision {precision_va:.2%}")

        programador.step(perdida_combinada)
        if seleccion_por_precision:
            mejora = precision_combinada > mejor_precision + 1e-4
        else:
            mejora = perdida_combinada < mejor_perdida - 1e-5
        if mejora:
            if seleccion_por_precision:
                mejor_precision = precision_combinada
            else:
                mejor_perdida = perdida_combinada
            mejor_estado = {k: v.detach().clone() for k, v in modelo.state_dict().items()}
            mejores_metricas = {"perdida_va": perdida_va, "precision_va": precision_va,
                                "precision_tr": precision_tr, "epoca": epoca}
            espera = 0
        else:
            espera += 1
            if parada_por_nueva:
                if precision_va > mejor_precision_nueva + 1e-4:
                    mejor_precision_nueva = precision_va
                    espera_nueva = 0
                else:
                    espera_nueva += 1
                    if espera_nueva >= paciencia:
                        if not silencioso:
                            print(f"  parada por tarea nueva en epoca {epoca}")
                        break
            elif espera >= paciencia:
                if not silencioso:
                    print(f"  parada temprana en epoca {epoca}")
                break

    if mejor_estado is not None:
        modelo.load_state_dict(mejor_estado)
    return modelo, mejores_metricas, historial


def evaluar(modelo, Xva, yva, Xtr=None, ytr=None, batch=256, tarea=None):
    """Precision y perdida de validacion (y de entrenamiento si se pasan).

    tarea: nombre de la cabeza a usar. Si es None, la red usa la primera
    cabeza disponible (comportamiento por defecto).
    """
    dispositivo = next(modelo.parameters()).device
    modelo.eval()
    criterio = nn.CrossEntropyLoss()
    with torch.no_grad():
        perdida_va = _perdida_batches(modelo, criterio, Xva, yva, batch, dispositivo, tarea)
        precision_va = _precision_batches(modelo, Xva, yva, batch, dispositivo, tarea)
        precision_tr = None
        if Xtr is not None:
            precision_tr = _precision_batches(modelo, Xtr, ytr, batch, dispositivo, tarea)
    modelo.train()
    return perdida_va, precision_va, precision_tr


def _perdida_batches(modelo, criterio, X, y, batch, dispositivo, tarea=None):
    total, n = 0.0, 0
    for i in range(0, X.shape[0], batch):
        xb, yb = X[i:i + batch].to(dispositivo), y[i:i + batch].to(dispositivo)
        total += criterio(modelo(xb, tarea), yb).item() * xb.shape[0]
        n += xb.shape[0]
    return total / max(n, 1)


def _precision_batches(modelo, X, y, batch, dispositivo, tarea=None):
    aciertos, n = 0, 0
    for i in range(0, X.shape[0], batch):
        xb, yb = X[i:i + batch].to(dispositivo), y[i:i + batch].to(dispositivo)
        pred = modelo(xb, tarea).argmax(dim=1)
        aciertos += (pred == yb).sum().item()
        n += xb.shape[0]
    return aciertos / max(n, 1)


def _penalizacion_ewc(modelo, ewc):
    """Termino de consolidacion elastica: castiga alejarse de lo ya aprendido.

    Solo ancla los pesos que existian en theta_prev y con el MISMO tamano:
    si una cabeza se recreo (p. ej. aparecieron categorias nuevas), sus pesos
    nuevos no se anclan (no hay referencia previa).
    """
    fisher, theta_prev, lam = ewc["fisher"], ewc["theta_prev"], ewc["lam"]
    extra = 0.0
    for nombre, p in modelo.named_parameters():
        if (p.requires_grad and nombre in fisher and nombre in theta_prev
                and p.shape == theta_prev[nombre].shape):
            dif = p - theta_prev[nombre]
            extra = extra + (fisher[nombre] * dif * dif).sum()
    return lam * extra


def calcular_fisher(modelo, X, y, batch=64, n_batchs=20, semilla=42, tarea=None):
    """Fisher diagonal: importancia de cada peso para la tarea dada.

    Se usa como memoria de consolidacion: los pesos importantes para tareas
    viejas quedan 'anclados' y no se destruyen al aprender lo nuevo.
    """
    torch.manual_seed(semilla)
    dispositivo = next(modelo.parameters()).device
    X, y = X.to(dispositivo), y.to(dispositivo)
    modelo.train()
    fisher = {}
    for nombre, p in modelo.named_parameters():
        if p.requires_grad:
            fisher[nombre] = torch.zeros_like(p)
    criterio = nn.CrossEntropyLoss()
    n = X.shape[0]
    n_batchs = min(n_batchs, max(n // batch, 1))
    perm = torch.randperm(n)[:n_batchs * batch]
    contados = 0
    for i in range(0, len(perm), batch):
        idx = perm[i:i + batch]
        xb, yb = X[idx], y[idx]
        modelo.zero_grad()
        salida = modelo(xb, tarea)
        perdida = criterio(salida, yb)
        perdida.backward()
        for nombre, p in modelo.named_parameters():
            if p.requires_grad and p.grad is not None:
                fisher[nombre] = fisher[nombre] + (p.grad * p.grad) / max(xb.shape[0], 1)
        contados += 1
    for nombre in fisher:
        fisher[nombre] = fisher[nombre] / max(contados, 1)
    modelo.zero_grad()
    modelo.eval()
    return fisher