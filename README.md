# Drone Swarm Simulator
Allows you to draw a pattern on the screen. The drones will then attempt to
display that pattern.

Each drone is very limited. They can see the area directly around them, and
message other drones within that space, but that is all. They do not have full
knowledge of the board, or even share a coordinate system. Instead, they
explore separately, trading maps with each other as they encounter one another,
until they have reached a (configurable) quorum, at which point they will
attempt to create the pattern. Drones can crash into each other, if they don't
communicate properly to one another where they are going, as their moves are
simultaneous (mostly), but they have a deference method in place to handle that.

Each drone knows the full pattern they're trying to create, but will up- or
down- scale it to match the current size of the environment it is aware of.
Obstacles are supported, so it should be possible to partition the drones off
and see them create multiple copies of the design. (Provided the quorum is set
low enough.)

It's a bit of a silly project, but I wanted to see if I could make this work
with such limited information available to each drone.
