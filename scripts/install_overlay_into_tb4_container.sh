#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TB4_CONTAINER="${TB4_CONTAINER:-tb4_sim}"
TARGET_WS="/root/cobot_tb4_integration_ws"
MYCOBOT_DESCRIPTION_SRC="${MYCOBOT_DESCRIPTION_SRC:-/home/mhc/Germany/Cobot/mycobot_docker/custom_ws/src/mycobot_description}"

if ! docker ps --format '{{.Names}}' | grep -qx "${TB4_CONTAINER}"; then
  echo "[!] Container ${TB4_CONTAINER} nao esta rodando."
  echo "    Inicie o TurtleBot4 primeiro:"
  echo "    cd /home/mhc/Germany/turtlebot4_jazzy && ./run_lab_world.sh true true 0.0 0.0 0.0"
  exit 1
fi

if [ ! -d "${MYCOBOT_DESCRIPTION_SRC}" ]; then
  echo "[!] mycobot_description nao encontrado em ${MYCOBOT_DESCRIPTION_SRC}"
  exit 1
fi

echo "[*] Preparando workspace de overlay em ${TB4_CONTAINER}:${TARGET_WS}"
docker exec "${TB4_CONTAINER}" bash -lc "rm -rf ${TARGET_WS} && mkdir -p ${TARGET_WS}/src"
docker cp "${ROOT_DIR}/ros2_ws/src/cobot_tb4_overlay" "${TB4_CONTAINER}:${TARGET_WS}/src/"
docker cp "${MYCOBOT_DESCRIPTION_SRC}" "${TB4_CONTAINER}:${TARGET_WS}/src/"

echo "[*] Build do overlay no container Jazzy..."
docker exec "${TB4_CONTAINER}" bash -lc "
  source /opt/ros/jazzy/setup.bash
  cd ${TARGET_WS}
  colcon build --symlink-install
"

echo "[OK] Overlay instalado."
