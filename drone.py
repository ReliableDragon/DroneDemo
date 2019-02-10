import random
import ast
import json

DEBUG = False

class Drone():

    TIME_BETWEEN_SYNCS = 10
    CONSENSUS_NEEDED = 0.25

    def __init__(self, num, target_pattern, num_drones):
        self.num = num
        # The first item here is (X_DIM, Y_DIM), so we can project it right.
        self.target_pattern = target_pattern
        if DEBUG: print("Target Pattern: {}".format(self.target_pattern))
        # What, in our terms, are the squares we care about?
        self.relative_targets = []
        # This is only a rough estimate, used to adjust search/post behavior.
        self.num_drones = num_drones
        # TODO: Track max/min map values to avoid map scan each iteration.
        self.relative_size = (0, 0)
        self.x = 0
        self.y = 0
        self.t = 0
        self.last_move = (0, 0)
        self.map = {(0, 0): ('M', 0)}
        # Unify coordinate systems as we go, in order to speed processing.
        self.coords = self.num
        # When did we last sync with a given drone?
        self.syncs = {}
        # Store where drones have said they are going next.
        self.choreographed_moves = {}
        # Where was the last known location of a given drone? Conditionally
        # authoritative, which is a bad idea.
        self.last_seen = {}
        self.assigned_target = None

    def update(self, unprocessed_map, msg_callback):
        if DEBUG: print("Drone {} running at location {}!".format(self.num, (self.x, self.y)))
        # if DEBUG: print("Choreographs: {}".format(self.choreographed_moves))
        if DEBUG: print("Raw map: {}".format(unprocessed_map))
        self.t += 1
        map = self.process_map(unprocessed_map, (self.x, self.y))
        self.update_map(map)
        if DEBUG: self.print_map()
        self.project_map()
        # If we move before messaging the map, then it will show us in
        # a different location than their sensors will, which complicates
        # things.
        self.message_map(map, msg_callback)
        # Move, so we can send our choreograph signal.
        move = self.move(map, msg_callback)
        self.message_move(map, msg_callback)
        self.choreographed_moves = {}
        return move

    def message_map(self, map, msg_callback):
        nearby = self.get_nearby(map)
        messages = []
        for n in nearby:
            if n not in self.syncs or self.syncs[n] > self.t - self.TIME_BETWEEN_SYNCS:
                messager = msg_callback(n)
                last_seen = self.last_seen[n]
                messager("MAP" + str(self.num) + "|" + str(self.coords)
                         + "M" + str((self.x, self.y)) + "U"
                         + str((last_seen[0], last_seen[1]))
                         + str(self.map))
                self.syncs[n] = self.t

    def message_move(self, map, msg_callback):
        nearby = self.get_nearby(map)
        messages = []
        for n in nearby:
            if int(n) > int(self.num):
                messager = msg_callback(n)
                messager("MOVE" + str(self.num) + str(self.last_move))

    def move(self, map, msg_callback):
        target = self.get_target()
        moves = []
        quorum = int(self.num_drones * self.CONSENSUS_NEEDED)
        if not target or len(self.last_seen) < quorum:
            moves = self.move_random(map)
        else:
            # moves = self.move_random(map)
            moves = self.move_to_target(target, map)

        # If we're blocked by another drone, give them our target.
        best_dir = moves[0]
        blocker = self.drone_at(best_dir, map)
        if blocker:
            self.message_target(blocker, target, msg_callback)
            moves = [(0, 0)]

        while moves:
            dir = moves.pop(0)
            if self.move_is_safe(dir, map):
                self.map[(self.x, self.y)] = ('O', self.t)
                self.x += dir[0]
                self.y += dir[1]
                self.map[(self.x, self.y)] = ('M', self.t)
                self.last_move = dir
                break
        # If we didn't break out of the loop, we can't move.
        else:
            self.last_move = (0, 0)
        if DEBUG: print("Moved {}".format(self.last_move))
        return self.last_move

    def message_target(self, blocker, target, msg_callback):
        if DEBUG: print("Assigning target {} to drone {}".format(target, blocker))
        messager = msg_callback(blocker)
        messager("TGT" + str(target))
        # If we were given the target, we can pick our own again now.
        if self.assigned_target:
            self.assigned_target = None

    def drone_at(self, move, map):
        move_space = (self.x + move[0], self.y + move[1])
        if DEBUG: print("Looking from drone at {}".format(move_space))
        in_space = self.map.get(move_space)[0]
        if in_space != 'X' and in_space != 'O' and in_space != 'M':
            return in_space
        else:
            return None

    def move_random(self, map):
        options = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        random.shuffle(options)
        return options

    def move_to_target(self, target, map):
        if self.x == target[0] and self.y == target[1]:
            return [(0, 0)]
        x_dist = target[0] - self.x
        y_dist = target[1] - self.y
        nearer = (1 if x_dist > 0 else -1, 0)
        further = (0, 1 if y_dist > 0 else -1)
        if abs(x_dist) > abs(y_dist):
            nearer, further = further, nearer
        moves = [further, nearer, (-further[0], -further[1]), (-nearer[0], -nearer[1])]
        if DEBUG: print("Moves generated: {}".format(moves))
        return moves

    def get_target(self):
        # If we're blocking another drone, move out of the way.
        if self.assigned_target:
            if DEBUG: print("Assigned target: {}".format(self.assigned_target))
            tgt = self.assigned_target[0]
            self.assigned_target[1] -= 1
            if self.assigned_target[1] == 0:
                self.assigned_target = None
            return tgt

        if DEBUG: print("Looking for target in {}".format(self.relative_targets))
        valid = []
        for f in self.relative_targets:
            if f not in self.map:
                continue
            if self.map[f][0] == 'O' or self.map[f][0] == 'M':
                valid.append(f)

        if not valid:
            if DEBUG: print("No target found.")
            return None
        else:
            target = min(valid, key=lambda a: abs(a[0] - self.x) + abs(a[1] - self.y))
            if DEBUG: print("Got target: {}".format(target))
            return target

    # TODO: Use just memory map instead of needing the sensor map.
    def move_is_safe(self, dir, map):
        new_loc = (self.x + dir[0], self.y + dir[1])
        if not self.map[new_loc][0] == 'O':
            return False
        # nearby = self.get_nearby(map)
        # for n in nearby:
        #     if n in self.choreographed_moves:
        #         choreograph = self.choreographed_moves[n]
        #         relative_n_loc = self.find_object(map, n)
        #         n_loc = (relative_n_loc[0] + self.x, relative_n_loc[1] + self.y)
        #         n_loc_choreo = (n_loc[0] + choreograph[0], n_loc[1] + choreograph[1])
        #         if n_loc_choreo == new_loc:
        #             return False

        return True

    def msg(self, msg):
        # if DEBUG: print("Drone {} got message: {}".format(self.num, msg))
        if msg[:4] == "MOVE":
            msg = msg[4:]
            dir_start = msg.find('(')
            num = msg[:dir_start]
            dir = msg[dir_start:]
            self.choreographed_moves[num] = ast.literal_eval(dir)
            # if DEBUG: print("Updated choreographs: {}".format(self.choreographed_moves))
        elif msg[:3] == "MAP":
            # Message format is (dicts in json)
            # MAP$THEIR_NUM|${COORDSYS}M${THEIR_LOC}U${OUR_LOC}{$DICT_DATA}
            msg = msg[3:]
            coord_start = msg.find('|')
            them_start = msg.find('M')
            us_start = msg.find('U')
            map_start = msg.find('{')
            num = msg[:coord_start]
            # if DEBUG: print("Num: {}".format(num))
            coords = msg[coord_start+1:them_start]
            # if DEBUG: print("Coords: {}".format(coords))
            them_loc = ast.literal_eval(msg[them_start+1:us_start])
            # if DEBUG: print("Their loc: {}".format(them_loc))
            us_loc = ast.literal_eval(msg[us_start+1:map_start])
            # if DEBUG: print("Us loc: {}".format(us_loc))
            unprocessed_map = ast.literal_eval(msg[map_start:])
            self.combine_maps(unprocessed_map, num, coords, them_loc, us_loc)
            # if DEBUG: print("Updated map: {}".format(self.map))
            # if DEBUG: self.print_map()
        elif msg[:3] == "TGT":
            # Attempt to move towards target for 2 turns, due to ordering.
            self.assigned_target = [ast.literal_eval(msg[3:]), 2]

    # Requires a sensor map, not the memory map.
    # TODO: Fix this so that it works with memory map instead.
    def get_nearby(self, map):
        near = []
        for k, v in map.items():
            if v != 'X' and v != 'M' and v != 'O':
                near.append(v)
        return near

    def process_map(self, unprocessed_map, offset=(0, 0)):
        offset_x = offset[0]
        offset_y = offset[1]
        new_map = {}
        for dir in unprocessed_map:
            adjusted_x  = dir[0] + offset_x
            adjusted_y = dir[1] + offset_y
            adjusted_loc = (adjusted_x, adjusted_y)
            new_map[adjusted_loc] = unprocessed_map[dir]
        return new_map

    def find_object(self, map, id):
        # Q_Q
        # TODO: Stop using two types of maps all over.
        for k, v in map.items():
            if v == id:
                return k

        for k, v in map.items():
            if v[0] == id:
                return k

        raise RuntimeError("Could not find key {} in map {}".format(id, map))

    def update_map(self, _map):
        already_processed = []
        nearby = list(map(int, self.get_nearby(_map)))
        nearby.sort()
        n_locs = []
        for n in nearby:
            n_locs.append(self.find_object(_map, str(n)))
        # We have to process all of the nearby drones in order, because
        # lower numbered droned choose their moves first, which means
        # higher numbered drones can plan to move into their
        # soon-to-be-vacated spaces, which result in us overwriting the
        # lower numbered drone's location in the map, and erroring out
        # when we try to move it later. Going in order avoids this.
        # We could also have copied the map, removed the drones, and
        # modified the copy. But this felt cleaner.
        for loc in n_locs:
            destination = self.update_cell(loc, _map, already_processed)
            # if DEBUG: print("Adding {} to skip list.".format(destination))
            already_processed.append(destination)
        for dir in _map:
            self.update_cell(dir, _map, already_processed)

    # Returns the cell that it authoritatively wrote for. Most of the time
    # this is the one it processed, but with choreographs it can be the
    # one that the drone is choreographing into.
    def update_cell(self, dir, map, already_processed):
        # Some cells are processed out of order due to choreographs.
        # We need to skip them in order to avoid overwriting.
        if dir in already_processed:
            # if DEBUG: print("Skipping {}!".format(dir))
            return dir

        char = map[dir]
        # Update last seen for drones.
        if char != 'O' and char != 'X':
            self.last_seen[char] = (dir[0], dir[1])
            # if DEBUG: print("Updated last seen for {} to {}".format(char, dir))

        # If they've choreographed a move, put their future location
        # into the map, rather than their old one, since they're
        # en route already. Also update last seen.
        if char in self.choreographed_moves:
            # if DEBUG: print("Updating {} for choreograph.".format(char))
            choreograph = self.choreographed_moves[char]
            future_loc = (dir[0] + choreograph[0],
                          dir[1] + choreograph[1])
            if char in self.last_seen:
                # As far as we know, this square is empty now.
                self.map[self.last_seen[char]] = ('O', self.t)
                already_processed.append(self.last_seen[char])
            self.last_seen[char] = future_loc
            self.map[future_loc] = (char, self.t)
            already_processed.append(future_loc)
            # if DEBUG: print("Set to location {}".format(future_loc))
            return future_loc
        else:
            self.map[(dir[0], dir[1])] = (char, self.t)
            return (dir[0], dir[1])

    def combine_maps(self, map, num, coords, their_pos, my_pos):
        # Update their location to have their ID, instead of 'M'.
        map[their_pos] = (str(num), map[their_pos][1])
        # Update our position to have 'M' instead of our ID.
        map[my_pos] = ('M', map[my_pos][1])

        offset_x = self.x - my_pos[0]
        offset_y = self.y - my_pos[1]

        if num < str(self.num) and self.coords != coords:
            # if DEBUG: print("Renumbering to coordinate system {}".format(coords))
            self.renumber_map((offset_x, offset_y))
            self.coords = coords

        if self.coords != coords:
            map = self.process_map(map, (offset_x, offset_y))

        # if DEBUG: print(map)
        for dir in map:
            char = map[dir]
            if (not dir in self.map) or char[1] > self.map[dir][1]:
                self.map[dir] = char
                # Also update last seen, so we have an idea of where everyone is.
                if char[0] != 'O' and char[0] != 'X' and char[0] != 'M':
                    if char[0] not in self.last_seen:
                        self.last_seen[char[0]] = dir
                    else:
                        if self.map[self.last_seen[char[0]]][1] < char[1]:
                            self.last_seen[char[0]] = dir

    def renumber_map(self, offset):
        # if DEBUG:
        #     print("Before renumbering by offset {}.".format(offset))
        #     self.print_map()
        new_map = {}
        for k in list(self.map.keys()):
            new_x = k[0] - offset[0]
            new_y = k[1] - offset[1]
            new_map[(new_x, new_y)] = self.map[k]
        del self.map
        self.map = new_map
        self.x -= offset[0]
        self.y -= offset[1]
        new_targets = []
        for k in list(self.last_seen.keys()):
            self.last_seen[k] = (self.last_seen[k][0] - offset[0],
                                 self.last_seen[k][1] - offset[1])
        for k in self.relative_targets:
            new_x = k[0] - offset[0]
            new_y = k[1] - offset[1]
            new_targets.append((new_x, new_y))
        del self.relative_targets
        self.relative_targets = new_targets
        # if DEBUG: print("After renumbering: {}".format(self.map))

    def make_abs_map(self):
        max_x = max([m[0] for m in self.map])
        min_x = min([m[0] for m in self.map])
        max_y = max([m[1] for m in self.map])
        min_y = min([m[1] for m in self.map])
        empty_map = [['?' for _ in range(min_x, max_x+1)] for _ in range(min_y, max_y + 1)]
        for k, v in self.map.items():
            x_rel = k[0]
            y_rel = k[1]
            x_abs = x_rel - min_x
            y_abs = y_rel - min_y
            y_tot = max_y - min_y
            x_tot = max_x - min_x
            empty_map[y_abs][x_abs] = v[0]

        return empty_map

    def print_map(self):
        abs_map = self.make_abs_map()
        s = ""
        for a in abs_map:
            s += ' '.join(a) + "\n"
        print(s)

    def project_map(self):
        abs_map = self.make_abs_map()
        relative_size = (len(abs_map), len(abs_map[0]))
        if relative_size == self.relative_size:
            return

        self.relative_targets = []
        self.relative_size = relative_size
        if DEBUG: print("Projecting target map: {}\n".format(self.target_pattern))
        if DEBUG: print(abs_map)
        me_y = ['M' in abs_map[i] for i in range(len(abs_map))].index(True)
        me_x = abs_map[me_y].index('M')
        max_x = self.target_pattern[0][0]
        max_y = self.target_pattern[0][1]
        for i in range(1, len(self.target_pattern)):
            rel_x = self.target_pattern[i][0] / max_x
            rel_y = self.target_pattern[i][1] / max_y
            abs_x = int(rel_x * len(abs_map[0]))
            abs_y = int(rel_y * len(abs_map))
            adj_x = self.x - me_x + abs_x
            adj_y = self.y - me_y + abs_y
            self.relative_targets.append((adj_x, adj_y))
        if DEBUG: print("Projected target map. New relative map: {}"
            .format(self.relative_targets))

    def __hash__(self):
        return self.num

    def __eq__(self, other):
        return self.num == other.num
