
class Drone():

    def __init__(self, num):
        self.num = num
        self.x = 0
        self.y = 0
        self.map = {(0, 0): "M"}

    def move(self, map):
        return (1, 0)

    def __hash__(self):
        return self.num

    def __eq__(self, other):
        return self.num == other.num
