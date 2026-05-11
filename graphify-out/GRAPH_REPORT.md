# Graph Report - cobot_tb4_integration  (2026-05-11)

## Corpus Check
- 12 files · ~2,793 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 66 nodes · 75 edges · 12 communities (8 shown, 4 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `91aa4fb3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]

## God Nodes (most connected - your core abstractions)
1. `JointStateUdpReceiver` - 7 edges
2. `Cobot + TurtleBot4 Integration Overlay` - 7 edges
3. `UdpJointStateImporter` - 6 edges
4. `TableMarkerNode` - 6 edges
5. `JointStateUdpExporter` - 5 edges
6. `StaticCobotJointStatePublisher` - 5 edges
7. `Uso rapido` - 5 edges
8. `occupied_mask()` - 4 edges
9. `obstacle_urdf()` - 4 edges
10. `main()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `JointStateUdpReceiver` --inherits--> `Node`  [EXTRACTED]
  tools_mycobot_joint_udp_receiver.py →   _Bridges community 4 → community 2_
- `StaticCobotJointStatePublisher` --inherits--> `Node`  [EXTRACTED]
  ros2_ws/src/cobot_tb4_overlay/cobot_tb4_overlay/static_cobot_joint_state_publisher.py →   _Bridges community 4 → community 6_
- `UdpJointStateImporter` --inherits--> `Node`  [EXTRACTED]
  ros2_ws/src/cobot_tb4_overlay/cobot_tb4_overlay/udp_joint_state_importer.py →   _Bridges community 4 → community 5_
- `TableMarkerNode` --inherits--> `Node`  [EXTRACTED]
  ros2_ws/src/cobot_tb4_overlay/cobot_tb4_overlay/table_marker_node.py →   _Bridges community 4 → community 3_

## Communities (12 total, 4 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.13
Nodes (14): Cobot + TurtleBot4 Integration Overlay, code:text (map), code:bash (cd /home/mhc/Germany/turtlebot4_jazzy_docker), code:bash (cd /home/mhc/Germany/cobot_tb4_integration), code:text (Galactic/container /joint_states -> UDP -> Jazzy/host /mycob), code:bash (cd /home/mhc/Germany/cobot_tb4_integration), code:bash (cd /home/mhc/Germany/cobot_tb4_integration), code:bash (cd /home/mhc/Germany/cobot_tb4_integration) (+6 more)

### Community 1 - "Community 1"
Cohesion: 0.42
Nodes (8): main(), mycobot_visual_urdf(), obstacle_urdf(), occupied_mask(), parse_simple_yaml(), read_pgm(), row_runs(), rviz_config()

### Community 3 - "Community 3"
Cohesion: 0.43
Nodes (3): main(), TableMarkerNode, yaw_to_quaternion()

### Community 4 - "Community 4"
Cohesion: 0.4
Nodes (3): JointStateUdpExporter, main(), Node

## Knowledge Gaps
- **9 isolated node(s):** `Ideia`, `code:text (map)`, `code:bash (cd /home/mhc/Germany/turtlebot4_jazzy_docker)`, `code:bash (cd /home/mhc/Germany/cobot_tb4_integration)`, `code:text (Galactic/container /joint_states -> UDP -> Jazzy/host /mycob)` (+4 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `JointStateUdpReceiver` connect `Community 2` to `Community 4`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `TableMarkerNode` connect `Community 3` to `Community 4`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Why does `UdpJointStateImporter` connect `Community 5` to `Community 4`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **What connects `Ideia`, `code:text (map)`, `code:bash (cd /home/mhc/Germany/turtlebot4_jazzy_docker)` to the rest of the system?**
  _9 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.13 - nodes in this community are weakly interconnected._