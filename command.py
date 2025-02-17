class CommandManager:
    def __init__(self, planes):
        # 비행체 id를 key로 하는 딕셔너리 생성
        self.planes = {plane.id: plane for plane in planes}

    def issue_command(self, plane_id, new_target=None, new_speed=None):
        if plane_id in self.planes:
            self.planes[plane_id].set_command(new_target=new_target, new_speed=new_speed)
        else:
            print(f"Plane {plane_id} not found.")
