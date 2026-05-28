#!/usr/bin/env python3
import argparse
import os
from pathlib import Path

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]


def default_mycobot_description_dir():
    env_path = os.environ.get("MYCOBOT_DESCRIPTION_DIR")
    candidates = [
        Path(env_path) if env_path else None,
        ROOT_DIR.parent / "cobot" / "mycobot_docker" / "custom_ws" / "src" / "mycobot_description",
        ROOT_DIR.parent / "Cobot" / "mycobot_docker" / "custom_ws" / "src" / "mycobot_description",
        Path("/home/mhc/Germany/Cobot/mycobot_docker/custom_ws/src/mycobot_description"),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return candidates[-1]


MYCOBOT_DESCRIPTION_DIR = default_mycobot_description_dir()
MYCOBOT_XACRO = (
    MYCOBOT_DESCRIPTION_DIR / "urdf" / "mycobot_280_jn" / "mycobot_280_jn.urdf.xacro"
)
DEFAULT_SCENE_YAML = ROOT_DIR / "config" / "b002_scene.yaml"


def parse_simple_yaml(path):
    data = {}
    for raw_line in Path(path).read_text().splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            data[key] = [float(part.strip()) for part in value[1:-1].split(",")]
        else:
            try:
                data[key] = float(value)
            except ValueError:
                data[key] = value.strip("\"'")
    return data


def load_scene_yaml(path):
    path = Path(path)
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Scene YAML must contain a mapping: {path}")
    return data


def read_pgm(path):
    data = Path(path).read_bytes()
    idx = 0

    def next_token():
        nonlocal idx
        while idx < len(data):
            char = data[idx]
            if char == 35:
                while idx < len(data) and data[idx] not in (10, 13):
                    idx += 1
            elif chr(char).isspace():
                idx += 1
            else:
                break
        start = idx
        while idx < len(data) and not chr(data[idx]).isspace():
            idx += 1
        return data[start:idx].decode("ascii")

    magic = next_token()
    if magic not in ("P2", "P5"):
        raise ValueError(f"Unsupported PGM format: {magic}")
    width = int(next_token())
    height = int(next_token())
    maxval = int(next_token())
    while idx < len(data) and chr(data[idx]).isspace():
        idx += 1

    if magic == "P5":
        pixels = list(data[idx: idx + width * height])
    else:
        pixels = [int(token) for token in data[idx:].decode("ascii").split()]
    if maxval != 255:
        pixels = [int(round(value * 255.0 / maxval)) for value in pixels]
    return width, height, pixels[: width * height]


def occupied_mask(yaml_path):
    meta = parse_simple_yaml(yaml_path)
    image = Path(str(meta["image"]))
    if not image.is_absolute():
        image = Path(yaml_path).parent / image
    width, height, pixels = read_pgm(image)
    resolution = float(meta.get("resolution", 0.05))
    origin = meta.get("origin", [0.0, 0.0, 0.0])
    occupied_thresh = float(meta.get("occupied_thresh", 0.65))
    negate = int(float(meta.get("negate", 0)))

    mask = []
    for row in range(height):
        row_mask = []
        for col in range(width):
            value = pixels[row * width + col]
            occ_prob = value / 255.0 if negate else (255 - value) / 255.0
            row_mask.append(occ_prob >= occupied_thresh)
        mask.append(row_mask)
    return mask, width, height, resolution, origin


def row_runs(mask):
    runs = []
    for row, values in enumerate(mask):
        col = 0
        while col < len(values):
            while col < len(values) and not values[col]:
                col += 1
            start = col
            while col < len(values) and values[col]:
                col += 1
            if col > start:
                runs.append((row, start, col - 1))
    return runs


def floor_urdf(yaml_path, out_path, _wall_height):
    meta = parse_simple_yaml(yaml_path)
    resolution = float(meta.get("resolution", 0.05))
    origin = meta.get("origin", [0.0, 0.0, 0.0])
    image = Path(str(meta["image"]))
    if not image.is_absolute():
        image = Path(yaml_path).parent / image
    data = image.read_bytes()
    idx = 0

    def next_token():
        nonlocal idx
        while idx < len(data):
            if data[idx] == 35:
                while idx < len(data) and data[idx] not in (10, 13):
                    idx += 1
            elif chr(data[idx]).isspace():
                idx += 1
            else:
                break
        start = idx
        while idx < len(data) and not chr(data[idx]).isspace():
            idx += 1
        return data[start:idx].decode("ascii")

    next_token()  # magic
    pgm_w = int(next_token())
    pgm_h = int(next_token())
    ox, oy = float(origin[0]), float(origin[1])
    floor_w = pgm_w * resolution
    floor_h = pgm_h * resolution
    cx = ox + floor_w / 2.0
    cy = oy + floor_h / 2.0
    content = f"""<?xml version="1.0"?>
<robot name="tb4_floor">
  <link name="map"/>
  <material name="floor_mat"><color rgba="0.30 0.32 0.34 1.00"/></material>
  <link name="floor_plane">
    <visual>
      <geometry><box size="{floor_w:.4f} {floor_h:.4f} 0.005"/></geometry>
      <material name="floor_mat"/>
    </visual>
  </link>
  <joint name="floor_joint" type="fixed">
    <parent link="map"/>
    <child link="floor_plane"/>
    <origin xyz="{cx:.4f} {cy:.4f} -0.0025" rpy="0 0 0"/>
  </joint>
</robot>
"""
    Path(out_path).write_text(content)


def obstacle_urdf(yaml_path, out_path, obstacle_height):
    mask, _width, height, resolution, origin = occupied_mask(yaml_path)
    runs = row_runs(mask)
    ox, oy = float(origin[0]), float(origin[1])

    lines = [
        '<?xml version="1.0"?>',
        '<robot name="tb4_map_obstacles_3d">',
        '  <link name="map"/>',
        '  <material name="obstacle_mat"><color rgba="0.12 0.13 0.14 1.0"/></material>',
    ]

    for idx, (row, col0, col1) in enumerate(runs):
        sx = (col1 - col0 + 1) * resolution
        sy = resolution
        sz = obstacle_height
        cx = ox + ((col0 + col1 + 1) * 0.5) * resolution
        cy = oy + (height - row - 0.5) * resolution
        cz = obstacle_height / 2.0
        name = f"map_obstacle_{idx}"
        lines.extend([
            f'  <link name="{name}">',
            '    <visual>',
            f'      <geometry><box size="{sx:.4f} {sy:.4f} {sz:.4f}"/></geometry>',
            '      <material name="obstacle_mat"/>',
            '    </visual>',
            '  </link>',
            f'  <joint name="{name}_joint" type="fixed">',
            '    <parent link="map"/>',
            f'    <child link="{name}"/>',
            f'    <origin xyz="{cx:.4f} {cy:.4f} {cz:.4f}" rpy="0 0 0"/>',
            '  </joint>',
        ])

    lines.append("</robot>")
    Path(out_path).write_text("\n".join(lines) + "\n")
    return len(runs)


def mycobot_visual_urdf(out_path):
    text = MYCOBOT_XACRO.read_text()
    text = text.replace("package://mycobot_description", MYCOBOT_DESCRIPTION_DIR.as_uri())
    Path(out_path).write_text(text)


def furniture_urdf(out_path, anchor_x=-0.338, anchor_y=1.106):
    """
    Visual semantic layer for B002.

    The occupancy-map extrusion remains the source of truth for walls and
    robot-seen obstacles. This layer adds recognizable lab landmarks from the
    annotated map/photos: factory bench, robot dock, workstations, student
    tables, whiteboards, columns, radiators, and cable clutter.
    """

    lines = [
        '<?xml version="1.0"?>',
        '<robot name="room_furniture">',
        '  <link name="map"/>',
    ]

    idx = [0]

    def add(geom_xml, cx, cy, cz, r, g, b, a=1.0, rpy="0 0 0"):
        name = f"furn_{idx[0]}"
        idx[0] += 1
        mat = f"mat_{name}"
        lines.extend([
            f'  <material name="{mat}"><color rgba="{r:.2f} {g:.2f} {b:.2f} {a:.2f}"/></material>',
            f'  <link name="{name}"><visual><geometry>{geom_xml}</geometry>'
            f'<material name="{mat}"/></visual></link>',
            f'  <joint name="{name}_j" type="fixed"><parent link="map"/>'
            f'<child link="{name}"/>'
            f'<origin xyz="{cx:.4f} {cy:.4f} {cz:.4f}" rpy="{rpy}"/></joint>',
        ])

    def box(sx, sy, sz, cx, cy, cz, r, g, b, a=1.0, rpy="0 0 0"):
        add(f'<box size="{sx:.4f} {sy:.4f} {sz:.4f}"/>', cx, cy, cz, r, g, b, a, rpy)

    def cyl(radius, length, cx, cy, cz, r, g, b, a=1.0, rpy="0 0 0"):
        add(f'<cylinder radius="{radius:.4f}" length="{length:.4f}"/>', cx, cy, cz, r, g, b, a, rpy)

    def zone(sx, sy, cx, cy, r, g, b):
        box(sx, sy, 0.018, cx, cy, 0.012, r, g, b, 0.45)

    def beacon(cx, cy, r, g, b):
        cyl(0.055, 1.20, cx, cy, 0.60, r, g, b, 0.85)
        cyl(0.12, 0.035, cx, cy, 1.215, r, g, b, 0.95)

    def desk(cx, cy, sx=0.82, sy=1.40, yaw=0.0):
        rpy = f"0 0 {yaw:.4f}"
        box(sx, sy, 0.045, cx, cy, 0.76, 0.94, 0.91, 0.82, rpy=rpy)
        box(sx - 0.08, sy - 0.08, 0.66, cx, cy, 0.35, 0.32, 0.32, 0.34, rpy=rpy)
        box(sx + 0.02, 0.055, 0.06, cx, cy + sy / 2.0, 0.79, 0.83, 0.62, 0.22, rpy=rpy)

    def chair(cx, cy, yaw=0.0):
        rpy = f"0 0 {yaw:.4f}"
        box(0.46, 0.44, 0.08, cx, cy, 0.46, 0.08, 0.08, 0.09, rpy=rpy)
        box(0.46, 0.06, 0.58, cx, cy + 0.23, 0.75, 0.08, 0.08, 0.09, rpy=rpy)
        box(0.52, 0.48, 0.055, cx, cy - 0.05, 0.08, 0.05, 0.05, 0.055, rpy=rpy)

    def monitor(cx, cy, yaw=0.0, wide=0.55):
        rpy = f"0 0 {yaw:.4f}"
        box(wide, 0.055, 0.34, cx, cy, 1.05, 0.03, 0.035, 0.04, rpy=rpy)
        box(0.06, 0.045, 0.28, cx, cy, 0.86, 0.08, 0.08, 0.085, rpy=rpy)
        box(0.26, 0.16, 0.025, cx, cy, 0.72, 0.08, 0.08, 0.085, rpy=rpy)

    def keyboard(cx, cy, yaw=0.0):
        box(0.34, 0.13, 0.018, cx, cy, 0.795, 0.025, 0.025, 0.025, rpy=f"0 0 {yaw:.4f}")

    def pc_tower(cx, cy):
        box(0.24, 0.46, 0.64, cx, cy, 0.34, 0.02, 0.02, 0.025)

    def whiteboard(cx, cy, yaw=0.0):
        rpy = f"0 0 {yaw:.4f}"
        box(0.055, 1.18, 0.92, cx, cy, 0.95, 0.96, 0.96, 0.94, rpy=rpy)
        box(0.075, 1.28, 0.065, cx, cy, 1.43, 0.28, 0.29, 0.30, rpy=rpy)
        box(0.075, 1.28, 0.065, cx, cy, 0.47, 0.28, 0.29, 0.30, rpy=rpy)
        box(0.045, 0.045, 1.65, cx, cy - 0.56, 0.82, 0.24, 0.25, 0.26, rpy=rpy)
        box(0.045, 0.045, 1.65, cx, cy + 0.56, 0.82, 0.24, 0.25, 0.26, rpy=rpy)
        box(0.08, 0.62, 0.035, cx, cy - 0.56, 0.035, 0.24, 0.25, 0.26, rpy=rpy)
        box(0.08, 0.62, 0.035, cx, cy + 0.56, 0.035, 0.24, 0.25, 0.26, rpy=rpy)

    # Color-coded floor areas:
    # green=factory, orange=PC/chairs L-desks, pink=tables/boards.
    # Centers are aligned to waypoints.yaml and the corrected map reading.
    pickup_x, pickup_y = -0.8660708069, 5.6563882827

    zone(1.00, 2.00, 0.00, 2.15, 0.05, 0.70, 0.24)       # factory centered at x=0, y 1.15..3.15
    zone(2.00, 0.62, 0.00, 6.78, 1.00, 0.55, 0.05)       # PC/chairs L: back desk
    zone(0.62, 1.80, 0.55, 5.62, 1.00, 0.55, 0.05)       # PC/chairs L: wall desk
    zone(1.30, 0.95, -4.45, 1.20, 0.95, 0.05, 0.70)      # tables/boards lower table
    zone(1.55, 1.25, -4.45, 5.35, 0.95, 0.05, 0.70)      # tables/boards upper table

    # Factory/ETS training line: cabinet row, conveyor, PLC panels, blue stations.
    fcx, fcy = 0.00, 2.15
    factory_len = 1.90
    box(0.82, factory_len, 0.86, fcx, fcy, 0.43, 0.92, 0.92, 0.88)
    box(0.90, factory_len + 0.05, 0.05, fcx, fcy, 0.89, 0.10, 0.10, 0.10)
    box(0.14, factory_len + 0.20, 0.12, fcx - 0.46, fcy, 1.02, 0.72, 0.73, 0.72)
    box(0.10, factory_len + 0.35, 0.10, fcx - 0.48, fcy, 0.30, 0.72, 0.73, 0.72)
    for dy in [-0.62, 0.0, 0.62]:
        box(0.32, 0.86, 1.05, fcx + 0.20, fcy + dy, 1.47, 0.74, 0.75, 0.72)
        box(0.028, 0.92, 1.18, fcx + 0.02, fcy + dy, 1.48, 0.60, 0.61, 0.58)
        box(0.035, 0.26, 0.18, fcx - 0.28, fcy + dy - 0.21, 1.48, 0.02, 0.65, 0.70)
        for px in [-0.34, -0.10, 0.14]:
            cyl(0.045, 0.045, fcx + px, fcy + dy - 0.34, 0.94, 0.02, 0.55, 0.18)
            cyl(0.045, 0.045, fcx + px, fcy + dy + 0.34, 0.94, 0.95, 0.82, 0.05)
    for dy in [-0.82, -0.55, -0.28, 0.0, 0.28, 0.55, 0.82]:
        box(0.13, 0.10, 0.38, fcx - 0.42, fcy + dy, 1.15, 0.08, 0.28, 0.78)

    # TV near the workstation table; compressor/cylinder moved inward so the
    # two visual hints no longer overlap in RViz.
    screen_x, screen_y = -0.10, 4.20
    box(0.10, 1.20, 0.75, screen_x, screen_y, 1.12, 0.03, 0.03, 0.035)
    box(0.08, 0.10, 1.65, screen_x, screen_y, 0.84, 0.86, 0.86, 0.82)
    box(0.62, 0.76, 0.045, screen_x, screen_y, 0.04, 0.86, 0.86, 0.82)
    cyl(0.23, 0.62, -0.30, 3.48, 0.32, 0.92, 0.82, 0.45, rpy="0 1.5708 0")
    box(0.36, 0.30, 0.34, -0.42, 3.48, 0.58, 0.25, 0.25, 0.25)

    # Tables and boards on the left wall: one low, one wider near the top wall.
    desk(-4.48, 1.20, sx=0.72, sy=0.90, yaw=3.1416)
    desk(-4.42, 5.35, sx=0.86, sy=1.35, yaw=3.1416)
    chair(-3.92, 1.10, yaw=0.0)
    chair(-3.86, 5.25, yaw=0.0)
    whiteboard(-4.70, 3.25, yaw=0.0)
    box(0.32, 0.46, 0.72, -4.92, 5.85, 0.36, 0.84, 0.84, 0.80)

    # PC/chairs as an L: back table across x -1..1 and a long table on the right wall.
    desk(0.00, 6.78, sx=1.92, sy=0.58, yaw=3.1416)
    desk(0.56, 5.62, sx=0.58, sy=1.75, yaw=3.1416)
    monitor(-0.35, 6.65, yaw=3.1416, wide=0.58)
    monitor(0.47, 5.62, yaw=-1.5708, wide=0.58)
    keyboard(-0.35, 6.48, yaw=3.1416)
    keyboard(0.35, 5.62, yaw=-1.5708)
    chair(-0.35, 6.20, yaw=3.1416)
    chair(0.02, 5.45, yaw=-1.5708)
    pc_tower(0.78, 5.15)
    box(0.52, 0.34, 0.16, 0.45, 6.95, 0.84, 0.02, 0.02, 0.025)

    # Window wall: dark radiators/low window band; room pillars are near x -1.
    for cx_col, cy_col in [(-1.80, -1.00), (-1.20, 7.00)]:
        cyl(0.19, 2.70, cx_col, cy_col, 1.35, 0.88, 0.88, 0.86)
    for ry in [0.55, 2.35, 4.20]:
        box(0.16, 1.10, 0.48, -5.08, ry, 0.27, 0.21, 0.20, 0.20)
    box(0.05, 4.90, 0.35, -5.22, 2.45, 1.30, 0.08, 0.09, 0.10, a=0.65)

    lines.append("</robot>")
    Path(out_path).write_text("\n".join(lines) + "\n")
    return idx[0]


def semantic_scene_urdf(scene_yaml, out_path, enabled=True):
    scene = load_scene_yaml(scene_yaml)
    overlay = scene.get("semantic_overlay", {})
    overlay_enabled = bool(overlay.get("enabled", True)) and enabled
    objects = overlay.get("objects", []) if overlay_enabled else []

    lines = [
        '<?xml version="1.0"?>',
        '<robot name="b002_semantic_scene">',
        '  <link name="map"/>',
    ]

    idx = 0
    for obj in objects:
        if not obj or not obj.get("enabled", True):
            continue
        obj_type = str(obj.get("type", "box"))
        obj_id = str(obj.get("id", f"object_{idx}")).replace(" ", "_")
        xyz = [float(v) for v in obj.get("xyz", [0.0, 0.0, 0.0])]
        rpy = [float(v) for v in obj.get("rpy", [0.0, 0.0, 0.0])]
        color = [float(v) for v in obj.get("color", [0.7, 0.7, 0.7, 0.5])]
        if len(xyz) != 3 or len(rpy) != 3 or len(color) != 4:
            raise ValueError(f"Invalid xyz/rpy/color for scene object {obj_id}")

        if obj_type == "box":
            size = [float(v) for v in obj.get("size", [0.1, 0.1, 0.1])]
            if len(size) != 3:
                raise ValueError(f"Invalid size for scene object {obj_id}")
            geom = f'<box size="{size[0]:.4f} {size[1]:.4f} {size[2]:.4f}"/>'
        elif obj_type == "cylinder":
            radius = float(obj.get("radius", 0.1))
            length = float(obj.get("length", 0.1))
            geom = f'<cylinder radius="{radius:.4f}" length="{length:.4f}"/>'
        else:
            raise ValueError(f"Unsupported scene object type {obj_type!r} in {obj_id}")

        name = f"scene_{idx}_{obj_id}"
        mat = f"{name}_mat"
        idx += 1
        lines.extend([
            f'  <material name="{mat}"><color rgba="{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} {color[3]:.3f}"/></material>',
            f'  <link name="{name}">',
            '    <visual>',
            f'      <geometry>{geom}</geometry>',
            f'      <material name="{mat}"/>',
            '    </visual>',
            '  </link>',
            f'  <joint name="{name}_joint" type="fixed">',
            '    <parent link="map"/>',
            f'    <child link="{name}"/>',
            f'    <origin xyz="{xyz[0]:.4f} {xyz[1]:.4f} {xyz[2]:.4f}" rpy="{rpy[0]:.4f} {rpy[1]:.4f} {rpy[2]:.4f}"/>',
            '  </joint>',
        ])

    lines.append("</robot>")
    Path(out_path).write_text("\n".join(lines) + "\n")
    return idx


def rviz_config(out_path, mycobot_urdf, obstacles_urdf, floor_urdf, furniture_urdf_path):
    content = f"""Panels:
  - Class: rviz_common/Displays
    Name: Displays
  - Class: rviz_common/Views
    Name: Views
Visualization Manager:
  Class: ""
  Displays:
    - Class: rviz_default_plugins/Grid
      Enabled: false
      Name: Grid
      Plane: XY
      Plane Cell Count: 30
      Cell Size: 1
      Color: 180; 180; 180
      Alpha: 0.3
    - Class: rviz_default_plugins/MarkerArray
      Enabled: true
      Name: Floor
      Namespaces:
        floor: true
      Topic:
        Value: /env3d/floor_markers
        Reliability Policy: Reliable
        Durability Policy: Transient Local
        History Policy: Keep Last
        Depth: 5
      Value: true
    - Class: rviz_default_plugins/MarkerArray
      Enabled: true
      Name: Walls 3D
      Namespaces:
        walls: true
      Topic:
        Value: /env3d/wall_markers
        Reliability Policy: Reliable
        Durability Policy: Transient Local
        History Policy: Keep Last
        Depth: 5
      Value: true
    - Class: rviz_default_plugins/RobotModel
      Enabled: true
      Name: TurtleBot4
      Description Source: Topic
      Description Topic:
        Value: /robot_description
        Reliability Policy: Reliable
        Durability Policy: Transient Local
        History Policy: Keep Last
        Depth: 5
      Collision Enabled: false
      Visual Enabled: true
    - Class: rviz_default_plugins/RobotModel
      Enabled: true
      Name: MyCobot Arm
      Description Source: Topic
      Description Topic:
        Value: /mycobot/robot_description
        Reliability Policy: Reliable
        Durability Policy: Transient Local
        History Policy: Keep Last
        Depth: 5
      Collision Enabled: false
      Visual Enabled: true
    - Class: rviz_default_plugins/MarkerArray
      Enabled: true
      Name: Room Furniture
      Namespaces:
        furniture: true
      Topic:
        Value: /env3d/furniture_markers
        Reliability Policy: Reliable
        Durability Policy: Transient Local
        History Policy: Keep Last
        Depth: 5
      Value: true
    - Class: rviz_default_plugins/TF
      Enabled: false
      Name: TF
      Show Arrows: false
      Show Axes: true
      Show Names: false
    - Class: rviz_default_plugins/Map
      Enabled: false
      Name: Nav2 Map (flat)
      Topic:
        Value: /map
        Durability Policy: Transient Local
        Reliability Policy: Reliable
      Alpha: 0.35
      Draw Behind: true
  Enabled: true
  Global Options:
    Fixed Frame: map
    Background Color: 210; 215; 225
    Frame Rate: 15
  Tools:
    - Class: rviz_default_plugins/Interact
    - Class: rviz_default_plugins/MoveCamera
    - Class: rviz_default_plugins/Measure
    - Class: rviz_default_plugins/PublishPoint
  Views:
    Current:
      Class: rviz_default_plugins/Orbit
      Distance: 14
      Focal Point:
        X: -2.33
        Y: 2.32
        Z: 0.4
      Pitch: 0.78
      Yaw: 0.60
      Name: Current View
Window Geometry:
  Width: 1400
  Height: 900
"""
    Path(out_path).write_text(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--map-yaml", required=True)
    parser.add_argument("--height", type=float, default=None)
    parser.add_argument("--scene-yaml", default=str(DEFAULT_SCENE_YAML))
    parser.add_argument("--no-semantic", action="store_true")
    args = parser.parse_args()

    scene = load_scene_yaml(args.scene_yaml)
    obstacle_height = args.height
    if obstacle_height is None:
        obstacle_height = float(scene.get("lidar_obstacle_height_m", 0.20))

    generated = ROOT_DIR / "generated"
    config_dir = ROOT_DIR / "config"
    generated.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    mycobot_urdf        = generated / "mycobot_280_jn_visual.urdf"
    obstacles_urdf      = generated / "map_obstacles_3d.urdf"
    floor_urdf_path     = generated / "map_floor_3d.urdf"
    furniture_urdf_path = generated / "room_furniture_3d.urdf"
    rviz_path           = config_dir / "turtle_cobot_3d.rviz"

    mycobot_visual_urdf(mycobot_urdf)
    count = obstacle_urdf(Path(args.map_yaml), obstacles_urdf, obstacle_height)
    floor_urdf(Path(args.map_yaml), floor_urdf_path, obstacle_height)
    overlay = scene.get("semantic_overlay", {})
    scene_mode = str(overlay.get("mode", "rich")).lower()
    if args.no_semantic or not bool(overlay.get("enabled", True)):
        semantic_count = semantic_scene_urdf(args.scene_yaml, furniture_urdf_path, enabled=False)
        scene_mode = "none"
    elif scene_mode in ("rich", "detailed"):
        semantic_count = furniture_urdf(furniture_urdf_path)
    elif scene_mode in ("minimal", "simple", "hints"):
        semantic_count = semantic_scene_urdf(args.scene_yaml, furniture_urdf_path, enabled=True)
    else:
        raise ValueError(f"Unsupported semantic_overlay.mode: {scene_mode!r}")
    rviz_config(rviz_path, mycobot_urdf, obstacles_urdf, floor_urdf_path, furniture_urdf_path)

    print(f"Generated {obstacles_urdf} with {count} LiDAR-height strips at {obstacle_height:.2f} m")
    print(f"Generated {floor_urdf_path}")
    print(f"Generated {furniture_urdf_path} with {semantic_count} semantic objects ({scene_mode})")
    print(f"Generated {mycobot_urdf}")
    print(f"Generated {rviz_path}")


if __name__ == "__main__":
    main()
