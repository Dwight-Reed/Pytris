import arcade
import copy
from dataclasses import dataclass
from enum import Enum
import pyglet
import random
# Constants
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 1000
SCREEN_TITLE = "Tetris"

# Length of each side of a tile
TILE_SIZE = 40
# Size of the grid in tiles, the actual grid is 1 taller than the visible grid
GRID_WIDTH = 10
GRID_HEIGHT = 22
RENDERED_GRID_HEIGHT = GRID_HEIGHT - 1

# The Size of the grid lines
MARGIN = 5

# Effective tile size, the amount of space a tile takes up including its margins (useful for calculating the space the board takes up)
EFF_TILE_SIZE = TILE_SIZE + MARGIN

# The location the center of a new piece spawns at
CENTER_SPAWN = [4, 20]

# Area on each side of the grid to be left blank (centers the grid)
PADDING_X = (SCREEN_WIDTH - (TILE_SIZE + MARGIN) * GRID_WIDTH) / 2
PADDING_Y = (SCREEN_HEIGHT - (TILE_SIZE + MARGIN) * GRID_HEIGHT) / 2

# Time before a piece is automatically locked when it is unable to fall
LOCK_DELAY = 0.5

# Number of times LOCK_DELAY can be reset when rotating/moving a piece
MAX_LOCK_RESET = 15

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


# Amount of points awarded for various moves
score_data = {
    "normal_clear": [100, 300, 500, 800],
    "mini_t_spin": [100, 200],
    "t_spin": [400, 800, 1200, 1600],
    # Multipliers
    "back_to_back_mp": 0.5,
    "soft_drop_mp": 1,
    "hard_drop_mp": 2
}

@dataclass
class Settings:
    # Keybinds
    move_left = pyglet.window.key.LEFT
    move_right = pyglet.window.key.RIGHT
    move_down = pyglet.window.key.DOWN
    hard_drop = pyglet.window.key.SPACE
    # SHIFT key, using pyglet.window.key.MOD_SHIFT would treat it as a modifier rather than a normal key
    hold = 65505
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

    # The time a left or right key must be held down before it moves additional tiles
    delayed_auto_shift = 0.08

    # The time between each movement while holding down a horizontal movement key
    auto_repeat_rate = 0.005

    # The time between each movement while holding the down key
    drop_auto_repeat_rate = 0

# Stores data for the active piece
@dataclass
class ActivePiece:
    type: str
    center: list[int]
    tiles: list[list[int]]
    rotation: int
    lowest_line: int
    lock_counter: int

# Stores data for the ghost piece
@dataclass
class GhostPiece:
    center: list[int]
    tiles: list[list[int]]

# Useful for distinguishing between falling and lock phases, and debugging
class GamePhase(Enum):
    GENERATION = 0
    FALLING = 1
    LOCK = 2
    PATTERN = 3
    ITERATE = 4
    ELIMINATE = 5
    COMPLETION = 6

@dataclass
class Statistics:
    score: int
    clear: list[int]
    mini_t_spin: list[int]
    t_spin: list[int]

class MyGame(arcade.Window):
    # Load default settings
    def __init__(self):

        self.fall_interval = 1
        self.cur_time = 0

        self.settings = Settings

        # Call the parent class and set up the window
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        # Create a grid of strings that represent the piece that was placed (for determining the color), empty strings represent an empty tile
        # This grid is only used to track placed tiles, active piece and ghost are separate
        self.grid = []
        for row in range(GRID_HEIGHT):
            self.grid.append([])
            for column in range(GRID_WIDTH):
                self.grid[row].append('')

        # Set the window's background color
        self.background_color = (self.settings.background_color)

        # Create a sprite list for batch drawing all the grid sprites
        self.grid_sprite_list = arcade.SpriteList()
        self.grid_sprites = []

        # Create a list of solid-color sprites to represent each grid location
        for row in range(RENDERED_GRID_HEIGHT):
            self.grid_sprites.append([])
            for column in range(GRID_WIDTH):
                x = column * (TILE_SIZE + MARGIN) + (TILE_SIZE / 2 + MARGIN) + PADDING_X
                y = row * (TILE_SIZE + MARGIN) + (TILE_SIZE / 2 + MARGIN) + PADDING_Y
                sprite = arcade.SpriteSolidColor(
                    TILE_SIZE, TILE_SIZE, self.settings.colors[''])
                sprite.center_x = x
                sprite.center_y = y
                self.grid_sprite_list.append(sprite)
                self.grid_sprites[row].append(sprite)

        # Create object to store ghost tiles (indicates where a piece will be dropped on a hard drop)
        self.ghost = GhostPiece([[0, 0], [0, 0], [0, 0], [0, 0]], [0, 0])

        # Initialize timers
        self.timers = {
            # Time until the active piece will move down automatically
            "fall": 0.0,
            # Time until the active piece will move down while the down key is pressed
            "drop_ARR": 0.0,
            # Auto Repeat Rate
            "ARR": 0.0,
            # Delayed Auto Shift
            "DAS": 0.0
        }
        self.game_phase = GamePhase
        self.fall_while_locking = False

        # Sets up handler for pressed keys
        self.keys = pyglet.window.key.KeyStateHandler()
        self.push_handlers(self.keys)


    # Updates sprite grid to match positions of tiles
    # TODO: don't only redraw modified tiles
    def redraw_grid(self):

        # Adds the placed pieces to the sprite grid (and clears anything else)
        for column in range(GRID_WIDTH):
            for row in range(RENDERED_GRID_HEIGHT):
                self.grid_sprites[row][column].color = self.settings.colors[self.grid[row][column]] + (self.settings.normal_opacity,)

        # Draws the ghost tiles
        for tile in self.ghost.tiles:
            if not tile[1] >= RENDERED_GRID_HEIGHT:
                self.grid_sprites[tile[1]][tile[0]].color = self.settings.colors[self.active_piece.type] + (self.settings.ghost_opacity,)
                # self.grid_sprite_list[(tile[0] * (RENDERED_GRID_HEIGHT)) + tile[1]
                #                       ].color = self.settings.colors[self.active_piece.type] + (self.settings.ghost_opacity,)

        # Draws the active piece (overwrites ghost tiles if overlapping)
        for tile in self.active_piece.tiles:
            if not tile[1] >= RENDERED_GRID_HEIGHT:
                self.grid_sprites[tile[1]][tile[0]].color = self.settings.colors[self.active_piece.type] + (self.settings.normal_opacity,)

        # Change opacity of ActivePiece.center for debugging
        try:
            self.grid_sprites[self.active_piece.center[1]][self.active_piece.center[0]].color = self.settings.colors[self.active_piece.type] + (self.settings.ghost_opacity,)
        # Center is above grid
        except:
            pass

    def setup(self):
        self.game_phase = GamePhase.GENERATION
        # Generate the first bag
        self.bag = ['I', 'J', 'L', 'O', 'S', 'T', 'Z']
        random.shuffle(self.bag)

        # Determines if the player can swap the active piece with their hold
        self.hold_ready = True
        self.active_piece = ActivePiece(
            '', [0, 0], [[0, 0], [0, 0], [0, 0], [0, 0]], 0, GRID_HEIGHT, 0)
        self.spawn_piece(False)
        self.fall_interval = 1
        self.cur_time = 0
        self.hold = ''

    def on_key_press(self, symbol, modifiers):
        cfg = self.settings
        if symbol == cfg.move_left:
            self.move_active(-1, 0)
            self.reset_lock_timer()
            self.timers["DAS"] = self.settings.delayed_auto_shift
            # Stores the most recent move_left or move_right key press  (determines which direction the piece should move if both are pressed)
            # Value is the direction the block would move in
            self.last_horizontal_key = -1

        elif symbol == cfg.move_right:
            self.move_active(1, 0)
            self.reset_lock_timer()
            self.timers["DAS"] = self.settings.delayed_auto_shift
            self.last_horizontal_key = 1

        # elif symbol == cfg.move_down:
        #     if self.move_active(0, -1):
        #         # Reset the fall timer when the player manually moves the piece, this make it easier to manipulate
        #         self.timers["fall"] = self.fall_interval

        elif symbol == cfg.hold and self.hold_ready:
            self.spawn_piece(True)
            self.hold_ready = False

        elif symbol == cfg.rotate_clockwise:
            self.rotate_active(1)
            self.check_lowest_pos()
            self.reset_lock_timer()

        elif symbol == cfg.rotate_counter_clockwise:
            self.rotate_active(-1)
            # Checked here rather than in rotate_active() to prevent the lowest_line from changing when a flip rotate fails
            self.check_lowest_pos()
            self.reset_lock_timer()

        # Tries to rotate the piece twice, if it fails, revert to original position
        elif symbol == cfg.rotate_flip:
            tmp_piece = copy.deepcopy(self.active_piece)

            if not (self.rotate_active(1) and self.rotate_active(1)):
                self.active_piece = copy.deepcopy(tmp_piece)
            else:
                self.check_lowest_pos()

        elif symbol == cfg.hard_drop:
            self.place_piece()

        self.update_ghost()

    # Applies ARR, DAS and drop_ARR
    def held_keys(self):
        # drop ARR
        if self.keys[self.settings.move_down]:
            # If drop_ARR is 0, move the active piece down until it hits an object
            if self.settings.drop_auto_repeat_rate == 0:
                for i in range(GRID_HEIGHT):
                    if not self.move_active(0, -1):
                        break
            elif self.timers["drop_ARR"] <= 0:
                self.move_active(0, -1)
                # Reset the fall timer when the piece is manually moved down, this make it easier to manipulate
                self.timers["fall"] = self.fall_interval

        # DAS and ARR
        if self.timers["DAS"] <= 0:
            # If ARR is 0, move the active piece in the corresponding direction until it hits an object
            if self.settings.auto_repeat_rate == 0:
                while True:
                    if not self.move_active(self.last_horizontal_key, 0):
                        self.update_ghost()
                        break
            elif self.timers["ARR"] <= 0:
                # If both horizontal movement keys are held down, use self.last_horizontal_key to determine direction
                if self.keys[self.settings.move_left] and self.keys[self.settings.move_right]:
                    self.move_active(self.last_horizontal_key, 0)

                elif self.keys[self.settings.move_left]:
                    self.move_active(-1, 0)

                elif self.keys[self.settings.move_right]:
                    self.move_active(1, 0)
                else:
                    return
                self.timers["ARR"] = self.settings.auto_repeat_rate
                self.update_ghost()



    def on_update(self, delta_time):
        self.cur_time += delta_time

        # Decrease all timers by the time since this function was last called
        for key in self.timers.keys():
            self.timers[key] -= delta_time

        # Execute appropriate functions for the current game phase
        if self.game_phase == GamePhase.FALLING:
            self.falling_piece()

        elif self.game_phase == GamePhase.LOCK:
            self.locking()

        self.held_keys()
    # Generation Phase
    def spawn_piece(self, from_hold: bool):
        if from_hold:
            # If hold is empty (first use of the current game), get a new piece from the bag instead of the hold
            if self.hold == '':
                self.hold = self.active_piece.type
                self.active_piece.type = self.bag.pop(0)

            # Swap active piece and hold
            else:
                self.active_piece.type, self.hold = self.hold, self.active_piece.type

        else:
            # Remove first type from the bag and set the new piece to that type
            self.active_piece.type = self.bag.pop(0)

        # Sets the rotational center of the piece to be at the spawn point
        self.active_piece.center = CENTER_SPAWN
        self.active_piece.rotation = 0

        # Place tiles relative to the center
        for i, tile in enumerate(spawn_positions[self.active_piece.type]):
            self.active_piece.tiles[i] = [
                CENTER_SPAWN[j] + tile[j] for j in range(2)]

        # If the new piece does not have room to spawn, the game is over
        if not self.is_valid_pos(self.active_piece.tiles):
            self.game_over("Block Out")

        # If the bag has fewer pieces than the preview is set to display, generate and append a new bag
        # Each bag has one of each tile, which ensures even distribution of pieces
        if len(self.bag) == self.settings.preview_count:
            self.new_bag = ['I', 'J', 'L', 'O', 'S', 'T', 'Z']
            random.shuffle(self.new_bag)
            self.bag.extend(self.new_bag)

        # Piece spawns partially outside of the visible grid, but tries to move down immediately; the lock phase is not started until it fails to move down naturally,
        # this gives additional time equal to fall_interval to move instead of the usual 0.5 when a piece cannot fall
        self.move_active(0, -1)
        self.timers["fall"] = self.fall_interval

        # Resets the lowest line to be used for tracking lock timer resets and switching from the lock to falling phase
        self.active_piece.lowest_line = GRID_HEIGHT
        self.check_lowest_pos()

        self.game_phase = GamePhase.FALLING

        # Updates the ghost tiles to match the new piece
        self.update_ghost()

    # Falling Phase
    def falling_piece(self):
        # If the fall timer has expired, try to move the active piece
        if self.timers["fall"] <= 0:
            # If the active piece cannot be moved, enter the locking phase
            if not self.move_active(0, -1):
                self.game_phase = GamePhase.LOCK
                self.timers["lock"] = LOCK_DELAY

            else:
                # Reset the fall timer
                self.timers["fall"] = self.fall_interval

    # Locking Phase
    def locking(self):
        # Pieces can fall during the locking phase if the lowest y position of any tile is greater than or equal to the lowest position any tile was previously (for the active piece)
        # If the piece falls below that threshold, check_lowest_pos() will switch back to the falling phase
        if self.fall_while_locking:
            if self.timers["fall"] <= 0:
                if not self.move_active(0, -1):
                    self.fall_while_locking = False
                    self.timers["lock"] = LOCK_DELAY

            # else:
                # Reset the fall timer
                # self.timers["fall"] = self.fall_interval
        # If the active piece can move down, reset the fall timer and allow it to fall during the lock phase
        elif self.active_piece.tiles != self.ghost.tiles:
            self.timers["fall"] = self.fall_interval
            self.fall_while_locking = True

        # If the lock timer has expired, place the active piece
        else:
            if self.timers["lock"] <= 0:
                self.place_piece()

    # Resets the lock timer and increments the lock counter if in the locking phase and the lock counter has not exceeded the max
    def reset_lock_timer(self):
        if self.game_phase == GamePhase.LOCK and self.active_piece.lock_counter < MAX_LOCK_RESET:
            self.active_piece.lock_counter += 1
            self.timers["lock"] = LOCK_DELAY

    # Places the active piece at the position of the ghost piece
    def place_piece(self):
        # End the game if the placed tile is completely outside the visible grid
        for tile in self.ghost.tiles:
            if tile[1] > GRID_HEIGHT - 2:
                self.game_over("Lock Out")

        for tile in self.ghost.tiles:
            self.grid[tile[1]][tile[0]] = self.active_piece.type

        # Pattern Phase
        self.game_phase = GamePhase.PATTERN
        self.pattern()

        # Iterate Phase
        self.game_phase = GamePhase.ITERATE
        self.iterate(set([self.ghost.tiles[i][1] for i in range(4)]))

        self.spawn_piece(False)
        self.hold_ready = True

    def pattern(self):
        pass
        # T-Spin
        # for each
        # filled_corners = 0
        # for corner in [self.ghost.tiles.[[-1, 1], [1, 1], [-1, -1], [1, -1]]]:
        #     if self.grid[corner[1]][corner[0]]:
        #         filled_corners += 1

    # Iterate Phase
    def iterate(self, rows: set[int]):
        clears = []
        # If a row has a value in each position, add it to the clears list
        for i in rows:
            for j in range(GRID_WIDTH):
                if not self.grid[i][j]:
                    break
            else:
                clears.append(i)

        # Eliminate Phase
        # Remove rows starting from the highest to prevent row numbers being offset
        clears.sort()
        for row in reversed(clears):
            self.grid.pop(row)
            # Add a new row at the top to replace the old row (This avoids moving every tile down)
            self.grid.append([])
            for j in range(GRID_WIDTH):
                self.grid[-1].append('')


    def on_draw(self):
        self.clear()

        # Update the sprite list
        self.redraw_grid()

        # Batch draw all the sprites
        self.grid_sprite_list.draw()

        # win = pyglet.window.Window()

    def rotate_active(self, steps: int) -> bool:
        # Stores the position of the piece after being rotated
        rotated_piece = copy.deepcopy(self.active_piece)
        # Stores the new position
        new_position = copy.deepcopy(self.active_piece)
        new_position.rotation = (self.active_piece.rotation + steps) % 4
        for i in range(4):
            # Rotate pieces around the center | for each tile: new_pos = (y, -x) (relative to center piece)
            rotated_piece.tiles[i] = [
                rotated_piece.center[j] + [
                    steps * (rotated_piece.tiles[i][1] - rotated_piece.center[1]),
                    - steps * ((rotated_piece.tiles[i][0] - rotated_piece.center[0]))
                    ][j] for j in range(2)
                ]

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
            if self.is_valid_pos(new_position.tiles):
                self.active_piece = copy.deepcopy(new_position)
                return True

        return False

    # Translates the active piece by the given value, returns false if it fails
    # TODO use for rotation
    def move_active(self, x: int, y: int) -> bool:

        new_pos = [[], [], [], []]
        for i, tile in enumerate(self.active_piece.tiles):
            new_pos[i] = [tile[j] + [x, y][j] for j in range(2)]

        if self.is_valid_pos(new_pos):
            self.active_piece.tiles = new_pos
            self.active_piece.center = [self.active_piece.center[i] + [x, y][i] for i in range(2)]
            self.check_lowest_pos()
            return True

        return False

    # Checks if a list of tiles overlaps any placed tiles or is out of bounds
    def is_valid_pos(self, tiles: list[list[int]]) -> bool:
        for tile in tiles:
            if not (0 <= tile[0] < GRID_WIDTH and 0 <= tile[1] < GRID_HEIGHT):
                return False

            elif self.grid[tile[1]][tile[0]]:
                return False

        return True

    # Updates the current position of the ghost tiles
    def update_ghost(self):
        new_ghost = GhostPiece
        new_ghost.tiles = copy.deepcopy(self.active_piece.tiles)
        new_ghost.center =  copy.deepcopy(self.active_piece.center)
        for i in range(GRID_HEIGHT):
            if not self.is_valid_pos(new_ghost.tiles):
                return
            self.ghost.tiles = copy.deepcopy(new_ghost.tiles)
            self.ghost.center = copy.deepcopy(new_ghost.center)

            for j in range(4):
                new_ghost.tiles[j][1] -= 1
            new_ghost.center[1] -= 1

    # When the active piece moves or rotates, if the lowest y position is less than the previous lowest for the piece, reset the lock_counter
    def check_lowest_pos(self):
        for tile in self.active_piece.tiles:
            if tile[1] < self.active_piece.lowest_line:
                self.active_piece.lowest_line = tile[1]
                self.active_piece.lock_counter = 0
                self.game_phase = GamePhase.FALLING

    def game_over(self, reason: str):
        print(f"game over - {reason}")
        exit(0)

def main():
    """Main function"""
    window = MyGame()
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()
