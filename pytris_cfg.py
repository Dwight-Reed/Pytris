from unittest.mock import DEFAULT
from arcade.key import *
from ast import literal_eval
import configparser
from os.path import dirname, exists, realpath

file_name = f'{dirname(realpath(__file__))}/pytris.cfg'

config = configparser.ConfigParser(allow_no_value=True)

DEFAULT_CONFIG = {
    'keybinds': {
        '# List of key names: https://api.arcade.academy/en/latest/arcade.key.html'
        'move_left': 'LEFT',
        'move_right': 'RIGHT',
        'move_down': 'DOWN',
        'hard_drop': 'SPACE',
        'hold': 'MOD_SHIFT',
        'rotate_clockwise': 'D',
        'rotate_counter_clockwise': 'A',
        'rotate_flip': 'W',
    },
    'colors': {
        'empty_tile': '(0, 0, 0)',
        'I': '(0, 255, 255)',
        'J': '(0, 0, 255)',
        'L': '(255, 170, 0)',
        'O': '(255, 255, 0)',
        'S': '(0, 255, 0)',
        'T': '(153, 0, 255)',
        'Z': '(255, 0, 1)',
        'background': '(0, 0, 0)',
        'grid_line': '(127, 127, 127)',
        'normal_opacity': '255',
        'ghost_opacity': '128'
    },
    'other': {
        '# The time a left or right key must be held down before it moves additional tiles': None,
        'delayed_auto_shift': '0.1',

        '\n# The time between each movement while holding down a horizontal movement key': None,
        'auto_repeat_rate': '0.005',

        '\n# The time between each movement while holding the down key': None,
        'drop_auto_repeat_rate': '0'
    }
}

def load_config():
    if exists(file_name):
        if validate_config():
            pass
        else:
            exit(1)
    else:
        generate_config()


def generate_config():
    config['keybinds'] = DEFAULT_CONFIG['keybinds']
    config['colors'] = DEFAULT_CONFIG['colors']
    config['other'] = DEFAULT_CONFIG['other']

    with open(file_name, 'w') as config_file:
        config.write(config_file)

def validate_config():
    failed, skip = False
    config.read(file_name)

    for section in config.sections():
        print(section)
        for key in DEFAULT_CONFIG[section].keys():
            if not key in config[section].keys() and not '#' in list(key):
                print(f'Config Error: Missing key: {key}')
                failed, skip = True
        for key in config[section].keys():
            if not key in DEFAULT_CONFIG[section].keys():
                print(f'Config Error: Unrecognized Key: {key}')
                failed, skip = True
        if not skip:
            for key, value in dict(config[section]).items():
                try:
                    if section == 'keybinds':
                        pass
                    else:
                        converted_value = literal_eval(value)

                        if section == 'colors':
                            if key in ('normal_opacity', 'ghost_opacity'):
                                if type(converted_value) != int or not converted_value in range(0, 256):
                                    raise Exception(f'{key} must be an integer in the range 0-255 (e.g. 24)')

                            elif type(converted_value) != tuple or len(converted_value) != 3 or min(converted_value) < 0 or max(converted_value) > 255:
                                raise Exception(f'{key} must be a tuple with 3 values in the range 0-255 (e.g. 125, 125, 30)')

                        elif section == 'other':
                            if not type(converted_value) in (int, float):
                                raise Exception(f'{key} must be either an int or a float')
                            pass

                        else:
                            raise Exception('Invalid section: {section}')

                except Exception as ex:
                    print(f'Config Error: {ex}')
                failed = True

        return not failed


