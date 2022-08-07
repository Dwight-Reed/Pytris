# About
This is my final project for CS50, it is a recreation of the game 'Tetris' written in python

This should run on Linux, MacOS and Windows, but I have only tested it on Linux

# Dependencies
Python 3.10.5+
arcade
pyglet
screeninfo

# Usage
`git clone https://github.com/Dwight-Reed/Pytris.git`

`pip install arcade pyglet screeninfo`

`python main.py`



# Configuration
Upon first launch (or if config is missing), a config file called `pyglet.cfg` will be automatically generated, if any issues are detected in the config (e.g. missing keys), a relevant error message will be shown prefixed with "Config Error:"

## Keybinds
Keybinds can be changed to any value listed in the [arcade.key](https://api.arcade.academy/en/latest/arcade.key.html) documentation (modifier keys do not work, use their normal equivalent further down the page)

## Colors
Colors are represented by an RGB tuple, any tuple with 3 values between 0 and 255 will work

## Other
normal_opacity and ghost_opacity are the alpha values applied to every tile other than the ghost, or the ghost, respectively

delayed_auto_shift is the time (in seconds) a horizontal directional key must be held for before the piece will continue moving in that direction (this prevents moving the piece further than intended)

auto_repeat_rate is the time (in seconds) between each movement of a piece while holding down a directional key

drop_auto_repeat_rate is the time (in seconds) the down key must be pressed
