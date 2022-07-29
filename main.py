"""
Platformer Game
"""

from operator import itemgetter
from types import new_class
import arcade
from dataclasses import dataclass
# import numpy
import pyglet
import random
# import time
# Constants
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 1000
SCREEN_TITLE = "Tetris"
# Length of each side of a tile
TILE_SIZE = 40
# Size of the grid in tiles
GRID_WIDTH = 10
GRID_HEIGHT = 20
# The Size of the grid lines
MARGIN = 5
# Effective tile size, the amount of space a tile takes up including its margins (useful for calculating the space the board takes up)
EFF_TILE_SIZE = TILE_SIZE + MARGIN
# The location the center of a new piece spawns at
CENTER_SPAWN = [4, 19]

# GRID_BORDER_X = [round(SCREEN_WIDTH / 2 - TILE_SIZE * GRID_WIDTH / 2), round(SCREEN_WIDTH / 2 + TILE_SIZE * GRID_WIDTH / 2)]

# Area on each side of the grid to be left blank (centers the grid)
PADDING_X = (SCREEN_WIDTH - (TILE_SIZE + MARGIN) * GRID_WIDTH) / 2
PADDING_Y = (SCREEN_HEIGHT - (TILE_SIZE + MARGIN) * GRID_HEIGHT) / 2
# GRID_BORDER_Y = [100, 900]

# Basic grid functionality copied from: https://api.arcade.academy/en/latest/examples/array_backed_grid_sprites_1.html#array-backed-grid-sprites-1

# https://tetris.wiki/Super_Rotation_System
offsets = {
    'I': [
        [[0, 0], [-1, 0], [2, 0], [-1, 0], [2, 0]],
        [[-1, 0], [0, 0], [0, 0], [0, 1], [0, -2]],
        [[-1, 1], [1, 1], [-2, 1], [1, 0], [-2, 0]],
        [[0, 1], [0, 1], [0, 1], [0, -1], [0, 2]]
    ],
    'O': [
        [[0, 0]],
        [[0, -1]],
        [[-1, -1]],
        [[-1, 0]]
    ]
}
# J, L, S, T, and Z use the same offsets
offsets.update(dict.fromkeys(['J', 'L', 'S', 'T', 'Z'], [
    [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
    [[0, 0], [1, 0], [1, -1], [0, 2], [1, 2]],
    [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
    [[0, 0], [-1, 0], [-1, -1], [0, 2], [-1, 2]]
]))

# Defines the shape and spawn positions relative to the center of the piece
spawn_positions = {
    'I': [[-1, 0], [0, 0], [1, 0], [2, 0]],
    'J': [[-1, 1], [-1, 0], [0, 0], [1, 0]],
    'L': [[1, 1], [-1, 0], [0, 0], [1, 0]],
    'O': [[0, 1], [1, 1], [0, 0], [1, 0]],
    'S': [[0, 1], [1, 1], [-1, 0], [0, 0]],
    'T': [[0, 1], [-1, 0], [0, 0], [1, 0]],
    'Z': [[-1, 1], [0, 1], [0, 0], [1, 0]]
}


@dataclass
class settings:
    # Keybinds
    move_left = pyglet.window.key.LEFT
    move_right = pyglet.window.key.RIGHT
    move_down = pyglet.window.key.DOWN
    instant_drop = pyglet.window.key.SPACE
    hold = pyglet.window.key.MOD_SHIFT
    rotate_clockwise = pyglet.window.key.D
    rotate_counter_clockwise = pyglet.window.key.A
    rotate_flip = pyglet.window.key.W


    # Other Settings
    preview_count = 2
    colors = {
        '': (150, 150, 150),
        'I': (0, 255, 255),
        'J': (0, 0, 255),
        'L': (255, 170, 0),
        'O': (255, 255, 0),
        'S': (0, 255, 0),
        'T': (153, 0, 255),
        'Z': (255, 0, 0)
    }

@dataclass
class active_piece:
    type = ''
    center = []
    tiles = [[], [], [], []]
    rotation = 0


class MyGame(arcade.Window):

    def __init__(self):
        self.settings = settings
        # print(offsets)
        # Call the parent class and set up the window
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        self.grid = []
        for column in range(GRID_WIDTH):
            # Add an empty array that will hold each cell
            # in this column
            self.grid.append([])
            for row in range(GRID_HEIGHT):
                self.grid[column].append('')  # Append a cell
        # print(self.grid)
        # Set the window's background color
        self.background_color = (0, 0, 0)
        # Create a spritelist for batch drawing all the grid sprites
        self.grid_sprite_list = arcade.SpriteList()

        # Create a list of solid-color sprites to represent each grid location
        for column in range(GRID_WIDTH):
            for row in range(GRID_HEIGHT):
                x = column * (TILE_SIZE + MARGIN) + \
                    (TILE_SIZE / 2 + MARGIN) + PADDING_X
                y = row * (TILE_SIZE + MARGIN) + \
                    (TILE_SIZE / 2 + MARGIN) + PADDING_Y
                sprite = arcade.SpriteSolidColor(
                    TILE_SIZE, TILE_SIZE, self.settings.colors[''])
                sprite.center_x = x
                sprite.center_y = y
                self.grid_sprite_list.append(sprite)


    # Updates sprite grid to match positions of tiles
    def redraw_grid(self):
        for i in range(GRID_WIDTH):
            self.grid[i][0] = 'T'
            # print(self.grid[i])
        # Adds the placed pieces to the sprite grid (and clears anything else)
        for row in range(GRID_HEIGHT):
            for column in range(GRID_WIDTH):
                self.grid_sprite_list[column * GRID_HEIGHT + row].color = self.settings.colors[self.grid[column][row]]

        ghost_tiles = self.active_piece.tiles
        for i in range(1, GRID_HEIGHT):
            # for j in range(0, 4):
            ghost_candidate = list(map(lambda a: [a[0], a[1] - 1], ghost_tiles))
            for tile in ghost_candidate:
                if self.grid[tile[0]][tile[1]]:
                    break
            else:
                ghost_tiles = ghost_candidate
                continue
            break
        print(ghost_tiles)

        # Draws the ghost tiles
        for tile in ghost_tiles:
            if not tile[1] >= GRID_HEIGHT:
                self.grid_sprite_list[(tile[0] * (GRID_HEIGHT)) + tile[1]].color = self.settings.colors[self.active_piece.type]

        # Draws the active piece (overwrites ghost tiles if overlapping)
        for tile in self.active_piece.tiles:
            if not tile[1] >= GRID_HEIGHT:
                self.grid_sprite_list[(tile[0] * (GRID_HEIGHT)) + tile[1]].color = self.settings.colors[self.active_piece.type]

        # Adds the ghost piece to the sprite grid

        # self.ghost_tiles = list(map(lambda a: [a[0], a - ghost_min], self.active_piece.tiles))
        # for i in self.ghost_tiles


    def setup(self):
        # Generate the first bag
        self.bag = ['I', 'J', 'L', 'O', 'S', 'T', 'Z']
        random.shuffle(self.bag)

        # Determines if the player can swap the active piece with their hold
        self.hold_ready = True
        self.active_piece = active_piece()
        self.spawn_piece(False)

    def on_key_press(self, symbol, modifiers):
        if symbol == self.settings.move_left:
            self.active_piece.center[0] -= 1
            for i, tile in enumerate(self.active_piece.tiles):
                self.active_piece.tiles[i][0] = tile[0] - 1
        elif symbol == self.settings.move_right:
            self.active_piece.center[0] += 1
            for i, tile in enumerate(self.active_piece.tiles):
                self.active_piece.tiles[i][0] = tile[0] + 1
        elif symbol == self.settings.move_down:
            self.active_piece.center[1] -= 1
            for i, tile in enumerate(self.active_piece.tiles):
                self.active_piece.tiles[i][1] = tile[1] - 1
        elif symbol == self.settings.hold:
            if self.hold_ready:
                self.spawn_piece(True)
        elif symbol == self.settings.rotate_clockwise:
            self.rotate_active(1)
        elif symbol == self.settings.rotate_counter_clockwise:
            self.rotate_active(3)
        elif symbol == self.settings.rotate_flip:
            self.rotate_active(2)

    def on_draw(self):

        self.clear()

        # Batch draw all the sprites
        self.redraw_grid()
        self.grid_sprite_list.draw()

    def on_update(self, dt):
        # print(f"time={time.time()}")
        pass

    def spawn_piece(self, from_hold: bool):

        if from_hold:
            # Swap active piece and hold
            self.active_piece.type, self.hold = self.hold, self.active_piece
        else:
            self.active_piece.type = self.bag.pop(0)
            # if self.active_piece.type != 'I' and self.active_piece.type != 'O':

        # Sets the center to be on the top row
        # this will make part of the piece appear out of bounds, but this is common in modern tetris games
        self.active_piece.center = CENTER_SPAWN
        for i, tile in enumerate(spawn_positions[self.active_piece.type]):
            print(f"test {i}")
            self.active_piece.tiles[i] = [CENTER_SPAWN[0] + tile[0], CENTER_SPAWN[1] + tile[1]]

        # If the bag has fewer pieces than the preview, generate and append a new bag
        # Info about bags: https://tetris.wiki/Random_Generator
        if len(self.bag) == self.settings.preview_count:
            self.new_bag = ['I', 'J', 'L', 'O', 'S', 'T', 'Z']
            random.shuffle(self.new_bag)
            self.bag.append(self.new_bag)
        # self.active_piece


        # self.bag.pop()
        print(self.bag)

    def place_piece(self):
        pass

    def rotate_active(self, steps: int):
        # Using SRS https://tetris.wiki/Super_Rotation_System
        # 'I' and 'O' must be treated differently due to being centered at the corner of a tile,
        # The center coordinates in the active_piece dataclass refer to the tile above and to the left
        for i in range(steps):
            for j, tile in enumerate(self.active_piece.tiles):
                # print(self.active_piece.tiles[i])
                # Rotates 90 degrees around the center tile
                self.active_piece.tiles[j] = [x + y for x, y in zip(self.active_piece.center, [tile[1] - self.active_piece.center[1], -(tile[0] - self.active_piece.center[0])])]
                # print(self.active_piece.tiles[i])
                # self.active_piece.tiles[i][0, 1] = -(tile[1] + self.active_piece.center[1]), tile[0] + self.active_piece.center[0]

def main():
    """Main function"""
    window = MyGame()
    window.setup()
    arcade.run()

# Returns the pair with the lowest y value for each unique x value
# def get_min_coordinate(coordinates: list[list]) -> list[list[int]]:
#     sorted_coordinates = sorted(coordinates, key=itemgetter(1))
#     output = []
#     updated = False
#     for coordinate in coordinates:
#         for i, min in enumerate(output):
#             updated = False
#             if coordinate[0] == min[0]:
#                 updated = True
#                 if coordinate[1] < min[1]:
#                 # if len(output) >= i:
#                     output[i] = coordinate
#                 # else:
#                 #     output.append(coordinate[i])
#         if not updated:
#             output.append(coordinate)
#     return output
#     # print(f"coords={coordinates.sort(key=sort_coordinates)}")

def sort_coordinates(e):
    return e[1]

if __name__ == "__main__":
    main()
