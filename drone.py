import random
import ast
import json

DEBUG = False

class Drone():

    TIME_BETWEEN_SYNCS = 10

    def __init__(self, num):
        self.num = num
        self.x = 0
        self.y = 0
        self.t = 0
        self.last_move = (0, 0)
        self.map = {(0, 0): ('M', 0)}
        # Unify coordinate systems as we go, in order to speed processing.
        self.coords = self.num
        self.syncs = {}
        self.choreographed_moves = {}
        # TODO: Make use of this to avoid map scans.
        self.last_seen = {}

    def update(self, unprocessed_map, msg_callback):
        if DEBUG: print("Drone {} running at location {}!".format(self.num, (self.x, self.y)))
        if DEBUG: print("Choreographs: {}".format(self.choreographed_moves))
        if DEBUG: print("Raw map: {}".format(unprocessed_map))
        self.t += 1
        map = self.process_map(unprocessed_map, (self.x, self.y))
        self.update_map(map)
        if DEBUG: self.print_map()
        # If we move before messaging the map, then it will show us in
        # a different location than their sensors will, which complicates
        # things.
        self.message_map(map, msg_callback)
        # Move, so we can send our choreograph signal.
        move = self.move(map)
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

    def move(self, map):
        options = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        random.shuffle(options)
        while options:
            dir = options.pop()
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
        if DEBUG: print("Drone {} got message: {}".format(self.num, msg))
        if msg[:4] == "MOVE":
            msg = msg[4:]
            dir_start = msg.find('(')
            num = msg[:dir_start]
            dir = msg[dir_start:]
            self.choreographed_moves[num] = ast.literal_eval(dir)
            if DEBUG: print("Updated choreographs: {}".format(self.choreographed_moves))
        elif msg[:3] == "MAP":
            # Message format is (dicts in json)
            # MAP$THEIR_NUM|${COORDSYS}M${THEIR_LOC}U${OUR_LOC}{$DICT_DATA}
            msg = msg[3:]
            coord_start = msg.find('|')
            them_start = msg.find('M')
            us_start = msg.find('U')
            map_start = msg.find('{')
            num = msg[:coord_start]
            if DEBUG: print("Num: {}".format(num))
            coords = msg[coord_start+1:them_start]
            if DEBUG: print("Coords: {}".format(coords))
            them_loc = ast.literal_eval(msg[them_start+1:us_start])
            if DEBUG: print("Their loc: {}".format(them_loc))
            us_loc = ast.literal_eval(msg[us_start+1:map_start])
            if DEBUG: print("Us loc: {}".format(us_loc))
            unprocessed_map = ast.literal_eval(msg[map_start:])
            self.combine_maps(unprocessed_map, num, coords, them_loc, us_loc)
            if DEBUG: print("Updated map: {}".format(self.map))
            if DEBUG: self.print_map()

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
            if DEBUG: print("Adding {} to skip list.".format(destination))
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
            if DEBUG: print("Skipping {}!".format(dir))
            return dir

        char = map[dir]
        # Update last seen for drones.
        if char != 'O' and char != 'X':
            self.last_seen[char] = (dir[0], dir[1])
            if DEBUG: print("Updated last seen for {} to {}".format(char, dir))

        # If they've choreographed a move, put their future location
        # into the map, rather than their old one, since they're
        # en route already. Also update last seen.
        if char in self.choreographed_moves:
            if DEBUG: print("Updating {} for choreograph.".format(char))
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
            if DEBUG: print("Set to location {}".format(future_loc))
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
            if DEBUG: print("Renumbering to coordinate system {}".format(coords))
            self.renumber_map((offset_x, offset_y))
            self.coords = coords

        if self.coords != coords:
            map = self.process_map(map, (offset_x, offset_y))

        if DEBUG: print(map)
        for dir in map:
            if (not dir in self.map) or map[dir][1] > self.map[dir][1]:
                self.map[dir] = map[dir]

    def renumber_map(self, offset):
        if DEBUG:
            print("Before renumbering by offset {}.".format(offset))
            self.print_map()
        new_map = {}
        for k in list(self.map.keys()):
            new_x = k[0] - offset[0]
            new_y = k[1] - offset[1]
            new_map[(new_x, new_y)] = self.map[k]
        del self.map
        self.map = new_map
        self.x -= offset[0]
        self.y -= offset[1]
        if DEBUG: print("After renumbering: {}".format(self.map))

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

    def __hash__(self):
        return self.num

    def __eq__(self, other):
        return self.num == other.num
