import random
from plane import Plane

class Map:
    def __init__(self, width, height, num_planes=16):
        self.width = width
        self.height = height
        self.planes = self._init_planes(num_planes)

    def _init_planes(self, num_planes):
        planes = []
        for i in range(num_planes):
            init_position = (random.uniform(0, self.width), random.uniform(0, self.height))
            target = (random.uniform(0, self.width), random.uniform(0, self.height))
            speed = random.uniform(50, 150)  # 단위 시간당 속도
            planes.append(Plane(id=i, position=init_position, target=target, speed=speed))
        return planes
