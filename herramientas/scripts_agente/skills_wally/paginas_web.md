# SKILL: Crear paginas web (HTML/CSS/JS)

Guia rapida para crear paginas web cuando el jefe lo pida.

## Estructura basica de una pagina HTML5

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Titulo de la pagina</title>
    <style>
        /* CSS aqui: colores, fuentes, layout */
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
    </style>
</head>
<body>
    <h1>Titulo principal</h1>
    <p>Texto de ejemplo.</p>
    <script>
        // JavaScript aqui: interactividad
    </script>
</body>
</html>

## Reglas

1. Crea SIEMPRE un archivo .html con la extension correcta usando write.
2. Incluye la estructura completa: doctype, html, head (meta charset UTF-8,
   title, style) y body.
3. Usa CSS dentro de <style> para el diseno (colores, fuentes, layout).
4. Usa JavaScript dentro de <script> para interactividad (botones, menus).
5. El archivo debe ser el producto final completo, no un script que lo
   genere.
6. Despues de crear, verifica con read y abre con la herramienta abrir
   (se abre en el navegador).
7. Para tiendas: secciones de productos, precios, botones de comprar,
   imagenes (pueden ser de placeholder como https://placehold.co/300x200).

## Ejemplos de secciones utiles

- Barra de navegacion: <nav><a href="#">Inicio</a> <a href="#">Productos</a></nav>
- Tarjeta de producto: <div class="producto"><h3>Nombre</h3><p>Precio</p><button>Comprar</button></div>
- Pie de pagina: <footer><p>Copyright 2026</p></footer>