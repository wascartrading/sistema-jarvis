"""Experimento de diagnostico: mide el olvido con distintas protecciones."""
import sys
sys.path.insert(0, ".")
import torch
import continuo, datos, entrenamiento, memoria


def evaluar_espiral(modelo, config):
    stats = config.get("stats_bn", {}).get("espiral")
    if stats:
        continuo._aplicar_stats_bn(modelo, stats)
    media = torch.tensor(config["normalizacion_global"]["media"])
    std = torch.tensor(config["normalizacion_global"]["std"]).clamp_min(1e-6)
    Xe, ye = datos.generar_tarea("espiral", n_puntos=2000, semilla=0)
    Xe = (Xe - media) / std
    _, prec, _ = entrenamiento.evaluar(modelo, Xe, ye)
    return prec


def preparar_lunas(config):
    X, y = datos.generar_tarea("lunas", n_puntos=2000, semilla=1)
    Xtr, ytr, Xva, yva = datos.dividir(X, y, semilla=1)
    media = torch.tensor(config["normalizacion_global"]["media"])
    std = torch.tensor(config["normalizacion_global"]["std"]).clamp_min(1e-6)
    return (Xtr - media) / std, ytr, (Xva - media) / std, yva


def main():
    # 1) Espiral sola (referencia)
    continuo.crear_cerebro("exp1", capas=6, ancho=64)
    continuo.aprender_tarea("exp1", "espiral", epocas=40, umbral=0.92, silencioso=True)
    modelo, config = continuo.cargar_cerebro("exp1")
    print(f"Referencia espiral: {evaluar_espiral(modelo, config):.2%}")

    # 2) Lunas con SOLO replay (sin EWC ni destilacion)
    Xtr, ytr, Xva, yva = preparar_lunas(config)
    exp = memoria.cargar_experiencia("exp1")
    media = torch.tensor(config["normalizacion_global"]["media"])
    std = torch.tensor(config["normalizacion_global"]["std"]).clamp_min(1e-6)
    X_prev = (exp["X"] - media) / std
    n = min(X_prev.shape[0], Xtr.shape[0])
    pv = torch.randperm(X_prev.shape[0])[:n]
    pn = torch.randperm(Xtr.shape[0])[:n]
    Xm = torch.cat([Xtr[pn], X_prev[pv]])
    ym = torch.cat([ytr[pn], exp["y"][pv]])
    modelo2, met, _ = entrenamiento.entrenar(modelo, Xm, ym, Xva, yva,
                                             epocas=40, lr=1e-3 * 0.4, silencioso=True)
    print(f"Solo replay: espiral={evaluar_espiral(modelo2, config):.2%} "
          f"lunas={met['precision_va']:.2%}")

    # 3) Lunas con replay + EWC
    modelo3, config3 = continuo.cargar_cerebro("exp1")
    Xtr3, ytr3, Xva3, yva3 = preparar_lunas(config3)
    exp3 = memoria.cargar_experiencia("exp1")
    X_prev3 = (exp3["X"] - media) / std
    n3 = min(X_prev3.shape[0], Xtr3.shape[0])
    pv3 = torch.randperm(X_prev3.shape[0])[:n3]
    pn3 = torch.randperm(Xtr3.shape[0])[:n3]
    Xm3 = torch.cat([Xtr3[pn3], X_prev3[pv3]])
    ym3 = torch.cat([ytr3[pn3], exp3["y"][pv3]])
    ewc = {"fisher": exp3["fisher"], "theta_prev": exp3["theta_prev"], "lam": 2.0}
    modelo3, met3, _ = entrenamiento.entrenar(modelo3, Xm3, ym3, Xva3, yva3,
                                              epocas=40, lr=1e-3 * 0.4,
                                              ewc=ewc, silencioso=True)
    print(f"Replay+EWC: espiral={evaluar_espiral(modelo3, config3):.2%} "
          f"lunas={met3['precision_va']:.2%}")


if __name__ == "__main__":
    main()