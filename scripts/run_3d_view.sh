#!/usr/bin/env bash
set -eo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCENE_PID_FILE="/tmp/cobot_tb4_env3d.pid"
RVIZ_PID_FILE="/tmp/cobot_tb4_3d_rviz.pid"
SCENE_LOG="/tmp/cobot_tb4_env3d.log"
RVIZ_LOG="/tmp/cobot_tb4_3d_rviz.log"

source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

MAP_YAML="$(
  ros2 param get /map_server yaml_filename 2>/dev/null \
    | sed -n 's/^String value is: //p' \
    | tail -1
)"

if [ -z "${MAP_YAML}" ] || [ ! -f "${MAP_YAML}" ]; then
  MAP_YAML="/home/mhc/Germany/turtlebot4_jazzy_docker/maps/mapa_quarto_final.yaml"
fi

echo "[*] Mapa para obstaculos 3D: ${MAP_YAML}"
python3 "${ROOT_DIR}/scripts/generate_3d_assets.py" --map-yaml "${MAP_YAML}" --height 0.80

"${ROOT_DIR}/scripts/run_host_overlay.sh" start >/dev/null

if [ -f "${SCENE_PID_FILE}" ]; then
  old_pid="$(cat "${SCENE_PID_FILE}")"
  if kill -0 "${old_pid}" >/dev/null 2>&1; then
    kill -- "-${old_pid}" >/dev/null 2>&1 || kill "${old_pid}" >/dev/null 2>&1 || true
    sleep 1
  fi
fi

if [ -f "${RVIZ_PID_FILE}" ]; then
  old_rviz_pid="$(cat "${RVIZ_PID_FILE}")"
  if kill -0 "${old_rviz_pid}" >/dev/null 2>&1; then
    kill "${old_rviz_pid}" >/dev/null 2>&1 || true
    sleep 1
  fi
fi

setsid bash -lc "
  source /opt/ros/jazzy/setup.bash
  export ROS_DOMAIN_ID=0
  export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
  export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
  ros2 launch ${ROOT_DIR}/launch/env3d.launch.py
" > "${SCENE_LOG}" 2>&1 < /dev/null &
echo "$!" > "${SCENE_PID_FILE}"

setsid rviz2 -d "${ROOT_DIR}/config/turtle_cobot_3d.rviz" \
  --ros-args -r __node:=rviz2_cobot_tb4_3d \
  > "${RVIZ_LOG}" 2>&1 < /dev/null &
echo "$!" > "${RVIZ_PID_FILE}"

echo "[OK] Janela RViz 3D solicitada."
echo "     Scene log: ${SCENE_LOG}"
echo "     RViz log:  ${RVIZ_LOG}"
