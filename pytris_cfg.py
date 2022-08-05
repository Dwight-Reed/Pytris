import arcade.key
from ast import literal_eval
import configparser
from globals import CONFIG_FILE, Settings
from os.path import exists



config = configparser.ConfigParser(allow_no_value=True, comment_prefixes='#')

# Default config values
DEFAULT_CONFIG = {
    'keybinds': {
        '# List of key names: https://api.arcade.academy/en/latest/arcade.key.html': None,
        '# (modifier keys do not work, use their normal equivalent further down the page)': None,
        'move_left': 'LEFT',
        'move_right': 'RIGHT',
        'move_down': 'DOWN',
        'hard_drop': 'SPACE',
        'hold': 'LSHIFT',
        'rotate_clockwise': 'X',
        'rotate_counter_clockwise': 'Z',
        'rotate_flip': 'F',
        'pause': 'ESCAPE',
        'restart': 'F4'
    },
    'colors': {
        'empty_tile': '(0, 0, 0)',
        '# Color of each type of piece': None,
        'I': '(0, 255, 255)',
        'J': '(0, 0, 255)',
        'L': '(255, 170, 0)',
        'O': '(255, 255, 0)',
        'S': '(0, 255, 0)',
        'T': '(153, 0, 255)',
        'Z': '(255, 0, 1)',
        'background': '(0, 0, 0)',
        'grid_lines': '(127, 127, 127)',
        'text': '(255, 255, 255)'

    },
    'other': {
        'normal_opacity': '255',
        'ghost_opacity': '128',

        '# The time a left or right key must be held down before it moves additional tiles': None,
        'delayed_auto_shift': '0.2',

        '\n# The time between each movement while holding down a horizontal movement key': None,
        'auto_repeat_rate': '0.005',

        '\n# The time between each movement while holding the down key': None,
        'drop_auto_repeat_rate': '0'
    }
}

# Loads and validates pytris.cfg, creates new cfg if missing
def load_config(settings: Settings):
    new_config = False
    if not exists(CONFIG_FILE):
        # Generate a new config
        config['keybinds'] = DEFAULT_CONFIG['keybinds']
        config['colors'] = DEFAULT_CONFIG['colors']
        config['other'] = DEFAULT_CONFIG['other']

        with open(CONFIG_FILE, 'w') as file:
            config.write(file)

        # Remove comments from config (configparser only removes comments when it is reading an existing config)
        for section in config.sections():
            for key, value in config[section].items():
                if '#' in key:
                    config.remove_option(section, key)

        print(f'New config generated at {CONFIG_FILE}')
        new_config = True

    if validate_config():
        if new_config:
            print('The config is meant to be changed manually\n\nDefault Keybinds:')
        for section in config.sections():
            for key, value in config[section].items():

                # If the key is keybind, convert it to its corresponding key code (int)
                if section == 'keybinds':
                    setattr(settings, key, getattr(arcade.key, value))
                    if new_config:
                        print(f'{key}: {value}')
                    continue

                value = literal_eval(value)
                if section == 'colors':
                    # If the length of a key is 1, (i.e. the single-letter name of a piece), convert it to uppercase
                    if len(key) == 1:
                        settings.colors[key.upper()] = value
                    # Empty tiles are represented by an empty string, but empty_tile is used in the config for clarity
                    elif key == 'empty_tile':
                        settings.colors[''] = value
                    else:
                        settings.colors[key] = value
                else:
                    setattr(settings, key, value)
    else:
        print('One or more config errors found, fix errors or delete pytris.cfg to generate a new one')
        exit(1)


# Validates pytris.cfg (used by load_config()
def validate_config() -> bool:
    failed, skip = False, False
    config.read(CONFIG_FILE)
    # sleep(10)

    for section in config.sections():
        # Check for missing keys
        for key in DEFAULT_CONFIG[section].keys():
            if not key in config[section].keys() and not '#' in list(key):
                print(f'Config Error: Missing key: {key}')
                failed, skip = True, True
        # Check for extra keys
        for key in config[section].keys():
            # configparser does not support case-sensitive keys
            if not key in [list(DEFAULT_CONFIG[section].keys())[i].lower() for i in range(len(list(DEFAULT_CONFIG[section].keys())))]:
                failed, skip = True, True
        # If there are missing/extra keys, don't finish validation
        if not skip:
            for key, value in config[section].items():
                try:
                    # Check for valid keybinds
                    if section == 'keybinds':
                        try:
                            getattr(arcade.key, value)
                        except BaseException as ex:
                            raise Exception(f'Invalid keybind: {value}')

                    elif section == 'colors':
                        try:
                            converted_value = literal_eval(value)
                            if type(converted_value) != tuple or len(converted_value) != 3 or min(converted_value) < 0 or max(converted_value) > 255:
                                raise Exception()
                        except:
                            raise Exception(f'{key} must be a tuple with 3 values in the range 0-255 (e.g. 125, 125, 30)')

                    elif section == 'other':
                        if key in ['normal_opacity', 'ghost_opacity']:
                            try:
                                converted_value = literal_eval(value)
                                if type(converted_value) != int or not converted_value in range(0, 256):
                                    raise Exception()
                            except:
                                raise Exception(f'{key} must be an integer in the range 0-255 (e.g. 24)')

                        else:
                            try:
                                converted_value = literal_eval(value)
                                if not type(converted_value) in (int, float):
                                    raise Exception()
                            except:
                                raise Exception(f'{key} must be either an int or a float')

                    else:
                        raise Exception(f'Invalid section: {section}')


                except Exception as ex:
                    failed = True
                    print(f'Config Error: {ex}')

    return not failed
