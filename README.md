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

They have some amount of cooperation in getting the pattern created, and can
tell other drones if they are in the way. They don't use any fancy pathfinding
or anything though, and can easily get stuck behind walls of obstacles. Adding
Dijkstra's would not be difficult, but since I've done that one plenty of times,
I decided not to bother. Provided obstacles are scarce, the drones do fine.

There's a method you can turn on called DYNAMIC_MODE that will cause drones
to be deleted and created constantly, in order to highlight their communication
abilities and how they don't have to explore the full map, and can hand down
information over time without needing a centralized leader.

Each drone does know the full pattern they're trying to create, but will up- or
down- scale it to match the current size of the environment it is aware of.
Obstacles are supported, so it should be possible to partition the drones off
and see them create multiple copies of the design. (Provided the quorum is set
low enough.)

It's a bit of a silly project, but I wanted to see if I could make this work
with such limited information available to each drone.
