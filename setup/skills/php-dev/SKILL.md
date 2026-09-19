---
name: php-dev
description: Programar en PHP: Laravel, WordPress, APIs y sitios web.
---

# php-dev

Guia practica de PHP moderno (8.4/8.5, 2026). PHP sigue siendo excelente para:
sitios web clasicos, CMS (WordPress), e-commerce y APIs REST sencillas con
hosting barato. Laravel es muy productivo para MVP y CRUD.

## Versiones y novedades

- PHP 8.3/8.4: maduro (property hooks, asymmetric visibility, #[\Deprecated]).
- PHP 8.5 (nov 2025): pipe operator `|>`, URI extension, clone with, array_first.
- PHP 8.6 en beta (ago 2026).
- Caracteristicas modernas: typed properties, readonly classes, match, enums,
  first-class callables, strict_types.

## Sintaxis moderna esencial

- Tipos estrictos al inicio de cada archivo: `declare(strict_types=1);`
- readonly class con constructor promotion:
  ```php
  readonly class Usuario {
      public function __construct(
          public int $id,
          public string $nombre,
      ) {}
  }
  ```
- match (mejor que switch):
  ```php
  $estado = match ($codigo) { 200, 201 => 'ok', 404 => 'no encontrado', default => 'error' };
  ```
- Enums: `enum Estado: string { case Activo = 'activo'; }`
- NO funciones mysql_*, NO concatenar SQL, NO md5() para passwords.

## Composer y autoloading

- composer init; composer require X; composer require --dev phpunit/phpunit.
- PSR-4 en composer.json mapea namespace -> carpeta:
  `"psr-4": { "App\\": "src/" }`.
- composer install respeta composer.lock; composer dump-autoload regenera.

## Laravel 12 (o 13)

- Crear: `composer create-project laravel/laravel mi-app` o `laravel new mi-app`;
  servir con `php artisan serve`. SQLite por defecto en .env.
- Estructura: routes/ (web.php, api.php), app/Http/Controllers/, app/Models/,
  database/migrations/, resources/views/ (Blade), config/.
- Rutas: `Route::get('/usuarios', [UsuarioController::class, 'index']);`
- Eloquent: `Usuario::where('activo', true)->orderBy('nombre')->get()`,
  `Usuario::findOrFail($id)`.
- Migraciones: `php artisan make:migration ...`, `php artisan migrate`.
- Blade: `{{ $nombre }}` escapa HTML (proteccion XSS).
- Artisan: make:model, make:controller, tinker, route:list.

## WordPress

- Themes en wp-content/themes/ (style.css + functions.php); Plugins en
  wp-content/plugins/. Hooks: add_action() y add_filter().
- Shortcodes: add_shortcode('saludo', fn() => '...') -> [saludo].
- Moderno: block themes con theme.json (Gutenberg) en vez de shortcodes custom.
- PHP 8.x ya soportado por WordPress.

## Seguridad (imprescindible)

- SQL: prepared statements PDO siempre:
  `$stmt = $pdo->prepare('SELECT * FROM usuarios WHERE email = ?'); $stmt->execute([$email]);`
- Passwords: password_hash / password_verify (NUNCA md5/sha1).
- XSS: htmlspecialchars($var, ENT_QUOTES, 'UTF-8') (Blade lo hace con {{ }}).
- No usar $_REQUEST crudo; validar/desinfectar input; cookies con HttpOnly,
  Secure y SameSite; regenerar sesion al login.

## Cuando tiene sentido PHP hoy

- SI: sitios web clasicos servidos en hosting, WordPress, e-commerce, APIs REST
  sencillas, MVPs con Laravel.
- NO: apps de tiempo real pesadas, alta concurrencia/latencia critica (ahi
  Node/Go/Java), computacion intensiva.
