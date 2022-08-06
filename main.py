import pytris_cfg

import arcade
from bisect import insort
import copy
from globals import *
from math import ceil
from os.path import exists
import pyglet
from random import shuffle
from screeninfo import get_monitors
TEST_VAR = False
class MyGame(arcade.Window):
    # Load default settings
    def __init__(self):
        # Set the default window size to be proportional to the primary monitor's resolution (to prevent the default size from varying based on dpi)
        for m in get_monitors():
            if m.is_primary:
                default_window_size = [round(m.height*0.75*(840/1000)), round(m.height*0.75)]
                break
        # If get_monitors() does not find a primary monitor, fall back to fixed resolution
        else:
            default_window_size = [1000, 840]
        # Call the parent class and set up the window
        super().__init__(default_window_size[0], default_window_size[1], SCREEN_TITLE, resizable=True)
        self.scale = WindowScale

        # Set default fall interval
        self.fall_interval = 1

        # Set time since game start (duration of game shown in stats at end)
        self.cur_time = 0

        # Create the main grid
        self.grid = self.create_grid(GRID_DIMS, '')
        self.grid_sprite_list = arcade.SpriteList()
        self.grid_sprites = []

        # Create the preview grid
        self.preview_grid = self.create_grid(PREVIEW_GRID_DIMS, 'background')
        self.preview_grid_sprite_list = arcade.SpriteList()
        self.preview_grid_sprites = []

        # Create the hold grid
        self.hold_grid = self.create_grid(INFO_GRID_DIMS, 'background')
        self.hold_grid_sprite_list = arcade.SpriteList()
        self.hold_grid_sprites = []
        # Create object to store ghost tiles (indicates where a piece will be dropped on a hard drop)
        self.ghost = GhostPiece([[0, 0], [0, 0], [0, 0], [0, 0]], [0, 0])

        # Initialize timers
        self.timers = {
            # Time until the active piece will move down automatically
            'fall': 0.0,
            # Time until the active piece will move down while the down key is pressed
            'drop_ARR': 0.0,
            # Auto Repeat Rate
            'ARR': 0.0,
            # Delayed Auto Shift
            'DAS': 0.0
        }
        self.game_phase = GamePhase
        self.fall_while_locking = False

        # Sets up handler for pressed keys
        self.keys = pyglet.window.key.KeyStateHandler()
        self.push_handlers(self.keys)

        # Load settings from config file (new one is generated if it does not exist)
        self.settings = Settings
        pytris_cfg.load_config(self.settings)

    def create_grid(self, size: list[int], default_value) -> list[list[int]]:
        # Create a grid of strings that represent the piece that was placed (for determining the color), empty strings represent an empty tile
        grid = []
        for row in range(size[1]):
            grid.append([])
            for column in range(size[0]):
                grid[row].append(default_value)
        return grid

    def create_sprite_grid(self, size: list[int], visible_size: list[int], tile_size: int, line_width: int, position: list[int], sprite_list, sprite_list_2d):
        # Create a sprite list for batch drawing all the grid sprites
        sprite_list.clear()
        # Create a 2d list of sprites (references to the main sprite list) for easy access
        sprite_list_2d.clear()

        # Create a list of solid-color sprites to represent each grid location
        for row in range(visible_size[1]):
            sprite_list_2d.append([])
            for column in range(visible_size[0]):
                x = column * (tile_size + line_width) + (tile_size / 2 + line_width) + position[0]
                y = row * (tile_size + line_width) + (tile_size / 2 + line_width) + position[1]
                sprite = arcade.SpriteSolidColor(
                    tile_size, tile_size, (255, 255, 255))
                sprite.center_x = x
                sprite.center_y = y
                sprite_list.append(sprite)
                sprite_list_2d[row].append(sprite)

    # Adjusts scaling when the window's size changes, this is automatically called once after __init__()
    def on_resize(self, width, height):
        super().on_resize(width, height)
        # The size of the window
        self.scale.size = [width, height]

        # Length of each side of a tile
        self.scale.tile_size = self.scale.size[1] // 23

        # The width of the grid lines
        self.scale.grid_line_width = ceil(self.scale.size[1] / 800)

        # Effective tile size, the amount of space a tile takes up including its margins
        self.scale.eff_tile_size = self.scale.tile_size + self.scale.grid_line_width

        # Calculate total size (in pixels) of each grid
        self.scale.grid_size = [self.scale.eff_tile_size * GRID_DIMS[0], self.scale.eff_tile_size * RENDERED_GRID_HEIGHT]
        self.scale.preview_size = [self.scale.eff_tile_size * INFO_GRID_DIMS[0], self.scale.eff_tile_size * INFO_GRID_DIMS[1] * PREVIEW_COUNT]
        self.scale.hold_size = [self.scale.eff_tile_size * INFO_GRID_DIMS[i] for i in range(2)]

        # Position of the three grids, main grid is centered
        self.scale.grid_pos = [(self.scale.size[i] - self.scale.grid_size[i]) / 2 for i in range(2)]

        # How far preview and hold should be from the main grid
        self.scale.info_offset = self.scale.size[1] / 200

        self.scale.preview_pos = [self.scale.grid_pos[0] + self.scale.grid_size[0] + self.scale.info_offset,
            self.scale.grid_pos[1] + self.scale.grid_size[1] - self.scale.preview_size[1]]

        self.scale.hold_pos = [self.scale.grid_pos[0] - self.scale.preview_size[0] - self.scale.info_offset,
            self.scale.grid_pos[1] + self.scale.grid_size[1] - self.scale.hold_size[1]]

        # Create new sprite grids with new parameters
        self.create_sprite_grid(GRID_DIMS, [GRID_DIMS[0], RENDERED_GRID_HEIGHT], self.scale.tile_size, self.scale.grid_line_width, self.scale.grid_pos, self.grid_sprite_list, self.grid_sprites)
        self.create_sprite_grid(PREVIEW_GRID_DIMS, PREVIEW_GRID_DIMS, self.scale.tile_size, self.scale.grid_line_width, self.scale.preview_pos, self.preview_grid_sprite_list, self.preview_grid_sprites)
        self.create_sprite_grid(INFO_GRID_DIMS,INFO_GRID_DIMS, self.scale.tile_size, self.scale.grid_line_width, self.scale.hold_pos, self.hold_grid_sprite_list, self.hold_grid_sprites)

        # Text size
        self.scale.font_size = 24

    # Updates sprite grid to match positions of tiles
    def redraw_grid(self):

        # Adds the placed pieces to the sprite grid (and clears anything else)
        for column in range(GRID_DIMS[0]):
            for row in range(RENDERED_GRID_HEIGHT):
                self.grid_sprites[row][column].color = self.settings.colors[self.grid[row][column]] + (self.settings.normal_opacity,)

        # Draws the ghost tiles
        for tile in self.ghost.tiles:
            if not tile[1] >= RENDERED_GRID_HEIGHT:
                self.grid_sprites[tile[1]][tile[0]].color = self.settings.colors[self.active_piece.type] + (self.settings.ghost_opacity,)

        # Draws the active piece (overwrites ghost tiles if overlapping)
        for tile in self.active_piece.tiles:
            if not tile[1] >= RENDERED_GRID_HEIGHT:
                self.grid_sprites[tile[1]][tile[0]].color = self.settings.colors[self.active_piece.type] + (self.settings.normal_opacity,)

        # Draw preview grid
        for column in range(PREVIEW_GRID_DIMS[0]):
            for row in range(PREVIEW_GRID_DIMS[1]):
                self.preview_grid_sprites[row][column].color = self.settings.colors[self.preview_grid[row][column]] + (self.settings.normal_opacity,)

        # Draw hold grid
        for column in range(INFO_GRID_DIMS[0]):
            for row in range(INFO_GRID_DIMS[1]):
                self.hold_grid_sprites[row][column].color = self.settings.colors[self.hold_grid[row][column]] + (self.settings.normal_opacity,)

    # Called at the beginning and when the restart keybind is pressed
    def setup(self):

        self.game_phase = GamePhase.GENERATION

        # Generate the first bag
        self.bag = ['I', 'J', 'L', 'O', 'S', 'T', 'Z']
        shuffle(self.bag)

        # Determines if the player can swap the active piece with their hold
        self.hold_ready = True
        self.active_piece = ActivePiece(
            '', [0, 0], [[0, 0], [0, 0], [0, 0], [0, 0]], 0, GRID_DIMS[1], 0, -1)

        self.fall_interval = 1
        self.cur_time = 0
        self.hold = ''
        self.back_to_back_bonus = False
        # Clear main grid
        for i in range(GRID_DIMS[1]):
            for j in range(GRID_DIMS[0]):
                self.grid[i][j] = ''

        # Clear preview grid
        for i in range(PREVIEW_GRID_DIMS[1]):
            for j in range(PREVIEW_GRID_DIMS[0]):
                self.preview_grid[i][j] = 'background'

        # Clear Hold grid
        for i in range(INFO_GRID_DIMS[1]):
            for j in range(INFO_GRID_DIMS[0]):
                self.hold_grid[i][j] = 'background'

        # Spawn the first piece
        self.spawn_piece(False)

        # Update preview for first bag
        for i, type in enumerate(reversed(self.bag[:PREVIEW_COUNT])):
            for tile in SPAWN_POSITIONS[type]:
                self.preview_grid[(INFO_CENTER_SPAWN[1] + (i)) * 2 + tile[1]][INFO_CENTER_SPAWN[0] + tile[0]] = type
        self.stats = game_statistics(0, [0, 0, 0], 0, 1, [0, 0, 0, 0], [0, 0])
        self.timers = {
            # Time until the active piece will move down automatically
            'fall': self.fall_interval,
            # Time until the active piece will move down while the down key is pressed
            'drop_ARR': 0.0,
            # Auto Repeat Rate
            'ARR': 0.0,
            # Delayed Auto Shift
            'DAS': 0.0
        }
        self.cur_time = 0
        self.paused = False
        self.game_ended = False
        self.stats = game_statistics(0, [0, 0, 0, 0], 0, 1, [0, 0, 0, 0], [0, 0])
    def on_key_press(self, symbol, modifiers):
        cfg = self.settings
        if symbol == cfg.pause:
            self.pause(not self.paused)
        elif symbol == cfg.restart:
            self.setup()

        # Don't check movement binds if the game is paused
        elif self.paused:
            return

        elif symbol == cfg.move_left:
            self.move_tiles(self.active_piece.tiles, -1, 0, center=self.active_piece.center)
            self.reset_lock_timer()
            self.timers['DAS'] = self.settings.delayed_auto_shift
            # Stores the most recent move_left or move_right key press (determines which direction the piece should move if both are pressed)
            # Value is the direction the block would move in
            self.last_horizontal_key = -1

        elif symbol == cfg.move_right:
            self.move_tiles(self.active_piece.tiles, 1, 0, center=self.active_piece.center)
            self.reset_lock_timer()
            self.timers['DAS'] = self.settings.delayed_auto_shift
            self.last_horizontal_key = 1

        elif symbol == cfg.hold and self.hold_ready:
            self.spawn_piece(True)
            self.hold_ready = False

        elif symbol == cfg.rotate_clockwise:
            self.rotate_active(1)
            # Checked here rather than in rotate_active() to prevent the lowest_line from changing when a flip rotate fails
            self.check_lowest_pos()
            self.reset_lock_timer()

        elif symbol == cfg.rotate_counter_clockwise:
            self.rotate_active(-1)
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
                for i in range(GRID_DIMS[1]):
                    if self.move_tiles(self.active_piece.tiles, 0, -1, center=self.active_piece.center):
                        if self.game_phase == GamePhase.FALLING:
                            # Soft drop score is applied before score() to show the score increasing as the piece is falling
                            self.stats.score += 1 * SCORE_DATA['soft_drop_mp']
                    else:
                        break
            elif self.timers['drop_ARR'] <= 0:
                if self.move_tiles(self.active_piece.tiles, 0, -1, center=self.active_piece.center) and self.game_phase == GamePhase.FALLING:
                    self.stats.score += 1 * SCORE_DATA['soft_drop_mp']
                # Reset the fall timer when the piece is manually moved down, this make it more predictable
                self.timers['fall'] = self.fall_interval

        # DAS and ARR
        if self.timers['DAS'] <= 0:
            # If ARR is 0, move the active piece in the corresponding direction until it hits an object
            if self.settings.auto_repeat_rate == 0:
                while True:
                    if not self.move_tiles(self.active_piece.tiles, self.last_horizontal_key, 0, center=self.active_piece.center):
                        self.update_ghost()
                        break
            elif self.timers['ARR'] <= 0:
                # If both horizontal movement keys are held down, use self.last_horizontal_key to determine direction
                if self.keys[self.settings.move_left] and self.keys[self.settings.move_right]:
                    self.move_tiles(self.active_piece.tiles, self.last_horizontal_key, 0, center=self.active_piece.center)

                elif self.keys[self.settings.move_left]:
                    self.move_tiles(self.active_piece.tiles, -1, 0, center=self.active_piece.center)

                elif self.keys[self.settings.move_right]:
                    self.move_tiles(self.active_piece.tiles, 1, 0, center=self.active_piece.center)
                else:
                    return
                self.timers['ARR'] = self.settings.auto_repeat_rate
                self.update_ghost()



    def on_update(self, delta_time):
        if not self.paused:
            self.cur_time += delta_time

            # Decrease all timers by the time since this function was last called
            for key in self.timers.keys():
                self.timers[key] -= delta_time

            # Execute appropriate functions for the current game phase
            if self.game_phase == GamePhase.FALLING:
                self.falling()

            elif self.game_phase == GamePhase.LOCK:
                self.locking()

            self.held_keys()
    # Generation Phase
    def spawn_piece(self, from_hold: bool):
        # Used for scoring T-Spins, see rotate_active for better description
        self.active_piece.rotation_point = -1
        if from_hold:
            # If hold is empty (first use of the current game), get a new piece from the bag instead of the hold
            if self.hold == '':
                self.hold = self.active_piece.type
                self.active_piece.type = self.bag.pop(0)
                self.update_preview()
                # Draw hold grid

            # Swap active piece and hold
            else:
                self.active_piece.type, self.hold = self.hold, self.active_piece.type
            self.update_hold()
        else:
            # Remove first type from the bag and set the new piece to that type
            self.active_piece.type = self.bag.pop(0)

        # Sets the rotational center of the piece to be at the spawn point
        self.active_piece.center = copy.deepcopy(CENTER_SPAWN)
        self.active_piece.rotation = 0

        # Place tiles relative to the center
        self.active_piece.tiles = [[CENTER_SPAWN[j] + SPAWN_POSITIONS[self.active_piece.type][i][j] for j in range(2)] for i in range(4)]

        # If the new piece does not have room to spawn, the game is over
        if not self.is_valid_pos(self.active_piece.tiles):
            self.game_over('Block Out')

        # If the bag has fewer pieces than the preview is set to display, generate and append a new bag
        # Each bag has one of each tile, which ensures even distribution of pieces
        if len(self.bag) == PREVIEW_COUNT:
            self.new_bag = ['I', 'J', 'L', 'O', 'S', 'T', 'Z']
            shuffle(self.new_bag)
            self.bag.extend(self.new_bag)

        # Piece spawns partially outside of the visible grid, but tries to move down immediately; the lock phase is not started until it fails to move down naturally,
        # this gives additional time equal to fall_interval to move instead of the usual 0.5 when a piece cannot fall
        self.move_tiles(self.active_piece.tiles, 0, -1, center=self.active_piece.center)
        self.timers['fall'] = self.fall_interval

        # Resets the lowest line to be used for tracking lock timer resets and switching from the lock to falling phase
        self.active_piece.lowest_line = GRID_DIMS[1]
        self.check_lowest_pos()

        self.game_phase = GamePhase.FALLING

        # Updates the ghost tiles to match the new piece
        self.update_ghost()

    # Falling Phase
    def falling(self):
        # If the fall timer has expired, try to move the active piece
        if self.timers['fall'] <= 0:
            # If the active piece cannot be moved, enter the locking phase
            if not self.move_tiles(self.active_piece.tiles, 0, -1, center=self.active_piece.center):
                self.game_phase = GamePhase.LOCK
                self.timers['lock'] = LOCK_DELAY

            else:
                # Reset the fall timer
                self.timers['fall'] = self.fall_interval

    # Locking Phase
    def locking(self):
        # Pieces can fall during the locking phase if the lowest y position of any tile is greater than or equal to the lowest position any tile was previously (for the active piece)
        # If the piece falls below that threshold, check_lowest_pos() will switch back to the falling phase
        if self.fall_while_locking:
            if self.timers['fall'] <= 0:
                if not self.move_tiles(self.active_piece.tiles, 0, -1, center=self.active_piece.center):
                    self.fall_while_locking = False
                    # Check but don't increment the lock counter
                    if self.active_piece.lock_counter < MAX_LOCK_RESET:
                        self.timers['lock'] = LOCK_DELAY

                self.timers['fall'] = self.fall_interval

        # If the active piece can move down, reset the fall timer and allow it to fall during the lock phase
        elif self.active_piece.tiles != self.ghost.tiles:
            self.timers['fall'] = self.fall_interval
            self.fall_while_locking = True

        # If the lock timer has expired, place the active piece
        else:
            if self.timers['lock'] <= 0:
                self.place_piece()

    # Resets the lock timer and increments the lock counter if in the locking phase and the lock counter has not exceeded the max
    def reset_lock_timer(self):
        if self.game_phase == GamePhase.LOCK and self.active_piece.lock_counter < MAX_LOCK_RESET:
            self.active_piece.lock_counter += 1
            self.timers['lock'] = LOCK_DELAY

    # Places the active piece at the position of the ghost piece
    def place_piece(self):
        # End the game if the placed piece is completely outside the visible grid
        if min([self.ghost.tiles[i][1] for i in range(4)]) >= RENDERED_GRID_HEIGHT:
            self.paused = False
            self.game_over('Lock Out')

        # Add the position of the ghost tiles to the main grid
        # (the ghost tiles are always the position a piece will be placed)
        for tile in self.ghost.tiles:
            self.grid[tile[1]][tile[0]] = self.active_piece.type

        # Clear any full rows (only checks rows which the piece was placed in)
        self.iterate(set([self.ghost.tiles[i][1] for i in range(4)]))

        # Calculate score
        self.score()

        # Round the score to an int (although the score never has a decimal value other than 0 aside from floating point imprecision)
        self.stats.score = round(self.stats.score)

        self.spawn_piece(False)
        self.hold_ready = True
        self.update_preview()

    # Iterate/Pattern/Eliminate Phase
    def iterate(self, rows: set[int]):
        self.game_phase = GamePhase.ITERATE
        clears = []
        # If a row has a value in each position, add it to the list of lines to be cleared
        for i in rows:
            for j in range(GRID_DIMS[0]):
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
            for j in range(GRID_DIMS[0]):
                self.grid[-1].append('')

        self.cleared_lines = len(clears)
        self.stats.total_clears += self.cleared_lines
        # If a new level has been reached and does not exceed the maximum
        if self.stats.total_clears // 10 > self.stats.level and self.stats.level < MAX_LEVEL:
            self.stats.level += 1
            # Calculate and apply new fall interval
            self.fall_interval = pow((0.8 - (( self.stats.level - 1) * 0.007)), self.stats.level)

    def score(self):
        self.game_phase = GamePhase.COMPLETION
        # Hard drop score, active piece is not moved on a hard drop, so the difference between it and the ghost is the number of lines dropped
        self.stats.score += (self.active_piece.center[1] - self.ghost.center[1]) * SCORE_DATA['hard_drop_mp']

        # Sets the effective multiplier for the back-to-back bonus
        if self.back_to_back_bonus:
            eff_back_to_back_mp = SCORE_DATA['back_to_back_mp']
        else:
            eff_back_to_back_mp = 1

        # If the active piece is a 'T' and the last movement was a rotation, check for a T-Spin
        if self.active_piece.type == 'T' and self.active_piece.rotation_point != -1:
            # A T-Spin/Mini T-Spin is when a 'T' piece is placed in a position where at least 3
            # of the 4 corners diagonally adjacent to its center are occupied or out of bounds
            # A rotation must be the last successful movement to count

            # the indices of corners[] (after rotation is applied) correspond with the numbers in the diagram below
            # Hashes represent the piece, underscore represents a blank tile, if rotated, the corner indices rotate as well
            # 0#1
            # ###
            # 3_2
            corners = [[-1, 1], [1, 1], [1, -1], [-1, -1]]
            # Align corners with the active piece's rotation
            for i in range(self.active_piece.rotation):
                corners.insert(0, corners.pop())

            # Convert corners into an array of booleans that indicate if a corner (relative to the active piece's center) is occupied/out of bounds
            for i, corner in enumerate([[self.active_piece.center[i] + corners[j][i] for i in range(2)] for j in range(4)]):
                try:
                    corners[i] = bool(self.grid[corner[1]][corner[0]])
                # Out of bounds
                except:
                    corners[i] = True

            # Normal T-Spin
            # If corners 0 and 1 are occupied or the final rotation used rotation point 4 (guideline says rotation point 5, but this is 0-indexed)
            if (corners[0] and corners[1] and (corners[2] or corners[3])) or self.active_piece.rotation_point == 4:
                self.stats.score += SCORE_DATA['t_spin'][self.cleared_lines] * eff_back_to_back_mp * self.stats.level

                self.stats.t_spin[self.cleared_lines] += 1
                # A T-Spin without any clears does not reset the back-to-back bonus, but does not start it either
                if self.cleared_lines > 0:
                    self.back_to_back_bonus = True
                return

            # Mini T-Spin
            # If at least 3 of the corners are occupied/out of bounds and the last movement was a rotation
            elif sum(corners) >= 3:
                self.stats.score += SCORE_DATA['t_spin'][self.cleared_lines] * self.stats.level
                self.stats.mini_t_spin[self.cleared_lines] += 1
                if self.cleared_lines > 0:
                    self.back_to_back_bonus = True
                return

        # Reset the back-to-back multiplier if the placement was not a tetris (i.e. 4 line clears)
        if self.cleared_lines != 4:
            eff_back_to_back_mp = 1
        if self.cleared_lines > 0:
            self.stats.score += SCORE_DATA['normal_clear'][self.cleared_lines - 1] * eff_back_to_back_mp * self.stats.level

        if self.cleared_lines == 4:
            self.back_to_back_bonus = True
        else:
            self.back_to_back_bonus = False

    def on_draw(self):
        self.clear()

        # Update the sprite list
        self.redraw_grid()

        # Draw grid lines for the main grid (the grid itself will be drawn over)
        arcade.draw_xywh_rectangle_filled(self.scale.grid_pos[0], self.scale.grid_pos[1],
            GRID_DIMS[0] * self.scale.eff_tile_size + self.scale.grid_line_width, RENDERED_GRID_HEIGHT * self.scale.eff_tile_size + self.scale.grid_line_width,
            self.settings.colors['grid_lines'])

        # Draw grids
        self.grid_sprite_list.draw()
        self.preview_grid_sprite_list.draw()
        self.hold_grid_sprite_list.draw()

        # Draw score
        arcade.draw_text(f'Score:\n{self.stats.score}\nLevel: {self.stats.level}',
        self.scale.hold_pos[0], self.scale.hold_pos[1] - self.scale.font_size * 2,
            font_size=self.scale.font_size,
            width=self.scale.hold_size[0],
            align='center',
            color=self.settings.colors['text'])

        # Draw Hold label if the hold is empty (this is just to indicate that there is a hold feature,
        # but is unnecessary to render once a piece is in it)
        if not self.hold:
            arcade.draw_text(f'Hold',
            self.scale.hold_pos[0], self.scale.hold_pos[1] + (self.scale.hold_size[1] - self.scale.font_size) / 2,
                width=self.scale.hold_size[0],
                font_size=self.scale.font_size,
                align='center',
                color=self.settings.colors['text'])

        if self.game_ended:
            arcade.draw_xywh_rectangle_filled(self.scale.grid_pos[0], self.scale.grid_pos[1] + self.scale.grid_size[1] // 2 - self.scale.font_size * 2, self.scale.grid_size[1], self.scale.font_size * 4, self.settings.colors['background'])
            arcade.draw_text(f'Game Over\nScore: {self.stats.score}', self.scale.grid_pos[0], self.scale.grid_pos[1] + self.scale.grid_size[1] // 2 + round(self.scale.font_size * 0.5), self.settings.colors['text'], self.scale.font_size, self.scale.grid_size[0], 'center')

    # Update the preview grid
    def update_preview(self):
        type = self.bag[PREVIEW_COUNT - 1]
        del self.preview_grid[PREVIEW_GRID_DIMS[1] - 2:PREVIEW_GRID_DIMS[1] - 1]
        # For each tile in 1 section of the preview grid
        for i in range(round(PREVIEW_GRID_DIMS[1] / PREVIEW_COUNT)):
            self.preview_grid.insert(0, [])
            for j in range(PREVIEW_GRID_DIMS[0]):
                self.preview_grid[0].append('background')
        for tile in SPAWN_POSITIONS[type]:
            self.preview_grid[INFO_CENTER_SPAWN[1] + tile[1]][INFO_CENTER_SPAWN[0] + tile[0]] = type

    # Update the hold grid
    def update_hold(self):
        for i in range(INFO_GRID_DIMS[1]):
            for j in range(INFO_GRID_DIMS[0]):
                self.hold_grid[i][j] = 'background'

        for tile in SPAWN_POSITIONS[self.hold]:
            self.hold_grid[INFO_CENTER_SPAWN[1] + tile[1]][INFO_CENTER_SPAWN[0] + tile[0]] = self.hold

    def rotate_active(self, steps: int) -> bool:
        # The 'Super Rotation System' is rather unintuitive,
        # I won't bother trying to fully explain it here, but these sources do a good job
        # https://tetris.wiki/Super_Rotation_System
        # https://www.youtube.com/watch?v=yIpk5TJ_uaI

        # Stores the position of the piece after being rotated
        rotated_piece = copy.deepcopy(self.active_piece)
        rotated_piece.rotation = (self.active_piece.rotation + steps) % 4
        # Stores the new position
        new_position = copy.deepcopy(self.active_piece)

        # Rotate pieces around the center
        # for each step: for each tile: new_pos = (y, -x) (relative to center piece)
        rotated_piece.tiles = [[
            rotated_piece.center[j] + [
                        steps * (rotated_piece.tiles[i][1] - rotated_piece.center[1]),
                        - steps * ((rotated_piece.tiles[i][0] - rotated_piece.center[0]))][j]
                    for j in range(2)]
                for i in range(4)]

        # The number of rotation tests to apply (1 for an 'O' piece, 5 for everything else)
        test_count = len(OFFSETS[self.active_piece.type][0])

        # The offsets for each test to be applied
        offset_data = [[
                    OFFSETS[self.active_piece.type][self.active_piece.rotation][test][i] -
                    OFFSETS[self.active_piece.type][rotated_piece.rotation][test][i]
                for i in range(2)]
            for test in range(test_count)]

        # Attempt each of the 5 translations
        for test in range(5):

            # Set the tile positions according to the offset
            new_position = copy.deepcopy(rotated_piece.tiles)
            if not (offset_data[test][0] == 0 and offset_data[test][1] == 0):
                self.move_tiles(new_position, offset_data[test][0], offset_data[test][1])

            # Check if the new tile positions are occupied
            if self.is_valid_pos(new_position):
                self.active_piece = copy.deepcopy(rotated_piece)
                self.active_piece.tiles = new_position
                self.active_piece.center = [rotated_piece.center[i] + offset_data[test][i] for i in range(2)]
                # Stores the index of the successful test,
                # if the piece is a 'T', this will be used in score() to identify what type of T-Spin (if any) was preformed
                self.active_piece.rotation_point = test
                return True

        return False

    # Translates the active piece by the given value, returns false if it fails
    def move_tiles(self, tiles: list[list[int]], x: int, y: int, center: list[int]=None) -> bool:
        # Add tile coordinates after translation to new_pos
        new_pos = [[tile[j] + [x, y][j] for j in range(2)] for tile in tiles]
        if self.is_valid_pos(new_pos):
            tiles[:] = new_pos
            if center:
                center[:] = [center[i] + [x, y][i] for i in range(2)]
                # If center is an argument, it can be assumed the active piece was moved
                self.check_lowest_pos()
                self.active_piece.rotation_point = -1
            return True
        return False

    # Checks if a list of tiles overlaps any placed tiles or is out of bounds
    def is_valid_pos(self, tiles: list[list[int]]) -> bool:
        for tile in tiles:
            if not (0 <= tile[0] < GRID_DIMS[0] and 0 <= tile[1] < GRID_DIMS[1]):
                return False

            elif self.grid[tile[1]][tile[0]]:
                return False

        return True
    # Updates the current position of the ghost tiles
    def update_ghost(self):
        new_ghost = GhostPiece
        new_ghost.tiles = copy.deepcopy(self.active_piece.tiles)
        new_ghost.center =  copy.deepcopy(self.active_piece.center)
        for i in range(GRID_DIMS[1]):
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

    # Pause or unpause the game
    def pause(self, new_pause_state: bool):
        # If unpaused after the game has ended, reset the game
        if self.paused and self.game_ended:
            self.setup()
        else:
            self.paused = new_pause_state


    def game_over(self, reason: str):
        # Print scores to terminal (didn't have time to make a GUI for this)
        print(
            f'Game Over: {reason}\n'
            f'Score: {self.stats.score}\n'
            f'Time: {int(self.cur_time // 60)}m {round(self.cur_time % 60)}s\n'
            f'Level: {self.stats.level}\n'
            f'Total Clears: {self.stats.total_clears}\n'
            f'Clears by line count (excluding T-Spins):\n'
            f'1: {self.stats.clears[0]}, 2: {self.stats.clears[1]}, 3: {self.stats.clears[2]}, 4: {self.stats.clears[3]}\n'
            f'T-Spins by line count:\n'
            f'0: {self.stats.t_spin[0]}, 1: {self.stats.t_spin[1]}, 2: {self.stats.t_spin[2]}, 3: {self.stats.t_spin[3]}\n'
            f'Mini T-Spins by line count:\n'
            f'0: {self.stats.mini_t_spin[0]}, 1: {self.stats.mini_t_spin[1]}')

        # Create a new score file if it does not exist
        if not exists(SCORE_FILE):
            with open(SCORE_FILE, 'w') as file:
                pass

        with open(SCORE_FILE, 'r') as file:
            lines = []
            for line in file.readlines():
                try:
                    lines.append(int(line))
                except:
                    pass
            lines.reverse()
            if self.stats.score >= lines[-1]:
                insort(lines, self.stats.score)
                if len(lines) > MAX_SAVED_SCORES:
                    lines.pop()
                print('New High SCore!')
        scores = ('\n'.join([str(line) for line in reversed(lines)]) + '\n')
        print(f'High Scores:{scores}')

        # Write scores to file
        with open(SCORE_FILE, 'w') as file:
            file.write('\n'.join([str(line) for line in reversed(lines)]) + '\n')

        self.game_ended = True
        self.pause(True)

def main():
    '''Main function'''
    window = MyGame()
    window.setup()
    arcade.run()


if __name__ == '__main__':
    main()
