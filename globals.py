from dataclasses import dataclass
from enum import Enum
from os.path import dirname, realpath

# Constants
CONFIG_FILE = f'{dirname(realpath(__file__))}/pytris.cfg'
SCORE_FILE = f'{dirname(realpath(__file__))}/pytris_scores.txt'

MAX_SAVED_SCORES = 5
SCREEN_TITLE = 'Pytris'

# Length of each side of a tile
# Size of the grid in tiles, the actual grid taller than the visible grid, this allows for manipulating pieces that are partially above the 'skyline'
GRID_DIMS = [10, 26]

RENDERED_GRID_HEIGHT = GRID_DIMS[1] - 6

# The location the center of a new piece spawns at (spawned pieces immediately move down if possible, so only part of it appears to spawn outside the grid)
CENTER_SPAWN = [4, 20]

# The position of a tile's center when displayed on the preview or hold grid
INFO_CENTER_SPAWN = [1, 0]

# Number of pieces to be shown in the preview grid
PREVIEW_COUNT = 5

# Dimensions of the preview and hold grids
INFO_GRID_DIMS = [4, 2]

# Scales the preview size based on the dimension that restricts space more, each preview is a 4x2 grid
PREVIEW_GRID_DIMS = [4, 2 * PREVIEW_COUNT]
# Time before a piece is automatically locked when it is unable to fall
LOCK_DELAY = 0.5

# Number of times LOCK_DELAY can be reset when rotating/moving a piece
MAX_LOCK_RESET = 15

# The highest level that can be reached (level increases drop speed and score multiplier)
MAX_LEVEL = 15
# Basic grid functionality copied from: https://api.arcade.academy/en/latest/examples/array_backed_grid_sprites_1.html#array-backed-grid-sprites-1


OFFSETS = {
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
OFFSETS.update(dict.fromkeys(['J', 'L', 'S', 'T', 'Z'], [
    [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
    [[0, 0], [1, 0], [1, -1], [0, 2], [1, 2]],
    [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
    [[0, 0], [-1, 0], [-1, -1], [0, 2], [-1, 2]]
]))

# Defines the shape and spawn positions relative to the center of the piece
SPAWN_POSITIONS = {
    'I': [[-1, 0], [0, 0], [1, 0], [2, 0]],
    'J': [[-1, 1], [-1, 0], [0, 0], [1, 0]],
    'L': [[1, 1], [-1, 0], [0, 0], [1, 0]],
    'O': [[0, 1], [1, 1], [0, 0], [1, 0]],
    'S': [[0, 1], [1, 1], [-1, 0], [0, 0]],
    'T': [[0, 1], [-1, 0], [0, 0], [1, 0]],
    'Z': [[-1, 1], [0, 1], [0, 0], [1, 0]]
}


# Amount of points awarded for various moves
SCORE_DATA = {
    'normal_clear': [100, 300, 500, 800],
    'mini_t_spin': [100, 200],
    't_spin': [400, 800, 1200, 1600],
    # Multiplier for getting more than 1 Tetris (4-line clear) and/or T-Spin/Mini T-Spin clears in a row
    'back_to_back_mp': 1.5,
    # Points awarded for each tile a piece is dropped
    'soft_drop_mp': 1,
    'hard_drop_mp': 2,
    #  Multiplier for combos
    'combo_mp': 50
}
# TODO: make defaults compliant with guideline, add control customization
@dataclass
class Settings:
    # Keybinds
    move_left: int
    move_right: int
    move_down: int
    hard_drop: int
    hold: int
    rotate_clockwise: int
    rotate_counter_clockwise: int
    rotate_flip: int
    pause: int
    restart: int

    # Other Settings
    colors = {
        # Empty Tile
        '': tuple,
        # Pieces
        'I': tuple,
        'J': tuple,
        'L': tuple,
        'O': tuple,
        'S': tuple,
        'T': tuple,
        'Z': tuple,
        # Other
        'background': tuple,
        'grid_line': tuple,
        'text': tuple
    }
    normal_opacity: int
    ghost_opacity: int

    # The time a left or right key must be held down before it moves additional tiles
    delayed_auto_shift: float

    # The time between each movement while holding down a horizontal movement key
    auto_repeat_rate: float

    # The time between each movement while holding the down key
    drop_auto_repeat_rate: float

# Stores data for the active piece
@dataclass
class ActivePiece:
    # Type of piece (e.g. 'I')
    type: str
    # The coordinates rotational center of the piece
    center: list[int]
    # The coordinates of each individual tile
    tiles: list[list[int]]
    # The number of clockwise rotations needed to put the pieces rotation in its current state relative to its spawn position
    # 0 = spawn, 1 = rotated clockwise, 2 = flipped (i.e. 2x clockwise), 3 = rotated counter-clockwise (i.e. 3x clockwise)
    rotation: int
    # The lowest line any tile of the active piece has reached,
    # this is for determining when to switch from the 'lock' phase to the 'falling' phase
    lowest_line: int
    # The number of rotations/translations applied by the player in the current lock phase (regardless of if they were successful)
    # After 15 (MAX_LOCK_RESET) rotations/translations during the lock phase, the lock timer will not be reset
    lock_counter: int
    # The index of the rotation test that succeeded if the last move was a rotation (otherwise -1)
    # This is used for scoring T-Spins
    rotation_point: int

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
    ITERATE = 3
    COMPLETION = 4

@dataclass
class game_statistics:
    # Total Score
    score: int
    # Number of times i - 1 rows were cleared (i = index of list)
    clears: list[int]
    total_clears: int
    level: int
    # Number of times a normal t-spin cleared i rows
    t_spin: list[int]
    # Number of times a mini t-spin cleared i rows
    mini_t_spin: list[int]

# Stores info for scaling, see on_resize()
@dataclass
class WindowScale:
    size: list[int]
    tile_size: int
    eff_tile_size: int
    grid_line_width: int
    grid_pos: list[int]
    grid_size: list[int]
    preview_pos: list[int]
    preview_size: list[int]
    hold_pos: list[int]
    hold_size: list[int]
    info_offset: int
    font_size: int
