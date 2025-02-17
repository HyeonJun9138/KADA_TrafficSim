import math

class UAMPlane:
    def __init__(self, name, initial_port, flight_plan, departure_time, speed=100):
        self.name = name                           # "UAM-1" ~ "UAM-16"
        self.initial_port = initial_port           # 출발 vertiport (Vertiport 인스턴스)
        self.current_port = initial_port           # 현재 위치한 vertiport (착륙 시 업데이트)
        self.current_position = initial_port.position  # 현재 좌표
        self.flight_plan = flight_plan[:]          # 방문할 vertiport 리스트 (순서대로; 모두 방문 후 복귀)
        self.departure_time = departure_time       # 출발 시각 (초 단위; 초기에는 순차적으로 출발)
        self.speed = speed                         # 단위 초당 이동 거리
        self.state = 'at_gate'                     # 초기 상태: gate에 대기
        self.target = None                         # 이동 목표 vertiport

    def update(self, dt, current_time):
        if self.state == 'at_gate':
            # 출발 시각이 도래하면 gate에서 이륙 준비 (gate 해제 후 moving 상태로 전환)
            if current_time >= self.departure_time:
                if self.current_port:
                    self.current_port.release_gate(self)
                if self.flight_plan:
                    self.target = self.flight_plan.pop(0)
                    self.state = 'moving'
                else:
                    self.state = 'done'
            return

        if self.state == 'moving':
            dx = self.target.position[0] - self.current_position[0]
            dy = self.target.position[1] - self.current_position[1]
            distance = math.hypot(dx, dy)
            if distance == 0:
                # 목적지 도착: 도착 vertiport에서 gate에 배정 및 대기
                self.current_position = self.target.position
                self.current_port = self.target
                self.current_port.assign_gate(self)
                self.state = 'at_gate'
                # 도착 후 3분(180초) 대기 후 이륙 준비
                self.departure_time = current_time + 180
                return
            direction = (dx / distance, dy / distance)
            travel_distance = self.speed * dt
            if travel_distance >= distance:
                self.current_position = self.target.position
                self.current_port = self.target
                self.current_port.assign_gate(self)
                self.state = 'at_gate'
                self.departure_time = current_time + 180
            else:
                self.current_position = (
                    self.current_position[0] + direction[0] * travel_distance,
                    self.current_position[1] + direction[1] * travel_distance,
                )
