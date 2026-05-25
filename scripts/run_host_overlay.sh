#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="/tmp/cobot_tb4_host_overlay.pid"
LOG_FILE="/tmp/cobot_tb4_host_overlay.log"
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

stop_overlay() {
  if [ -f "${PID_FILE}" ]; then
    old_pid="$(cat "${PID_FILE}")"
    if kill -0 "${old_pid}" >/dev/null 2>&1; then
      kill -- "-${old_pid}" >/dev/null 2>&1 || kill "${old_pid}" >/dev/null 2>&1 || true
      sleep 1
    fi
    rm -f "${PID_FILE}"
  fi
}

stop_joint_bridge() {
  "${ROOT_DIR}/scripts/start_mycobot_joint_exporter.sh" stop >/dev/null 2>&1 || true
}

case "${1:-start}" in
  start)
    setup_ros_env
    stop_overlay
    if ! "${ROOT_DIR}/scripts/start_mycobot_joint_exporter.sh" start; then
      echo "[!] Ponte de juntas reais do MyCobot nao iniciou; o braco 3D so atualiza quando /mycobot/joint_states existir."
    fi
    setsid bash -lc "
      $(ros_env_for_child)
      ros2 launch ${ROOT_DIR}/launch/host_overlay.launch.py
    " > "${LOG_FILE}" 2>&1 < /dev/null &
    echo "$!" > "${PID_FILE}"
    echo "[OK] Host overlay iniciado. PID=$(cat "${PID_FILE}")"
    echo "     Logs: tail -f ${LOG_FILE}"
    ;;
  stop)
    stop_overlay
    stop_joint_bridge
    echo "[OK] Host overlay parado."
    ;;
  status)
    if [ -f "${PID_FILE}" ] && kill -0 "$(cat "${PID_FILE}")" >/dev/null 2>&1; then
      echo "[OK] Rodando. PID=$(cat "${PID_FILE}")"
    else
      echo "[!] Nao esta rodando."
      exit 1
    fi
    ;;
  logs)
    tail -f "${LOG_FILE}"
    ;;
  *)
    echo "Uso: $0 [start|stop|status|logs]"
    exit 1
    ;;
esac
