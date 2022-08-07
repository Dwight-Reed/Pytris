# Super Rotation System
One of the most popular rotation systems

There are a variety of resources online that document how this works such as the [Hard Drop Wiki](https://harddrop.com/wiki/SRS)

In summary, it applies a series of offsets (i.e. wall kicks) to a piece after it is rotated, the first offset that is a valid position is where the piece ends up, otherwise, the rotation fails

One addition to this I added is 180 degree rotation, this is effectively a macro for 2 clockwise rotations, but nothing happens if either would fail. This means there are no additional possibilities for wall kicks. I chose to do it this way because there is no widely accepted method for how it should work.

# Scoring
I used the scores system documented [here](https://tetris.wiki/Scoring#Recent_guideline_compatible_games) (Except mini-t-spin doubles are counted as a normal t-spin)
