#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="/tmp/cobot_tb4_host_overlay.pid"
LOG_FILE="/tmp/cobot_tb4_host_overlay.log"

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
    stop_overlay
    if ! "${ROOT_DIR}/scripts/start_mycobot_joint_exporter.sh" start; then
      echo "[!] Ponte de juntas reais do MyCobot nao iniciou; o braco 3D so atualiza quando /mycobot/joint_states existir."
    fi
    setsid bash -lc "
      source /opt/ros/jazzy/setup.bash
      export ROS_DOMAIN_ID=0
      export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
      export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
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
