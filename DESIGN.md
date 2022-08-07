# Super Rotation System
One of the most popular rotation systems

There are a variety of resources online that document how this works such as the [Hard Drop Wiki](https://harddrop.com/wiki/SRS)

In summary, it applies a series of offsets (i.e. wall kicks) to a piece after it is rotated, the first offset that is a valid position is where the piece ends up, otherwise, the rotation fails

One addition to this I added is 180 degree rotation, this is effectively a macro for 2 clockwise rotations, but nothing happens if either would fail. This means there are no additional possibilities for wall kicks. I chose to do it this way because there is no widely accepted method for how it should work.

# Scoring
I used the scores system documented [here](https://tetris.wiki/Scoring#Recent_guideline_compatible_games) (with the exception that mini-t-spin doubles are counted as a normal t-spin)
## T-Spins
A T-Spin is when a T piece's last movement is a rotation and at least 3 of the tiles diagonally adjacent to the center (corners) are occupied

A normal T-Spin is when the corners that border 2 tiles in the T piece are occupied and at least 1 of the other corners are occupied, or rotation point 5 is used

A Mini T-Spin is when 3 corners are occupied but does not meet the criteria for a normal T-Spin
