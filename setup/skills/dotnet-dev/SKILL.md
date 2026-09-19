---
name: dotnet-dev
description: Programar en C# y .NET: APIs, escritorio y juegos.
---

# dotnet-dev

Guia practica de C# / .NET moderno (.NET 10 LTS, C# 13/14). .NET es ideal para:
aplicaciones de escritorio (Windows), APIs web, juegos (Unity) y servicios
empresariales. Multiplataforma (Windows, Linux, macOS).

## Versiones y novedades

- .NET 10 (nov 2025): LTS, soportado 3 anos. Acompanado de C# 14.
- C# 12: primary constructors, collection expressions `[1, 2, 3]`, init, required.
- C# 13: params collections (Span, ReadOnlySpan), ref struct, System.Threading.Lock.
- C# 14: keyword `field` en propiedades, extension members, null-conditional
  assignment, partial constructors.
- .NET 11 en preview; usar .NET 10 LTS en produccion.

## Estructura de un proyecto

- CLI dotnet: `dotnet new console` / `webapi` / `maui` / `sln` (solucion).
- `dotnet run` (compila y ejecuta), `dotnet watch run` (recarga en caliente),
  `dotnet add package X` (NuGet), `dotnet test`, `dotnet publish`.
- Top-level statements: un Program.cs puede ser el programa completo sin clase
  Program ni Main.

## ASP.NET Core: Minimal APIs (recomendado)

- Microsoft recomienda Minimal APIs para proyectos nuevos (menos boilerplate,
  mejor rendimiento, testing facil). Controllers solo para equipos MVC u OData.
- Ejemplo minimo (Program.cs completo):
  ```csharp
  var builder = WebApplication.CreateBuilder(args);
  var app = builder.Build();
  app.MapGet("/", () => "Hola");
  app.MapGet("/users/{id}", (int id) => $"Usuario {id}");
  app.Run();
  ```
- Binding de JSON con records; validacion con DataAnnotations o FluentValidation.

## EF Core (Code First)

- `dotnet add package Microsoft.EntityFrameworkCore.Sqlite` (+ provider de la BD).
- `dotnet tool install --global dotnet-ef` + `dotnet ef migrations add Inicial`
  + `dotnet ef database update`.
- Contexto: clase que hereda DbContext con DbSet<T>. Modelos = clases POCO.
- Consultas LINQ se traducen a SQL: `.Where(u => u.Nombre.StartsWith("A"))`,
  `.OrderBy(...)`, `.ToListAsync()`.

## Async y concurrencia

- `async Task` SIEMPRE (nunca `async void` salvo eventos). Sufijo `Async` en nombres.
- Evitar `.Result` / `.Wait()` (bloquean).
- Task (concurrencia cooperativa para I/O), Parallel.ForEachAsync para CPU
  (evitar Parallel dentro de web apps).
- Channel<T>: cola productor-consumidor segura (WriteAsync/ReadAsync).
- System.Threading.Lock (C# 13) reemplaza el lock clasico.

## Programacion de juegos: Unity y C#

- Unity usa C# (su propio runtime, generalmente C# 9/LTS): los scripts heredan
  MonoBehaviour con GameObjects y componentes (Transform, Rigidbody, Collider).
- Ciclo de vida: Update() (cada frame), Start() (una vez), FixedUpdate() (fisica).
- Movimiento independiente de FPS: multiplicar por Time.deltaTime.
- Eventos: OnTriggerEnter / OnCollisionEnter; GetComponent<T>() para acceder a
  otros componentes; Destroy(gameObject).
- Patrones: object pooling, ScriptableObjects (data-driven), coroutines.

## Escritorio

- WPF (Windows, clasico, XAML), WinUI 3 (moderno Windows 11) o MAUI
  (cross-platform: Windows, macOS, Android, iOS). MAUI es la apuesta moderna de
  Microsoft para multiplataforma.

## Buenas practicas

- Inyeccion de dependencias integrada (builder.Services.AddSingleton/Scoped).
- Records para DTOs inmutables. Records con primary constructors.
- Configuracion: appsettings.json + IConfiguration + Options pattern.
- Logging: ILogger<T> integrado (Serilog opcional para sinks extra).
- Tests: xUnit o MSTest + Microsoft Testing Platform (dotnet test en .NET 10).
- NO .NET Framework (solo legacy), NO controllers por defecto, NO async void.
