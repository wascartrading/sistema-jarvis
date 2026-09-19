"""red.py - Red neuronal profunda de JARVIS con cabezas por tarea.

Arquitectura: entrada -> N capas ocultas compartidas (Lineal + ReLU +
Dropout) -> UNA cabeza de salida por tarea (Lineal). Cada dominio etiqueta
el mismo espacio de forma distinta; dar a cada tarea su propia cabeza de
salida evita el conflicto (es la solucion estandar en aprendizaje continuo).

Sin BatchNorm a proposito: las stats de BN se desajustan entre tareas y
rompen la evaluacion (leccion de los experimentos). Con cabezas separadas
no hace falta.

La red puede CRECER en caliente: inserta capas ocultas nuevas con
inicializacion identidad para no romper lo aprendido.
"""
import torch
import torch.nn as nn

ACTIVACIONES = {"relu": nn.ReLU, "silu": nn.SiLU, "gelu": nn.GELU}


class RedJarvis(nn.Module):
    def __init__(self, entrada, salida, capas_ocultas, activacion="relu",
                 dropout=0.15, semilla=42):
        super().__init__()
        torch.manual_seed(semilla)
        if isinstance(capas_ocultas, (int, float)):
            capas_ocultas = [int(capas_ocultas)] * int(capas_ocultas)
        self.entrada = int(entrada)
        self.salida = int(salida)
        self.act_nombre = activacion
        self.drop_p = float(dropout)
        self.act = ACTIVACIONES[activacion]()
        self.drop = nn.Dropout(self.drop_p)
        # Capas ocultas COMPARTIDAS (sin capa de salida: esa vive en cabezas)
        dims = [self.entrada] + [int(d) for d in capas_ocultas]
        self.capas = nn.ModuleList(
            [nn.Linear(dims[i], dims[i + 1]) for i in range(len(dims) - 1)]
        )
        # Cabezas de salida: una por tarea (domino)
        self.cabezas = nn.ModuleDict()
        self._inicializar()

    def _inicializar(self):
        for capa in self.capas:
            nn.init.kaiming_normal_(capa.weight, mode="fan_in",
                                    nonlinearity="relu" if self.act_nombre == "relu" else "linear")
            nn.init.zeros_(capa.bias)

    def _nueva_cabeza(self, tarea, n_salidas=None):
        """Crea y registra una cabeza de salida para una tarea nueva.

        n_salidas: numero de clases de la tarea (por defecto self.salida).
        Cada tarea puede tener su propio numero de clases.
        """
        if n_salidas is None:
            n_salidas = self.salida
        ultimo = self.capas[-1].out_features if self.capas else self.entrada
        cabeza = nn.Linear(ultimo, int(n_salidas))
        nn.init.xavier_normal_(cabeza.weight)
        nn.init.zeros_(cabeza.bias)
        self.cabezas[tarea] = cabeza
        return cabeza

    def tareas(self):
        return list(self.cabezas.keys())

    def forward(self, x, tarea=None):
        """Forward con la cabeza de 'tarea'. Si no se indica y solo hay una
        cabeza, la usa; si hay varias y no se indica, usa la primera."""
        if x.dim() == 1:
            x = x.unsqueeze(0)
        h = x
        for capa in self.capas:
            h = capa(h)
            h = self.act(h)
            h = self.drop(h)
        if tarea is None:
            if not self.cabezas:
                raise ValueError("La red no tiene cabezas de salida")
            tarea = next(iter(self.cabezas))
        return self.cabezas[tarea](h)

    def profundidad(self):
        return len(self.capas) + 1

    def arquitectura(self):
        base = [self.entrada] + [c.out_features for c in self.capas]
        return base + [self.salida] * max(len(self.cabezas), 1)

    def contar_parametros(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def insertar_capa(self):
        """Inserta una capa oculta con peso identidad justo antes de las
        cabezas. Con peso identidad y bias cero el flujo apenas cambia, asi
        el conocimiento previo no se destruye y la red gana profundidad."""
        ancho = self.capas[-1].out_features if self.capas else self.entrada
        nueva = nn.Linear(ancho, ancho)
        nn.init.eye_(nueva.weight)
        nn.init.zeros_(nueva.bias)
        self.capas.append(nueva)
        # Las cabezas siguen conectadas al MISMO ancho (ultima capa oculta),
        # asi que no hay que tocarlas.
        return nueva

    def refrescar_ultimas(self, n):
        """Reinicializa las ultimas n capas ocultas para dar capacidad fresca."""
        n = max(1, int(n))
        for capa in self.capas[-n:]:
            nn.init.kaiming_normal_(capa.weight, mode="fan_in",
                                    nonlinearity="relu" if self.act_nombre == "relu" else "linear")
            nn.init.zeros_(capa.bias)


def crear_red(entrada, salida, capas_ocultas, activacion="relu", dropout=0.15, semilla=42):
    return RedJarvis(entrada, salida, capas_ocultas, activacion, dropout, semilla)


def guardar_modelo(modelo, ruta):
    torch.save(modelo.state_dict(), ruta)


def cargar_modelo(modelo, ruta):
    estado = torch.load(ruta, weights_only=True)
    modelo.load_state_dict(estado)
    return modelo