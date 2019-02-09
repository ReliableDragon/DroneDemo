import tkinter as tk
import random
import sys

from drone import Drone

class Driver(tk.Canvas):

    NUM_DRONES = 5
    TURN_TIME = 1000
    X_DIM = 10
    Y_DIM = 10

    HEIGHT = 600
    WIDTH = 600

    graphics = {}
    drones = []
    board = {(1, 3): "X", (4, 2): "X", (2, 4): "X"}

    drones_made = 0

    def __init__(self, root):
        tk.Canvas.__init__(self, root, bg='#FFFFFF', bd=0, height=self.HEIGHT, width=self.WIDTH, highlightthickness=0)
        self.pack()
        self.start()

    def start(self):
        draw_lines()

        build_drones()

        create_graphics()

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
            while tries == 0 or (tries < 10 and self.crashed(drone)):
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

        for obstacle in board:
            if board[obstable] == "X":
                self.graphics[obstacle] =
                    self.create_oval(
                        *self.get_drone_draw_pos(*obstacle)[0], fill="#4444ff")

        for drone in drones:
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
        new_board = copy(self.board)
        self.move_drones(new_board)

        self.commit_drones(new_board)

        self.board = new_board
        self.draw()

    def move_drones(self, new_board):
        for drone in self.drones:
            map = {}
            directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
            for d in directions:
                char = 'O'
                if (drone.x + d[0], drone.y + d[1]) in self.board:
                    char = 'X'
                map[d] = char
            move = drone.move(map)
            del new_board[(drone.x, drone.y)]
            drone.x += move[0]
            drone.y += move[1]

    def commit_drones(self, new_board):
        for drone in list(self.drones.keys()):
            if self.crashed(drone):
                for i in self.graphics[drone]:
                    self.delete(i)
                del self.board[(drone.x, drone.y)]
                del self.graphics[drone]
                del self.drones[drone].drone
                del self.drones[drone]
            new_board[(drone.x, drone.y)] = "D"

    def draw(self):
        for drone in self.graphics:
            drone_draw_pos = self.get_drone_draw_pos(drone)
            self.coords(self.graphics[drone][0], *drone_draw_pos[0])
            self.coords(self.graphics[drone][1], *drone_draw_pos[1])
        self.after(self.TURN_TIME, self.update)

    def get_drone_draw_pos(self, drone):
        rect_width = self.WIDTH / self.X_DIM
        rect_height = self.HEIGHT / self.Y_DIM
        drone_x_mid = (drone.x + 0.5) * rect_width
        drone_y_mid = (drone.y + 0.5) * rect_height

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

    def crashed(self, drone):
        # Check for collisions
        if (drone.x, drone.y) in self.board:
            object_present = self.board[drone.x, drone.y]
            if object_present == "X":
                print("Drone {} crashed into an obstacle!".format(drone.num))
                return True
            elif object_present != str(drone.drone.num):
                print("Drone {} crashed into drone {}!".format(drone.drone.num, object_present))
                return True

        # Check for out-of-bounds
        if (self.drones[drone].x < 0
          or self.drones[drone].y < 0
          or self.drones[drone].x >= self.X_DIM
          or self.drones[drone].y >= self.Y_DIM):
            print("Drone {} went out of bounds and crashed!".format(drone.num))
            return True

        return False

class AbsDrone():
    def __init__(self, drone, x, y):
        self.drone = drone
        self.x = x
        self.y = y
