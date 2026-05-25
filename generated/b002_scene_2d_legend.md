# B002 3D Scene Overview

- Map: `/home/mhc/Germany/turtlebot4_jazzy_docker/maps/B002_map.yaml`
- Furniture URDF: `/home/mhc/Germany/cobot_tb4_integration/generated/room_furniture_3d.urdf`
- Parsed semantic objects/parts: `96`
- Coordinates are ROS `map` frame meters.

| ID | Area | Center `(x, y)` | Approx range | Meaning |
|---:|---|---:|---|---|
| 1 | Factory / ETS line | `(0.000, 2.150)` | `x -0.50..0.50, y 1.15..3.15` | Zona verde. Retangulo principal x=-0.5..0.5 e y=1.15..3.15. |
| 3 | PC + chairs L-desks | `(0.000, 5.905)` | `x -1.00..1.00, y 6.47..7.09; x 0.24..0.86, y 4.72..6.52` | Duas mesas em L: uma no fundo x=-1..1, outra encostada na parede direita. |
| 4 | Tables + boards | `(-4.450, 3.350)` | `x -5.10..-3.80, y 0.72..1.67; x -5.23..-3.68, y 4.72..5.97` | Mesas/boards separadas, com uma board/tela entre as duas. |
| 6 | Pillars | `(-1.500, 3.000)` | `(-1.80, -1.00) r 0.19; (-1.20, 7.00) r 0.19` | Pilares movidos para os pontos indicados. |
| 8 | MyCobot anchor | `(-0.338, 1.106)` | `r 0.12` | Frame map -> mycobot_base_link, z=0.80. |

Editing notes:

- Current `config/b002_scene.yaml` uses `semantic_overlay.mode: rich`; those objects are generated in `scripts/generate_3d_assets.py`, function `furniture_urdf()`.
- If you want easy YAML editing, switch to `semantic_overlay.mode: minimal` and edit the `objects:` list in `config/b002_scene.yaml`.
- The black occupied cells in the map are still the LiDAR-level source of truth. The semantic objects are visual hints only.
