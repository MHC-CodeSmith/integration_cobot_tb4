#!/usr/bin/env bash
set -eo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCENE_PID_FILE="/tmp/cobot_tb4_env3d.pid"
RVIZ_PID_FILE="/tmp/cobot_tb4_3d_rviz.pid"
SCENE_LOG="/tmp/cobot_tb4_env3d.log"
RVIZ_LOG="/tmp/cobot_tb4_3d_rviz.log"
DISCOVERY_MODE="${COBOT_TB4_DISCOVERY_MODE:-auto}"

setup_ros_env() {
  had_nounset=0
  case "$-" in *u*) had_nounset=1; set +u ;; esac
  source /opt/ros/jazzy/setup.bash
  if [ "${had_nounset}" -eq 1 ]; then
    set -u
  fi
  export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
  export ROS_AUTOMATIC_DISCOVERY_RANGE="${ROS_AUTOMATIC_DISCOVERY_RANGE:-SUBNET}"
  export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"
  export COBOT_TB4_DISCOVERY_MODE="${DISCOVERY_MODE}"

  if [ "${DISCOVERY_MODE}" = "local" ]; then
    unset ROS_DISCOVERY_SERVER ROS_SUPER_CLIENT
  elif [ -n "${ROS_DISCOVERY_SERVER:-}" ]; then
    export ROS_SUPER_CLIENT="${ROS_SUPER_CLIENT:-True}"
  else
    unset ROS_DISCOVERY_SERVER ROS_SUPER_CLIENT
  fi
}

ros_env_for_child() {
  printf 'source /opt/ros/jazzy/setup.bash\n'
  printf 'export ROS_DOMAIN_ID=%q\n' "${ROS_DOMAIN_ID}"
  printf 'export ROS_AUTOMATIC_DISCOVERY_RANGE=%q\n' "${ROS_AUTOMATIC_DISCOVERY_RANGE}"
  printf 'export RMW_IMPLEMENTATION=%q\n' "${RMW_IMPLEMENTATION}"
  printf 'export COBOT_TB4_DISCOVERY_MODE=%q\n' "${COBOT_TB4_DISCOVERY_MODE}"
  if [ -n "${ROS_DISCOVERY_SERVER:-}" ]; then
    printf 'export ROS_DISCOVERY_SERVER=%q\n' "${ROS_DISCOVERY_SERVER}"
    printf 'export ROS_SUPER_CLIENT=%q\n' "${ROS_SUPER_CLIENT:-True}"
  else
    printf 'unset ROS_DISCOVERY_SERVER ROS_SUPER_CLIENT\n'
  fi
}

setup_ros_env

default_map_yaml() {
  local candidate
  for candidate in \
    "${B002_MAP_YAML:-}" \
    "${ROOT_DIR}/../turtlebot4_jazzy/maps/B002_map.yaml" \
    "/home/mhc/Germany/turtlebot4_jazzy/maps/B002_map.yaml"; do
    if [ -n "${candidate}" ] && [ -f "${candidate}" ]; then
      printf '%s\n' "${candidate}"
      return
    fi
  done
  printf '%s\n' "/home/mhc/Germany/turtlebot4_jazzy/maps/B002_map.yaml"
}

MAP_YAML="$(
  (ros2 param get /map_server yaml_filename 2>/dev/null || true) \
    | sed -n 's/^String value is: //p' \
    | tail -1
)"

if [ -z "${MAP_YAML}" ] || [ ! -f "${MAP_YAML}" ]; then
  MAP_YAML="$(default_map_yaml)"
fi

echo "[*] Mapa para obstaculos 3D: ${MAP_YAML}"
if [ -n "${ROS_DISCOVERY_SERVER:-}" ]; then
  echo "[*] DDS discovery: servidor ${ROS_DISCOVERY_SERVER} (ROS_SUPER_CLIENT=${ROS_SUPER_CLIENT:-True})"
else
  echo "[*] DDS discovery: local/subnet sem ROS_DISCOVERY_SERVER"
fi
python3 "${ROOT_DIR}/scripts/generate_3d_assets.py" \
  --map-yaml "${MAP_YAML}" \
  --scene-yaml "${ROOT_DIR}/config/b002_scene.yaml"

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

# Clean up the common manual starts of this same 3D view so stale processes
# do not keep old DDS environment variables or old URDF descriptions alive.
pkill -f "[r]os2 launch .*cobot_tb4_integration.*/launch/env3d.launch.py" >/dev/null 2>&1 || true
pkill -f "[r]os2 launch launch/env3d.launch.py" >/dev/null 2>&1 || true
pkill -f "[m]ap_obstacles_3d_state_publisher" >/dev/null 2>&1 || true
pkill -f "[u]rdf_marker_publisher_env3d" >/dev/null 2>&1 || true
pkill -f "[r]obot_description_publisher_env3d" >/dev/null 2>&1 || true
pkill -f "__ns:=/env3d_" >/dev/null 2>&1 || true
pkill -f "[r]viz2 -d ${ROOT_DIR}/config/turtle_cobot_3d.rviz" >/dev/null 2>&1 || true
sleep 1

setsid bash -lc "
  $(ros_env_for_child)
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
