import random
import ast

class Drone():

    def __init__(self, num):
        self.num = num
        self.x = 0
        self.y = 0
        self.t = 0
        self.last_move = (0, 0)
        self.map = {(0, 0): ['M', 0]}
        self.syncs = {}
        self.choreographed_moves = {}

    def update(self, unprocessed_map, msg_callback):
        map = self.process_map(unprocessed_map, (self.x, self.y))
        # We have to move first, so we know which way to choreograph.
        move = self.move(map)
        self.message(map, msg_callback)
        return move

    def message(self, map, msg_callback):
        nearby = self.get_nearby(map)
        messages = []
        for n in nearby:
            print("Drone #{} messaging drone #{}.".format(self.num, n))
            messager = msg_callback(n)
            messager("MOVE" + str(self.num) + str(self.last_move))
            messager("MAP" + str(self.num) + str(self.map))

    def move(self, map):
        self.t += 1
        self.update_map(map)
        options = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        random.shuffle(options)
        while options:
            dir = options.pop()
            if self.map[(self.x + dir[0], self.y + dir[1])][0] == 'O': #self.move_is_safe(dir, map):
                self.map[(self.x, self.y)] = ['O', self.t]
                self.x += dir[0]
                self.y += dir[1]
                self.map[(self.x, self.y)] = ['M', self.t]
                self.last_move = dir
                break
        # If we didn't break out of the loop, we can't move.
        else:
            self.last_move = (0, 0)
        return self.last_move

    # TODO: Handle choreographs.
    def move_is_safe(self, dir, map):
        pass


    def msg(self, msg):
        print("Drone #{} received message: {}".format(self.num, msg))
        if msg[:4] == "MOVE":
            msg = msg[4:]
            dir_start = msg.find('(')
            num = msg[:dir_start]
            dir = msg[dir_start:]
            self.choreographed_moves[num] = ast.literal_eval(dir)
        elif msg[:3] == "MAP":
            msg = msg[3:]
            map_start = msg.find('{')
            num = msg[:map_start]
            unprocessed_map = msg[map_start:]
            unprocessed_map = ast.literal_eval(unprocessed_map)
            self.combine_maps(unprocessed_map, num)

    # Requires a sensor map, not the memory map.
    # TODO: Fix this so that it works with memory map instead.
    def get_nearby(self, map):
        print("#{}: {}\n".format(self.num, map))
        near = []
        for k, v in map.items():
            if v[0] != 'X' and v[0] != 'M' and v[0] != 'O':
                near.append(v)
                print("Drone {} saw drone {}!".format(self.num, v))
        return near

    def process_map(self, unprocessed_map, offset=(0, 0)):
        offset_x = offset[0]
        offset_y = offset[1]
        new_map = {}
        for dir in unprocessed_map:
            adjusted_x  = dir[0] + offset_x
            adjusted_y = dir[1] + offset_y
            adjusted_loc = (adjusted_x, adjusted_y)
            if adjusted_loc != (0, 0):
                new_map[adjusted_loc] = unprocessed_map[dir]
        return new_map

    def find_object(self, map, id):
        for k, v in map.items():
            if v[0] == id:
                return k
        raise RuntimeError("Could not find key {} in map {}".format(id, map))

    def update_map(self, map):
        for dir in map:
            self.map[(dir[0], dir[1])] = (map[dir], self.t)

    def combine_maps(self, unprocessed_map, num):
        my_pos_to_them = self.find_object(unprocessed_map, str(self.num))
        their_pos = self.find_object(unprocessed_map, 'M')
        # Update their location to have their ID, instead of 'M'.
        unprocessed_map[their_pos] = [str(num), unprocessed_map[their_pos][1]]

        offset_x = self.x - my_pos_to_them[0]
        offset_y = self.y - my_pos_to_them[1]

        map = self.process_map(unprocessed_map, (offset_x, offset_y))
        for dir in map:
            if not dir in self.map or map[dir][1] > self.map[dir][1]:
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
