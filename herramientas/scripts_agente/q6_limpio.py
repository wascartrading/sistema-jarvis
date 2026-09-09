#!/usr/bin/env python3
"""Juego Snake - versión sin curses (funciona en Windows sin dependencias extra)"""

import os
import sys
import time

# Inicializar el juego
WIDTH = 20
HEIGHT = 20
GRID_SIZE = WIDTH * HEIGHT

# Colores para el terminal (si están disponibles)
COLOR_BG = "\033[2;37m"      # gris claro
COLOR_FOOD = "\033[2;32m"    # verde
COLOR_SNAKE = "\033[2;33m"   # amarillo
COLOR_HEAD = "\033[2;34m"    # azul
COLOR_WALL = "\033[91m"      # rojo

def clear_screen():
    """Limpiar la pantalla de forma compatible con Windows"""
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_grid():
    """Dibujar la cuadrícula del juego"""
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if (x + y) % 2 == 0:
                print(f"\r[{x:2d},{y:2d}]", end='')
    print()

def draw_snake(snake_body):
    """Dibujar la serpiente en la consola"""
    for i, segmento in enumerate(snake_body):
        x = i * 2
        y = (len(snake_body) - 1 - i) * 2
        if y < 0 or y >= HEIGHT or x < 0 or x >= WIDTH:
            continue
        if segmento == 'head':
            print(f"\r[{x:2d},{y:2d}]>", end='')
        else:
            print(f"\r[{x:2d},{y:2d}]", end='')

def draw_food(food_pos):
    """Dibujar la comida"""
    x, y = food_pos
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        print(f"\r[{x:2d},{y:2d}]", end='')

def main():
    """Juego Snake principal"""
    # Posición inicial de la serpiente
    snake = [
        {'x': WIDTH // 2, 'y': HEIGHT // 2},
        {'x': WIDTH // 4, 'y': HEIGHT // 2},
        {'x': WIDTH // 6, 'y': HEIGHT // 2}
    ]
    direction = (0, 1)  # derecha
    food = (WIDTH - 2, HEIGHT - 2)
    
    print("=" * 50)
    print("   JUEGO SNAKE - Versión sin curses")
    print("=" * 50)
    print("Controla con las flechas del teclado")
    print("Presiona 'q' para salir")
    print()
    
    while True:
        clear_screen()
        draw_grid()
        draw_food(food)
        draw_snake(snake)
        
        # Obtener entrada del teclado
        key = sys.stdin.read(1)
        
        # Mover la serpiente
        if key == 'q':
            print("Juego terminado. Saliendo...")
            break
        
        dx, dy = direction
        new_head = {
            'x': snake[0]['x'] + dx,
            'y': snake[0]['y'] + dy
        }
        
        # Verificar colisión con paredes
        if (new_head['x'] < 0 or new_head['x'] >= WIDTH or
            new_head['y'] < 0 or new_head['y'] >= HEIGHT):
            print("¡GAME OVER! Has chocado contra la pared.")
            break
        
        # Verificar colisión con la propia serpiente
        if new_head in snake:
            print("¡GAME OVER! Has chocado contigo mismo.")
            break
        
        # Añadir nueva cabeza
        snake.insert(0, new_head)
        
        # Verificar si se comió la comida
        if new_head == food:
            print("¡Comió la comida! Creciendo...")
            # Mover la cola (eliminar el final)
            snake.pop()
        else:
            # Eliminar la cola si no se comió
            snake.pop()
        
        # Continuar el bucle
        time.sleep(0.1)
    
    print("\nJuego terminado. Gracias por jugar, jefe!")

if __name__ == "__main__":
    main()
