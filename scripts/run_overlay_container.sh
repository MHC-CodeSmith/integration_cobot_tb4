#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-turtlebot4:jazzy}"
NAME="${OVERLAY_CONTAINER:-cobot_tb4_overlay}"
JOINT_SOURCE="${1:-static}"
MYCOBOT_DESCRIPTION_SRC="${MYCOBOT_DESCRIPTION_SRC:-/home/mhc/Germany/Cobot/mycobot_docker/custom_ws/src/mycobot_description}"

if [ "${JOINT_SOURCE}" != "static" ] && [ "${JOINT_SOURCE}" != "udp" ]; then
  echo "Uso: $0 [static|udp]"
  exit 1
fi

if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -qx "${IMAGE}"; then
  echo "[!] Imagem ${IMAGE} nao encontrada."
  echo "    Build esperado:"
  echo "    cd /home/mhc/Germany/turtlebot4_jazzy_docker && docker build --no-cache -t turtlebot4:jazzy ."
  exit 1
fi

if [ ! -d "${MYCOBOT_DESCRIPTION_SRC}" ]; then
  echo "[!] mycobot_description nao encontrado em ${MYCOBOT_DESCRIPTION_SRC}"
  exit 1
fi

if docker ps -aq --filter "name=^/${NAME}$" | grep -q .; then
  docker rm -f "${NAME}" >/dev/null 2>&1 || true
fi

echo "[*] Subindo overlay ${NAME} (${JOINT_SOURCE})..."
docker run -d \
  --name "${NAME}" \
  --net host \
  --ipc host \
  -v "${ROOT_DIR}:/root/integration:ro" \
  -v "${MYCOBOT_DESCRIPTION_SRC}:/root/mycobot_description:ro" \
  -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -e ROS_DOMAIN_ID=0 \
  -e ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET \
  -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4 \
  "${IMAGE}" bash -lc "
    set -eo pipefail
    source /opt/ros/jazzy/setup.bash
    rm -rf /root/cobot_tb4_overlay_ws
    mkdir -p /root/cobot_tb4_overlay_ws/src
    cp -a /root/integration/ros2_ws/src/cobot_tb4_overlay /root/cobot_tb4_overlay_ws/src/
    cp -a /root/mycobot_description /root/cobot_tb4_overlay_ws/src/
    cd /root/cobot_tb4_overlay_ws
    colcon build --symlink-install
    source install/setup.bash
    export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
    export ROS_DOMAIN_ID=0
    export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
    export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
    ros2 launch cobot_tb4_overlay integrated_scene.launch.py joint_source:=${JOINT_SOURCE}
  "

echo "[OK] Overlay em execucao no container ${NAME}."
echo "    Logs: docker logs -f ${NAME}"
