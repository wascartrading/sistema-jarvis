// ============================================================
//  Temas de color de la esfera de JARVIS
//  Fuente única para la interfaz de voz y el widget flotante.
//
//  Cada tema se define por su TONO (hue) en el círculo cromático,
//  repartidos para que ninguno se parezca al de al lado. Las
//  variantes por estado (espera, reposo, inactivo) se derivan del
//  tono base bajando la luminosidad, así la jerarquía visual queda
//  garantizada por construcción y no depende de acertar a mano
//  seis valores RGB por color.
//
//  Solo se tiñen los estados "identitarios". Los que comunican algo
//  concreto mantienen su color universal:
//    · naranja = procesando
//    · rojo    = escribiendo (JARVIS tiene el teclado tomado)
//  Cambiarlos haría perder información de un vistazo.
// ============================================================
(function (global) {
  'use strict';

  // Colores que NO dependen del tema: significan estado, no identidad.
  var FIJOS = {
    escribiendo: [255, 45, 45],
    pensando: [255, 196, 0]
  };

  // ---------- Conversión HSL -> RGB ----------

  function _hsl(h, s, l) {
    h = ((h % 360) + 360) % 360;
    s = Math.max(0, Math.min(100, s)) / 100;
    l = Math.max(0, Math.min(100, l)) / 100;
    var c = (1 - Math.abs(2 * l - 1)) * s;
    var x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    var m = l - c / 2;
    var r = 0, g = 0, b = 0;
    if (h < 60) { r = c; g = x; }
    else if (h < 120) { r = x; g = c; }
    else if (h < 180) { g = c; b = x; }
    else if (h < 240) { g = x; b = c; }
    else if (h < 300) { r = x; b = c; }
    else { r = c; b = x; }
    return [
      Math.round((r + m) * 255),
      Math.round((g + m) * 255),
      Math.round((b + m) * 255)
    ];
  }

  // ---------- Definición: tono, saturación y luz del color base ----------
  // Los tonos están separados para que no haya dos parecidos. El orden es el
  // del círculo cromático, así la paleta se lee como un degradado.
  // Tonos separados ~28° o más, que es el umbral a partir del cual el ojo los
  // lee como colores distintos y no como variantes del mismo.
  var DEF = {
    cyan:      { nombre: 'Cian',      descripcion: 'El clásico de JARVIS',    h: 180, s: 100, l: 50 },
    azul:      { nombre: 'Azul',      descripcion: 'Sobrio y frío',           h: 210, s: 90,  l: 56 },
    indigo:    { nombre: 'Índigo',    descripcion: 'Azul nocturno',           h: 245, s: 85,  l: 62 },
    violeta:   { nombre: 'Violeta',   descripcion: 'Profundo, con carácter',  h: 278, s: 85,  l: 66 },
    magenta:   { nombre: 'Magenta',   descripcion: 'Fucsia de neón',          h: 310, s: 95,  l: 58 },
    rosa:      { nombre: 'Rosa',      descripcion: 'Claro y cálido',          h: 342, s: 95,  l: 74 },
    rojo:      { nombre: 'Rojo',      descripcion: 'Directo, sin rodeos',     h: 4,   s: 88,  l: 54 },
    naranja:   { nombre: 'Naranja',   descripcion: 'Intenso, tipo reactor',   h: 30,  s: 95,  l: 54 },
    // El tramo naranja→verde del círculo es estrecho: entre 30° y 95° solo
    // caben DOS colores que el ojo lea como distintos. Poner tres (ámbar,
    // oro, amarillo) daba pares a 16°, indistinguibles en pantalla.
    oro:       { nombre: 'Oro',       descripcion: 'Dorado, como el reactor', h: 52,  s: 95,  l: 52 },
    lima:      { nombre: 'Lima',      descripcion: 'Ácido y luminoso',        h: 82,  s: 85,  l: 52 },
    // Verde y esmeralda están a 22° (el ojo es poco sensible en esta zona del
    // círculo), así que además se separan por luminosidad: el verde va claro y
    // la esmeralda oscura. Así no se confunden ni en la paleta ni en la esfera.
    verde:     { nombre: 'Verde',     descripcion: 'Terminal, estilo consola', h: 136, s: 80, l: 56 },
    esmeralda: { nombre: 'Esmeralda', descripcion: 'Verde agua, profundo',    h: 158, s: 90,  l: 34 },
    hielo:     { nombre: 'Hielo',     descripcion: 'Blanco azulado, minimalista', h: 200, s: 45, l: 86 },
    acero:     { nombre: 'Acero',     descripcion: 'Gris azulado, discreto',  h: 214, s: 18,  l: 58 },
    // Neutro cálido: se distingue de todos los demás por saturación, no por
    // tono, así no compite con ninguno del círculo.
    arena:     { nombre: 'Arena',     descripcion: 'Beige cálido, sobrio',    h: 34,  s: 30,  l: 70 }
  };

  // ---------- Derivación de las variantes por estado ----------
  // Bajando la luz de forma monótona, la jerarquía de brillo
  // (activo > espera > reposo > inactivo) se cumple siempre.
  function _lum(a) {
    return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2];
  }

  /**
   * Genera una variante más apagada que la anterior.
   *
   * No basta con bajar la luz: al desaturar un azul su luminancia SUBE (el gris
   * es más claro que el azul puro), así que un cálculo fijo rompía la jerarquía
   * en índigo y azul. Acá se baja la luz hasta que la luminancia queda
   * realmente por debajo de la del paso anterior.
   */
  function _apagar(h, s, l, refLum) {
    var out = _hsl(h, s, l);
    var intentos = 0;
    while (_lum(out) >= refLum - 6 && l > 3 && intentos < 40) {
      l -= 1.5;
      out = _hsl(h, s, l);
      intentos++;
    }
    return out;
  }

  function _construir(d) {
    var activo = _hsl(d.h, d.s, d.l);
    // En espera y reposo se va apagando, pero conserva su tono.
    var espera = _apagar(d.h, d.s * 0.92, d.l * 0.58, _lum(activo));
    var reposo = _apagar(d.h, d.s * 0.82, d.l * 0.42, _lum(espera));
    // Inactivo: casi apagado. Se desatura menos de lo que se bajaba antes,
    // justamente para que no rebote de brillo en los tonos fríos.
    var inactivo = _apagar(d.h, d.s * 0.70, d.l * 0.30, _lum(reposo));
    return {
      nombre: d.nombre,
      descripcion: d.descripcion,
      h: d.h, s: d.s, l: d.l,
      base: activo,
      activo: activo,
      // Al hablar sube el brillo: se nota que está emitiendo.
      hablando: _hsl(d.h, d.s * 0.88, Math.min(90, d.l + 14)),
      espera: espera,
      reposo: reposo,
      inactivo: inactivo
    };
  }

  var TEMAS = {};
  Object.keys(DEF).forEach(function (k) { TEMAS[k] = _construir(DEF[k]); });

  var DEFECTO = 'cyan';

  function tema(clave) {
    return TEMAS[clave] || TEMAS[DEFECTO];
  }

  function rgb(arr) {
    return 'rgb(' + arr[0] + ',' + arr[1] + ',' + arr[2] + ')';
  }

  function rgba(arr, a) {
    return 'rgba(' + arr[0] + ',' + arr[1] + ',' + arr[2] + ',' + a + ')';
  }

  /** Colores de la esfera grande (interfaz de voz), por modo. */
  function coloresInterfaz(clave) {
    var t = tema(clave);
    var o = function (a) { return { r: a[0], g: a[1], b: a[2] }; };
    return {
      escuchando: o(t.activo),
      atento: o(t.espera),
      reposo: o(t.reposo),
      inactivo: o(t.inactivo),
      escribiendo: o(FIJOS.escribiendo)
    };
  }

  /** Colores del widget flotante, por estado de la sesión. */
  function coloresWidget(clave) {
    var t = tema(clave);
    return {
      MUTED: t.inactivo.slice(),
      LISTENING: t.activo.slice(),
      SPEAKING: t.hablando.slice(),
      ARMED: t.espera.slice(),
      ASLEEP: t.reposo.slice(),
      THINKING: FIJOS.pensando.slice(),
      WRITING: FIJOS.escribiendo.slice()
    };
  }

  /** Escribe las variables CSS del tema en el documento. */
  function aplicarVariables(clave, raiz) {
    var t = tema(clave);
    var el = raiz || document.documentElement;
    el.style.setProperty('--jarvis-base', t.base.join(', '));
    el.style.setProperty('--jarvis-base-rgb', rgb(t.base));
    el.style.setProperty('--esfera-color', rgb(t.activo));
    el.style.setProperty('--esfera-color-alpha', rgba(t.activo, 0.23));
    el.style.setProperty('--esfera-color-suave', rgba(t.activo, 0.08));
    return t;
  }

  global.TemasEsfera = {
    TEMAS: TEMAS,
    DEFECTO: DEFECTO,
    FIJOS: FIJOS,
    tema: tema,
    claves: function () { return Object.keys(TEMAS); },
    rgb: rgb,
    rgba: rgba,
    hsl: _hsl,
    coloresInterfaz: coloresInterfaz,
    coloresWidget: coloresWidget,
    aplicarVariables: aplicarVariables
  };
})(window);
