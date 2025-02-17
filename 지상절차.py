# 상태 전이만 모아놓은 예시 코드입니다.

def manage_ground_procedure(self, uam, simulation_time):
    if uam.current_state == "착륙 완료":
        # 착륙 후 시동 종료 절차로 진입
        simulation_time = self.perform_shutdown_procedure(uam, simulation_time)

    elif uam.current_state == "시동 종료 및 견인 장비 연결 중":
        # 시동 종료 절차 진행 중 계속 상태 유지 확인
        simulation_time = self.perform_shutdown_procedure(uam, simulation_time)

    elif uam.current_state == "시동 종료 및 견인 장비 연결 완료":
        # 착륙 Que로 이동할 경로가 정해지면 상태 전이
        uam.update_state("착륙 Que로 이동 중", simulation_time)

    elif uam.current_state == "착륙 Que로 이동 중":
        # 경로 이동 후 최종 Que(4번 노드)에 도달하면 상태 전이
        if uam.current_node == "4":
            uam.update_state("최종 Que 도착", simulation_time)
        else:
            # 착륙 Que 상에서 다음 Que 노드로 이동
            uam.update_state("착륙 Que로 이동 중", simulation_time)

    elif uam.current_state == "최종 Que 도착":
        # Gate가 비어있지 않으면 대기, 비어있으면 Gate로 이동 준비
        # (조건에 따라 두 가지 상태 중 하나로 전이)
        uam.update_state("Gate 대기 중", simulation_time)
        # 또는
        uam.update_state("Gate로 이동 준비 완료", simulation_time)

    elif uam.current_state == "Gate 대기 중":
        # 대기 중 Gate가 비면 이동 준비
        uam.update_state("Gate로 이동 준비 완료", simulation_time)

    elif uam.current_state == "Gate로 이동 준비 완료":
        # 실제 경로 이동 (move_along_path) 후 Gate에 도착하면 상태 전이
        pass  # 이동 자체는 다른 함수에서 처리

    elif uam.current_state == "Gate 도착":
        # Gate에 도착한 뒤 승객 하차 및 지상 조업
        uam.update_state("승객 하차 및 지상 조업 중", simulation_time)

    elif uam.current_state == "승객 하차 및 지상 조업 중":
        # 지상 조업이 끝나면 출발 준비 완료
        uam.update_state("출발 준비 완료", simulation_time)

    elif uam.current_state == "출발 준비 완료":
        # 이륙 Que로 이동할 경로가 정해지면 상태 전이
        uam.update_state("Take_off Que로 이동 중", simulation_time)

    elif uam.current_state == "Take_off Que로 이동 중":
        # 최종적으로 31번 노드 도착 시 이륙 Que 대기로 전이
        if uam.current_node == "31":
            uam.update_state("이륙 Que 대기중", simulation_time)
        else:
            # 중간 Que 이동 중 계속 상태 유지
            uam.update_state("Take_off Que로 이동 중", simulation_time)

    elif uam.current_state == "이륙 Que 대기중":
        # 이륙 지점(FATO_Takeoff)이 비면 이동 시작
        uam.update_state("FATO_Takeoff로 이동 중", simulation_time)

    elif uam.current_state == "FATO_Takeoff로 이동 중":
        # FATO_Takeoff 노드에 도착하면 시동 모드로 전환
        if uam.current_node == "FATO_Takeoff":
            uam.update_state("시동 모드", simulation_time)

    elif uam.current_state == "시동 모드":
        # 일정 시간 후 시동 중으로 상태 전이
        uam.update_state("시동 중", simulation_time)

    elif uam.current_state == "시동 중":
        # 시동 시간이 지나면 이륙 준비 완료 상태로 전이
        if simulation_time >= uam.operation_end_time:
            uam.update_state("이륙 준비 완료", simulation_time)

    elif uam.current_state == "이륙 준비 완료":
        # FATO_Takeoff 해제 후 UATM으로 비행 시작을 알리고 상태 전이
        uam.update_state("outbound 비행 중", simulation_time)


def move_along_path(self, uam, path, simulation_time):
    # 경로 이동 후 Gate에 최종 도착 시 상태 전이
    current_node = uam.current_node
    # next_node가 없고 현재 노드가 GATE면 Gate 도착 상태로 전환
    if len(path) == 1 and current_node.startswith("GATE"):
        uam.update_state("Gate 도착", simulation_time)
    return simulation_time


def perform_shutdown_procedure(self, uam, simulation_time):
    # 이미 완료 상태라면 그대로 반환
    if uam.current_state == "시동 종료 및 견인 장비 연결 완료":
        return simulation_time

    # 견인 장비 연결 중 상태가 아니었다면 연결 중으로 전환
    if uam.current_state != "시동 종료 및 견인 장비 연결 중":
        uam.update_state("시동 종료 및 견인 장비 연결 중", simulation_time)

    # 장비 연결 완료 시간이 지났다면 완료 상태로 전환
    if simulation_time >= uam.node_arrival_time:
        uam.update_state("시동 종료 및 견인 장비 연결 완료", simulation_time)

    return simulation_time
