import time
from vertiport import Vertiport
from uam_plane import UAMPlane
from simulation_engine import SimulationEngine

def create_simulation():
    # 4개 버티포트 생성 (ground map: offset, airspace: 중심 좌표)
    vp_A = Vertiport("Vertiport A", position=(5, 30), offset=(0,0))
    vp_B = Vertiport("Vertiport B", position=(25, 30), offset=(30,0))
    vp_C = Vertiport("Vertiport C", position=(5, 5), offset=(0,30))
    vp_D = Vertiport("Vertiport D", position=(25, 5), offset=(30,30))
    vertiports = [vp_A, vp_B, vp_C, vp_D]

    planes = []
    for origin in vertiports:
        # flight_plan: origin 제외한 나머지 버티포트 순서대로, 마지막에 origin 복귀
        flight_plan = [vp for vp in vertiports if vp != origin] + [origin]
        for i in range(4):
            departure_time = i * 60  # 60초 간격
            plane = UAMPlane(
                name=f"UAM-{len(planes)+1}",
                origin_vp=origin,
                dest_vp=flight_plan[0],
                departure_time=departure_time,
                flight_plan=flight_plan
            )
            planes.append(plane)
    return planes, vertiports




def main():
    planes, vertiports = create_simulation()
    engine = SimulationEngine(planes, time_step=0.1, acceleration=1)
    
    while any(p.state != "done" for p in planes):
        engine.update()
        if int(engine.simulation_time) % 60 == 0:
            print(f"시뮬레이션 시간: {engine.simulation_time:.1f} 초")
            for p in planes:
                print(f"{p.name}: 상태 {p.state}, 위치 {p.current_pos}")
        time.sleep(engine.time_step)
    print("시뮬레이션 완료.")

if __name__ == "__main__":
    main()
