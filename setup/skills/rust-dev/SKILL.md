---
name: rust-dev
description: Programacion en Rust moderna (Edition 2024): ownership y borrow checker, manejo de errores con Result, async con tokio, web con axum, crates imprescindibles (serde, clap, tracing, sqlx) y tooling cargo. Usar para crear CLIs, servicios, herramientas de rendimiento critico y backend en Rust.
---

# rust-dev

Guia practica de Rust moderno (Edition 2024, estable ~1.85+ / 1.97). Rust es
ideal para: rendimiento critico, sistemas sin GC, CLIs rapidas, servicios de
red, WebAssembly y donde la seguridad de memoria es prioridad.

## Edition 2024 y novedades

- Rust 1.85: Edition 2024 (cambios en gen, match, unsafe, macro rules).
- Caracteristicas clave: ownership, borrow checker, lifetimes, Result/Option,
  pattern matching, traits, generics, const generics.
- Rust no tiene GC ni null; la memoria se gestiona con ownership (cada valor
  tiene UN dueno que lo libera al salir de scope) y borrows (& referencias).

## Tooling (cargo)

- cargo: gestor de paquetes, build, test y run en uno.
- `cargo new proyecto` crea un binario; `cargo add serde` anade dependencia
  (Cargo.toml); `cargo build` / `cargo run` / `cargo test`.
- clippy: linter recomendado (cargo clippy). rustfmt: formateador (cargo fmt).
- Workspaces (cargo workspace) para multiples crates.
- Perfil release: `cargo build --release` (optimizado).

## Manejo de errores

- Result<T, E> para errores recuperables; `?` propaga el error:
  `let data = File::read(path)?;`
- thiserror: para definir tipos de error propios en librerias (derive).
- anyhow: para aplicaciones/CLIs (error generico con contexto, `.context()`).
- Regla: thiserror en librerias, anyhow en binarios.
- Option<T> para valores que pueden no existir; `.ok_or(...)` para convertir.

## Async y Tokio

- tokio es el runtime async estandar: `#[tokio::main]`, `async fn`,
  `tokio::spawn` para tareas en paralelo, `tokio::time::sleep`.
- `tokio::select!` para manejar multiples futuros.
- No usar `std::thread` para I/O; usar async. Async solo ayuda con I/O, no con CPU.
- Canales: `tokio::sync::mpsc` para productor-consumidor.

## Web en Rust

- axum (construido sobre tokio): el framework web moderno recomendado.
  - Router con `route("/", get(handler))`, extractors (Path, Json, Query, State),
    respuestas con `impl IntoResponse`.
- actix-web: alternativa madura (actores, alto rendimiento) pero axum es la
  tendencia actual y comparte ecosistema con tokio.
- warp: mas viejo y menos recomendado hoy.
- Ejemplo minimo:
  ```rust
  #[tokio::main]
  async fn main() {
      let app = Router::new().route("/", get(|| async { "hola" }));
      let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
      axum::serve(listener, app).await.unwrap();
  }
  ```

## Crates imprescindibles

- serde + serde_json: serializacion/deserializacion (derive Serialize/Deserialize).
- tokio: async runtime.
- clap: CLIs con derive (argparse moderno en Rust).
- tracing + tracing-subscriber: logging estructurado moderno (en vez de log/env_logger).
- reqwest: cliente HTTP async.
- sqlx: acceso a SQL con queries compiladas en tiempo de compilacion (sin ORM);
  sqlx::query! valida contra la BD. Alternativa ORM: sea-orm o diesel.
- chrono (o time): fechas y horas.
- uuid: IDs; rand: aleatoriedad.

## JSON

- serde_json: `serde_json::to_string` / `from_str` / `to_value`.
- Structs con derive(Serialize, Deserialize) + atributos (#[serde(rename)]).

## Cuando usar Rust vs cuando NO

- SI: rendimiento critico, sistemas, WASM, CLIs rapidas, servicios de red,
  reemplazar C/C++, procesamiento pesado.
- NO: prototipos rapidos, scripts pequenos, ciencia de datos (Python), frontend
  web (JS) salvo WASM. Curva de aprendizaje alta: no es para todo.
