from dijkstra import dijkstra
import math

class UAMPlane:
    def __init__(
        self, name, origin_vp, dest_vp, departure_time,
        ground_speed=1.34, air_speed=1.34, flight_plan=None
    ):
        """
        flight_plan: 방문할 Vertiport 인스턴스 리스트 (출발지 제외 후 마지막에 origin 복귀)
        """
        self.name = name

        # "다음 운항" 계획을 위해 저장 (필요 없으면 삭제 가능)
        self.origin_vp = origin_vp
        self.dest_vp   = dest_vp

        # === 이번 (현재) 운항에서 쓰는 출발/도착 ===
        self.flight_origin = origin_vp  
        self.flight_dest   = dest_vp

        self.departure_time = departure_time
        self.ground_speed = ground_speed
        self.air_speed = air_speed
        self.flight_plan = flight_plan[:] if flight_plan else []

        # === 초기 상태: flight_origin의 Gate에서 대기 ===
        self.current_vp = self.flight_origin
        self.gate_assigned = self.current_vp.request_gate(self)
        if self.gate_assigned is not None:
            self.current_pos = self.current_vp.gates[self.gate_assigned]["pos"]
        else:
            self.current_pos = (0, 0)

        self.state = "at_gate"
        self.ground_route_nodes = []
        self.ground_route_positions = []
        self.current_ground_index = 0
        self.in_air_route = []
        self.air_progress = 0.0

    def plan_ground_route(self, vp, start_node, goal_node):
        route_nodes = dijkstra(vp.nodes, vp.links, start_node, goal_node)
        route_positions = []
        for node in route_nodes:
            base = vp.nodes[node]
            pos = (base[0] + vp.offset[0], base[1] + vp.offset[1])
            route_positions.append(pos)
        return route_nodes, route_positions

    def update(self, dt, current_time):
        if self.state == "at_gate":
            # 게이트 재할당 시도
            if self.gate_assigned is None:
                new_gate = self.current_vp.request_gate(self)
                if new_gate is None:
                    return
                self.gate_assigned = new_gate
                self.current_pos = self.current_vp.gates[new_gate]["pos"]

            if current_time >= self.departure_time:
                gate_name = self.gate_assigned
                self.current_vp.release_gate(self)
                # 여기서는 flight_origin의 ground map을 사용하여, Gate → FATO_Takeoff 경로 계산
                self.ground_route_nodes, self.ground_route_positions = self.plan_ground_route(
                    self.flight_origin, gate_name, "FATO_Takeoff"
                )
                self.current_ground_index = 0
                self.flight_origin.reserve_node(self, self.ground_route_nodes[0])
                self.state = "takeoff_ground"

        elif self.state == "takeoff_ground":
            vp = self.flight_origin
            if self.current_ground_index < len(self.ground_route_positions) - 1:
                next_node = self.ground_route_nodes[self.current_ground_index + 1]
                if vp.node_occupancy.get(next_node) in [None, self]:
                    if vp.node_occupancy.get(next_node) is None:
                        vp.reserve_node(self, next_node)
                    target_pos = self.ground_route_positions[self.current_ground_index + 1]
                    self.current_pos = self.move_towards(self.current_pos, target_pos, self.ground_speed, dt)
                    if self.reached(self.current_pos, target_pos):
                        prev_node = self.ground_route_nodes[self.current_ground_index]
                        vp.release_node(self, prev_node)
                        self.current_ground_index += 1
            else:
                vp.release_node(self, self.ground_route_nodes[self.current_ground_index])
                # in_air 경로는 flight_origin의 FATO_Takeoff → flight_dest의 FATO_Landing 사용
                start_pt = (vp.nodes["FATO_Takeoff"][0] + vp.offset[0],
                            vp.nodes["FATO_Takeoff"][1] + vp.offset[1])
                end_pt = (self.flight_dest.nodes["FATO_Landing"][0] + self.flight_dest.offset[0],
                        self.flight_dest.nodes["FATO_Landing"][1] + self.flight_dest.offset[1])
                self.in_air_route = [start_pt, end_pt]
                self.air_progress = 0.0
                self.state = "in_air"

        elif self.state == "in_air":
            total_dist = self.distance(*self.in_air_route)
            if total_dist <= 0:
                self.air_progress = 1.0
            else:
                self.air_progress += (self.air_speed * dt) / total_dist

            if self.air_progress >= 1.0:
                self.air_progress = 1.0
                self.current_pos = self.in_air_route[1]
                # flight_dest의 Gate 할당 (새로운 운항 전까지 고정)
                gate_name = None
                for g in self.flight_dest.gates.keys():
                    if self.flight_dest.gates[g]["occupied"] is None:
                        gate_name = g
                        break
                if gate_name is None:
                    return  # Gate 대기
                self.flight_dest.gates[gate_name]["occupied"] = self
                self.flight_dest.reserve_node(self, gate_name)
                self.gate_assigned = gate_name
                self.current_vp = self.flight_dest
                # flight_dest의 ground map에서 FATO_Landing → Gate 경로 계산
                self.ground_route_nodes, self.ground_route_positions = self.plan_ground_route(
                    self.flight_dest, "FATO_Landing", gate_name
                )
                self.current_ground_index = 0
                self.state = "landing_ground"
            else:
                start_pt, end_pt = self.in_air_route
                self.current_pos = self.lerp(start_pt, end_pt, self.air_progress)

        elif self.state == "landing_ground":
            vp = self.flight_dest
            if self.gate_assigned is None:
                new_gate = vp.request_gate(self)
                if new_gate is None:
                    return
                self.gate_assigned = new_gate

            if self.current_ground_index < len(self.ground_route_positions) - 1:
                next_node = self.ground_route_nodes[self.current_ground_index + 1]
                if vp.node_occupancy.get(next_node) in [None, self]:
                    if vp.node_occupancy.get(next_node) is None:
                        vp.reserve_node(self, next_node)
                    target_pos = self.ground_route_positions[self.current_ground_index + 1]
                    self.current_pos = self.move_towards(self.current_pos, target_pos, self.ground_speed, dt)
                    if self.reached(self.current_pos, target_pos):
                        prev_node = self.ground_route_nodes[self.current_ground_index]
                        vp.release_node(self, prev_node)
                        self.current_ground_index += 1
            else:
                gate_pos = vp.gates[self.gate_assigned]["pos"]
                if self.reached(self.current_pos, gate_pos):
                    # 착륙 완료: 다음 운항 준비
                    if self.flight_plan:
                        # **중요**: 이번 운항이 끝났으므로, 새로운 운항을 위해 flight_origin과 flight_dest를 갱신하고,
                        # current_vp도 새 flight_origin의 ground 좌표계를 사용하도록 업데이트
                        self.flight_origin = self.flight_dest
                        self.flight_dest = self.flight_plan.pop(0)
                        self.current_vp = self.flight_origin  # 갱신!
                        new_gate = self.flight_origin.request_gate(self)
                        if new_gate is None:
                            return
                        self.gate_assigned = new_gate
                        self.current_pos = self.flight_origin.gates[new_gate]["pos"]
                        self.departure_time = current_time + 180
                        self.ground_route_nodes.clear()
                        self.ground_route_positions.clear()
                        self.current_ground_index = 0
                        self.state = "at_gate"
                    else:
                        self.state = "done"
                else:
                    self.current_pos = self.move_towards(self.current_pos, gate_pos, self.ground_speed, dt)


    # -------------------------- 보조 메서드들 --------------------------
    def move_towards(self, current, target, speed, dt):
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        dist = math.hypot(dx, dy)
        if dist == 0:
            return target
        step = speed * dt
        if step >= dist:
            return target
        ratio = step / dist
        return (current[0] + dx * ratio, current[1] + dy * ratio)

    def reached(self, current, target, tol=0.5):
        return self.distance(current, target) < tol

    def distance(self, a, b):
        return math.hypot(a[0]-b[0], a[1]-b[1])

    def lerp(self, a, b, t):
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
