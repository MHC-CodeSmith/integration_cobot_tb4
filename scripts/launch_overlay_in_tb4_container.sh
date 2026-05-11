#!/usr/bin/env bash
set -euo pipefail

TB4_CONTAINER="${TB4_CONTAINER:-tb4_sim}"
TARGET_WS="/root/cobot_tb4_integration_ws"
JOINT_SOURCE="${1:-static}"

if [ "${JOINT_SOURCE}" != "static" ] && [ "${JOINT_SOURCE}" != "udp" ]; then
  echo "Uso: $0 [static|udp]"
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "${TB4_CONTAINER}"; then
  echo "[!] Container ${TB4_CONTAINER} nao esta rodando."
  exit 1
fi

docker exec -it "${TB4_CONTAINER}" bash -lc "
  source /opt/ros/jazzy/setup.bash
  source ${TARGET_WS}/install/setup.bash
  export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
  ros2 launch cobot_tb4_overlay integrated_scene.launch.py joint_source:=${JOINT_SOURCE}
"
