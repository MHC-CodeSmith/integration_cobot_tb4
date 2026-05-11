#!/usr/bin/env python3
import argparse
from pathlib import Path


ROOT_DIR = Path("/home/mhc/Germany/cobot_tb4_integration")
MYCOBOT_DESCRIPTION_DIR = Path(
    "/home/mhc/Germany/Cobot/mycobot_docker/custom_ws/src/mycobot_description"
)
MYCOBOT_XACRO = (
    MYCOBOT_DESCRIPTION_DIR / "urdf" / "mycobot_280_jn" / "mycobot_280_jn.urdf.xacro"
)


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


def obstacle_urdf(yaml_path, out_path, obstacle_height):
    mask, _width, height, resolution, origin = occupied_mask(yaml_path)
    runs = row_runs(mask)
    ox, oy = float(origin[0]), float(origin[1])

    lines = [
        '<?xml version="1.0"?>',
        '<robot name="tb4_map_obstacles_3d">',
        '  <link name="map"/>',
        '  <material name="obstacle_mat"><color rgba="0.12 0.14 0.16 0.82"/></material>',
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


def rviz_config(out_path, mycobot_urdf, obstacles_urdf):
    content = f"""Panels:
  - Class: rviz_common/Displays
    Name: Displays
  - Class: rviz_common/Views
    Name: Views
Visualization Manager:
  Class: ""
  Displays:
    - Class: rviz_default_plugins/Grid
      Enabled: true
      Name: Grid
      Plane: XY
      Plane Cell Count: 20
      Cell Size: 1
      Color: 120; 120; 120
      Alpha: 0.5
    - Class: rviz_default_plugins/Map
      Enabled: false
      Name: Flat Nav2 Map
      Topic:
        Value: /map
        Durability Policy: Transient Local
        Reliability Policy: Reliable
      Alpha: 0.45
      Draw Behind: true
    - Class: rviz_default_plugins/RobotModel
      Enabled: true
      Name: TurtleBot4 Model
      Description Source: Topic
      Description Topic:
        Value: /robot_description
        Reliability Policy: Reliable
        Durability Policy: Volatile
        History Policy: Keep Last
        Depth: 5
      Collision Enabled: false
      Visual Enabled: true
    - Class: rviz_default_plugins/RobotModel
      Enabled: true
      Name: MyCobot Model
      Description Source: File
      Description File: {mycobot_urdf}
      Collision Enabled: false
      Visual Enabled: true
    - Class: rviz_default_plugins/RobotModel
      Enabled: true
      Name: Occupancy Obstacles 3D
      Description Source: File
      Description File: {obstacles_urdf}
      Collision Enabled: false
      Visual Enabled: true
    - Class: rviz_default_plugins/TF
      Enabled: true
      Name: TF
      Show Arrows: true
      Show Axes: true
      Show Names: false
  Enabled: true
  Global Options:
    Fixed Frame: map
    Background Color: 35; 35; 35
    Frame Rate: 30
  Tools:
    - Class: rviz_default_plugins/Interact
    - Class: rviz_default_plugins/MoveCamera
    - Class: rviz_default_plugins/Measure
  Views:
    Current:
      Class: rviz_default_plugins/Orbit
      Distance: 8
      Focal Point:
        X: -1.5
        Y: 2.0
        Z: 0.4
      Pitch: 0.82
      Yaw: 0.75
      Name: Current View
Window Geometry:
  Width: 1400
  Height: 900
"""
    Path(out_path).write_text(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--map-yaml", required=True)
    parser.add_argument("--height", type=float, default=0.80)
    args = parser.parse_args()

    generated = ROOT_DIR / "generated"
    config_dir = ROOT_DIR / "config"
    generated.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    mycobot_urdf = generated / "mycobot_280_jn_visual.urdf"
    obstacles_urdf = generated / "map_obstacles_3d.urdf"
    rviz_path = config_dir / "turtle_cobot_3d.rviz"

    mycobot_visual_urdf(mycobot_urdf)
    count = obstacle_urdf(Path(args.map_yaml), obstacles_urdf, args.height)
    rviz_config(rviz_path, mycobot_urdf, obstacles_urdf)

    print(f"Generated {obstacles_urdf} with {count} obstacle strips")
    print(f"Generated {mycobot_urdf}")
    print(f"Generated {rviz_path}")


if __name__ == "__main__":
    main()
