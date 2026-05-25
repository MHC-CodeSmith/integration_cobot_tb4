#!/usr/bin/env python3
import argparse
import math
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Ellipse, Polygon, Rectangle

from generate_3d_assets import parse_simple_yaml, read_pgm


ROOT_DIR = Path(__file__).resolve().parents[1]


def default_map_yaml():
    env_path = os.environ.get("B002_MAP_YAML")
    candidates = [
        Path(env_path) if env_path else None,
        ROOT_DIR.parent / "turtlebot4_jazzy" / "maps" / "B002_map.yaml",
        Path("/home/mhc/Germany/turtlebot4_jazzy/maps/B002_map.yaml"),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return candidates[-1]


DEFAULT_MAP_YAML = default_map_yaml()
DEFAULT_FURNITURE_URDF = ROOT_DIR / "generated" / "room_furniture_3d.urdf"
DEFAULT_OUT_PNG = ROOT_DIR / "generated" / "b002_scene_2d_overview.png"
DEFAULT_OUT_MD = ROOT_DIR / "generated" / "b002_scene_2d_legend.md"


GROUPS = [
    {
        "id": "1",
        "name": "Factory / ETS line",
        "kind": "rectangle",
        "center": (0.00, 2.15),
        "size": (1.00, 2.00),
        "color": "#16a34a",
        "note": "Zona verde. Retangulo principal x=-0.5..0.5 e y=1.15..3.15.",
    },
    {
        "id": "3",
        "name": "PC + chairs L-desks",
        "kind": "multi_rect",
        "rects": [
            {"center": (0.00, 6.78), "size": (2.00, 0.62)},
            {"center": (0.55, 5.62), "size": (0.62, 1.80)},
        ],
        "color": "#f97316",
        "note": "Duas mesas em L: uma no fundo x=-1..1, outra encostada na parede direita.",
    },
    {
        "id": "4",
        "name": "Tables + boards",
        "kind": "multi_rect",
        "rects": [
            {"center": (-4.45, 1.20), "size": (1.30, 0.95)},
            {"center": (-4.45, 5.35), "size": (1.55, 1.25)},
        ],
        "color": "#db2777",
        "note": "Mesas/boards separadas, com uma board/tela entre as duas.",
    },
    {
        "id": "6",
        "name": "Pillars",
        "kind": "multi_circle",
        "circles": [
            {"center": (-1.80, -1.00), "radius": 0.19},
            {"center": (-1.20, 7.00), "radius": 0.19},
        ],
        "color": "#64748b",
        "note": "Pilares movidos para os pontos indicados.",
    },
    {
        "id": "8",
        "name": "MyCobot anchor",
        "kind": "circle",
        "center": (-0.338416188955307, 1.1060110330581665),
        "radius": 0.12,
        "color": "#0ea5e9",
        "note": "Frame map -> mycobot_base_link, z=0.80.",
    },
]


def load_map_image(map_yaml):
    meta = parse_simple_yaml(map_yaml)
    image = Path(str(meta["image"]))
    if not image.is_absolute():
        image = Path(map_yaml).parent / image
    width, height, pixels = read_pgm(image)
    resolution = float(meta.get("resolution", 0.05))
    origin = meta.get("origin", [0.0, 0.0, 0.0])
    ox, oy = float(origin[0]), float(origin[1])
    arr = np.array(pixels, dtype=np.uint8).reshape((height, width))
    extent = [ox, ox + width * resolution, oy, oy + height * resolution]
    return arr, extent, resolution


def parse_rpy(rpy_text):
    values = [float(v) for v in (rpy_text or "0 0 0").split()]
    while len(values) < 3:
        values.append(0.0)
    return values[:3]


def parse_xyz(xyz_text):
    values = [float(v) for v in (xyz_text or "0 0 0").split()]
    while len(values) < 3:
        values.append(0.0)
    return values[:3]


def parse_color(rgba_text):
    values = [float(v) for v in (rgba_text or "0.6 0.6 0.6 0.5").split()]
    while len(values) < 4:
        values.append(1.0)
    return tuple(values[:4])


def furniture_shapes(urdf_path):
    tree = ET.parse(urdf_path)
    root = tree.getroot()

    materials = {}
    for material in root.findall("material"):
        color = material.find("color")
        if color is not None:
            materials[material.attrib.get("name", "")] = parse_color(color.attrib.get("rgba"))

    joints = {}
    for joint in root.findall("joint"):
        child = joint.find("child")
        origin = joint.find("origin")
        if child is None or origin is None:
            continue
        joints[child.attrib["link"]] = {
            "xyz": parse_xyz(origin.attrib.get("xyz")),
            "rpy": parse_rpy(origin.attrib.get("rpy")),
        }

    shapes = []
    for link in root.findall("link"):
        name = link.attrib.get("name", "")
        visual = link.find("visual")
        if visual is None or name not in joints:
            continue
        geometry = visual.find("geometry")
        if geometry is None:
            continue
        material = visual.find("material")
        color = (0.45, 0.45, 0.45, 0.45)
        if material is not None:
            color = materials.get(material.attrib.get("name", ""), color)

        pose = joints[name]
        cx, cy, cz = pose["xyz"]
        roll, pitch, yaw = pose["rpy"]
        box = geometry.find("box")
        cylinder = geometry.find("cylinder")
        if box is not None:
            sx, sy, sz = [float(v) for v in box.attrib["size"].split()]
            shapes.append({
                "type": "box",
                "name": name,
                "center": (cx, cy),
                "size": (sx, sy),
                "z": cz,
                "height": sz,
                "yaw": yaw,
                "color": color,
            })
        elif cylinder is not None:
            radius = float(cylinder.attrib["radius"])
            length = float(cylinder.attrib["length"])
            horizontal = abs(abs(roll) - math.pi / 2.0) < 0.1 or abs(abs(pitch) - math.pi / 2.0) < 0.1
            shapes.append({
                "type": "cylinder",
                "name": name,
                "center": (cx, cy),
                "radius": radius,
                "length": length,
                "horizontal": horizontal,
                "z": cz,
                "yaw": yaw,
                "color": color,
            })
    return shapes


def rect_corners(cx, cy, sx, sy, yaw):
    dx = sx / 2.0
    dy = sy / 2.0
    corners = [(-dx, -dy), (dx, -dy), (dx, dy), (-dx, dy)]
    c = math.cos(yaw)
    s = math.sin(yaw)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in corners]


def draw_shape(ax, shape, alpha_scale=0.62, linewidth=0.45):
    color = shape["color"]
    rgba = (color[0], color[1], color[2], min(max(color[3] * alpha_scale, 0.18), 0.72))
    edge = (color[0], color[1], color[2], 0.95)
    if shape["type"] == "box":
        cx, cy = shape["center"]
        sx, sy = shape["size"]
        poly = Polygon(rect_corners(cx, cy, sx, sy, shape["yaw"]), closed=True,
                       facecolor=rgba, edgecolor=edge, linewidth=linewidth)
        ax.add_patch(poly)
    else:
        cx, cy = shape["center"]
        if shape["horizontal"]:
            patch = Ellipse((cx, cy), width=shape["radius"] * 2.0, height=shape["length"],
                            angle=math.degrees(shape["yaw"]), facecolor=rgba,
                            edgecolor=edge, linewidth=linewidth)
        else:
            patch = Circle((cx, cy), radius=shape["radius"], facecolor=rgba,
                           edgecolor=edge, linewidth=linewidth)
        ax.add_patch(patch)


def draw_group(ax, group):
    color = group["color"]
    if group["kind"] == "rectangle":
        cx, cy = group["center"]
        sx, sy = group["size"]
        patch = Rectangle((cx - sx / 2.0, cy - sy / 2.0), sx, sy,
                          facecolor="none", edgecolor=color, linewidth=2.2)
        ax.add_patch(patch)
        label_x = cx - sx / 2.0 + 0.05
        label_y = cy + sy / 2.0 - 0.18
    elif group["kind"] == "circle":
        cx, cy = group["center"]
        patch = Circle((cx, cy), radius=group["radius"], facecolor="none",
                       edgecolor=color, linewidth=2.2)
        ax.add_patch(patch)
        label_x = cx + 0.15
        label_y = cy + 0.15
    elif group["kind"] == "multi_rect":
        label_x = label_y = None
        for rect in group["rects"]:
            cx, cy = rect["center"]
            sx, sy = rect["size"]
            patch = Rectangle((cx - sx / 2.0, cy - sy / 2.0), sx, sy,
                              facecolor="none", edgecolor=color, linewidth=2.2)
            ax.add_patch(patch)
            if label_x is None:
                label_x = cx - sx / 2.0 + 0.05
                label_y = cy + sy / 2.0 - 0.18
    elif group["kind"] == "multi_circle":
        label_x = label_y = None
        for circle in group["circles"]:
            cx, cy = circle["center"]
            patch = Circle((cx, cy), radius=circle["radius"], facecolor="none",
                           edgecolor=color, linewidth=2.2)
            ax.add_patch(patch)
            if label_x is None:
                label_x = cx + 0.18
                label_y = cy + 0.18
    else:
        raise ValueError(f"Unsupported group kind: {group['kind']}")
    ax.text(label_x, label_y, group["id"], fontsize=10, fontweight="bold",
            color="white", ha="center", va="center",
            bbox={"boxstyle": "circle,pad=0.22", "facecolor": color, "edgecolor": "white", "linewidth": 0.9})


def group_center_and_bounds(group):
    if group["kind"] == "rectangle":
        cx, cy = group["center"]
        sx, sy = group["size"]
        return (cx, cy), f"x {cx - sx / 2.0:.2f}..{cx + sx / 2.0:.2f}, y {cy - sy / 2.0:.2f}..{cy + sy / 2.0:.2f}"
    if group["kind"] == "circle":
        cx, cy = group["center"]
        return (cx, cy), f"r {group['radius']:.2f}"
    if group["kind"] == "multi_rect":
        centers = [rect["center"] for rect in group["rects"]]
        min_x = min(cx - rect["size"][0] / 2.0 for rect, (cx, _cy) in zip(group["rects"], centers))
        max_x = max(cx + rect["size"][0] / 2.0 for rect, (cx, _cy) in zip(group["rects"], centers))
        min_y = min(cy - rect["size"][1] / 2.0 for rect, (_cx, cy) in zip(group["rects"], centers))
        max_y = max(cy + rect["size"][1] / 2.0 for rect, (_cx, cy) in zip(group["rects"], centers))
        center = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
        parts = []
        for rect in group["rects"]:
            cx, cy = rect["center"]
            sx, sy = rect["size"]
            parts.append(f"x {cx - sx / 2.0:.2f}..{cx + sx / 2.0:.2f}, y {cy - sy / 2.0:.2f}..{cy + sy / 2.0:.2f}")
        return center, "; ".join(parts)
    if group["kind"] == "multi_circle":
        centers = [circle["center"] for circle in group["circles"]]
        center = (sum(cx for cx, _cy in centers) / len(centers), sum(cy for _cx, cy in centers) / len(centers))
        parts = [f"({cx:.2f}, {cy:.2f}) r {circle['radius']:.2f}"
                 for circle, (cx, cy) in zip(group["circles"], centers)]
        return center, "; ".join(parts)
    raise ValueError(f"Unsupported group kind: {group['kind']}")


def write_legend(path, map_yaml, furniture_urdf, shapes):
    lines = [
        "# B002 3D Scene Overview",
        "",
        f"- Map: `{map_yaml}`",
        f"- Furniture URDF: `{furniture_urdf}`",
        f"- Parsed semantic objects/parts: `{len(shapes)}`",
        "- Coordinates are ROS `map` frame meters.",
        "",
        "| ID | Area | Center `(x, y)` | Approx range | Meaning |",
        "|---:|---|---:|---|---|",
    ]
    for group in GROUPS:
        (cx, cy), bounds = group_center_and_bounds(group)
        lines.append(
            f"| {group['id']} | {group['name']} | `({cx:.3f}, {cy:.3f})` | `{bounds}` | {group['note']} |"
        )
    lines.extend([
        "",
        "Editing notes:",
        "",
        "- Current `config/b002_scene.yaml` uses `semantic_overlay.mode: rich`; those objects are generated in `scripts/generate_3d_assets.py`, function `furniture_urdf()`.",
        "- If you want easy YAML editing, switch to `semantic_overlay.mode: minimal` and edit the `objects:` list in `config/b002_scene.yaml`.",
        "- The black occupied cells in the map are still the LiDAR-level source of truth. The semantic objects are visual hints only.",
        "",
    ])
    Path(path).write_text("\n".join(lines))


def render(map_yaml, furniture_urdf, out_png, out_md):
    arr, extent, _resolution = load_map_image(map_yaml)
    shapes = furniture_shapes(furniture_urdf)

    fig = plt.figure(figsize=(15.5, 10.2), dpi=150)
    gs = fig.add_gridspec(1, 2, width_ratios=[4.7, 1.55], wspace=0.04)
    ax = fig.add_subplot(gs[0, 0])
    legend_ax = fig.add_subplot(gs[0, 1])

    ax.imshow(arr, cmap="gray", origin="upper", extent=extent, interpolation="nearest", alpha=0.90)
    for shape in shapes:
        draw_shape(ax, shape)
    for group in GROUPS:
        draw_group(ax, group)

    ax.set_title("B002 semantic 3D objects over LiDAR map", fontsize=14, fontweight="bold")
    ax.set_xlabel("x in map frame (m)")
    ax.set_ylabel("y in map frame (m)")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(extent[0] - 0.15, extent[1] + 0.15)
    ax.set_ylim(extent[2] - 0.15, extent[3] + 0.15)
    ax.set_xticks(np.arange(math.floor(extent[0]), math.ceil(extent[1]) + 1, 1.0))
    ax.set_yticks(np.arange(math.floor(extent[2]), math.ceil(extent[3]) + 1, 1.0))
    ax.grid(True, color="#8a8a8a", linewidth=0.45, alpha=0.45)
    ax.scatter([-0.338416188955307], [1.1060110330581665], s=60, c="#0ea5e9",
               edgecolors="white", linewidths=1.0, zorder=20)
    ax.text(-0.338416188955307 + 0.12, 1.1060110330581665 + 0.10,
            "MyCobot anchor", fontsize=8.5, color="#075985",
            bbox={"facecolor": "white", "edgecolor": "#0ea5e9", "alpha": 0.82, "pad": 2})

    legend_ax.axis("off")
    legend_ax.set_title("Legenda", fontsize=13, fontweight="bold", loc="left")
    y = 0.96
    legend_ax.text(0.00, y, "Base", fontsize=10, fontweight="bold", transform=legend_ax.transAxes)
    y -= 0.045
    legend_ax.add_patch(Rectangle((0.00, y - 0.005), 0.08, 0.025, transform=legend_ax.transAxes,
                                  facecolor="#111827", edgecolor="#111827"))
    legend_ax.text(0.11, y, "Preto/cinza: mapa YAML visto pelo LiDAR (~20 cm)", fontsize=8.6,
                   transform=legend_ax.transAxes, va="center")
    y -= 0.06
    legend_ax.text(0.00, y, "Areas semanticas", fontsize=10, fontweight="bold", transform=legend_ax.transAxes)
    y -= 0.045
    for group in GROUPS:
        legend_ax.add_patch(Rectangle((0.00, y - 0.012), 0.08, 0.028, transform=legend_ax.transAxes,
                                      facecolor=group["color"], edgecolor="black", alpha=0.72))
        (cx, cy), _bounds = group_center_and_bounds(group)
        if group["kind"] == "rectangle":
            sx, sy = group["size"]
            line = f"{group['id']} {group['name']}\ncenter ({cx:.2f}, {cy:.2f}), size {sx:.2f} x {sy:.2f}"
        elif group["kind"] == "multi_rect":
            line = f"{group['id']} {group['name']}\n{len(group['rects'])} retangulos, center approx ({cx:.2f}, {cy:.2f})"
        elif group["kind"] == "multi_circle":
            line = f"{group['id']} {group['name']}\n{len(group['circles'])} pontos, center approx ({cx:.2f}, {cy:.2f})"
        else:
            line = f"{group['id']} {group['name']}\ncenter ({cx:.2f}, {cy:.2f})"
        legend_ax.text(0.11, y, line, fontsize=8.2, transform=legend_ax.transAxes, va="center")
        y -= 0.082
    y -= 0.01
    legend_ax.text(0.00, y, "Notas", fontsize=10, fontweight="bold", transform=legend_ax.transAxes)
    y -= 0.045
    notes = [
        f"Objetos/partes desenhados: {len(shapes)}",
        "As caixas coloridas grandes sao zonas; as formas menores sao partes do modelo 3D.",
        "Coordenadas em metros no frame map.",
        "Para editar o rich scene: scripts/generate_3d_assets.py -> furniture_urdf().",
    ]
    for note in notes:
        legend_ax.text(0.00, y, f"- {note}", fontsize=8.0, transform=legend_ax.transAxes, va="top", wrap=True)
        y -= 0.055

    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)
    write_legend(out_md, map_yaml, furniture_urdf, shapes)
    return len(shapes)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--map-yaml", default=str(DEFAULT_MAP_YAML))
    parser.add_argument("--furniture-urdf", default=str(DEFAULT_FURNITURE_URDF))
    parser.add_argument("--out-png", default=str(DEFAULT_OUT_PNG))
    parser.add_argument("--out-md", default=str(DEFAULT_OUT_MD))
    args = parser.parse_args()

    count = render(Path(args.map_yaml), Path(args.furniture_urdf), Path(args.out_png), Path(args.out_md))
    print(f"Rendered {args.out_png} with {count} semantic objects/parts")
    print(f"Wrote {args.out_md}")


if __name__ == "__main__":
    main()
