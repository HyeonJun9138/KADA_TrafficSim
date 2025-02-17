class SimulationEngine:
    def __init__(self, planes, time_step=0.1, acceleration=1):
        """
        planes: UAMPlane 인스턴스 리스트
        time_step: 실제 업데이트 지연 (초)
        acceleration: 시뮬레이션 배속 (dt에 곱해짐)
        """
        self.planes = planes
        self.time_step = time_step
        self.acceleration = acceleration
        self.simulation_time = 0

    def update(self):
        dt = self.time_step * self.acceleration
        self.simulation_time += dt
        for plane in self.planes:
            if plane.state != "done":
                plane.update(dt, self.simulation_time)
