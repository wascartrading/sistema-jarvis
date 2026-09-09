#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gemma_chat_web.py  -  Chat web con Gemma (LM Studio) o Atomic AI, para el móvil

JARVIS - interfaz HTML que chatea con dos servidores locales (a elegir desde
la propia página):
  * LM Studio  -> http://127.0.0.1:1234  (modelos locales, p.ej. google/gemma-4-e2b)
  * Atomic AI  -> http://127.0.0.1:8000  (proxy de descomposición atómica, OpenAI-compatible)

El micro-servidor escucha en 0.0.0.0, de modo que un celular en la misma red
local chatea sin CORS ni tener que tocar la config de ninguno de los dos.

Uso (persistente, sin consola):
    pythonw gemma_chat_web.py [--port 8123] [--host 0.0.0.0]
                              [--lm http://127.0.0.1:1234]
                              [--atomic http://127.0.0.1:8000]
                              [--model google/gemma-4-e2b]

Sin dependencias externas: solo stdlib (http.server + urllib).
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Configuración por defecto (sobrescribible por argumentos)
# ---------------------------------------------------------------------------
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8123
DEFAULT_LM = "http://127.0.0.1:1234"
DEFAULT_ATOMIC = "http://127.0.0.1:8000"
DEFAULT_MODEL = "google/gemma-4-e2b"

CHAT_TIMEOUT = 300   # segundos máximo para una respuesta (Atomic descompone)
MODELS_TIMEOUT = 6
MAX_VUELTA = 40      # mensajes de historial que se reenvían

NOMBRES = {"lm": "LM Studio", "atomic": "Atomic AI"}

# ---------------------------------------------------------------------------
# Interfaz HTML (embebida para que sea un solo archivo)
# ---------------------------------------------------------------------------
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>JARVIS · Chat IA</title>
<style>
  :root{
    --bg:#0b0e14; --panel:#11161f; --panel2:#161d2a; --borde:#223047;
    --tx:#e6edf7; --sub:#8aa0bf; --acc:#38bdf8; --acc2:#818cf8; --ok:#34d399;
    --err:#f87171; --user:#12314a;
  }
  *{box-sizing:border-box; margin:0; padding:0}
  html,body{height:100%}
  body{
    background:radial-gradient(1200px 600px at 80% -10%, #13213a 0%, var(--bg) 55%);
    color:var(--tx); font-family:"Segoe UI", system-ui, -apple-system, Roboto, sans-serif;
    display:flex; flex-direction:column; height:100dvh; overflow:hidden;
  }
  header{
    display:flex; align-items:center; gap:8px; padding:10px 12px;
    border-bottom:1px solid var(--borde); background:rgba(15,20,30,.85);
    backdrop-filter:blur(6px); flex-wrap:wrap; flex:0 0 auto;
  }
  header h1{font-size:15px; font-weight:600; letter-spacing:.5px; margin-right:4px}
  h1 .dot{color:var(--acc); font-size:20px; vertical-align:-2px}
  .estado{font-size:11px; color:var(--sub); margin-left:auto; white-space:nowrap}
  .estado.ok{color:var(--ok)} .estado.bad{color:var(--err)}
  select, input[type=text], textarea{
    background:var(--panel2); color:var(--tx); border:1px solid var(--borde);
    border-radius:8px; padding:8px 10px; font-size:13px; outline:none;
  }
  select:focus, input:focus, textarea:focus{border-color:var(--acc)}
  #servidor{max-width:150px}
  #modelo{max-width:250px}
  #sysWrap{display:none; width:100%}
  #sysWrap.abierto{display:block}
  #sys{width:100%; min-height:52px; resize:vertical}
  .btn{
    background:linear-gradient(135deg,var(--acc),var(--acc2)); color:#06121f;
    border:none; border-radius:10px; padding:10px 14px; font-weight:700; font-size:13px;
    cursor:pointer; box-shadow:0 4px 14px rgba(56,189,248,.25);
  }
  .btn:active{transform:translateY(1px)}
  .btn.ghost{background:transparent; color:var(--sub); border:1px solid var(--borde);
    box-shadow:none; font-weight:600}
  main{flex:1 1 auto; overflow-y:auto; padding:14px 12px 8px; display:flex;
    flex-direction:column; gap:12px; scroll-behavior:smooth}
  .msg{max-width:86%; padding:10px 13px; border-radius:14px; font-size:14px;
    line-height:1.5; white-space:pre-wrap; word-wrap:break-word; position:relative}
  .msg.user{align-self:flex-end; background:var(--user); border:1px solid #1d4a63;
    border-bottom-right-radius:4px}
  .msg.ia{align-self:flex-start; background:var(--panel2); border:1px solid var(--borde);
    border-bottom-left-radius:4px}
  .msg .cabeza{display:block; font-size:10px; letter-spacing:1px; color:var(--sub);
    margin-bottom:4px; text-transform:uppercase}
  .msg.user .cabeza{color:#7cc4ee}
  .msg.ia .cabeza{color:#a5b4fc}
  .msg .servidor{color:#64748b; font-size:10px; margin-left:6px; text-transform:none}
  .msg.err{border-color:var(--err); color:#ffd9d9; background:#2a1518}
  .cursor{display:inline-block; width:8px; height:15px; background:var(--acc);
    margin-left:2px; vertical-align:-2px; animation:parpadeo 1s steps(2) infinite}
  @keyframes parpadeo{50%{opacity:0}}
  footer{flex:0 0 auto; padding:10px 12px calc(10px + env(safe-area-inset-bottom));
    border-top:1px solid var(--borde); background:rgba(15,20,30,.85);
    display:flex; gap:8px}
  #entrada{flex:1 1 auto; background:var(--panel2); color:var(--tx);
    border:1px solid var(--borde); border-radius:12px; padding:11px 12px;
    font-size:15px; outline:none}
  #entrada:focus{border-color:var(--acc)}
  #enviar{flex:0 0 auto}
  #enviar:disabled, #parar:disabled{opacity:.45; cursor:not-allowed}
  #parar{display:none; background:linear-gradient(135deg,#f87171,#fb923c); color:#1c0606}
  .hint{text-align:center; color:var(--sub); font-size:12px; padding:6px 0}
</style>
</head>
<body>
<header>
  <h1><span class="dot">●</span> JARVIS · Chat</h1>
  <select id="servidor" title="Servidor">
    <option value="lm">LM Studio</option>
    <option value="atomic">Atomic AI</option>
  </select>
  <select id="modelo" title="Modelo"></select>
  <button class="btn ghost" id="btnSys" title="Instrucciones del sistema">Sistema</button>
  <span id="estado" class="estado">Conectando...</span>
</header>
<div id="sysWrap"><textarea id="sys" placeholder="Instrucciones del sistema (opcional)"></textarea></div>
<main id="chat">
  <div class="hint" id="bienvenido">Hola, jefe. Elija servidor y modelo arriba y escríbame algo.<br>LM Studio habla con Gemma local; Atomic AI descompone la respuesta en pasos.</div>
</main>
<footer>
  <input id="entrada" type="text" placeholder="Escríbeme aquí..." autocomplete="off">
  <button class="btn" id="enviar">Enviar</button>
  <button class="btn" id="parar">Parar</button>
</footer>
<script>
(function(){
  "use strict";
  var base = location.origin;
  var servidor = document.getElementById("servidor");
  var modelo = document.getElementById("modelo");
  var estado = document.getElementById("estado");
  var chat = document.getElementById("chat");
  var entrada = document.getElementById("entrada");
  var enviar = document.getElementById("enviar");
  var parar = document.getElementById("parar");
  var btnSys = document.getElementById("btnSys");
  var sysWrap = document.getElementById("sysWrap");
  var sys = document.getElementById("sys");
  var historial = [];
  var leyendo = null;
  var catalogo = {};        // servidor -> {modelos:[...], ok:bool}
  var nombreServidor = {lm:"LM Studio", atomic:"Atomic AI"};

  function log(t){
    var em = document.createElement("div");
    em.className = "msg ia err";
    em.innerHTML = "<span class='cabeza'>JARVIS</span>" + t.replace(/</g,"&lt;");
    chat.appendChild(em); chat.scrollTop = chat.scrollHeight;
  }
  function pieza(msg){
    var div = document.createElement("div");
    div.className = "msg " + (msg.rol === "user" ? "user" : msg.rol === "error" ? "ia err" : "ia");
    var cab = document.createElement("span");
    cab.className = "cabeza";
    cab.textContent = msg.rol === "user" ? "Tú" : msg.rol === "error" ? "Error" : "IA";
    if(msg.servidor && msg.rol !== "user"){
      var s2 = document.createElement("span");
      s2.className = "servidor";
      s2.textContent = nombreServidor[msg.servidor] || msg.servidor;
      cab.appendChild(s2);
    }
    div.appendChild(cab);
    div.appendChild(document.createTextNode(msg.contenido));
    chat.appendChild(div); chat.scrollTop = chat.scrollHeight;
    return div;
  }
  function UL(){
    var c = document.createElement("span");
    c.className = "cursor"; c.id = "cursor";
    return c;
  }
  function pintarModelos(){
    var cat = catalogo[servidor.value];
    modelo.innerHTML = "";
    if(!cat || !cat.modelos || !cat.modelos.length){
      var op = document.createElement("option");
      op.value = ""; op.textContent = "(sin modelos)";
      modelo.appendChild(op);
      return;
    }
    cat.modelos.forEach(function(m){
      var op = document.createElement("option");
      op.value = m; op.textContent = m;
      modelo.appendChild(op);
    });
  }
  function actualizarEstado(){
    var cat = catalogo[servidor.value];
    if(leyendo){ estado.textContent = "Pensando..."; estado.className = "estado"; }
    else if(!cat){ estado.textContent = "Conectando..."; estado.className = "estado"; }
    else if(cat.ok === false && (!cat.modelos || !cat.modelos.length)){
      estado.textContent = nombreServidor[servidor.value] + " apagado"; estado.className = "estado bad";
    } else {
      estado.textContent = servidor.value === "lm" ? "LM Studio OK" : "Atomic AI OK";
      estado.className = "estado ok";
    }
  }
  function cargarCatalogo(){
    estado.textContent = "Conectando..."; estado.className = "estado";
    var ctl = new AbortController();
    var tmp = setTimeout(function(){ ctl.abort(); }, 6000);
    fetch(base + "/api/models", {signal: ctl.signal}).then(function(r){ return r.json(); }).then(function(d){
      clearTimeout(tmp);
      catalogo = {};
      (d.servidores || []).forEach(function(s){ catalogo[s.id] = s; });
      if(d.porDefecto && d.porDefecto.servidor) { servidor.value = d.porDefecto.servidor; }
      pintarModelos();
      cargarDefecto(d);
      actualizarEstado();
    }).catch(function(e){
      clearTimeout(tmp);
      catalogo = {};
      pintarModelos();
      estado.textContent = "Sin conexión · ¿misma WiFi?";
      estado.className = "estado bad";
      entrada.disabled = false;
      enviar.disabled = false;
    });
  }
  function cargarDefecto(d){
    if(d.porDefecto && d.porDefecto.modelo && d.porDefecto.servidor === servidor.value){
      var m = d.porDefecto.modelo;
      for (var i=0;i<modelo.options.length;i++){
        if(modelo.options[i].value === m){ modelo.selectedIndex = i; break; }
      }
    }
  }
  servidor.addEventListener("change", function(){
    pintarModelos(); actualizarEstado();
  });
  function enviarMensaje(){
    var texto = entrada.value.trim();
    if(!texto || leyendo) return;
    entrada.value = "";
    var srv = servidor.value;
    historial.push({rol:"user", contenido:texto});
    pieza({rol:"user", contenido:texto});
    var body = JSON.stringify({
      servidor: srv,
      model: modelo.value || (catalogo[srv] && catalogo[srv].modelos ? catalogo[srv].modelos[0] : "") || "",
      system: sys.value.trim() || null,
      stream: true,
      messages: historial
    });
    abrir(pieza({rol:"ia", contenido:"", servidor:srv}), body);
  }
  function abrir(burbuja, body){
    leyendo = new AbortController();
    enviar.disabled = true; parar.style.display = "inline-block";
    parar.disabled = false; actualizarEstado();
    // quita cualquier texto/cursor previo
    while(burbuja.childNodes.length > 1){ burbuja.removeChild(burbuja.lastChild); }
    var cursor = UL(); burbuja.appendChild(cursor);
    var texto = "";
    fetch(base + "/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: body,
      signal: leyendo.signal
    }).then(function(resp){
      if(!resp.ok){
        return resp.text().then(function(t){
          throw new Error(t || ("HTTP " + resp.status));
        });
      }
      if(!resp.body){ throw new Error("sin streaming"); }
      var lector = resp.body.getReader();
      var dec = new TextDecoder();
      var buf = "";
      function paso(){
        return lector.read().then(function(r){
          if(r.done) return;
          buf += dec.decode(r.value, {stream:true});
          var partes = buf.split("\n\n"); buf = partes.pop();
          partes.forEach(function(p){
            if(p.indexOf("data:") !== 0) return;
            var carga = p.slice(5).trim();
            if(carga === "[DONE]") return;
            try{
              var j = JSON.parse(carga);
              if(j.error){ throw new Error(j.error.message || j.error); }
              var d = (j.choices && j.choices[0] && j.choices[0].delta && j.choices[0].delta.content) || "";
              if(d){
                texto += d;
                if(burbuja.childNodes.length && burbuja.childNodes[burbuja.childNodes.length-1].id === "cursor"){
                  burbuja.removeChild(burbuja.lastChild);
                }
                burbuja.appendChild(document.createTextNode(d));
                chat.scrollTop = chat.scrollHeight;
              }
            }catch(e2){ /* fragmento no JSON: se ignora */ }
          });
          return paso();
        });
      }
      return paso();
    }).then(function(){
      // fin sin contenido humano visible pero con respuestas válidas
      if(texto){
        historial.push({rol:"assistant", contenido:texto});
      }
      terminar(true);
    }).catch(function(e){
      if(e.name === "AbortError"){
        if(texto){ historial.push({rol:"assistant", contenido:texto}); }
        terminar(true);
      } else {
        terminar(false);
        log("No respondió el servidor: " + (e.message || e));
      }
    });
  }
  function terminar(conContenido){
    if(!conContenido){
      // quita el cursor y deja un hueco vacío sin mensajes fantasma
      while(chat.lastChild && chat.lastChild.querySelector && chat.lastChild.querySelector("#cursor")){
        chat.removeChild(chat.lastChild);
      }
    }
    leyendo = null;
    enviar.disabled = false; parar.style.display = "none";
    actualizarEstado();
  }
  parar.addEventListener("click", function(){ if(leyendo){ leyendo.abort(); } });
  btnSys.addEventListener("click", function(){ sysWrap.classList.toggle("abierto"); });
  enviar.addEventListener("click", enviarMensaje);
  entrada.addEventListener("keydown", function(e){
    if(e.key === "Enter"){ e.preventDefault(); enviarMensaje(); }
  });
  cargarCatalogo();
})();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Servidor HTTP
# ---------------------------------------------------------------------------
class GemmaHandler(BaseHTTPRequestHandler):
    server_version = "GemmaChat/1.0"

    def _leer_json(self):
        largo = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(largo) if largo else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _enviar(self, codigo, cuerpo, tipo="application/json"):
        if isinstance(cuerpo, (dict, list)):
            cuerpo = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        elif isinstance(cuerpo, str):
            cuerpo = cuerpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo + "; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _get_json(self, base, ruta, timeout=MODELS_TIMEOUT):
        req = urllib.request.Request(base.rstrip("/") + ruta)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    # ---- Rutas ----
    def do_GET(self):
        ruta = urlparse(self.path).path
        if ruta in ("/", "/index.html"):
            self._enviar(200, INDEX_HTML, "text/html")
            return
        if ruta == "/api/models":
            self._lista_modelos()
            return
        self._enviar(404, {"error": "no existe"}, "application/json")

    def do_POST(self):
        ruta = urlparse(self.path).path
        if ruta == "/api/chat":
            self._chat()
            return
        self._enviar(404, {"error": "no existe"}, "application/json")

    # ---- /api/models ----
    def _lista_modelos(self):
        resultado = []
        # LM Studio
        try:
            d = self._get_json(self.server.lm_base, "/v1/models")
            ids = [m.get("id") for m in d.get("data", []) if m.get("id")]
            resultado.append({"id": "lm", "nombre": NOMBRES["lm"],
                              "modelos": ids, "ok": True})
        except Exception as e:
            resultado.append({"id": "lm", "nombre": NOMBRES["lm"],
                              "modelos": [], "ok": False, "error": str(e)})
        # Atomic AI (un solo modelo upstream)
        try:
            d = self._get_json(self.server.atomic_base, "/v1/models")
            ids = [m.get("id") for m in d.get("data", []) if m.get("id")]
            if ids:
                self.server.atomic_modelo = ids[0]
            resultado.append({"id": "atomic", "nombre": NOMBRES["atomic"],
                              "modelos": ids, "ok": True})
        except Exception as e:
            resultado.append({"id": "atomic", "nombre": NOMBRES["atomic"],
                              "modelos": [], "ok": False, "error": str(e)})

        modelolm = self.server.modelo
        if modelolm not in (resultado[0].get("modelos") or []):
            modelolm = (resultado[0].get("modelos") or [None])[0]
        self._enviar(200, {
            "servidores": resultado,
            "porDefecto": {"servidor": "lm", "modelo": modelolm},
        })

    # ---- /api/chat ----
    def _chat(self):
        datos = self._leer_json()
        mensajes = datos.get("messages") or []
        srv = datos.get("servidor") or "lm"
        modelo = datos.get("model") or ""
        sistema = datos.get("system")
        stream = bool(datos.get("stream", True))

        if srv == "atomic":
            base = self.server.atomic_base
            modelo = modelo or self.server.atomic_modelo or self.server.modelo
            nombre = NOMBRES["atomic"]
        else:
            base = self.server.lm_base
            modelo = modelo or self.server.modelo
            nombre = NOMBRES["lm"]

        msgs = []
        if sistema:
            msgs.append({"role": "system", "content": sistema})
        for m in mensajes[-MAX_VUELTA:]:
            rol = m.get("rol")
            if rol not in ("user", "assistant"):
                continue
            msgs.append({"role": rol, "content": m.get("contenido", "")})

        payload = {"model": modelo, "messages": msgs, "stream": stream}
        try:
            resp = self._proxy(base, "/v1/chat/completions", payload)
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "replace")[:1500]
            self._enviar(502, {"error": "%s: HTTP %d - %s" % (nombre, e.code, cuerpo)})
            return
        except Exception as e:
            self._enviar(502, {"error": "No responde %s (%s) ¿está encendido?" % (nombre, base)})
            return

        if not stream:
            body = resp.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return

        # Streaming: reenvía el SSE del backend al cliente tal cual.
        # OJO: NO mandamos "Connection: keep-alive" porque al terminar el
        # stream (data: [DONE]) debemos cerrar la conexion para que el
        # navegador del movil vea el fin y pueda volver a enviar. Si la
        # dejamos viva, la UI se queda en "Pensando..." para siempre.
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            while True:
                # read1 devuelve lo que haya llegado YA (no bloquea pidiendo 4096
                # bytes completos como read()), asi el streaming llega en vivo
                # al movil en vez de quedar colgado hasta juntar todo.
                chunk = resp.read1(4096)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
                # LM Studio manda "data: [DONE]" como cierre del stream y puede
                # dejar la conexion abierta (keep-alive). Si no cortamos aqui,
                # el movil se queda en "Pensando..." para siempre y el boton
                # Enviar queda bloqueado. Al detectar el cierre, terminamos.
                if b"[DONE]" in chunk:
                    # Forzamos el cierre de ESTA conexion al terminar la
                    # respuesta: sin esto el navegador no ve nunca el fin del
                    # streaming y no puede volver a enviar mensajes.
                    self.close_connection = True
                    break
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            pass
        finally:
            try:
                resp.close()
            except Exception:
                pass

    def _proxy(self, base, ruta, datos):
        url = base.rstrip("/") + ruta
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=cuerpo,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return urllib.request.urlopen(req, timeout=CHAT_TIMEOUT)

    def log_message(self, fmt, *args):
        try:
            ip = self.client_address[0] if self.client_address else "?"
            sys.stderr.write("[%s] %-15s %s\n" % (time.strftime("%H:%M:%S"), ip, fmt % args))
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="Chat web con LM Studio o Atomic AI para el móvil.")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--lm", default=DEFAULT_LM)
    ap.add_argument("--atomic", default=DEFAULT_ATOMIC)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    srv = ThreadingHTTPServer((args.host, args.port), GemmaHandler)
    srv.lm_base = args.lm
    srv.atomic_base = args.atomic
    srv.modelo = args.model
    srv.atomic_modelo = None

    print("JARVIS · Chat web en marcha")
    print("  LM Studio : %s  (modelo por defecto: %s)" % (args.lm, args.model))
    print("  Atomic AI : %s" % args.atomic)
    print("  Escucha   : %s:%d" % (args.host, args.port))
    if args.host in ("0.0.0.0", "::"):
        print("  Abre en tu móvil: http://<IP-DE-ESTA-PC>:%d" % args.port)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        print("Chat web detenido.")


if __name__ == "__main__":
    main()
