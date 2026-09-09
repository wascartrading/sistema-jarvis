---
name: go-dev
description: Programacion en Go (Golang) moderna: estructuras de proyecto, web con net/http o chi, concurrencia con goroutines y channels, JSON, SQL, errores y tooling. Usar para crear APIs, CLIs, servicios y herramientas de sistema en Go con practicas actualizadas.
---

# go-dev

Guia practica de Go moderno (Go 1.24+ / 1.26). Go es ideal para: APIs y
microservicios, herramientas CLI, redes, concurrencia alta y deploys simples
(binario unico). Compilado, rapido y con goroutines nativas.

## Novedades recientes (2024-2026)

- Go 1.22: for loop con variables por iteracion (no mas bug del loop).
- Go 1.23: iterators (range sobre funciones), range-over-func.
- Go 1.24: generics mejorados, `//go:wasmexport`, tool management.
- Go 1.25+: mejoras de JSON (structs), mapas, memory optimizations.
- Generics estan desde 1.18 (type parameters).

## Estructura de proyecto

- Todo vive en un modulo: `go mod init <nombre>` crea go.mod.
- Convencion de carpetas: `cmd/` (main por aplicacion: cmd/api/main.go),
  `internal/` (codigo privado), `pkg/` (codigo publico reutilizable),
  `api/` o `migrations/` si aplica.
- NO organizar por capas tecnicas (models/, controllers/) si no es necesario;
  Go prefiere paquetes por dominio o feature.
- Nombres cortos y claros. Exported = Mayuscula inicial.

## Web en Go

- net/http nativo con el nuevo ServeMux (1.22+): rutas con method y wildcards:
  `mux.HandleFunc("GET /users/{id}", handler)` y `r.PathValue("id")`.
- Para APIs mas completas: chi (ligero, compatible con net/http) o echo/gin.
  Recomendacion: net/http para APIs simples; chi si necesitas middlewares.
- Middlewares: funciones que envuelven http.Handler (logging, auth, CORS).
- JSON: `encoding/json` con `json.Marshal` / `json.Unmarshal`; structs con tags.
  `json.NewEncoder(w).Encode(data)` para responder; `json.NewDecoder(r.Body)`.
- Ejemplo minimo:
  ```go
  mux := http.NewServeMux()
  mux.HandleFunc("GET /hola", func(w http.ResponseWriter, r *http.Request) {
      w.Header().Set("Content-Type", "application/json")
      json.NewEncoder(w).Encode(map[string]string{"msg": "hola"})
  })
  http.ListenAndServe(":8080", mux)
  ```

## Concurrencia

- Goroutines: `go funcion()` lanza en paralelo (hilos ligeros).
- Channels: `ch := make(chan T)` para comunicar goroutines; `<-ch` recibe.
- sync.WaitGroup para esperar a varias goroutines: Add/Done/Wait.
- errgroup (golang.org/x/sync/errgroup) para lanzar en paralelo y recibir el
  primer error.
- context: `context.Context` para timeouts y cancelacion, pasar siempre como
  primer parametro en I/O.
- NO compartir memoria entre goroutines sin sincronizacion (mutex, channels).

## SQL y bases de datos

- `database/sql` + driver (`github.com/lib/pq` o mejor `pgx` para Postgres).
- sqlc: genera codigo Go tipado desde consultas SQL (la opcion moderna).
- GORM: ORM pesado, solo si de verdad lo necesitas. Preferir sqlc o database/sql.
- Practicas: prepared statements (parametros ? o $1), cerrar rows con defer,
  ctx con timeout en queries.

## Errores

- Envolver siempre: `fmt.Errorf("leyendo usuario: %w", err)`.
- Comprobar con `errors.Is(err, ...)` (sentinel) o `errors.As(err, &tipo)`.
- Nunca ignorar errores con `_` sin justificacion.
- Logging: `log/slog` (stdlib, moderno, estructurado) en lugar de log viejo.

## Tooling

- gofmt para formato (o gofmt -s). go vet para detectar problemas.
- golangci-lint: linter completo recomendado.
- go test: tests unitarios; `go test ./...`; tabla de tests con t.Run.
- Go workspaces (`go work`) para multiples modulos relacionados.
- Version de Go: mantener la LTS/reciente; go.mod declara la version.
- go mod tidy para limpiar dependencias.

## JSON y configuracion

- Structs con tags: `json:"nombre,omitempty"`, `json:"-"` para omitir.
- Preferir `encoding/json` sobre libs externas salvo necesidad.
- Config: variables de entorno con `os.Getenv` + defaults, o Viper si es compleja.
- Flags CLI: `flag` stdlib o cobra (spf13) para CLIs grandes.

## Cuando usar Go vs otros

- Go: APIs, CLIs, servicios de red, herramientas de sistema, sustituir scripts
  Python que necesitan velocidad/despliegue sin runtime.
- NO: ciencia de datos/IA (Python), frontend (JS), aplicaciones GUI complejas.
