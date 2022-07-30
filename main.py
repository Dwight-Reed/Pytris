import copy
from types import new_class
import arcade
from dataclasses import dataclass, replace
import pyglet
import random

# Constants
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 1000
SCREEN_TITLE = "Tetris"
# Length of each side of a tile
TILE_SIZE = 40
# Size of the grid in tiles, the actual grid is 1 taller than the visibile grid
GRID_WIDTH = 10
GRID_HEIGHT = 21
RENDERED_GRID_HEIGHT = GRID_HEIGHT - 1
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
# https://www.youtube.com/watch?v=yIpk5TJ_uaI
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
    type: str
    center: list[int]
    tiles: list[list[int]]
    rotation: int


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
            for row in range(RENDERED_GRID_HEIGHT):
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
        for row in range(RENDERED_GRID_HEIGHT):
            for column in range(GRID_WIDTH):
                self.grid_sprite_list[column * RENDERED_GRID_HEIGHT +
                                      row].color = self.settings.colors[self.grid[column][row]] + (self.settings.normal_opacity,)

        # Draws the ghost tiles
        for tile in self.ghost_tiles:
            if not tile[1] >= RENDERED_GRID_HEIGHT:
                # print(f"ghost tile = {tile}")
                self.grid_sprite_list[(tile[0] * (RENDERED_GRID_HEIGHT)) + tile[1]
                                      ].color = self.settings.colors[self.active_piece.type] + (self.settings.ghost_opacity,)

        # Draws the active piece (overwrites ghost tiles if overlapping)
        for tile in self.active_piece.tiles:
            if not tile[1] >= RENDERED_GRID_HEIGHT:
                # print(f"active tile = {tile}")
                self.grid_sprite_list[(tile[0] * (RENDERED_GRID_HEIGHT)) + tile[1]
                                      ].color = self.settings.colors[self.active_piece.type] + (self.settings.normal_opacity,)

        # Change opacity of active_piece.center for debugging
        self.grid_sprite_list[(self.active_piece.center[0] * (RENDERED_GRID_HEIGHT)) + self.active_piece.center[1]
                              ].color = self.settings.colors[self.active_piece.type] + (self.settings.ghost_opacity,)

    def setup(self):
        # Generate the first bag
        self.bag = ['I', 'J', 'L', 'O', 'S', 'T', 'Z']
        random.shuffle(self.bag)

        # Determines if the player can swap the active piece with their hold
        self.hold_ready = True
        self.active_piece = active_piece(
            '', [0, 0], [[0, 0], [0, 0], [0, 0], [0, 0]], 0)
        self.spawn_piece(False)

    def on_key_press(self, symbol, modifiers):
        # TODO clean up and don't crash on boundries
        valid = True
        if symbol == self.settings.move_left:
            self.active_piece.center[0] -= 1
            for i in range(4):
                if self.active_piece.tiles[i][0] == 0:
                    valid = False
            if valid:
                for i, tile in enumerate(self.active_piece.tiles):
                    self.active_piece.tiles[i][0] = tile[0] - 1
        elif symbol == self.settings.move_right:
            for i in range(4):
                if self.active_piece.tiles[i][0] == 19:
                    valid = False
            if valid:
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
        # Clears the grid
        self.clear()

        # Update the sprite list
        self.redraw_grid()

        # Batch draw all the sprites

        self.grid_sprite_list.draw()

    def on_update(self, dt):
        self.update_ghost()

    def spawn_piece(self, from_hold: bool):

        if from_hold:
            # Swap active piece and hold
            self.active_piece.type, self.hold = self.hold, self.active_piece
        else:
            # Remove first type from the bag and set the new piece to that type
            self.active_piece.type = self.bag.pop(0)

        # Sets the center to be on the top row
        # this will make part of some pieces appear out of bounds, but this is common in modern tetris games
        self.active_piece.center = CENTER_SPAWN

        # Place tiles relative to the center
        for i, tile in enumerate(spawn_positions[self.active_piece.type]):
            self.active_piece.tiles[i] = [
                CENTER_SPAWN[j] + tile[j] for j in range(2)]

        # If the bag has fewer pieces than the preview is set to display, generate and append a new bag
        # Info about bags: https://tetris.wiki/Random_Generator
        if len(self.bag) == self.settings.preview_count:
            self.new_bag = ['I', 'J', 'L', 'O', 'S', 'T', 'Z']
            random.shuffle(self.new_bag)
            self.bag.append(self.new_bag)

    def place_piece(self):
        pass

    def rotate_active(self, steps: int):
        # Stores the position of the piece after being rotated
        rotated_piece = copy.deepcopy(self.active_piece)
        # Stores the new position
        new_position = copy.deepcopy(self.active_piece)
        new_position.rotation = (self.active_piece.rotation + steps) % 4

        for step in range(steps):
            for i in range(4):
                # Rotate pieces around the center | for each tile: new_pos = (y, -x) (relative to center piece)
                rotated_piece.tiles[i] = [rotated_piece.center[j] + [rotated_piece.tiles[i][1] - rotated_piece.center[1], -(
                    rotated_piece.tiles[i][0] - rotated_piece.center[0])][j] for j in range(2)]

        # Stores the offset data for the current piece type
        offset_data = offsets[self.active_piece.type]

        # Run the 5 tests
        for test in range(5):
            # Calculate the offset for the current test according to the offset data
            offset = [offset_data[self.active_piece.rotation][test][i] -
                      offset_data[new_position.rotation][test][i] for i in range(2)]

            # Set the tile positions according to the offset
            for i in range(4):
                new_position.tiles[i] = [
                    rotated_piece.tiles[i][0] + offset[0], rotated_piece.tiles[i][1] + offset[1]]
            new_position.center = [rotated_piece.center[0] +
                                   offset[0], rotated_piece.center[1] + offset[1]]

            # Check if the new tile positions are occupied
            for check in range(4):
                try:
                    if self.grid[new_position.tiles[check][0]][new_position.tiles[check][1]]:
                        break
                # List index out of range (Out of bounds)
                except:
                    break
            else:
                # If all tiles are in free positions, update the active piece; if this block is not executed, the rotation fails
                self.active_piece = new_position
                break

    # Updates the current position of the ghost tiles
    # TODO Chnange to a generic function that returns the position of ghost/placed tile
    def update_ghost(self):

        self.ghost_tiles = self.active_piece.tiles
        for i in range(1, GRID_HEIGHT):
            ghost_candidate = list(
                # checks if there are any placed tiles immediately below tiles in ghost_candidate
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
