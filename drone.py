import random
import ast

class Drone():

    def __init__(self, num):
        self.num = num
        self.x = 0
        self.y = 0
        self.t = 0
        self.last_move = (0, 0)
        self.map = {(0, 0): ('M', 0)}
        self.syncs = {}
        self.choreographed_moves = {}
        # TODO: Make use of this to avoid map scans.
        self.last_seen = {}

    def update(self, unprocessed_map, msg_callback):
        # print("Drone {} running!".format(self.num))
        # print("Choreographs: {}".format(self.choreographed_moves))
        self.t += 1
        map = self.process_map(unprocessed_map, (self.x, self.y))
        self.update_map(map)
        # self.print_map()
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
            messager = msg_callback(n)
            messager("MAP" + str(self.num) + str(self.map))

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
        # print("Moved {}".format(self.last_move))
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
        # print("Drone {} got message: {}".format(self.num, msg))
        if msg[:4] == "MOVE":
            msg = msg[4:]
            dir_start = msg.find('(')
            num = msg[:dir_start]
            dir = msg[dir_start:]
            self.choreographed_moves[num] = ast.literal_eval(dir)
            # print("Updated choreographs: {}".format(self.choreographed_moves))
        elif msg[:3] == "MAP":
            msg = msg[3:]
            map_start = msg.find('{')
            num = msg[:map_start]
            # print("Num: {}".format(num))
            unprocessed_map = msg[map_start:]
            unprocessed_map = ast.literal_eval(unprocessed_map)
            self.combine_maps(unprocessed_map, num)
            # print("Updated map: {}".format(self.map))
            # self.print_map()

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
        for k, v in map.items():
            if v[0] == id:
                return k
        raise RuntimeError("Could not find key {} in map {}".format(id, map))

    def update_map(self, map):
        already_processed = []
        for dir in map:
            # Some cells are processed out of order due to choreographs.
            # We need to skip them in order to avoid overwriting.
            if dir in already_processed:
                continue
            char = map[dir]
            # Update last seen for drones.
            if char != 'O' and char != 'X':
                self.last_seen[char] = (dir[0], dir[1])
                # print("Updated last seen for {} to {}".format(char, dir))

            # If they've choreographed a move, put their future location
            # into the map, rather than their old one, since they're
            # en route already. Also update last seen.
            if char in self.choreographed_moves:
                # print("Updating {} for choreograph.".format(char))
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
                # print("Set to location {}".format(future_loc))
            else:
                self.map[(dir[0], dir[1])] = (char, self.t)

    def combine_maps(self, unprocessed_map, num):
        my_pos_to_them = self.find_object(unprocessed_map, str(self.num))
        their_pos = self.find_object(unprocessed_map, 'M')
        # Update their location to have their ID, instead of 'M'.
        unprocessed_map[their_pos] = [str(num), unprocessed_map[their_pos][1]]
        # Update our position to have 'M' instead of our ID.
        unprocessed_map[my_pos_to_them] = ['M', unprocessed_map[my_pos_to_them][1]]

        offset_x = self.x - my_pos_to_them[0]
        offset_y = self.y - my_pos_to_them[1]

        map = self.process_map(unprocessed_map, (offset_x, offset_y))
        # print(map)
        for dir in map:
            if (not dir in self.map) or map[dir][1] > self.map[dir][1]:
                self.map[dir] = map[dir]

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
            empty_map[y_tot - y_abs][x_abs] = v[0]

        return empty_map

    def print_map(self):
        abs_map = self.make_abs_map()
        s = ""
        for a in abs_map:
            s += ''.join(a) + "\n"
        print(s)

    def __hash__(self):
        return self.num

    def __eq__(self, other):
        return self.num == other.num
