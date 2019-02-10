import tkinter as tk
import random
import sys

from drone import Drone

class Driver(tk.Canvas):

    NUM_DRONES = 20
    TURN_TIME = 100
    X_DIM = 10
    Y_DIM = 10

    HEIGHT = 600
    WIDTH = 600

    graphics = {}
    obstacle_graphics = {}
    drones = []
    board = {(1, 3): "X", (4, 2): "X", (2, 4): "X", (9, 4): "X", (9, 8): "X"}

    drones_made = 0

    def __init__(self, root):
        tk.Canvas.__init__(self, root, bg='#FFFFFF', bd=0, height=self.HEIGHT, width=self.WIDTH, highlightthickness=0)
        self.pack()
        self.start()

    def start(self):
        self.draw_lines()

        self.build_drones()

        self.create_graphics()

        print("Visualizations created. Starting simulation.")
        self.after(self.TURN_TIME, self.update)

    def draw_lines(self):
        print("Drawing board.")
        for i in range(1, self.X_DIM):
            x_loc = i * self.WIDTH / self.X_DIM
            self.create_line(
                x_loc,
                0,
                x_loc,
                self.HEIGHT)
        for i in range(1, self.Y_DIM):
            y_loc = i * self.HEIGHT / self.Y_DIM
            self.create_line(
                0,
                y_loc,
                self.WIDTH,
                y_loc)

    def build_drones(self):
        print("Building drones.")
        for i in range(self.NUM_DRONES):
            tries = 0
            while (tries == 0 or (tries < 10 and
                  (self.drone_collision(drone) or self.obstacle_crash(drone)))):
                tries += 1
                drone = AbsDrone(
                    Drone(self.drones_made),
                    random.randint(0, self.X_DIM-1),
                    random.randint(0, self.Y_DIM-1))

            self.board[(drone.x, drone.y)] = str(drone.drone.num)
            self.drones.append(drone)
            self.drones_made += 1

    def create_graphics(self):
        print("Drones built. Creating visualizations.")

        for obstacle in self.board:
            if self.board[obstacle] == "X":
                self.obstacle_graphics[obstacle] = self.create_oval(
                    *self.get_rect_and_mid(*obstacle)[0], fill="#4444ff")

        for drone in self.drones:
            drone_draw_pos = self.get_drone_draw_pos(drone)
            d_rect = self.create_rectangle(
                *drone_draw_pos[0],
                fill = 'red')
            d_text = self.create_text(
                *drone_draw_pos[1],
                text=str(drone.drone.num),
                font=('arial', 28))
            self.graphics[drone] = (d_rect, d_text)

    def update(self):
        new_board = self.board.copy()
        # Clear all drones from board, to avoid
        for k in list(new_board):
            if new_board[k] != "X":
                del new_board[k]

        # Use list() to allow modification during iteration, in case of crash.
        for drone in list(self.drones):
            map = self.make_map(drone)

            move = drone.drone.update(map, self.send_message)

            drone.x += move[0]
            drone.y += move[1]
            if self.obstacle_crash(drone):
                self.destroy_drone(drone)
            else:
                # Note later drones can overwrite earlier ones here. This is
                # semi-intentional, and the collision method ensures that all
                # drones except the one with current claim to the tile will
                # crash, which seems reasonable.
                new_board[(drone.x, drone.y)] = str(drone.drone.num)
        self.board = new_board
        for drone in list(self.drones):
            if self.drone_collision(drone):
                self.destroy_drone(drone)

        self.draw()

    def send_message(self, to):
        return self.get_drone(to).msg

    def make_map(self, drone):
        map = {}
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, 1),
            (1, -1), (-1, -1), (0, 2), (0, -2), (2, 0), (-2, 0)]
        for d in directions:
            char = 'O'
            new_x = drone.x + d[0]
            new_y = drone.y + d[1]
            if (new_x >= self.X_DIM or new_y >= self.Y_DIM
            or new_x < 0 or new_y < 0):
                char = 'X'
            if (new_x, new_y) in self.board:
                char = self.board[(new_x, new_y)]
            map[d] = char
        return map

    def get_drone(self, n):
        drone = list(filter(lambda d: d.num == int(n), [d.drone for d in self.drones]))
        if not drone:
            self.debug_dump(drone = drone)
            raise RuntimeError("Could not find drone #{}".format(n))
        else:
            return drone[0]

    def draw(self):
        for drone in self.graphics:

            drone_draw_pos = self.get_drone_draw_pos(drone)
            self.coords(self.graphics[drone][0], *drone_draw_pos[0])
            self.coords(self.graphics[drone][1], *drone_draw_pos[1])
        self.after(self.TURN_TIME, self.update)

    def get_drone_draw_pos(self, drone):
        return self.get_rect_and_mid(drone.x, drone.y)

    def get_rect_and_mid(self, x, y):
        rect_width = self.WIDTH / self.X_DIM
        rect_height = self.HEIGHT / self.Y_DIM
        drone_x_mid = (x + 0.5) * rect_width
        drone_y_mid = (y + 0.5) * rect_height

        d_rect = (
            drone_x_mid - 0.4 * rect_width,
            drone_y_mid - 0.4 * rect_height,
            drone_x_mid + 0.4 * rect_width,
            drone_y_mid + 0.4 * rect_height,
            )
        d_text = (
            drone_x_mid,
            drone_y_mid,
            )
        return (d_rect, d_text)

    def obstacle_crash(self, drone):
        # Check for collisions
        drone_loc = (drone.x, drone.y)
        if drone_loc in self.board:
            object_present = self.board[drone_loc]
            if object_present == "X":
                print("Drone {} crashed into an obstacle at {}!"
                    .format(drone.drone.num, drone_loc))
                return True

        # Check for out-of-bounds
        if (drone.x < 0 or drone.y < 0
            or drone.x >= self.X_DIM or drone.y >= self.Y_DIM):
            print("Drone {} went out of bounds at {} and crashed!"
                .format(drone.drone.num, drone_loc))
            return True

        return False

    def drone_collision(self, drone):
        # Check for collisions
        for d in self.drones:
            if ((drone.x, drone.y) == (d.x, d.y)
                and drone.drone.num != d.drone.num):
                # All drones except the last one to move into a tile crash.
                if self.board[(drone.x, drone.y)] != str(drone.drone.num):
                    print("Drone {} crashed into drone {}!"
                        .format(drone.drone.num, d.drone.num))
                    print("Absolute position: {}".format((drone.x, drone.y)))
                    drone.drone.print_map()
                    print("It had choreographs of {}"
                        .format(drone.drone.choreographed_moves))

                    return True

        return False

    def destroy_drone(self, drone):
        print("Destroying drone {}!".format(drone.drone.num))
        for i in self.graphics[drone]:
            self.delete(i)
        del self.graphics[drone]
        self.drones.remove(drone)
        drone_loc = (drone.x, drone.y)
        if (drone_loc in self.board
          and self.board[drone_loc] == str(drone.drone.num)):
            del self.board[drone_loc]

    def debug_dump(self, **kwargs):
        print("Board: {}\n".format(self.board))
        print("Drones: {}\n".format([str(d) for d in self.drones]))
        print("Drone Graphics: {}\n".format(
            ["{}: {}".format(str(d), v) for d, v in self.graphics.items()]))
        print("Obstacle Graphics: {}\n".format(self.obstacle_graphics))
        for k,v in kwargs.items():
            print("{}: {}\n".format(k, v))

class AbsDrone():
    def __init__(self, drone, x, y):
        self.drone = drone
        self.x = x
        self.y = y

    def __str__(self):
        return "#{}: ({}, {})".format(self.drone.num, self.x, self.y)
