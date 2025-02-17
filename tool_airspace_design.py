import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk, simpledialog, messagebox, filedialog
import json
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# Matplotlib 한글 폰트(Windows: 맑은 고딕)
matplotlib.rcParams['font.family'] = 'Malgun Gothic'
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

###############################################################################
# 전역 데이터
###############################################################################
routes = []
vertiports = []

ROUTE_COLORS = [
    "red", "blue", "green", "orange", "purple",
    "brown", "cyan", "magenta", "gray", "navy"
]

class UAMMapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UAM 다중 경로 & 버티포트 설계")

        # 한글 폰트
        font_name = tkFont.Font(family="맑은 고딕", size=10)
        self.root.option_add("*Font", font_name)

        # 경로/버티포트 카운트
        self.route_count = 0
        self.vertiport_count = 0
        self.current_route_idx = None

        # 모드
        self.input_mode = "NODE"  # NODE, VERTIPORT, UPDATE_NODE
        self.temp_vertiport_type = None
        self.node_to_update = None

        # 지도/캔버스
        self.MAP_SIZE = 30_000   # (m)
        self.GRID_SIZE = 100     # (m)
        self.GRID_COUNT = self.MAP_SIZE // self.GRID_SIZE
        self.CANVAS_SIZE = 600
        self.zoom_level = 1.0  # 2D Canvas용 임의 Zoom 값

        # 우클릭 드래그로 Canvas를 이동하기 위한 내부 변수
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0

        # ---------------------------
        # Layout
        # ---------------------------
        # 상단(왼쪽/오른쪽) + 하단(테이블)
        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        #  하단 프레임(트리뷰)
        self.bottom_frame = tk.Frame(self.root)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # 왼/오른쪽 프레임
        self.left_frame = tk.Frame(self.top_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        self.right_frame = tk.Frame(self.top_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 2D Canvas
        self.canvas_2d = tk.Canvas(
            self.left_frame,
            width=self.CANVAS_SIZE,
            height=self.CANVAS_SIZE,
            bg="white"
        )
        self.canvas_2d.pack(padx=5, pady=5)

        # 좌클릭: 노드/버티포트 배치
        self.canvas_2d.bind("<Button-1>", self.on_canvas_click)
        # 마우스 휠: 확대/축소
        self.canvas_2d.bind("<MouseWheel>", self.on_mouse_wheel_2d)
        # 우클릭 드래그: 지도 이동(팬)
        self.canvas_2d.bind("<Button-3>", self.on_right_click_press)
        self.canvas_2d.bind("<B3-Motion>", self.on_right_click_drag)

        self.canvas_2d.bind("<Motion>", self.on_canvas_mouse_move)

        # 버튼들
        btn_frame = tk.Frame(self.left_frame)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="새 경로 추가",
                  command=self.create_new_route).grid(row=0, column=0, padx=5)

        tk.Button(btn_frame, text="2FATO-4GATE",
                  command=lambda: self.set_vertiport_input("2FATO-4GATE"))\
            .grid(row=0, column=1, padx=5)

        tk.Button(btn_frame, text="2FATO-6GATE",
                  command=lambda: self.set_vertiport_input("2FATO-6GATE"))\
            .grid(row=0, column=2, padx=5)

        # Clear 버튼
        tk.Button(btn_frame, text="Clear",
                  command=self.clear_all).grid(row=0, column=3, padx=5)

        # Load / Save 버튼
        tk.Button(btn_frame, text="Load",
                  command=self.load_data).grid(row=1, column=0, padx=5, pady=2)
        tk.Button(btn_frame, text="Save",
                  command=self.save_data).grid(row=1, column=1, padx=5, pady=2)

        # 3D Matplotlib
        self.fig = plt.Figure(figsize=(5, 5))
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_title("UAM 3D 항로 설계")
        # 3D에서 기본 마우스 인터랙션(줌/회전) 사용
        self.ax.mouse_init()

        self.canvas_3d = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas_3d_widget = self.canvas_3d.get_tk_widget()
        self.canvas_3d_widget.pack(fill=tk.BOTH, expand=True)

        # 트리뷰
        self.tree = ttk.Treeview(
            self.bottom_frame,
            columns=("route", "node", "x", "y", "z"),
            show="headings"
        )
        self.tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        for col in ("route", "node", "x", "y", "z"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=80)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        self.mouse_info_label = tk.Label(
            self.canvas_2d,
            bg="white",
            text="(x, y)",
            font=("맑은 고딕", 9),
            relief="solid",
            borderwidth=1
        )
        # 초기에는 숨겨도 되고, place_forget()하거나
        self.mouse_info_label.place(x=10, y=10)  # 일단 임의 위치에 두었다가
        # --------------------------------------------------------

        self.draw_grid()
        self.create_new_route()

    ############################################################################
    # 우클릭(드래그)로 2D 지도 이동
    ############################################################################
    def on_right_click_press(self, event):
        """우클릭 누를 때 위치 기록, Canvas scan_mark"""
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.canvas_2d.scan_mark(event.x, event.y)
        self.show_corner_coords()

    def on_right_click_drag(self, event):
        """우클릭 드래그 중 → Canvas scan_dragto 로 이동"""
        if not self.is_panning:
            return
        self.canvas_2d.scan_dragto(event.x, event.y, gain=1)
        self.show_corner_coords()

    # ------------------------------------------------------------------------
    # 마우스 이동 시 좌표 표시
    # ------------------------------------------------------------------------
    def on_canvas_mouse_move(self, event):
        # 스크롤 반영
        real_cx = self.canvas_2d.canvasx(event.x)
        real_cy = self.canvas_2d.canvasy(event.y)
        wx, wy = self.canvas_to_world(real_cx, real_cy)

        # 50단위 스냅
        sx = round(wx/50)*50
        sy = round(wy/50)*50

        # Label 배치(물리 위치는 event.x,event.y 기준)
        offset = 20
        self.mouse_info_label.place(x=event.x + offset, y=event.y + offset)
        self.mouse_info_label.config(text=f"({sx}, {sy})")

    ############################################################################
    # Clear (모든 데이터 삭제)
    ############################################################################
    def clear_all(self):
        routes.clear()
        vertiports.clear()
        self.route_count = 0
        self.vertiport_count = 0
        self.current_route_idx = None
        self.node_to_update = None
        self.input_mode = "NODE"
        # 화면 갱신
        self.draw_grid()
        self.refresh_all()

        # ★ 새 경로 자동 생성 (원한다면)
        self.create_new_route()

    ############################################################################
    # Load/Save (JSON)
    ############################################################################
    def load_data(self):
        """JSON 파일에서 routes, vertiports 로드"""
        global routes, vertiports
        filename = filedialog.askopenfilename(
            title="Load JSON",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not filename:
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 기존 데이터 비우고 다시 채움
            routes.clear()
            vertiports.clear()

            # 라우트 정보 복원
            routes_data = data.get("routes", [])
            for r in routes_data:
                # {name, node_count, nodes, links}
                new_r = {
                    "name": r["name"],
                    "node_count": r["node_count"],
                    "nodes": {},
                    "links": []
                }
                # nodes
                for k, nd in r["nodes"].items():
                    # k = "x,y" 형태 or just a string?
                    # 혹은 원래 (x,y) tuple을 dict key로 썼다면 JSON 저장 시 문자열이었을 가능성
                    # 여기서는 x,y를 float 변환
                    x_str, y_str = k.split(",")
                    xx = float(x_str)
                    yy = float(y_str)
                    new_r["nodes"][(xx, yy)] = {
                        "z": nd["z"],
                        "node_name": nd["node_name"]
                    }
                # links
                for ln in r["links"]:
                    # ln = [[x1, y1], [x2, y2]] 형태라고 가정
                    p1, p2 = ln
                    new_r["links"].append(((p1[0], p1[1]), (p2[0], p2[1])))

                routes.append(new_r)

            # 버티포트
            verts_data = data.get("vertiports", [])
            for vp in verts_data:
                vertiports.append({
                    "name": vp["name"],
                    "type": vp["type"],
                    "x": vp["x"],
                    "y": vp["y"],
                    "z": vp["z"],
                    "radius_outer": vp["radius_outer"],
                    "radius_inner": vp["radius_inner"]
                })

            # 카운트값 재설정
            self.route_count = len(routes)
            self.vertiport_count = len(vertiports)
            self.current_route_idx = 0 if len(routes) > 0 else None

            self.refresh_all()
            messagebox.showinfo("로드 성공", f"파일 '{filename}' 로드 완료.")
        except Exception as e:
            messagebox.showerror("로드 실패", f"에러: {e}")

    def save_data(self):
        """현재 routes, vertiports 데이터를 JSON 파일로 저장"""
        filename = filedialog.asksaveasfilename(
            title="Save JSON",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not filename:
            return

        try:
            data = {
                "routes": [],
                "vertiports": []
            }
            # routes
            for r in routes:
                # 노드 딕셔너리는 (x,y) -> {...} 형태이므로
                # JSON에 저장하려면 key를 문자열로 변환
                node_dict = {}
                for (xx, yy), nd in r["nodes"].items():
                    key_str = f"{xx},{yy}"
                    node_dict[key_str] = {
                        "z": nd["z"],
                        "node_name": nd["node_name"]
                    }
                # links: [((x1,y1),(x2,y2)), ...] -> [[[x1,y1],[x2,y2]],...]
                link_list = []
                for (p1, p2) in r["links"]:
                    link_list.append([[p1[0], p1[1]], [p2[0], p2[1]]])

                data["routes"].append({
                    "name": r["name"],
                    "node_count": r["node_count"],
                    "nodes": node_dict,
                    "links": link_list
                })

            # vertiports
            for vp in vertiports:
                data["vertiports"].append({
                    "name": vp["name"],
                    "type": vp["type"],
                    "x": vp["x"],
                    "y": vp["y"],
                    "z": vp["z"],
                    "radius_outer": vp["radius_outer"],
                    "radius_inner": vp["radius_inner"]
                })

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("저장 완료", f"파일 '{filename}' 저장되었습니다.")
        except Exception as e:
            messagebox.showerror("저장 실패", f"에러: {e}")

    ############################################################################
    # 마우스 휠(확대/축소)
    ############################################################################
    def on_mouse_wheel_2d(self, event):
        """마우스 휠로 간단한 Zoom (Canvas 상 테스트용)"""
        if event.delta > 0:
            self.zoom_level *= 1.1
        else:
            self.zoom_level *= 0.9
        #  너무 작아지거나 커지는 것 방지
        self.zoom_level = max(0.1, min(self.zoom_level, 10.0))
        self.refresh_all()

    ###########################################################################
    # 좌표 변환
    ###########################################################################
    def world_to_canvas(self, x, y):
        """
        World 좌표 (x,y) -> Canvas 픽셀좌표 (cx, cy), 
        패닝(스크롤) + 줌(zoom_level) 모두 반영
        """

        step_px = (self.CANVAS_SIZE / self.GRID_COUNT) * self.zoom_level
        real_px = (x / self.GRID_SIZE) * step_px
        real_py = (y / self.GRID_SIZE) * step_px

        offset_x = self.canvas_2d.canvasx(0)
        offset_y = self.canvas_2d.canvasy(0)

        # 스크롤 오프셋만큼 빼줘야 "현재 보이는" 캔버스 좌표가 됨
        local_cx = real_px - offset_x
        local_cy = real_py - offset_y

        return int(local_cx), int(local_cy)

    def canvas_to_world(self, cx, cy):
        """
        Canvas 픽셀좌표 (cx, cy) -> World 좌표 (x, y),
        패닝(스크롤) + 줌(zoom_level) 모두 반영
        """
        offset_x_pix = self.canvas_2d.canvasx(0)
        offset_y_pix = self.canvas_2d.canvasy(0)

        step_px = (self.CANVAS_SIZE / self.GRID_COUNT) * self.zoom_level

        # 실제 캔버스 내부 절대 좌표 = 스크롤 오프셋 + 현재 로컬 픽셀
        real_cx = offset_x_pix + cx
        real_cy = offset_y_pix + cy

        step_px = (self.CANVAS_SIZE / self.GRID_COUNT) * self.zoom_level
        x_m = (real_cx / step_px) * self.GRID_SIZE
        y_m = (real_cy / step_px) * self.GRID_SIZE

        return x_m, y_m

    ###########################################################################
    # 경로
    ###########################################################################
    def create_new_route(self):
        self.route_count += 1
        rname = f"경로{self.route_count}"
        new_route = {
        "name": rname,
        "nodes": {},
        "links": [],
        "node_count": 0,
        "last_node": None
        }
        routes.append(new_route)
        self.current_route_idx = len(routes) - 1
        messagebox.showinfo("안내", f"'{rname}'를 입력하세요.")

    def add_node_to_route(self, route_idx, x, y, z):
        """
        교차점 로직 그대로:
        - last_node(LN) ~ user_node(UN) 선분
        - 중간에 교차점 I1..I2..가 있다면 순차 삽입
        """

        route = routes[route_idx]

        # ### 1) last_node가 None이면 = 경로 첫 노드 ###
        if route["last_node"] is None:
            # 첫 노드 단순 등록
            self._create_node(route, x, y, z)
            # 방금 추가한 노드가 last_node
            route["last_node"] = (x,y)
            return

        # ### 2) last_node(LN) 좌표, Z ###
        (lx, ly) = route["last_node"]
        if (lx, ly) not in route["nodes"]:
            # 혹시나 last_node 정보가 꼬였을 경우(예외상황)
            # 그냥 딕셔너리 마지막 등을 쓰거나, None 처리
            # 여기서는 간단히 None 처리
            route["last_node"] = None
            # 그리고 다시 재귀호출(한 번 더 시도)
            self.add_node_to_route(route_idx, x, y, z)
            return

        lz = route["nodes"][(lx, ly)]["z"]

        # ### 교차점 로직 기존 그대로 ###
        # LN->UN
        intersects = self.find_all_intersections((lx, ly, lz), (x, y, z), route_idx)
        intersects.sort(key=lambda itm: itm[0])

        current_start = (lx, ly, lz)
        for (t, ix, iy, iz, o_idx, n1, n2, tB) in intersects:
            # LN->(ix,iy,iz)
            iCoord = self._create_node(route, ix, iy, iz)
            prevCoord = (current_start[0], current_start[1])
            route["links"].append((prevCoord, iCoord))

            # 상대 경로(o_idx)에도 교차노드 추가
            self.insert_intersection_node(o_idx, n1, n2, (ix, iy, iz), tB)

            current_start = (ix, iy, iz)

        # 최종 사용자 노드
        userCoord = self._create_node(route, x, y, z)
        route["links"].append(((current_start[0], current_start[1]), userCoord))

        # ### 새로 추가된 노드를 last_node로 갱신 ###
        route["last_node"] = userCoord


    def update_node_position(self, route_idx, old_x, old_y, new_x, new_y, new_z):
        route = routes[route_idx]
        old_node_name = route["nodes"][(old_x,old_y)]["node_name"]

        # 1) pop old
        route["nodes"].pop((old_x, old_y), None)
        # 2) insert new
        route["nodes"][(new_x, new_y)] = {
            "z": new_z,
            "node_name": old_node_name
        }

        # 링크 치환
        old_links = []
        for ln in route["links"]:
            if (old_x, old_y) in ln:
                old_links.append(ln)
        for ln in old_links:
            route["links"].remove(ln)
            a,b = ln
            # 치환
            if a == (old_x,old_y): a = (new_x,new_y)
            if b == (old_x,old_y): b = (new_x,new_y)
            # 다시 추가
            route["links"].append((a,b))

        # 만약 last_node가 old_x,old_y였으면 업데이트
        if route["last_node"] == (old_x,old_y):
            route["last_node"] = (new_x, new_y)

    def _create_node(self, route, x, y, z):
        """
        route에 (x,y,z) 노드를 생성
        이미 존재하면 그대로 반환
        """
        if (x, y) in route["nodes"]:
            return (x, y)

        route["node_count"] += 1
        node_name = f"{route['name']}-Node{route['node_count']}"
        route["nodes"][(x, y)] = {
            "z": z,
            "node_name": node_name
        }
        return (x, y)

    def find_all_intersections(self, pA, pB, this_route_idx):
        """
        pA=(x1,y1,z1), pB=(x2,y2,z2).
        다른 경로들의 모든 링크와 교차(2D)하는 지점을 찾고,
        z가 거의 일치하면 리스트로 반환.
        리턴: [ (tA, iX, iY, iZ, otherRouteIdx, linkN1, linkN2, tB), ... ]
         - tA: this segment에서의 파라미터(0~1)
         - iX,iY,iZ: 교차점
         - otherRouteIdx: 교차된 경로 인덱스
         - linkN1, linkN2: 그 경로의 링크 노드
         - tB: 그 경로에서의 파라미터
        """
        (x1, y1, z1) = pA
        (x2, y2, z2) = pB

        results = []
        for r_idx, routeB in enumerate(routes):
            if r_idx == this_route_idx:
                continue
            for (n1, n2) in routeB["links"]:
                (xa, ya) = n1
                (xb, yb) = n2
                zb_a = routeB["nodes"][n1]["z"]
                zb_b = routeB["nodes"][n2]["z"]

                # 2D 교차
                inter = self.line_intersection_2d((x1, y1), (x2, y2),
                                                  (xa, ya), (xb, yb))
                if not inter:
                    continue
                iX, iY, tA, tB = inter
                if 0 < tA < 1 and 0 < tB < 1:
                    # z 보간
                    zA = z1 + tA * (z2 - z1)
                    zB = zb_a + tB * (zb_b - zb_a)
                    if abs(zA - zB) < 1.0:
                        iZ = (zA + zB)/2
                        results.append((tA, iX, iY, iZ, r_idx, n1, n2, tB))

        return results

    def insert_intersection_node(self, route_idx, n1, n2, iCoord, tB):
        """
        다른 경로(route_idx)의 링크 n1->n2를 분할하고,
        교차점 iCoord=(iX,iY,iZ)를 노드로 추가한다.
        이미 있는 노드면 추가 X
        """
        route = routes[route_idx]
        (iX, iY, iZ) = iCoord

        if (iX, iY) in route["nodes"]:
            return

        # 새 노드 생성
        route["node_count"] += 1
        node_name = f"{route['name']}-Node{route['node_count']}"
        route["nodes"][(iX, iY)] = {"z": iZ, "node_name": node_name}

        # 원래 링크 제거
        if (n1, n2) in route["links"]:
            route["links"].remove((n1, n2))
        elif (n2, n1) in route["links"]:
            route["links"].remove((n2, n1))

        # 새 링크 2개
        route["links"].append((n1, (iX, iY)))
        route["links"].append(((iX, iY), n2))

    def line_intersection_2d(self, p1, p2, p3, p4):
        """
        2D 선분 교차: p1->p2, p3->p4
        반환: (iX, iY, tA, tB) 또는 None
        """
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4

        denom = (y4-y3)*(x2-x1) - (x4-x3)*(y2-y1)
        if abs(denom) < 1e-12:
            return None
        ua = ((x4-x3)*(y1-y3) - (y4-y3)*(x1-x3)) / denom
        ub = ((x2-x1)*(y1-y3) - (y2-y1)*(x1-x3)) / denom
        if not (0 <= ua <= 1 and 0 <= ub <= 1):
            return None
        iX = x1 + ua*(x2-x1)
        iY = y1 + ua*(y2-y1)
        return (iX, iY, ua, ub)

    ###########################################################################
    # 버티포트
    ###########################################################################
    def set_vertiport_input(self, vtype):
        self.input_mode = "VERTIPORT"
        self.temp_vertiport_type = vtype
        messagebox.showinfo("버티포트 추가",
                            f"{vtype} 버티포트 생성 모드입니다.\n지도를 클릭하세요.")

    def add_vertiport(self, x, y, vtype):
        self.vertiport_count += 1
        vname = f"Vertiport{self.vertiport_count}"
        vp = {
            "name": vname,
            "type": vtype,
            "x": x,
            "y": y,
            "z": 0,
            "radius_outer": 1350,
            "radius_inner": 700
        }
        vertiports.append(vp)

    ###########################################################################
    # Canvas 이벤트
    ###########################################################################
    def on_canvas_click(self, event):
        real_cx = self.canvas_2d.canvasx(event.x)
        real_cy = self.canvas_2d.canvasy(event.y)
        wx, wy = self.canvas_to_world(real_cx, real_cy)

        # 50단위 스냅
        sx = round(wx/50)*50
        sy = round(wy/50)*50

        if self.input_mode == "NODE":
            z_val = self._ask_integer_near_mouse(
                event.x, event.y,
                title="노드 Z 입력",
                prompt=f"({sx},{sy}) 고도(ft):",
                initial=1000,
                minval=0
            )
            if z_val is None:
                return
            if self.current_route_idx is not None:
                self.add_node_to_route(self.current_route_idx,
                                    sx, sy, z_val)

        elif self.input_mode == "VERTIPORT":
            self.add_vertiport(sx, sy, self.temp_vertiport_type)
            # 버티포트 생성 후 NODE 모드로 복귀
            self.input_mode = "NODE"

        elif self.input_mode == "UPDATE_NODE":
            if not self.node_to_update:
                return
            (r_idx, old_x, old_y, old_name, old_links) = self.node_to_update

            new_z = self._ask_integer_near_mouse(
                event.x, event.y,
                title="노드 Z 재입력",
                prompt="새 고도(ft):",
                initial=1000,
                minval=0
            )
            if new_z is None:
                # 취소
                self.input_mode = "NODE"
                self.node_to_update = None
                return

            route = routes[r_idx]
            # 기존 노드 삭제
            route["nodes"].pop((old_x, old_y), None)
            # 새 노드 등록(노드명 그대로 사용)
            route["nodes"][(sx, sy)] = {
                "z": new_z,
                "node_name": old_name
            }

            # 링크 재설정
            new_links = []
            for ln in old_links:
                a, b = ln
                if a == (old_x, old_y):
                    a = (sx, sy)
                if b == (old_x, old_y):
                    b = (sx, sy)
                new_links.append((a, b))

            # route["links"]에서 old_links 제거
            for ln in old_links:
                if ln in route["links"]:
                    route["links"].remove(ln)
                rev = (ln[1], ln[0])
                if rev in route["links"]:
                    route["links"].remove(rev)

            # 새 링크 등록(중복되면 제외)
            for nl in new_links:
                if nl not in route["links"] and (nl[1], nl[0]) not in route["links"]:
                    route["links"].append(nl)

            # ### 추가: 만약 이 노드가 last_node면 갱신 ###
            if route["last_node"] == (old_x, old_y):
                route["last_node"] = (sx, sy)

            self.input_mode = "NODE"
            self.node_to_update = None
        self.refresh_all()

    ###########################################################################
    # 노드 업데이트용
    ###########################################################################
    def on_tree_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        route_idx_str, old_x_str, old_y_str = item_id.split("-")
        r_idx = int(route_idx_str)
        old_x = float(old_x_str)
        old_y = float(old_y_str)
        route = routes[r_idx]
        if (old_x, old_y) not in route["nodes"]:
            return
        old_node_name = route["nodes"][(old_x, old_y)]["node_name"]
        # 해당 노드에 연결된 링크 수집
        old_links = []
        for ln in route["links"]:
            if (old_x, old_y) in ln:
                old_links.append(ln)

        self.node_to_update = (r_idx, old_x, old_y,
                               old_node_name, old_links)
        self.input_mode = "UPDATE_NODE"
        messagebox.showinfo("노드 위치 변경",
                            "지도를 클릭하여 새 위치를 지정하세요.")

    ###########################################################################
    # 간단 입력 함수 (정수)
    ###########################################################################
    def _ask_integer_near_mouse(self, mouse_x, mouse_y,
                                title="입력", prompt="값을 입력하세요",
                                initial=1000, minval=0):
        """
        Dialog를 띄워 사용자가 직접 숫자 입력.
        - IntVar 대신 entry.get()으로 파싱 → 원하는 값 입력 가능
        """
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        abs_x = self.root.winfo_rootx() + mouse_x + 30
        abs_y = self.root.winfo_rooty() + mouse_y
        dlg.geometry(f"+{abs_x}+{abs_y}")

        lbl = tk.Label(dlg, text=prompt)
        lbl.pack(padx=10, pady=5)

        entry_var = tk.StringVar(value=str(initial))
        entry = tk.Entry(dlg, textvariable=entry_var)
        entry.pack(padx=10, pady=5)
        entry.focus()

        ret = [None]

        def on_ok():
            val_str = entry_var.get().strip()
            try:
                val_int = int(val_str)
            except ValueError:
                messagebox.showwarning("주의", "정수로 입력해주세요.")
                return
            if val_int < minval:
                messagebox.showwarning("주의", f"{minval} 이상의 값을 입력하세요.")
                return
            ret[0] = val_int
            dlg.destroy()

        def on_cancel():
            dlg.destroy()

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="확인", command=on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="취소", command=on_cancel).pack(side=tk.LEFT, padx=5)

        dlg.bind("<Return>", lambda e: on_ok())
        dlg.bind("<Escape>", lambda e: on_cancel())

        dlg.grab_set()
        dlg.wait_window()
        return ret[0]

    ###########################################################################
    # 표(트리뷰)
    ###########################################################################
    def refresh_treeview(self):
        self.tree.delete(*self.tree.get_children())
        for i, route in enumerate(routes):
            for (x, y), nd in route["nodes"].items():
                rname = route["name"]
                nname = nd["node_name"]
                zz = nd["z"]
                iid = f"{i}-{x}-{y}"
                self.tree.insert("", "end", iid=iid,
                                 values=(rname, nname, x, y, zz))

    ###########################################################################
    # 그리기 (2D/3D)
    ###########################################################################
    def draw_grid(self):
        self.canvas_2d.delete("grid")
        step_px = (self.CANVAS_SIZE // self.GRID_COUNT) * self.zoom_level
        for i in range(self.GRID_COUNT + 1):
            c = i * step_px
            self.canvas_2d.create_line(c, 0, c, self.CANVAS_SIZE,
                                       fill="lightgray", tags="grid")
            self.canvas_2d.create_line(0, c, self.CANVAS_SIZE, c,
                                       fill="lightgray", tags="grid")


    def draw_all_routes_2d(self):
        for i, route in enumerate(routes):
            color = ROUTE_COLORS[i % len(ROUTE_COLORS)]
            # 노드
            for (x, y), nd in route["nodes"].items():
                cx, cy = self.world_to_canvas(x, y)
                self.canvas_2d.create_oval(cx-4, cy-4, cx+4, cy+4,
                                           fill=color, outline=color)
                self.canvas_2d.create_text(cx+10, cy,
                                           text=nd["node_name"],
                                           anchor="w", fill=color,
                                           font=("맑은 고딕", 8))
            # 링크
            for (n1, n2) in route["links"]:
                x1, y1 = n1
                x2, y2 = n2
                cx1, cy1 = self.world_to_canvas(x1, y1)
                cx2, cy2 = self.world_to_canvas(x2, y2)
                self.canvas_2d.create_line(cx1, cy1, cx2, cy2,
                                           fill=color, width=2)

    def draw_all_vertiports_2d(self):
        for vp in vertiports:
            x, y = vp["x"], vp["y"]
            cx, cy = self.world_to_canvas(x, y)
            self.canvas_2d.create_text(cx, cy-10,
                                       text=vp["name"],
                                       anchor="s", fill="black",
                                       font=("맑은 고딕", 9, "bold"))
            # Outer
            r_out_px = int(vp["radius_outer"]
                           / (self.MAP_SIZE/self.CANVAS_SIZE)
                           * self.zoom_level)
            self.canvas_2d.create_oval(cx-r_out_px, cy-r_out_px,
                                       cx+r_out_px, cy+r_out_px,
                                       outline="gray", width=2)
            # Inner
            r_in_px = int(vp["radius_inner"]
                          / (self.MAP_SIZE/self.CANVAS_SIZE)
                          * self.zoom_level)
            self.canvas_2d.create_oval(cx-r_in_px, cy-r_in_px,
                                       cx+r_in_px, cy+r_in_px,
                                       outline="gray", width=2, dash=(4,2))

    def draw_all_routes_3d(self):
        for i, route in enumerate(routes):
            color = ROUTE_COLORS[i % len(ROUTE_COLORS)]
            xs, ys, zs = [], [], []
            for (x, y), nd in route["nodes"].items():
                xs.append(x)
                ys.append(y)
                zs.append(nd["z"])
            self.ax.scatter(xs, ys, zs, marker='o', color=color,
                            label=route["name"])
            # 링크
            for (n1, n2) in route["links"]:
                x1, y1 = n1
                x2, y2 = n2
                z1 = route["nodes"][n1]["z"]
                z2 = route["nodes"][n2]["z"]
                self.ax.plot([x1, x2], [y1, y2], [z1, z2], color=color)

    def draw_all_vertiports_3d(self):
        """
        버티포트를 3D에서 투명한 원통형으로 표시
        - z=0 ~ 1000(ft) 라고 가정(필요시 변경)
        - alpha=0.2 (투명도)
        """
        for vp in vertiports:
            cx, cy = vp["x"], vp["y"]
            self.ax.scatter(cx, cy, vp["z"],
                            marker='^', color="black", label=vp["name"])

            # 원통: theta=[0,2pi], z=[0,1000]
            # Outer
            height = 2000
            theta = np.linspace(0, 2*np.pi, 30)
            zvals = np.linspace(0, height, 5)
            theta_grid, z_grid = np.meshgrid(theta, zvals)
            X = cx + vp["radius_outer"] * np.cos(theta_grid)
            Y = cy + vp["radius_outer"] * np.sin(theta_grid)
            Z = z_grid
            self.ax.plot_surface(X, Y, Z,
                                 color='gray',
                                 alpha=0.2,
                                 linewidth=0,
                                 shade=True)

            # Inner
            X2 = cx + vp["radius_inner"] * np.cos(theta_grid)
            Y2 = cy + vp["radius_inner"] * np.sin(theta_grid)
            Z2 = z_grid
            self.ax.plot_surface(X2, Y2, Z2,
                                 color='gray',
                                 alpha=0.2,
                                 linewidth=0,
                                 shade=True)
            
    def show_corner_coords(self):
        """
        Canvas (0,0), (width,0), (0,height), (width,height)에 해당하는
        실제 World 좌표를 작은 텍스트로 표시
        """
        # 우선 혹시 기존 표시를 지우고 시작
        # (tags="corner_label" 로 붙은걸 모두 지우기)
        self.canvas_2d.delete("corner_label")

        w = self.CANVAS_SIZE
        h = self.CANVAS_SIZE

        # canvasx, canvasy:
        #  - canvasx(0) : 스크롤이 반영된 후 실제 "보이는" 0px 위치의 내부 좌표
        #  - canvasx(w) : 보이는 오른쪽 끝 px 위치의 내부 좌표
        x0_pix = self.canvas_2d.canvasx(0)
        y0_pix = self.canvas_2d.canvasy(0)
        x1_pix = self.canvas_2d.canvasx(w)
        y1_pix = self.canvas_2d.canvasy(h)

        # 이제 이 픽셀좌표 → World 좌표
        x0_world, y0_world = self.canvas_to_world(x0_pix, y0_pix)
        x1_world, y1_world = self.canvas_to_world(x1_pix, y1_pix)

        # 좌상단 (x0_pix, y0_pix)에 해당하는 world
        #   - anchor="nw"로 표시
        self.canvas_2d.create_text(
            x0_pix + 5, y0_pix + 5,
            text=f"({x0_world}, {y0_world})",
            fill="blue", anchor="nw",
            font=("맑은 고딕", 9, "bold"),
            tags="corner_label"
        )

        # 우상단 (x1_pix, y0_pix)
        self.canvas_2d.create_text(
            x1_pix - 5, y0_pix + 5,
            text=f"({x1_world}, {y0_world})",
            fill="blue", anchor="ne",
            font=("맑은 고딕", 9, "bold"),
            tags="corner_label"
        )

        # 좌하단 (x0_pix, y1_pix)
        self.canvas_2d.create_text(
            x0_pix + 5, y1_pix - 5,
            text=f"({x0_world}, {y1_world})",
            fill="blue", anchor="sw",
            font=("맑은 고딕", 9, "bold"),
            tags="corner_label"
        )

        # 우하단 (x1_pix, y1_pix)
        self.canvas_2d.create_text(
            x1_pix - 5, y1_pix - 5,
            text=f"({x1_world}, {y1_world})",
            fill="blue", anchor="se",
            font=("맑은 고딕", 9, "bold"),
            tags="corner_label"
        )

    def refresh_all(self):
        # 2D
        self.draw_grid()
        self.canvas_2d.delete("all")
        self.draw_grid()  # 그리드 다시
        self.draw_all_routes_2d()
        self.draw_all_vertiports_2d()

        # 3D
        self.ax.clear()
        self.ax.set_title("UAM 3D 항로 설계")
        self.draw_all_routes_3d()
        self.draw_all_vertiports_3d()
        self.ax.set_xlabel("X(m)")
        self.ax.set_ylabel("Y(m)")
        self.ax.set_zlabel("Z(ft)")

        # 범례 중복 제거
        handles, labels = self.ax.get_legend_handles_labels()
        unique = dict(zip(labels, handles))
        self.ax.legend(unique.values(), unique.keys())

        self.canvas_3d.draw()

        # 트리뷰
        self.refresh_treeview()

        self.show_corner_coords()

###############################################################################
# 실행
###############################################################################
if __name__ == "__main__":
    root = tk.Tk()
    app = UAMMapApp(root)
    root.mainloop()
