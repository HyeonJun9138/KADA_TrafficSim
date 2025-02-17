import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from vertiport import Vertiport
from uam_plane import UAMPlane
from simulation_engine import SimulationEngine
import itertools

COLORS = ['blue','red','green','orange','purple','brown',
          'cyan','magenta','yellow','black','lime','pink',
          'teal','lavender','turquoise','gold']

def create_simulation():
    vp_A = Vertiport("Vertiport A", position=(5, 30), offset=(0,0))
    vp_B = Vertiport("Vertiport B", position=(25, 30), offset=(30,0))
    vp_C = Vertiport("Vertiport C", position=(5, 5),  offset=(0,30))
    vp_D = Vertiport("Vertiport D", position=(25, 5), offset=(30,30))
    vertiports = [vp_A, vp_B, vp_C, vp_D]

    planes = []
    color_cycle = itertools.cycle(COLORS)

    for origin in vertiports:
        # flight_plan: origin 제외한 나머지 3개 + origin 복귀
        flight_plan = [vp for vp in vertiports if vp != origin] + [origin]
        for i in range(4):
            departure_time = i*5
            plane = UAMPlane(
                name=f"UAM-{len(planes)+1}",
                origin_vp=origin,
                dest_vp=flight_plan[0],
                departure_time=departure_time,
                flight_plan=flight_plan
            )
            plane.color = next(color_cycle)
            planes.append(plane)

    return planes, vertiports

def draw_ground(ax, vp):
    for node, neighbors in vp.links.items():
        x0 = vp.nodes[node][0] + vp.offset[0]
        y0 = vp.nodes[node][1] + vp.offset[1]
        for nb in neighbors:
            x1 = vp.nodes[nb][0] + vp.offset[0]
            y1 = vp.nodes[nb][1] + vp.offset[1]
            ax.plot([x0,x1],[y0,y1],c="gray",lw=0.5)
    for node, coord in vp.nodes.items():
        x, y = coord[0]+vp.offset[0], coord[1]+vp.offset[1]
        ax.plot(x, y, 'ko', ms=3)
    # gate들
    for gate, info in vp.gates.items():
        gx, gy = info["pos"]
        ax.plot(gx, gy, 'rs', ms=6)
        ax.text(gx+0.5, gy+0.5, gate, fontsize=6, color="red")

def main():
    planes, vertiports = create_simulation()
    engine = SimulationEngine(planes, time_step=0.1, acceleration=3)

    fig, axs = plt.subplots(2,3, figsize=(12,8))
    ax_A = axs[0,0]
    ax_B = axs[0,1]
    ax_C = axs[1,0]
    ax_D = axs[1,1]
    ax_air = axs[0,2]
    axs[1,2].axis('off')

    ground_axes = {}
    for ax, vp in zip([ax_A, ax_B, ax_C, ax_D], vertiports):
        ax.set_title(vp.name+"(Ground)")
        draw_ground(ax, vp)
        ax.set_xlim(-5+vp.offset[0], 25+vp.offset[0])
        ax.set_ylim(-5+vp.offset[1], 25+vp.offset[1])
        ground_axes[vp.name] = ax

    ax_air.set_title("Airspace")
    ax_air.set_xlim(0,30)
    ax_air.set_ylim(0,35)

    # airspace 내 버티포트 위치(초록 사각)
    for vp in vertiports:
        ax_air.plot(vp.position[0], vp.position[1], marker='s', ms=10, color='green', zorder=2)
        ax_air.text(vp.position[0]+0.5, vp.position[1]+0.5, vp.name, fontsize=9, color='green', zorder=2)

    # ground scatter
    scat_ground = {}
    for vp in vertiports:
        scat_ground[vp.name] = ground_axes[vp.name].scatter([],[], s=50, c='blue', zorder=3)

    occ_scats = {}
    for vp in vertiports:
        occ_scats[vp.name] = ground_axes[vp.name].scatter([],[], s=100, marker='x', zorder=5)

    scat_air_depart = ax_air.scatter([],[], s=50, c='blue', marker='o', zorder=4)
    scat_air_arrive = ax_air.scatter([],[], s=50, c='cyan', marker='o', zorder=1)

    ground_lines = {}

    def update(frame):
        engine.update()

        ground_positions = {vp.name:[] for vp in vertiports}
        air_depart_positions = []
        air_arrive_positions = []
        new_ground_routes = {}

        for p in planes:
            # 이륙 전/중인 경우
            if p.state in ["at_gate","takeoff_ground"]:
                # subplot은 이번 운항 출발지 flight_origin
                home_name = p.flight_origin.name
                ground_positions[home_name].append(p.current_pos)
                # 공역에서도 flight_origin.position 찍어준다
                air_depart_positions.append(p.flight_origin.position)

                if p.state=="takeoff_ground" and p.ground_route_positions:
                    route = [p.current_pos]+p.ground_route_positions[p.current_ground_index+1:]
                    new_ground_routes[p.name] = route

            elif p.state=="in_air":
                # 공역 보간
                t = p.air_progress
                ox, oy = p.flight_origin.position
                dx, dy = p.flight_dest.position
                px = ox+(dx-ox)*t
                py = oy+(dy-oy)*t
                air_depart_positions.append((px,py))

            elif p.state=="landing_ground":
                # subplot은 이번 운항 목적지 flight_dest
                home_name = p.flight_dest.name
                ground_positions[home_name].append(p.current_pos)
                # 공역에서는 flight_dest.position 찍어준다
                air_arrive_positions.append(p.flight_dest.position)

                if p.ground_route_positions:
                    route = [p.current_pos]+p.ground_route_positions[p.current_ground_index+1:]
                    new_ground_routes[p.name] = route

        # ground scatter
        for vp in vertiports:
            arr = ground_positions[vp.name]
            scat_ground[vp.name].set_offsets(np.array(arr) if arr else np.empty((0,2)))

            # 점유 노드
            occX, occY, occColors = [],[],[]
            for node, occupant in vp.node_occupancy.items():
                if occupant is not None:
                    bx = vp.nodes[node][0]+vp.offset[0]
                    by = vp.nodes[node][1]+vp.offset[1]
                    occX.append(bx)
                    occY.append(by)
                    occColors.append(occupant.color)
            occ_scats[vp.name].set_offsets(np.column_stack((occX, occY)) if occX else np.empty((0,2)))
            if occColors:
                occ_scats[vp.name].set_color(occColors)

        # air scatter
        if air_depart_positions:
            scat_air_depart.set_offsets(np.array(air_depart_positions))
        else:
            scat_air_depart.set_offsets(np.empty((0,2)))

        if air_arrive_positions:
            scat_air_arrive.set_offsets(np.array(air_arrive_positions))
        else:
            scat_air_arrive.set_offsets(np.empty((0,2)))

        # ground route line
        for line in ground_lines.values():
            line.remove()
        ground_lines.clear()

        for p in planes:
            if p.name in new_ground_routes:
                route = new_ground_routes[p.name]
                # 현재 상태에 따라 subplot 결정
                if p.state in ["at_gate","takeoff_ground"]:
                    ax = ground_axes[p.flight_origin.name]
                elif p.state=="landing_ground":
                    ax = ground_axes[p.flight_dest.name]
                else:
                    continue

                xs = [pt[0] for pt in route]
                ys = [pt[1] for pt in route]
                lineObj, = ax.plot(xs, ys, color=p.color, lw=2, zorder=4)
                ground_lines[p.name] = lineObj

        return list(scat_air_depart.get_offsets()) + list(scat_air_arrive.get_offsets())

    ani = animation.FuncAnimation(fig, update, frames=600, interval=50, blit=False)
    plt.tight_layout()
    plt.show()

if __name__=="__main__":
    main()
