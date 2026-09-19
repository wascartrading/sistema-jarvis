---
name: game-dev
description: Juegos 2D/3D: Canvas, Phaser, PixiJS, Three.js, Pygame y Godot.
---

# game-dev

Guia practica de desarrollo de videojuegos 2026. Cubre juegos web (Canvas,
Phaser, PixiJS, Three.js), Python (Pygame/Arcade) y Godot con GDScript.

## Conceptos universales (todos los motores)

- Game loop: actualizar estado + dibujar + esperar al siguiente frame.
- Delta time (dt): multiplicar velocidades por dt para que el juego no dependa
  de los FPS.
- Sprites: imagenes dibujadas en posiciones (x, y); animaciones = cambiar de
  sprite o de recorte (sprite sheet).
- Colisiones: AABB para rectangulos (`a.x < b.x+b.w && a.x+a.w > b.x && ...`),
  circulos (`distancia <= r1+r2`).
- Audio: reanudar AudioContext tras un gesto del usuario (autoplay policy).
- Input: teclado (estado de teclas), raton, touch, gamepad.

## Juegos web con Canvas 2D puro

- Lo minimo y sin dependencias. Ideal para juegos simples y prototipos.
- Game loop estandar:
  `requestAnimationFrame` con `dt = (t - last) / 1000`; update(dt); render();
- Sprites: `ctx.drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh)` para recortar.
- Collisions: AABB y circulos (ver conceptos).
- Limites de canvas: `canvas.width` / `canvas.height`, resize con `ResizeObserver`.
- Ejemplo minimo: un rectangulo que se mueve con flechas + colision con borde.

## Juegos 2D web con librerias

- Phaser 4: framework 2D completo ("baterias incluidas"): fisica Arcade/Matter,
  camaras, tweens, input, partículas, atlas. Ideal para juegos completos.
  Plantillas: `npm create @phaserjs/game@latest`.
- PixiJS 8: motor de render 2D WebGPU/WebGL, el mas rapido, PERO no trae loop
  ni fisica (es solo renderer). Para HUD/apps ricas o engines propios.
- Kaplay (antes Kaboom): API super sencilla, ideal para jams, aprender y juegos
  pequenos. Prototipo en 10 lineas.
- MelonJS: estable pero ritmo lento. Impact.js: muerto, NO usar.
- Fisica 2D: Matter.js (integrado en Phaser como "Matter").
- Audio: Howler.js o WebAudio API.

## Juegos 3D web

- Three.js (r160+): la libreria 3D estandar. Conceptos: Scene, PerspectiveCamera,
  Mesh (Geometry + Material), WebGLRenderer (o WebGPURenderer), GLTFLoader,
  OrbitControls, EffectComposer para postprocesado.
- Babylon.js: engine 3D "baterias incluidas" con GUI y fisica.
- Fisica 3D: Rapier (moderno) o Ammo.js/Jolt.

## Juegos con Python

- Pygame: la clasica y mantenida para juegos 2D en Python. Game loop con
  `pygame.event.get()`, `pygame.display.flip()`, `pygame.time.Clock().tick(FPS)`.
- Arcade: alternativa moderna y mas limpia que Pygame (basada en Pyglet), con
  clases como `arcade.Window`, sprites, fisica de plataformas, particle effects.
- pgzero (Pygame Zero): wrapper educativo simplificado, bueno para aprender.
- Para prototipos rapidos en Python: Arcade o pgzero. Para control total: Pygame.
- Para juegos web desde Python: Pygbag (compila Pygame a WebAssembly).

## Godot Engine con GDScript

- Godot 4: motor libre completo (2D y 3D). Exporta a Windows, Linux, macOS,
  Android, iOS y web (WebAssembly).
- Conceptos: Nodes (nodos) y Scenes (escenas), arbol de escenas, signals,
  `_ready()`, `_process(delta)`, `_physics_process(delta)`, @onready,
  Input.is_action_pressed.
- GDScript: sintaxis tipo Python. `extends Node2D`, `func _ready():`, `var x = 0`.
- Escenas = componentes reutilizables (.tscn). Prefabs/instancias = instanciar
  escenas con `load()` / `preload()`.
- Fisica 2D: CharacterBody2D + CollisionShape2D + Area2D para deteccion.
- Es la opcion recomendada para juegos desktop/movil sin depender de navegador.

## Decision rapida de tecnologia

- Juego web 2D completo: Phaser 4.
- Juego web 2D pequeno/jam/prototipo: Kaplay o Canvas puro.
- Juego web 3D: Three.js (o Babylon si quieres todo integrado).
- Juego desktop/movil (2D o 3D): Godot 4 con GDScript.
- Juego educativo/simple en Python: Arcade o pgzero.
- Juego Python con control total: Pygame.
- Render 2D de maximo rendimiento dentro de una app: PixiJS 8.

## Buenas practicas

- Separar update (logica) de render (dibujo). No dibujar en update.
- Usar dt siempre para movimiento, nunca pasos fijos por frame.
- Object pooling para balas/particulas (reusar objetos, no crear/destruir).
- Estado del juego (menu, jugando, pausa, game over) con maquina de estados.
- Asset loading: precargar y mostrar pantalla de carga; manejar errores.
- Audio: boton de silencio; reanudar AudioContext con el primer click.
- Fijar FPS: canvas.requestPointerLock para juegos 3D en primera persona.
- Probar en el navegador real (Canvas/WebGL fallan en test runner).
