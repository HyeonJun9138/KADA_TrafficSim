import math
import heapq

def dijkstra(nodes, links, start, goal):
    """
    nodes: dict of {node: [x, y]}
    links: dict of {node: [인접 node들]} - 각 간선의 거리는 10m로 고정.
    start, goal: 시작, 목표 노드 키
    반환: start부터 goal까지의 최단 경로 (노드 리스트). 경로가 없으면 빈 리스트.
    """
    queue = []
    heapq.heappush(queue, (0, start, [start]))
    visited = set()

    while queue:
        cost, current, path = heapq.heappop(queue)
        if current == goal:
            return path
        if current in visited:
            continue
        visited.add(current)
        for neighbor in links.get(current, []):
            if neighbor in visited:
                continue
            # 각 간선 비용은 10m
            heapq.heappush(queue, (cost + 10, neighbor, path + [neighbor]))
    return []
