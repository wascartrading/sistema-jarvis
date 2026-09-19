# -*- coding: utf-8 -*-
"""
GENERADOR DE CONOCIMIENTO BASE - Da al cerebro de JARVIS una base solida
========================================================================
Genera cientos de ejemplos variados por intencion para que el cerebro
aprenda a generalizar desde el primer momento, y luego entrena con ellos
junto a la experiencia real recogida del sistema.

Uso:
  python generar_conocimiento.py            # genera y entrena
  python generar_conocimiento.py --epocas 40
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from red_neuronal import CerebroJarvis  # noqa: E402

# Ejemplos variados por intencion (base de conocimiento)
EJEMPLOS = {
    "abrir_app": [
        "abre youtube", "abre el navegador", "abre la calculadora", "abre spotify",
        "abre el explorador de archivos", "abre word", "abre excel", "abre el bloc de notas",
        "lanzar el editor de codigo", "ejecuta la calculadora", "abre el panel de control",
        "inicia el navegador chrome", "abre la carpeta de descargas", "abre el administrador de tareas",
        "ejecuta el juego", "abre la tienda de windows", "abre la camara", "abre el reproductor",
        "abre la configuracion", "abre el correo", "abre whatsapp", "abre telegram",
        "abre discord", "abre la terminal", "abre el powershell", "abre el cmd",
    ],
    "buscar_web": [
        "busca en google que es python", "busca el clima de hoy", "busca noticias de tecnologia",
        "investiga sobre inteligencia artificial", "consulta el precio del dolar",
        "busca recetas de cocina", "busca videos de gatos", "busca el horario del cine",
        "googlea mi nombre", "busca vuelos a madrid", "consulta el estado del trafico",
        "busca la definicion de machine learning", "investiga sobre el nuevo iphone",
        "busca restaurantes cerca", "consulta el resultado del partido", "busca tutoriales de python",
        "busca ofertas de trabajo", "busca la pagina de opencode", "investiga sobre trading",
        "busca el significado de la palabra efimero", "consulta el pronostico del tiempo",
    ],
    "reproducir_musica": [
        "reproduce musica relajante", "pon una cancion de rock", "pon musica para concentrarme",
        "reproduce mi playlist favorita", "pon algo de jazz", "reproduce el ultimo album de mi artista",
        "pon musica de fondo", "reproduce un video de youtube", "pon la radio",
        "reproduce sonidos de lluvia", "pon musica clasica", "reproduce el top 50",
        "pon una cancion de reggaeton", "reproduce musica para dormir", "pon algo tranquilo",
        "reproduce el video musical nuevo", "pon musica electronica", "reproduce audiolibros",
        "pon la cancion que me gusta", "reproduce el podcast de tecnologia",
    ],
    "crear_proyecto": [
        "crea un juego de snake", "hazme una pagina web", "crea un bot de trading",
        "desarrolla una aplicacion de notas", "hazme un script para organizar archivos",
        "crea un proyecto de python", "inventa un juego de domino", "hazme una calculadora",
        "crea un sistema de inventario", "desarrolla un bot de telegram", "hazme un sitio web personal",
        "crea un juego 3d", "hazme una app de tareas", "crea un programa de facturacion",
        "desarrolla un asistente de voz", "hazme un juego de memoria", "crea un dashboard de ventas",
        "inventa un juego de preguntas", "hazme una extension de navegador", "crea un sistema solar 3d",
    ],
    "modificar_codigo": [
        "modifica el script de trading", "arregla el error del bot", "corrige el bug de la pagina",
        "mejora el rendimiento del juego", "cambia el color del boton", "arregla el codigo de la calculadora",
        "modifica la interfaz del asistente", "corrige el error de conexion", "mejora la velocidad del script",
        "cambia el texto del mensaje", "arregla el problema del audio", "modifica el diseño de la web",
        "corrige el error de la base de datos", "mejora el codigo del bot", "cambia la logica del juego",
        "arregla el error de la camara", "modifica el script de youtube", "corrige el problema del login",
        "mejora la calidad del sonido", "cambia el tamaño de la ventana",
    ],
    "automatizar": [
        "automatiza la copia de seguridad", "programa una tarea cada dia", "vigila la carpeta de descargas",
        "automatiza el envio de correos", "programa un recordatorio cada hora", "monitorea el rendimiento del pc",
        "automatiza la organizacion de archivos", "programa el apagado automatico", "vigila el precio del bitcoin",
        "automatiza la descarga de videos", "programa un respaldo semanal", "monitorea la temperatura del pc",
        "automatiza el reporte de ventas", "programa el inicio de la musica", "vigila los procesos del sistema",
        "automatiza la limpieza de archivos temporales", "programa un aviso cuando llegue el correo",
        "monitorea el estado del servidor", "automatiza la publicacion en redes", "programa el respaldo de la base de datos",
    ],
    "informacion": [
        "que es python", "como funciona la inteligencia artificial", "dime que hora es",
        "cuando es navidad", "donde esta la capital de francia", "por que el cielo es azul",
        "explica que es el machine learning", "que es una red neuronal", "como se hace un cafe",
        "dime el significado de la vida", "que es el trading", "como funciona un motor",
        "explica la teoria de la relatividad", "que es la fotosintesis", "como se forman las nubes",
        "dime un dato curioso", "que es la energia solar", "como funciona el wifi",
        "explica que es la bolsa de valores", "que es la inteligencia artificial generativa",
    ],
    "memoria": [
        "recuerda que me gusta el cafe", "aprende que trabajo de noche", "guarda esto en memoria",
        "recuerda que mi nombre es wascar", "anota que prefiero el te", "no olvides que tengo reunion el lunes",
        "recuerda mi nombre", "recuerda mi fecha de nacimiento", "recuerda mi correo electronico",
        "recuerda mi direccion", "recuerda mi numero de telefono", "recuerda mis gustos musicales",
        "recuerda que mi color favorito es azul", "aprende que uso windows", "guarda que mi contraseña es secreta",
        "recuerda que me gusta la musica clasica", "anota que mi cumpleaños es en mayo",
        "aprende que no me gusta el ruido", "recuerda que trabajo con trading", "guarda que mi equipo es el real madrid",
        "recuerda que prefiero el cafe sin azucar", "aprende que duermo temprano", "anota que mi perro se llama rocky",
        "recuerda que me gusta programar de noche", "guarda que mi ciudad es bogota", "aprende que soy madrugador",
    ],
    "trading": [
        "analiza el mercado de opciones", "muestrame las velas de iq option", "como va el bitcoin hoy",
        "dame una señal de trading", "analiza la tendencia del dolar", "que dice el indicador rsi",
        "abre el bot de trading", "revisa mis operaciones de hoy", "analiza el par eur usd",
        "que tan volatil esta el mercado", "dame el precio del oro", "analiza las velas de 5 minutos",
        "revisa la gestion de riesgo", "como esta el mercado de criptomonedas", "dame una estrategia de trading",
        "analiza el volumen de operaciones", "que dice el indicador macd", "revisa el saldo de mi cuenta",
        "analiza la tendencia del petroleo", "dame el analisis del dia",
    ],
    "juego": [
        "juega snake conmigo", "abre el juego de domino", "juguemos algo", "crea una partida de ajedrez",
        "juega al tres en raya", "abre el juego de memoria", "juguemos al ahorcado",
        "abre el sistema solar 3d", "juega al cubo rubik", "hagamos un juego de preguntas",
        "juguemos al gato", "abre el juego de la serpiente", "juguemos a adivinar el numero",
        "abre el juego de naves", "juguemos al buscaminas", "abre el juego de cartas",
        "juguemos al piedra papel tijera", "abre el juego de plataformas", "juguemos al memory",
        "abre el juego de carreras",
    ],
    "sistema": [
        "apaga el equipo", "reinicia el sistema", "cierra el navegador", "muestrame los procesos",
        "cuanta memoria tiene el pc", "que programas estan abiertos", "instala una aplicacion",
        "borra la carpeta temporal", "muestrame el espacio del disco", "actualiza windows",
        "cierra el juego", "apaga la pantalla", "reinicia el asistente", "muestrame la bateria",
        "que version de windows tengo", "abre el administrador de dispositivos", "limpia la papelera",
        "muestrame el uso de cpu", "desinstala un programa", "configura el fondo de pantalla",
    ],
    "saludo": [
        "hola jarvis", "buenos dias", "buenas tardes", "buenas noches", "hey que tal",
        "hola como estas", "saludos jarvis", "buenas", "que onda", "hola amigo",
        "buenos dias jarvis", "hey jarvis", "hola de nuevo", "que tal todo", "buenas tardes jarvis",
    ],
    "despedida": [
        "adios jarvis", "hasta luego", "nos vemos", "chao", "bye", "terminamos por hoy",
        "hasta mañana", "me voy a dormir", "apaga todo y adios", "nos vemos luego",
        "hasta la proxima", "adios por ahora", "me despido", "buenas noches y adios", "hasta pronto",
    ],
}


def main():
    parser = argparse.ArgumentParser(description="Genera conocimiento base y entrena el cerebro de JARVIS")
    parser.add_argument("--epocas", type=int, default=40, help="Epocas de entrenamiento")
    args = parser.parse_args()

    textos, intenciones = [], []
    for intencion, ejemplos in EJEMPLOS.items():
        for ej in ejemplos:
            textos.append(ej)
            intenciones.append(intencion)

    print(f"Conocimiento base: {len(textos)} ejemplos en {len(EJEMPLOS)} intenciones")
    print("Entrenando el cerebro...")
    cerebro = CerebroJarvis()
    perdida, precision = cerebro.entrenar(textos, intenciones, epocas=args.epocas)
    ruta = cerebro.guardar()
    print(f"Listo. Perdida {perdida:.4f} | Precision {precision:.2%}")
    print(f"Checkpoint: {ruta}")

    # Prueba de generalizacion con frases NUEVAS que no estaban en el entrenamiento
    print("\nPrueba de generalizacion (frases nuevas):")
    pruebas = [
        "abre el editor", "busca el clima", "pon algo de musica", "hazme un juego",
        "arregla el codigo", "programa un respaldo", "que es el universo", "recuerda mi nombre",
        "analiza el mercado", "juguemos algo", "apaga el pc", "hola", "hasta luego",
    ]
    for t in pruebas:
        pred = cerebro.predecir(t)[0]
        print(f"  '{t}' -> {pred[0]} ({pred[1]:.0%})")

    print(f"\nResumen: {cerebro.resumen()}")


if __name__ == "__main__":
    main()