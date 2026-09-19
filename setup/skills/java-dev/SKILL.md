---
name: java-dev
description: Programar en Java: Spring, APIs, aplicaciones y JUnit.
---

# java-dev

Guia practica de Java moderno (JDK 21/25 LTS, 2026). Java es ideal para:
aplicaciones empresariales, APIs REST con Spring Boot, servicios grandes,
Android y sistemas legacy con requisitos de estabilidad.

## Versiones y novedades

- JDK 21 (LTS, sep 2023) y JDK 25 (LTS, sep 2025). Cadencia: LTS cada 2 anos.
- JDK 21: records, virtual threads (JEP 444), pattern matching for switch
  (JEP 441), record patterns, text blocks, sealed classes, sequenced collections.
- JDK 25: compact source files + instance main methods (scripts sin class),
  module import declarations, scoped values, generational Shenandoah.
- Virtual threads: millones de hilos ligeros para I/O
  (`Executors.newVirtualThreadPerTaskExecutor()`); thread-per-request sin coste.

## Sintaxis moderna esencial

- Records: clases inmutables de datos con equals/hashCode/toString generados:
  `public record Usuario(long id, String nombre) {}` -> `u.id()`, `u.nombre()`.
- Pattern matching + switch expression:
  ```java
  return switch (forma) {
      case Circulo c -> "Circulo r=" + c.r();
      case Rectangulo r -> "Rectangulo " + r.b() + "x" + r.a();
  };
  ```
- Text blocks: `String html = """<html>...</html>""";`
- Sealed classes: control de subtipos con `permits`.
- List.of(), Map.of() para colecciones inmutables.

## Spring Boot (4.x)

- Spring Boot 4.x es la version actual (3.x migra hacia 4). Requiere Java 17+
  (recomendado 21/25). Proyectos desde start.spring.io.
- Estructura: ApiApplication (@SpringBootApplication + main), Controller
  (@RestController), Service (@Service), Repository (@Repository, JpaRepository),
  entidades/records.
- Ejemplo minimo de controller:
  ```java
  @RestController
  @RequestMapping("/api/usuarios")
  public class UsuarioController {
      private final UsuarioService service;
      public UsuarioController(UsuarioService service) { this.service = service; }

      @GetMapping
      public List<Usuario> listar() { return service.listar(); }

      @PostMapping
      @ResponseStatus(HttpStatus.CREATED)
      public Usuario crear(@RequestBody Usuario u) { return service.crear(u); }
  }
  ```
- Inyeccion por constructor (no @Autowired en campos).
- Maven (pom.xml, estandar) o Gradle (build.gradle, mas rapido/flexible).
  Comandos: `./mvnw spring-boot:run`, `./mvnw test`.

## Java sin Spring (plain Java)

- Viable hoy: records + switch + text blocks + List.of() dan POJO moderno sin
  Lombok ni JPA. HttpClient del JDK para HTTP.
- Microframeworks ligeros: Javalin, Helidon, Quarkus, Vert.x.
- Compact source files (JDK 25) permiten scripts/CLIs sin scaffolding.

## Testing

- JUnit 5: @Test, @BeforeEach, @SpringBootTest, @WebMvcTest, @MockitoBean.
- AssertJ para asserts fluidos.

## Herramientas

- JDK (Temurin/Adoptium recomendado), Maven o Gradle.
- Compilar/ejecutar: mvn compile / mvn package; java -jar target/app.jar.
- Configuracion: application.properties o application.yml; @ConfigurationProperties.
- NO Java 8 en proyectos nuevos, NO XML config, NO threads manuales donde
  aplican virtual threads.
