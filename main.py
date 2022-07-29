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
    normal_opacity = 255
    ghost_opacity = 128
    background_color = (0, 0, 0)


@dataclass
class active_piece:
    type = ''
    center = []
    tiles = [[0, 0], [0, 0], [0, 0], [0, 0]]
    rotation = 0


class MyGame(arcade.Window):
    # Load default settings
    def __init__(self):
        self.settings = settings

        # Call the parent class and set up the window
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        # Create a grid of strings that represent the piece that was placed (for determining the color), empty strings represent an empty tile
        # This grid is only used to track placed tiles
        self.grid = []
        for column in range(GRID_WIDTH):
            self.grid.append([])
            for row in range(GRID_HEIGHT):
                self.grid[column].append('')

        # Set the window's background color
        self.background_color = (self.settings.background_color)

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

        # Adds the placed pieces to the sprite grid (and clears anything else)
        for row in range(GRID_HEIGHT):
            for column in range(GRID_WIDTH):
                self.grid_sprite_list[column * GRID_HEIGHT +
                                      row].color = self.settings.colors[self.grid[column][row]] + (self.settings.normal_opacity,)

        # Draws the ghost tiles
        for tile in self.ghost_tiles:
            if not tile[1] >= GRID_HEIGHT:
                self.grid_sprite_list[(tile[0] * (GRID_HEIGHT)) + tile[1]
                                      ].color = self.settings.colors[self.active_piece.type] + (self.settings.ghost_opacity,)

        # Draws the active piece (overwrites ghost tiles if overlapping)
        for tile in self.active_piece.tiles:
            if not tile[1] >= GRID_HEIGHT:
                self.grid_sprite_list[(tile[0] * (GRID_HEIGHT)) + tile[1]
                                      ].color = self.settings.colors[self.active_piece.type] + (self.settings.normal_opacity,)

    def setup(self):
        # Generate the first bag
        self.bag = ['I', 'J', 'L', 'O', 'S', 'T', 'Z']
        random.shuffle(self.bag)
        self.bag = ['I', 'J', 'L', 'O', 'S', 'T', 'Z']

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
        self.update_ghost()
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
        # this will make part of some pieces appear out of bounds, but this is common in modern tetris games
        self.active_piece.center = CENTER_SPAWN
        self.align_active()
        # for i, tile in enumerate(spawn_positions[self.active_piece.type]):
        #     print(f"test {i}")
        #     self.active_piece.tiles[i] = [
        #         CENTER_SPAWN[0] + tile[0], CENTER_SPAWN[1] + tile[1]]

        # If the bag has fewer pieces than the preview, generate and append a new bag
        # Info about bags: https://tetris.wiki/Random_Generator
        if len(self.bag) == self.settings.preview_count:
            self.new_bag = ['I', 'J', 'L', 'O', 'S', 'T', 'Z']
            random.shuffle(self.new_bag)
            self.bag.append(self.new_bag)

        print(self.bag)

    def place_piece(self):
        pass

    def rotate_active(self, steps: int):

        init_state = self.active_piece.rotation
        end_state = (self.active_piece.rotation + steps) % 3
        # Using SRS https://tetris.wiki/Super_Rotation_System
        # for i in range(steps):
        #     for j, tile in enumerate(self.active_piece.tiles):
        #         self.active_piece.tiles[j] = [x + y for x, y in zip(self.active_piece.center, [
        #                                                             tile[1] - self.active_piece.center[1], -(tile[0] - self.active_piece.center[0])])]
        # for i in range():
        #     self.active_piece.rotation += 1
        #     if self.active_piece.rotation == 4:
        #         self.active_piece.rotation = 0
        # self.align_active()

        for i in range(steps):
            for j, tile in enumerate(self.active_piece.tiles):
                self.active_piece.tiles[j] = [x + y for x, y in zip(self.active_piece.center, [tile[1] - self.active_piece.center[1], -(tile[0] - self.active_piece.center[0])])]

        success = False
        for i in range(5):
            new_tiles = []
            try_offset = [offsets[self.active_piece.type][init_state][i][j] - offsets[self.active_piece.type][end_state][i][j] for j in range(2)]
            for j in range(4):
                new_tiles.append([self.active_piece.tiles[j][k] + try_offset[k] for k in range(2)])
            for tile in new_tiles:
                try:
                    if self.grid[tile[0]][tile[1]]:
                        break
                # List index out of range (out of bounds)
                except:
                    break
            else:
                success = True
                break

        if success:
            self.active_piece.tiles = new_tiles

        # self.active_piece.tiles[i][j] = self.active_piece.tiles[i][j] - offsets[self.active_piece.type][self.active_piece.rotation][0][j]


        # print(self.active_piece.tiles)
        # for i in range(4):
        #     for j in range(2):
        #         # print(offsets[self.active_piece.type][self.active_piece.rotation][0])
        #         if self.active_piece.tiles[i] == self.active_piece.center:
        #             self.active_piece.center[j] = offsets[self.active_piece.type][self.active_piece.rotation][0][j]
        #         self.active_piece.tiles[i][j] = offsets[self.active_piece.type][self.active_piece.rotation][0][j]
            # self.active_piece.tiles[i] = [self.active_piece.tiles[j] + offsets[self.active_piece.type][self.active_piece.rotation][0][j] for j in range(2)]
        # self.active_piece.tiles = [offsets[self.active_piece.type][self.active_piece.rotation][0] + self.active_piece.tiles[i] for i in range(4)]
        # print(self.active_piece.tiles)

    # Adjusts the (true and offset) tile positions for the active piece according to its center
    def align_active(self):


        # Set default true positions
        for i, tile in enumerate(spawn_positions[self.active_piece.type]):
            # print(f"test {i}")
            # use zip
            self.active_piece.tiles[i] = [
                CENTER_SPAWN[0] + tile[0], CENTER_SPAWN[1] + tile[1]]
        # Change true positions to reflect rotation
        for i in range(self.active_piece.rotation):
            for j, tile in enumerate(self.active_piece.tiles):
                self.active_piece.tiles[j] = [x + y for x, y in zip(self.active_piece.center, [tile[1] - self.active_piece.center[1], -(tile[0] - self.active_piece.center[0])])]

        # Set offset positions
        for i in range(4):
            for j in range(2):
                # print(f"align_active {i, j}")
                self.active_piece.tiles[i][j] = self.active_piece.tiles[i][j] - offsets[self.active_piece.type][self.active_piece.rotation][0][j]

        print(f"true: {self.active_piece.tiles}\noffset: {self.active_piece.tiles}")

    def update_ghost(self):
        # Find the current position of the ghost tiles
        self.ghost_tiles = self.active_piece.tiles
        for i in range(1, GRID_HEIGHT):
            # for j in range(0, 4):
            ghost_candidate = list(
                map(lambda a: [a[0], a[1] - 1], self.ghost_tiles))
            for tile in ghost_candidate:
                try:
                    if self.grid[tile[0]][tile[1]]:
                        break
                # List index out of range (out of bounds)
                except:
                    break
            else:
                self.ghost_tiles = ghost_candidate
                continue
            break


def main():
    """Main function"""
    window = MyGame()
    window.setup()
    arcade.run()

def sort_coordinates(e):
    return e[1]


if __name__ == "__main__":
    main()
