from vertiport_2f6g import ground_nodes, ground_links, gates

class Vertiport:
    def __init__(self, name, position, offset=(0,0)):
        """
        name: 버티포트 이름 (예: "Vertiport A")
        position: 공역에서의 버티포트 중심 (시각화용)
        offset: ground map 좌표에 적용할 오프셋 (각 버티포트마다 다름)
        """
        self.name = name
        self.position = position
        self.offset = offset
        self.nodes = ground_nodes
        self.links = ground_links
        # Gate는 ground map상의 노드명으로 관리
        self.gates = {gate: {"occupied": None, "pos": (self.nodes[gate][0] + offset[0],
                                                         self.nodes[gate][1] + offset[1])}
                      for gate in gates}
        # 각 ground node의 점유 상태 (초기에는 모두 비어있음)
        self.node_occupancy = {node: None for node in self.nodes}

    def reserve_node(self, uam, node):
        """노드가 비어있으면 uam을 예약하고 True 반환, 아니면 False"""
        if self.node_occupancy.get(node) is None:
            self.node_occupancy[node] = uam
            return True
        return False

    def release_node(self, uam, node):
        """해당 노드에 uam이 점유 중이면 해제"""
        if self.node_occupancy.get(node) == uam:
            self.node_occupancy[node] = None
            return True
        return False

    def request_gate(self, uam):
        """Gate 중 비어있는 것을 찾아 할당; 할당되면 Gate 이름 반환, 아니면 None"""
        for gate_name, info in self.gates.items():
            if info["occupied"] is None:
                self.gates[gate_name]["occupied"] = uam
                # Gate 노드 점유도 함께 예약
                self.node_occupancy[gate_name] = uam
                return gate_name
        return None

    def release_gate(self, uam):
        """uAM이 할당받은 Gate를 해제"""
        for gate, info in self.gates.items():
            if info["occupied"] == uam:
                info["occupied"] = None
                self.node_occupancy[gate] = None
                return gate
        return None
