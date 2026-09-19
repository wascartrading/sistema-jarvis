# -*- coding: utf-8 -*-
"""
CEREBRO DE JARVIS - Red neuronal profunda de autoaprendizaje
=============================================================
Arquitectura:
  - Tokenizador por n-gramas con hashing (sin dependencias externas).
  - Autoencoder profundo (codifica la experiencia en un vector latente).
  - Clasificador de intenciones con MUCHAS capas residuales + BatchNorm + Dropout.
  - Entrenamiento incremental: carga el checkpoint anterior y sigue aprendiendo.
  - Guarda checkpoints y un historial de perdida para medir el progreso.

Uso:
  from red_neuronal import CerebroJarvis
  cerebro = CerebroJarvis()
  cerebro.entrenar(textos, intenciones)   # aprende de la experiencia
  intencion, confianza = cerebro.predecir("abre youtube")
  cerebro.guardar()
"""

import hashlib
import json
import math
import os
import re
import time
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
DIM_VOCAB = 4096          # tamano del vector de entrada (hashing de n-gramas)
DIM_LATENTE = 128         # representacion interna aprendida
DIM_OCULTO = 512          # ancho de las capas del clasificador
NUM_CAPAS = 12            # numero de capas residuales del clasificador
DROPOUT = 0.25
RUTA_DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos")
RUTA_CHECKPOINT = os.path.join(RUTA_DATOS, "checkpoints", "cerebro.pt")
RUTA_HISTORIAL = os.path.join(RUTA_DATOS, "historial.json")
RUTA_VOCAB = os.path.join(RUTA_DATOS, "vocabulario.json")

# Intenciones que JARVIS aprende a reconocer
INTENCIONES = [
    "abrir_app", "buscar_web", "reproducir_musica", "crear_proyecto",
    "modificar_codigo", "automatizar", "informacion", "memoria",
    "trading", "juego", "sistema", "saludo", "despedida", "otro",
]

# Palabras clave por intencion para generar etiquetas iniciales
PALABRAS_CLAVE = {
    "abrir_app": ["abre", "abrir", "abrime", "lanzar", "ejecuta", "ejecutar", "inicia", "abri"],
    "buscar_web": ["busca", "buscar", "google", "investiga", "consulta", "pagina", "web", "url"],
    "reproducir_musica": ["musica", "cancion", "reproduce", "reproducir", "youtube", "video", "play", "suena"],
    "crear_proyecto": ["crea", "crear", "hazme", "desarrolla", "construye", "proyecto", "nuevo", "inventa"],
    "modificar_codigo": ["modifica", "cambia", "arregla", "corrige", "mejora", "codigo", "script", "bug", "error"],
    "automatizar": ["automatiza", "automatico", "programa", "tarea", "cada dia", "cada hora", "vigila", "monitor"],
    "informacion": ["que es", "como", "explica", "dime", "cuando", "donde", "por que", "informacion", "saber"],
    "memoria": ["recuerda", "aprende", "memoria", "olvida", "guarda", "anota", "no olvides"],
    "trading": ["trading", "opciones", "iq", "velas", "mercado", "invertir", "inversion", "bot de trading"],
    "juego": ["juego", "juega", "snake", "domino", "3d", "sistema solar", "partida"],
    "sistema": ["sistema", "windows", "apaga", "reinicia", "cierra", "proceso", "archivo", "carpeta", "instala"],
    "saludo": ["hola", "buenos dias", "buenas tardes", "buenas noches", "hey", "que tal", "saludos"],
    "despedida": ["adios", "hasta luego", "nos vemos", "chao", "bye", "terminamos"],
}


def _hash_ngram(texto, n, dim):
    """Convierte un n-grama en un indice estable dentro de [0, dim)."""
    digest = hashlib.md5(texto.encode("utf-8", errors="ignore")).hexdigest()
    return int(digest[:8], 16) % dim


def vectorizar(texto, dim=DIM_VOCAB, n_gramas=(1, 2, 3)):
    """Convierte texto en un vector denso de conteos de n-gramas con hashing."""
    texto = re.sub(r"[^a-z0-9áéíóúñü ]", " ", texto.lower())
    tokens = [t for t in texto.split() if t]
    vec = np.zeros(dim, dtype=np.float32)
    for n in n_gramas:
        for i in range(len(tokens) - n + 1):
            grama = " ".join(tokens[i:i + n])
            idx = _hash_ngram(grama, n, dim)
            vec[idx] += 1.0
    # Normalizacion L2 para estabilidad
    norma = np.linalg.norm(vec)
    if norma > 0:
        vec /= norma
    return vec


def inferir_intencion(texto):
    """Etiqueta rapida por palabras clave (para generar datos iniciales)."""
    texto = texto.lower()
    puntajes = {}
    for intencion, palabras in PALABRAS_CLAVE.items():
        puntajes[intencion] = sum(1 for p in palabras if p in texto)
    mejor = max(puntajes, key=puntajes.get)
    if puntajes[mejor] == 0:
        return "otro"
    return mejor


# ---------------------------------------------------------------------------
# Bloques de la red
# ---------------------------------------------------------------------------
class BloqueResidual(nn.Module):
    """Capa residual: Lineal -> BatchNorm -> GELU -> Dropout, con atajo."""

    def __init__(self, dim, dropout=DROPOUT):
        super().__init__()
        self.lineal = nn.Linear(dim, dim)
        self.norma = nn.BatchNorm1d(dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        identidad = x
        out = self.lineal(x)
        out = self.norma(out)
        out = F.gelu(out)
        out = self.dropout(out)
        return out + identidad


class Autoencoder(nn.Module):
    """Codifica la experiencia en un vector latente y la reconstruye."""

    def __init__(self, dim_in=DIM_VOCAB, dim_latente=DIM_LATENTE):
        super().__init__()
        self.codificador = nn.Sequential(
            nn.Linear(dim_in, 1024), nn.BatchNorm1d(1024), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(1024, 512), nn.BatchNorm1d(512), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(512, 256), nn.BatchNorm1d(256), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(256, dim_latente),
        )
        self.decodificador = nn.Sequential(
            nn.Linear(dim_latente, 256), nn.BatchNorm1d(256), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(256, 512), nn.BatchNorm1d(512), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(512, 1024), nn.BatchNorm1d(1024), nn.GELU(), nn.Dropout(DROPOUT),
            nn.Linear(1024, dim_in),
        )

    def forward(self, x):
        latente = self.codificador(x)
        reconstruido = self.decodificador(latente)
        return reconstruido, latente


class ClasificadorProfundo(nn.Module):
    """Clasificador de intenciones con muchas capas residuales."""

    def __init__(self, dim_in=DIM_VOCAB, dim_oculto=DIM_OCULTO,
                 num_capas=NUM_CAPAS, num_clases=len(INTENCIONES)):
        super().__init__()
        self.entrada = nn.Sequential(
            nn.Linear(dim_in, dim_oculto), nn.BatchNorm1d(dim_oculto), nn.GELU(),
        )
        self.capas = nn.Sequential(*[BloqueResidual(dim_oculto) for _ in range(num_capas)])
        self.salida = nn.Linear(dim_oculto, num_clases)

    def forward(self, x):
        x = self.entrada(x)
        x = self.capas(x)
        return self.salida(x)


# ---------------------------------------------------------------------------
# Cerebro completo
# ---------------------------------------------------------------------------
class CerebroJarvis:
    """Orquesta el autoencoder y el clasificador, entrena y predice."""

    def __init__(self, dim_vocab=DIM_VOCAB, dim_latente=DIM_LATENTE,
                 dim_oculto=DIM_OCULTO, num_capas=NUM_CAPAS):
        self.dim_vocab = dim_vocab
        self.autoencoder = Autoencoder(dim_vocab, dim_latente)
        self.clasificador = ClasificadorProfundo(dim_vocab, dim_oculto, num_capas)
        self.historial = self._cargar_historial()
        self.epoca_global = self.historial.get("epoca_global", 0)
        self.cargar()

    # -- persistencia -------------------------------------------------------
    def _cargar_historial(self):
        if os.path.exists(RUTA_HISTORIAL):
            try:
                with open(RUTA_HISTORIAL, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"epoca_global": 0, "perdidas": [], "precisiones": [], "ejemplos_vistos": 0}

    def _guardar_historial(self):
        os.makedirs(os.path.dirname(RUTA_HISTORIAL), exist_ok=True)
        with open(RUTA_HISTORIAL, "w", encoding="utf-8") as f:
            json.dump(self.historial, f, ensure_ascii=False, indent=2)

    def cargar(self):
        if os.path.exists(RUTA_CHECKPOINT):
            try:
                estado = torch.load(RUTA_CHECKPOINT, map_location="cpu", weights_only=False)
                self.autoencoder.load_state_dict(estado["autoencoder"])
                self.clasificador.load_state_dict(estado["clasificador"])
                self.epoca_global = estado.get("epoca_global", self.epoca_global)
                return True
            except Exception as e:
                print(f"[cerebro] No pude cargar el checkpoint: {e}")
        return False

    def guardar(self):
        os.makedirs(os.path.dirname(RUTA_CHECKPOINT), exist_ok=True)
        estado = {
            "autoencoder": self.autoencoder.state_dict(),
            "clasificador": self.clasificador.state_dict(),
            "epoca_global": self.epoca_global,
        }
        torch.save(estado, RUTA_CHECKPOINT)
        self._guardar_historial()
        return RUTA_CHECKPOINT

    # -- entrenamiento ------------------------------------------------------
    def entrenar(self, textos, intenciones, epocas=30, lote=32, lr=1e-3,
                 reportar=True):
        """Entrena con la experiencia acumulada. Incremental: sigue desde donde iba."""
        if not textos:
            return 0.0, 0.0
        X = np.stack([vectorizar(t) for t in textos])
        y = np.array([INTENCIONES.index(i) if i in INTENCIONES else INTENCIONES.index("otro")
                      for i in intenciones], dtype=np.int64)

        Xt = torch.tensor(X, dtype=torch.float32)
        yt = torch.tensor(y, dtype=torch.long)

        optim_ae = torch.optim.AdamW(self.autoencoder.parameters(), lr=lr, weight_decay=1e-5)
        optim_clf = torch.optim.AdamW(self.clasificador.parameters(), lr=lr, weight_decay=1e-5)
        criterio_recon = nn.MSELoss()
        criterio_clf = nn.CrossEntropyLoss()

        n = len(Xt)
        mejor_perdida = float("inf")
        paciencia = 0

        for epoca in range(epocas):
            self.autoencoder.train()
            self.clasificador.train()
            perm = torch.randperm(n)
            perdida_total, correctos, total = 0.0, 0, 0
            for i in range(0, n, lote):
                idx = perm[i:i + lote]
                if len(idx) < 2:  # BatchNorm necesita al menos 2 ejemplos
                    continue
                xb, yb = Xt[idx], yt[idx]

                # Autoencoder: reconstruir la experiencia
                optim_ae.zero_grad()
                reconstruido, _ = self.autoencoder(xb)
                perdida_ae = criterio_recon(reconstruido, xb)
                perdida_ae.backward()
                optim_ae.step()

                # Clasificador: predecir la intencion
                optim_clf.zero_grad()
                logits = self.clasificador(xb)
                perdida_clf = criterio_clf(logits, yb)
                perdida_clf.backward()
                optim_clf.step()

                perdida_total += perdida_clf.item() * len(xb)
                correctos += (logits.argmax(1) == yb).sum().item()
                total += len(xb)

            perdida_media = perdida_total / total
            precision = correctos / total
            self.epoca_global += 1

            # Early stopping suave
            if perdida_media < mejor_perdida:
                mejor_perdida = perdida_media
                paciencia = 0
            else:
                paciencia += 1
                if paciencia >= 8:
                    break

            if reportar and (epoca + 1) % 5 == 0:
                print(f"  epoca {epoca + 1}/{epocas} | perdida {perdida_media:.4f} | precision {precision:.2%}")

        self.historial["epoca_global"] = self.epoca_global
        self.historial["perdidas"].append(round(perdida_media, 5))
        self.historial["precisiones"].append(round(precision, 5))
        self.historial["ejemplos_vistos"] += n
        self._guardar_historial()
        return perdida_media, precision

    # -- inferencia ---------------------------------------------------------
    def predecir(self, texto, top_k=3):
        """Devuelve la intencion mas probable y su confianza."""
        self.clasificador.eval()
        with torch.no_grad():
            x = torch.tensor(vectorizar(texto), dtype=torch.float32).unsqueeze(0)
            logits = self.clasificador(x)
            probs = F.softmax(logits, dim=1).squeeze(0)
            valores, indices = torch.topk(probs, k=min(top_k, len(probs)))
            resultados = [(INTENCIONES[i], float(v)) for i, v in zip(indices.tolist(), valores.tolist())]
        return resultados

    def representar(self, texto):
        """Vector latente aprendido del texto (para memoria semantica)."""
        self.autoencoder.eval()
        with torch.no_grad():
            x = torch.tensor(vectorizar(texto), dtype=torch.float32).unsqueeze(0)
            _, latente = self.autoencoder(x)
            return latente.squeeze(0).numpy()

    def resumen(self):
        """Estado actual del cerebro."""
        total_params = (sum(p.numel() for p in self.autoencoder.parameters())
                        + sum(p.numel() for p in self.clasificador.parameters()))
        return {
            "epoca_global": self.epoca_global,
            "ejemplos_vistos": self.historial.get("ejemplos_vistos", 0),
            "parametros": total_params,
            "ultima_perdida": self.historial["perdidas"][-1] if self.historial["perdidas"] else None,
            "ultima_precision": self.historial["precisiones"][-1] if self.historial["precisiones"] else None,
            "checkpoint": os.path.exists(RUTA_CHECKPOINT),
        }


if __name__ == "__main__":
    # Prueba rapida de autoaprendizaje
    print("Cerebro de JARVIS - prueba de autoaprendizaje")
    cerebro = CerebroJarvis()
    textos = [
        "abre youtube", "abre el navegador", "abre la calculadora",
        "busca en google que es python", "busca el clima de hoy",
        "reproduce musica relajante", "pon una cancion de rock",
        "crea un juego de snake", "hazme una pagina web",
        "modifica el script de trading", "arregla el error del bot",
        "recuerda que me gusta el cafe", "guarda esto en memoria",
        "hola jarvis buenos dias", "adios hasta luego",
    ]
    intenciones = [inferir_intencion(t) for t in textos]
    perdida, precision = cerebro.entrenar(textos, intenciones, epocas=15)
    print(f"Perdida final: {perdida:.4f} | Precision: {precision:.2%}")
    for t in ["abre spotify", "que hora es", "crea un bot de trading"]:
        print(f"  '{t}' -> {cerebro.predecir(t)}")
    ruta = cerebro.guardar()
    print(f"Checkpoint guardado en: {ruta}")
    print(f"Resumen: {cerebro.resumen()}")