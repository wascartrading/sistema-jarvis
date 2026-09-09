"""estrategia_saturacion.py - ESTRATEGIA DE SATURACION VELA A VELA (28/08/2026).

REGLAS (definidas con el jefe):
- La secuencia empieza con 2 velas consecutivas del MISMO color (verde o rojo). Ese color es el de SATURACION.
- Despues se cuentan TODAS las velas de ese color. Entre bloques se permite UNA sola vela contraria aislada.
- INVALIDA si: 2 contrarias seguidas o bloque sat con <2 velas entre contrarias.
- Hasta X velas (velas_saturacion, default 10) y opera EN CONTRA (verde->PUT, rojo->CALL).
- Doji reinicia.
- MARTINGALA VELA A VELA (28/08/2026, pedido del jefe): si la operativa se pierde, la SIGUIENTE vela se opera DE INMEDIATO en la misma direccion (misma direccion del ciclo), sin esperar nueva saturacion, vela tras vela hasta ganar o agotar niveles. Ciclo ATADO al activo.

Estados genericos: buscando | activo | listo
"""
import time
import velas as velas_mod


CONFIG = [
    {'clave': 'velas_saturacion', 'tipo': 'int', 'min': 3, 'max': 50, 'paso': 1,
     'default': 10, 'etiqueta': 'Velas Saturacion', 'formato': '%d velas',
     'desc': 'Numero de velas del color dominante para considerar saturacion y operar en contra.'},
]


class EstrategiaSaturacionActivo:
    """Maquina de saturacion, UNA por activo - VELA A VELA."""

    CONFIG = CONFIG
    NOMBRE = 'saturacion'

    _ESTADOS_GENERICOS = {
        'buscando': 'buscando',
        'contando': 'activo',
        'listo': 'listo',
    }

    def __init__(self, activo, **params):
        self.activo = activo
        self.velas_saturacion = max(int(params.get('velas_saturacion', 10)), 1)
        self.margen_compra_seg = float(params.get('margen_compra_seg', 30.0))
        self.desfase = float(params.get('desfase', 0.0))
        self._estado = 'buscando'
        self.color_sat = None
        self.total_sat = 0
        self.racha_sat = 0
        self.racha_contra = 0
        self.ultimo_color = None
        self.ultimo_ts = None
        self.senal = None
        self.ultimo_evento = 'buscando 2 velas iguales para iniciar'
        self.secuencia = []
        # ciclo vela a vela
        self._ciclo_vela = False
        self._direccion_ciclo = None
        self._ultimo_motivo_invalida = ''

    @property
    def estado(self):
        return self._ESTADOS_GENERICOS.get(self._estado, 'buscando')

    def color(self, vela):
        return velas_mod.color_vela(vela)

    def color_contrario(self):
        if self.color_sat == 'verde':
            return 'rojo'
        if self.color_sat == 'rojo':
            return 'verde'
        return None

    def _seg_broker(self):
        try:
            return (time.time() + self.desfase) % 60.0
        except Exception:
            return 0.0

    def direccion(self):
        if self._ciclo_vela and self._direccion_ciclo:
            return self._direccion_ciclo
        if self._estado == 'listo' and self.color_sat:
            return 'put' if self.color_sat == 'verde' else 'call'
        return None

    def punto_entrada(self):
        return None

    def indicadores(self):
        if self._ciclo_vela:
            return ['\U0001f525', '\u26a1']
        if self._estado == 'listo':
            return ['\U0001f525', '\u26a1']
        if self._estado == 'contando' and self.color_sat:
            faltan = self.velas_saturacion - self.total_sat
            if faltan <= 2:
                return ['\U0001f525']
        return []

    def prioridad(self):
        if self._ciclo_vela:
            return -2000
        if self._estado == 'listo':
            return -1000
        if self._estado == 'contando':
            return -self.total_sat
        return 0

    def configurar(self, **params):
        if 'velas_saturacion' in params:
            try:
                v = int(params['velas_saturacion'])
                if 1 <= v <= 50:
                    self.velas_saturacion = v
            except Exception:
                pass
        if 'margen_compra_seg' in params:
            try:
                self.margen_compra_seg = max(float(params['margen_compra_seg']), 1.0)
            except Exception:
                pass
        if 'desfase' in params:
            try:
                self.desfase = float(params['desfase'])
            except Exception:
                pass

    def _reset(self, motivo=''):
        self.color_sat = None
        self.total_sat = 0
        self.racha_sat = 0
        self.racha_contra = 0
        self._estado = 'buscando'
        self.senal = None
        self.secuencia = []
        if motivo:
            self.ultimo_evento = 'reinicio (%s): buscando 2 iguales' % motivo
            self._ultimo_motivo_invalida = motivo
        else:
            self.ultimo_evento = 'buscando 2 velas iguales para iniciar'

    def _reset_patron_sin_ciclo(self, motivo=''):
        # reset solo patron, mantiene ciclo si esta activo (usado tras disparar)
        self.color_sat = None
        self.total_sat = 0
        self.racha_sat = 0
        self.racha_contra = 0
        self._estado = 'buscando'
        self.senal = None
        self.secuencia = []
        self.ultimo_color = None
        if motivo:
            self._ultimo_motivo_invalida = motivo

    def reconstruir(self, velas):
        # reconstruir NO toca el ciclo de martingala si esta activo (lo conserva)
        ciclo_activo = self._ciclo_vela
        dir_ciclo = self._direccion_ciclo
        self._estado = 'buscando'
        self.color_sat = None
        self.total_sat = 0
        self.racha_sat = 0
        self.racha_contra = 0
        self.ultimo_color = None
        self.ultimo_ts = None
        self.senal = None
        self.ultimo_evento = 'buscando 2 velas iguales para iniciar'
        self.secuencia = []
        if ciclo_activo:
            # si hay ciclo vela a vela, no reconstruir patron (sigue en recuperacion)
            self._ciclo_vela = ciclo_activo
            self._direccion_ciclo = dir_ciclo
            self._estado = 'contando'
            return
        for v in velas:
            self.alimentar([v])

    def _alimentar_una(self, vela):
        # procesa UNA vela cerrada, asume self.ultimo_ts ya actualizado
        # MODO RECUPERACION VELA A VELA
        if self._ciclo_vela and self._direccion_ciclo is not None:
            if self._seg_broker() >= 50.0:
                self._estado = 'contando'
                return None
            self._ultimo_motivo_invalida = 'disparada (vela a vela)'
            self._estado = 'buscando'
            self.ultimo_evento = 'vela a vela -> %s (recuperacion)' % self._direccion_ciclo
            return ('operar', self._direccion_ciclo)
        col = self.color(vela)

        # DOJI reinicia (pero NO mata el ciclo vela a vela)
        if col == 'doji':
            if self._ciclo_vela:
                return None
            if self._estado != 'buscando':
                self._reset('vela DOJI')
                self.ultimo_color = None
                self.secuencia = []
            else:
                self.ultimo_color = None
            return None

        # ESTADO BUSCANDO
        if self._estado == 'buscando':
            if self.ultimo_color is not None and self.ultimo_color == col:
                self.color_sat = col
                self.total_sat = 2
                self.racha_sat = 2
                self.racha_contra = 0
                self.secuencia = [col, col]
                self._estado = 'contando'
                self.ultimo_color = col
                if self.total_sat >= self.velas_saturacion:
                    self._estado = 'listo'
                    direccion = 'put' if self.color_sat == 'verde' else 'call'
                    self.senal = ('operar', direccion)
                    self.ultimo_evento = 'SATURACION %s %d/%d -> LISTO %s' % (self.color_sat, self.total_sat, self.velas_saturacion, direccion.upper())
                    # al disparar, guardar ciclo potencial pero aun no activo (se activa si se pierde)
                    self._secuencia_operada = self.color_sat
                    self._direccion_operada = direccion
                    return self.senal
                self.ultimo_evento = 'inicio %s 2/%d' % (col, self.velas_saturacion)
                return None
            else:
                self.ultimo_color = col
                self.secuencia = [col]
                return None

        # ESTADO CONTANDO
        if self._estado == 'contando':
            self.secuencia.append(col)
            if len(self.secuencia) > 60:
                self.secuencia = self.secuencia[-60:]
            if col == self.color_sat:
                if self.racha_contra == 1:
                    self.racha_sat = 1
                    self.racha_contra = 0
                else:
                    self.racha_sat += 1
                    self.racha_contra = 0
                self.total_sat += 1
                self.ultimo_color = col
                if self.total_sat >= self.velas_saturacion:
                    self._estado = 'listo'
                    direccion = 'put' if self.color_sat == 'verde' else 'call'
                    self.senal = ('operar', direccion)
                    self.ultimo_evento = 'SATURACION %s %d/%d -> LISTO %s' % (self.color_sat, self.total_sat, self.velas_saturacion, direccion.upper())
                    self._secuencia_operada = self.color_sat
                    self._direccion_operada = direccion
                    return self.senal
                self.ultimo_evento = 'contando %s %d/%d racha %d' % (self.color_sat, self.total_sat, self.velas_saturacion, self.racha_sat)
                return None
            else:
                if self.racha_contra == 1:
                    motivo = '2 contrarias seguidas'
                    self._reset(motivo)
                    self.ultimo_color = col
                    self.secuencia = [col]
                    return None
                else:
                    if self.racha_sat < 2:
                        motivo = 'bloque %s de %d (<2) antes de contraria' % (self.color_sat, self.racha_sat)
                        self._reset(motivo)
                        self.ultimo_color = col
                        self.secuencia = [col]
                        return None
                    self.racha_contra = 1
                    self.racha_sat = 0
                    self.ultimo_color = col
                    self.ultimo_evento = 'contraria aislada permitida, faltan %d' % (self.velas_saturacion - self.total_sat)
                    return None

        if self._estado == 'listo':
            return None
        return None

    def alimentar(self, velas):
        if not velas:
            return None
        # construir lista de velas nuevas desde el ultimo_ts (evita delay y perdidas por dormir)
        nuevas = []
        if self.ultimo_ts is None:
            nuevas = list(velas)
        else:
            for v in velas:
                try:
                    fv = float(v.get('from', 0))
                except Exception:
                    continue
                if fv > self.ultimo_ts:
                    nuevas.append(v)
        if not nuevas:
            # puede ser la misma ultima vela ya procesada (dedupe)
            # verificar si la ultima coincide exactamente (sin nuevas)
            try:
                if float(velas[-1].get('from', 0)) == self.ultimo_ts:
                    return None
            except Exception:
                pass
            return None
        senal = None
        for v in nuevas:
            try:
                self.ultimo_ts = float(v.get('from', 0))
            except Exception:
                pass
            s = self._alimentar_una(v)
            if s is not None:
                senal = s
                break
        return senal

    def registrar_resultado(self, gano, direccion, sigue=True):
        if gano or not sigue:
            # ciclo cerrado (ganada o perdida definitiva)
            self._ciclo_vela = False
            self._direccion_ciclo = None
            self._reset('operativa %s' % ('ganada' if gano else 'perdida definitiva'))
            self.ultimo_color = None
            self.secuencia = []
            self.ultimo_evento = 'ciclo cerrado (%s)' % ('ganada' if gano else 'perdida')
            return
        # perdida con ciclo en curso -> activar vela a vela
        self._ciclo_vela = True
        self._direccion_ciclo = direccion
        # reset patron pero mantener ciclo
        self.color_sat = None
        self.total_sat = 0
        self.racha_sat = 0
        self.racha_contra = 0
        self._estado = 'contando'
        self.ultimo_evento = 'perdida: recuperando vela a vela %s' % direccion
        self._ultimo_motivo_invalida = 'vela a vela'

    def descripcion(self):
        if self._ciclo_vela and self._direccion_ciclo:
            return 'recuperando vela a vela %s' % self._direccion_ciclo
        if self._estado == 'buscando':
            return 'buscando saturacion'
        if self._estado == 'contando':
            return 'saturando %s %d/%d' % (self.color_sat, self.total_sat, self.velas_saturacion)
        if self._estado == 'listo':
            dir_txt = 'venta' if self.color_sat == 'verde' else 'compra'
            return 'listo para %s (%d/%d)' % (dir_txt, self.total_sat, self.velas_saturacion)
        return 'buscando'

    def lineas_reporte(self):
        if self._ciclo_vela and self._direccion_ciclo:
            lineas = [' \u251c RECUPERANDO VELA A VELA:']
            lineas.append(' \u2502 Dir: %s' % ('PUT \u2b07' if self._direccion_ciclo == 'put' else 'CALL \u2b06'))
            lineas.append(' \u2514 Siguiente vela inmediata')
            return lineas
        if self._estado == 'buscando':
            return None
        if self._estado == 'contando':
            if self.color_sat == 'verde':
                lineas = [' \u251c SATURACION VERDE \U0001f7e2:']
            else:
                lineas = [' \u251c SATURACION ROJA \U0001f534:']
            lineas.append(' \u2502 %d / %d velas' % (self.total_sat, self.velas_saturacion))
            # mostrar secuencia real contada para verificar que no hay delay (ultimas 12)
            try:
                seq_emojis = ' '.join('\U0001f7e2' if c == 'verde' else '\U0001f534' for c in self.secuencia[-12:])
                if seq_emojis:
                    lineas.append(' \u2502 Sec: ' + seq_emojis)
            except Exception:
                pass
            if self.racha_sat > 0:
                lineas.append(' \u251c Racha: %d %s' % (self.racha_sat, self.color_sat))
            else:
                lineas.append(' \u251c Racha: 1 contraria')
            faltan = self.velas_saturacion - self.total_sat
            lineas.append(' \u2514 Faltan %d | dir: %s' % (faltan, 'PUT \u2b07' if self.color_sat == 'verde' else 'CALL \u2b06'))
            return lineas
        if self._estado == 'listo':
            if self.color_sat == 'verde':
                lineas = [' \u251c SATURACION VERDE COMPLETA \U0001f7e2:']
            else:
                lineas = [' \u251c SATURACION ROJA COMPLETA \U0001f534:']
            lineas.append(' \u2502 %d / %d velas' % (self.total_sat, self.velas_saturacion))
            if self.color_sat == 'verde':
                lineas.append(' \u251c Operar PUT \u2b07 en contra')
            else:
                lineas.append(' \u251c Operar CALL \u2b06 en contra')
            lineas.append(' \u2514 \u26a1 LISTO PARA ENTRADA')
            return lineas
        return None

    def reintento_inmediato(self):
        return bool(self._ciclo_vela and self._direccion_ciclo is not None)

    def ciclo_enfocado(self):
        return bool(self._ciclo_vela and self._direccion_ciclo is not None)


# Alias del contrato de la plantilla
EstrategiaActivo = EstrategiaSaturacionActivo
CONFIG = EstrategiaSaturacionActivo.CONFIG


def observar_estado(velas, **params):
    if not velas:
        return 'buscando', None
    tmp = EstrategiaSaturacionActivo('__obs__', **params)
    for v in velas:
        tmp.alimentar([v])
    return tmp.estado, tmp.lineas_reporte()


def estado_observado(velas, **params):
    clave, _ = observar_estado(velas, **params)
    return clave
