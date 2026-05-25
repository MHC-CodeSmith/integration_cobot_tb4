#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MYCOBOT_CONTAINER="${MYCOBOT_CONTAINER:-mycobot_ros2}"
SOURCE_TOPIC="${MYCOBOT_JOINT_SOURCE_TOPIC:-/joint_states}"
PORT="${MYCOBOT_JOINT_UDP_PORT:-30242}"
EXPORTER_IN_CONTAINER="/tmp/mycobot_joint_udp_exporter.py"
EXPORTER_LOG_IN_CONTAINER="/tmp/mycobot_joint_udp_exporter.log"
RECEIVER_PID_FILE="/tmp/cobot_tb4_mycobot_joint_receiver.pid"
RECEIVER_LOG="/tmp/cobot_tb4_mycobot_joint_receiver.log"
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

container_is_running() {
  docker ps --format '{{.Names}}' | grep -qx "${MYCOBOT_CONTAINER}"
}

stop_receiver() {
  if [ -f "${RECEIVER_PID_FILE}" ]; then
    old_pid="$(cat "${RECEIVER_PID_FILE}")"
    if kill -0 "${old_pid}" >/dev/null 2>&1; then
      kill -- "-${old_pid}" >/dev/null 2>&1 || kill "${old_pid}" >/dev/null 2>&1 || true
      sleep 1
    fi
    rm -f "${RECEIVER_PID_FILE}"
  fi
}

stop_exporter() {
  if container_is_running; then
    docker exec "${MYCOBOT_CONTAINER}" bash -lc \
      "pkill -f '${EXPORTER_IN_CONTAINER}.*--port ${PORT}' || true" >/dev/null 2>&1 || true
  fi
}

container_host_ip() {
  docker exec "${MYCOBOT_CONTAINER}" bash -lc "ip route | awk '/default/ {print \$3; exit}'" 2>/dev/null \
    | tr -d '\r' \
    | head -1
}

start_receiver() {
  setup_ros_env
  stop_receiver
  setsid bash -lc "
    $(ros_env_for_child)
    python3 ${ROOT_DIR}/tools_mycobot_joint_udp_receiver.py \
      --bind 0.0.0.0 \
      --port ${PORT} \
      --topic /mycobot/joint_states
  " > "${RECEIVER_LOG}" 2>&1 < /dev/null &
  echo "$!" > "${RECEIVER_PID_FILE}"
}

start_exporter() {
  if ! container_is_running; then
    echo "[!] Container ${MYCOBOT_CONTAINER} nao esta rodando."
    echo "    Inicie o MyCobot como de costume: cd /home/mhc/Germany/Cobot && ./mycobot_docker/RUN_PLANNING_PC.sh"
    return 1
  fi

  stop_exporter
  docker cp "${ROOT_DIR}/tools_mycobot_joint_udp_exporter.py" "${MYCOBOT_CONTAINER}:${EXPORTER_IN_CONTAINER}" >/dev/null

  host_ip="${MYCOBOT_JOINT_HOST:-$(container_host_ip)}"
  if [ -z "${host_ip}" ]; then
    host_ip="172.17.0.1"
  fi

  docker exec -d "${MYCOBOT_CONTAINER}" bash -lc "
    source /opt/ros/galactic/setup.bash
    source /root/custom_ws/install/setup.bash
    export ROS_DOMAIN_ID=42
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    export CYCLONEDDS_URI=/root/custom_ws/cyclonedds_pc.xml
    export PYTHONUNBUFFERED=1
    python3 ${EXPORTER_IN_CONTAINER} \
      --topic ${SOURCE_TOPIC} \
      --host ${host_ip} \
      --port ${PORT} \
      > ${EXPORTER_LOG_IN_CONTAINER} 2>&1
  " >/dev/null

  echo "${host_ip}"
}

case "${1:-start}" in
  start)
    start_receiver
    if ! host_ip="$(start_exporter)"; then
      stop_receiver
      exit 1
    fi
    echo "[OK] Ponte de juntas MyCobot iniciada."
    echo "     Galactic/container ${SOURCE_TOPIC} -> udp://${host_ip}:${PORT} -> Jazzy/host /mycobot/joint_states"
    echo "     Receiver log: tail -f ${RECEIVER_LOG}"
    echo "     Exporter log: docker exec ${MYCOBOT_CONTAINER} tail -f ${EXPORTER_LOG_IN_CONTAINER}"
    ;;
  stop)
    stop_exporter
    stop_receiver
    echo "[OK] Ponte de juntas MyCobot parada."
    ;;
  status)
    if [ -f "${RECEIVER_PID_FILE}" ] && kill -0 "$(cat "${RECEIVER_PID_FILE}")" >/dev/null 2>&1; then
      echo "[OK] Receiver host rodando. PID=$(cat "${RECEIVER_PID_FILE}")"
    else
      echo "[!] Receiver host nao esta rodando."
      exit 1
    fi

    if container_is_running && docker exec "${MYCOBOT_CONTAINER}" pgrep -f "${EXPORTER_IN_CONTAINER}.*--port ${PORT}" >/dev/null 2>&1; then
      echo "[OK] Exporter container rodando."
    else
      echo "[!] Exporter container nao esta rodando."
      exit 1
    fi
    ;;
  logs)
    tail -f "${RECEIVER_LOG}"
    ;;
  *)
    echo "Uso: $0 [start|stop|status|logs]"
    exit 1
    ;;
esac
