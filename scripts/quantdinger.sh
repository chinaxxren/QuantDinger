#!/usr/bin/env bash
# Start/stop/restart the local QuantDinger backend and frontend without Docker.
# Kafka is not used. PostgreSQL must already be running.

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend_api_python"
FRONTEND_DIR="${ROOT_DIR}/QuantDinger-Vue"
ROOT_ENV_FILE="${ROOT_DIR}/.env"
BACKEND_ENV_FILE="${BACKEND_DIR}/.env"
ENV_FILE="${QD_ENV_FILE:-${ROOT_ENV_FILE}}"

# The repository template uses the root .env. Older local installations often
# still keep their runtime settings in backend_api_python/.env, so use that file
# automatically when the root file has no active DATABASE_URL.
env_has_value() {
  local file="$1"
  local key="$2"
  [[ -f "${file}" ]] && awk -F= -v key="${key}" \
    '$1 ~ "^[[:space:]]*" key "[[:space:]]*$" && $2 ~ /[^[:space:]]/ { found=1; exit } END { exit(found ? 0 : 1) }' \
    "${file}"
}

if [[ -z "${QD_ENV_FILE:-}" ]] && ! env_has_value "${ROOT_ENV_FILE}" DATABASE_URL && env_has_value "${BACKEND_ENV_FILE}" DATABASE_URL; then
  ENV_FILE="${BACKEND_ENV_FILE}"
fi

[[ -f "${ENV_FILE}" ]] && export QUANTDINGER_ENV_FILE="${ENV_FILE}"

STATE_DIR="${QD_STATE_DIR:-${ROOT_DIR}/.quantdinger}"
LOG_DIR="${STATE_DIR}/logs"
PID_DIR="${STATE_DIR}/pids"

BACKEND_PID_FILE="${PID_DIR}/backend.pid"
FRONTEND_PID_FILE="${PID_DIR}/frontend.pid"
MIGRATION_LOG="${LOG_DIR}/migration.log"
BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"

dotenv_value() {
  local key="$1"
  local fallback="$2"
  local value=""
  if [[ -f "${ENV_FILE}" ]]; then
    value="$(awk -F= -v key="${key}" '$1 ~ "^[[:space:]]*" key "[[:space:]]*$" { sub(/^[^=]*=/, ""); print; exit }' "${ENV_FILE}")"
  fi
  value="${value#\"}"
  value="${value%\"}"
  printf '%s' "${value:-${fallback}}"
}

BACKEND_PORT="${QD_BACKEND_PORT:-$(dotenv_value PYTHON_API_PORT 5000)}"
FRONTEND_HOST="${QD_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${QD_FRONTEND_PORT:-8000}"

PYTHON_BIN="${QD_PYTHON_BIN:-${BACKEND_DIR}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi

usage() {
  cat <<USAGE
用法: $(basename "$0") <start|stop|restart|status>

命令:
  start    初始化数据库并启动后端、前端
  stop     停止本脚本启动的后端、前端
  restart  先 stop，再 start
  status   查看后端、前端运行状态

默认地址:
  前端: http://${FRONTEND_HOST}:${FRONTEND_PORT}
  后端: http://127.0.0.1:${BACKEND_PORT}

可选环境变量:
  QD_PYTHON_BIN   指定 Python 解释器
  QD_STATE_DIR    指定 PID 和日志目录
  QD_BACKEND_PORT 覆盖后端端口（默认读取 .env 的 PYTHON_API_PORT）
  QD_FRONTEND_HOST / QD_FRONTEND_PORT 覆盖前端监听地址和端口
  QD_SKIP_MIGRATION=true 跳过启动前数据库迁移
USAGE
}

fail() {
  echo "[ERROR] $*" >&2
  exit 1
}

prepare_dirs() {
  mkdir -p "${LOG_DIR}" "${PID_DIR}"
}

require_file() {
  [[ -f "$1" ]] || fail "文件不存在: $1"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "找不到命令 '$1'，请先安装并加入 PATH"
}

read_pid() {
  local pid_file="$1"
  [[ -f "${pid_file}" ]] || return 1
  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  [[ "${pid}" =~ ^[0-9]+$ ]] || return 1
  printf '%s\n' "${pid}"
}

pid_is_running() {
  local pid="$1"
  kill -0 "${pid}" 2>/dev/null
}

process_status() {
  local name="$1"
  local pid_file="$2"
  local pid
  if pid="$(read_pid "${pid_file}")" && pid_is_running "${pid}"; then
    echo "${name}: running (pid ${pid})"
    return 0
  fi
  echo "${name}: stopped"
  return 1
}

cleanup_stale_pid() {
  local pid_file="$1"
  local pid
  if pid="$(read_pid "${pid_file}")" && ! pid_is_running "${pid}"; then
    rm -f "${pid_file}"
  elif [[ ! -f "${pid_file}" ]]; then
    :
  fi
}


tmux_session_name() {
  local name="$1"
  printf 'quantdinger-%s' "${name}"
}

tmux_available() {
  command -v tmux >/dev/null 2>&1
}

tmux_has_session() {
  local session_name="$1"
  tmux_available && tmux has-session -t "${session_name}" 2>/dev/null
}

shell_quote() {
  printf '%q' "$1"
}

wait_for_exit() {
  local pid="$1"
  local seconds=0
  while pid_is_running "${pid}" && (( seconds < 10 )); do
    sleep 1
    ((seconds += 1))
  done
  if pid_is_running "${pid}"; then
    echo "[WARN] PID ${pid} 未响应，发送 SIGKILL"
    kill -KILL "${pid}" 2>/dev/null || true
  fi
}

stop_process() {
  local name="$1"
  local pid_file="$2"
  local pid
  local session_name
  session_name="$(tmux_session_name "${name}")"

  if ! pid="$(read_pid "${pid_file}")"; then
    rm -f "${pid_file}"
    if tmux_has_session "${session_name}"; then
      tmux kill-session -t "${session_name}" 2>/dev/null || true
      echo "${name}: stopped"
    else
      echo "${name}: already stopped"
    fi
    return 0
  fi

  if ! pid_is_running "${pid}"; then
    rm -f "${pid_file}"
    tmux_has_session "${session_name}" && tmux kill-session -t "${session_name}" 2>/dev/null || true
    echo "${name}: already stopped (stale pid removed)"
    return 0
  fi

  echo "Stopping ${name} (pid ${pid})..."
  kill -TERM "${pid}" 2>/dev/null || true
  wait_for_exit "${pid}"
  tmux_has_session "${session_name}" && tmux kill-session -t "${session_name}" 2>/dev/null || true
  rm -f "${pid_file}"
  echo "${name}: stopped"
}

start_process() {
  local name="$1"
  local pid_file="$2"
  local log_file="$3"
  shift 3
  local pid

  if pid="$(read_pid "${pid_file}")" && pid_is_running "${pid}"; then
    echo "${name}: already running (pid ${pid})"
    return 0
  fi
  rm -f "${pid_file}"
  : >"${log_file}"

  # Prefer tmux when available because it survives launcher/terminal cleanup
  # reliably on macOS. Set QD_USE_TMUX=false to force the portable nohup path.
  if [[ "${QD_USE_TMUX:-auto}" != "false" ]] && tmux_available; then
    local session_name
    local quoted_root
    local quoted_log
    local command_line
    local arg
    session_name="$(tmux_session_name "${name}")"
    tmux_has_session "${session_name}" && tmux kill-session -t "${session_name}" 2>/dev/null || true
    quoted_root="$(shell_quote "${ROOT_DIR}")"
    quoted_log="$(shell_quote "${log_file}")"
    command_line="cd ${quoted_root} && exec"
    for arg in "$@"; do
      command_line+=" $(shell_quote "${arg}")"
    done
    command_line+=" >>${quoted_log} 2>&1"
    tmux new-session -d -s "${session_name}" "${command_line}"
    sleep 0.2
    pid="$(tmux display-message -p -t "${session_name}" '#{pane_pid}' 2>/dev/null || true)"
    [[ "${pid}" =~ ^[0-9]+$ ]] || fail "无法获取 ${name} 的 tmux 进程 PID"
  else
    # Without nohup/disown, a service can receive SIGHUP when `quantdinger.sh`
    # exits, producing a false successful start followed by an immediate stop.
    nohup "$@" >>"${log_file}" 2>&1 </dev/null &
    pid=$!
    disown "${pid}" 2>/dev/null || true
  fi

  printf '%s\n' "${pid}" >"${pid_file}"
  echo "${name}: started (pid ${pid})"
}

wait_for_http() {
  local name="$1"
  local url="$2"
  local pid_file="$3"
  local log_file="$4"
  local attempts=0

  while (( attempts < 30 )); do
    if ! pid="$(read_pid "${pid_file}")" || ! pid_is_running "${pid}"; then
      echo "[ERROR] ${name} 启动失败，进程已退出。详细日志: ${log_file}" >&2
      tail -n 50 "${log_file}" >&2 || true
      return 1
    fi
    if curl --silent --show-error --fail --max-time 2 "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    ((attempts += 1))
  done

  echo "[ERROR] ${name} 启动超时，无法访问 ${url}。详细日志: ${log_file}" >&2
  tail -n 50 "${log_file}" >&2 || true
  return 1
}

run_migration() {
  if [[ "${QD_SKIP_MIGRATION:-false}" == "true" ]]; then
    echo "Skipping database migration (QD_SKIP_MIGRATION=true)"
    return 0
  fi

  echo "Applying database migrations..."
  (
    cd "${BACKEND_DIR}"
    QD_PROCESS_ROLE=migration "${PYTHON_BIN}" -m app.commands.migrate
  ) >>"${MIGRATION_LOG}" 2>&1 || {
    echo "[ERROR] 数据库迁移失败，详细日志: ${MIGRATION_LOG}" >&2
    tail -n 30 "${MIGRATION_LOG}" >&2 || true
    exit 1
  }
}

start_backend() {
  require_file "${ENV_FILE}"
  require_file "${BACKEND_DIR}/run.py"
  [[ -x "${PYTHON_BIN}" ]] || fail "找不到 Python 虚拟环境: ${BACKEND_DIR}/.venv/bin/python"

  start_process "backend" "${BACKEND_PID_FILE}" "${BACKEND_LOG}" \
    env QD_PROCESS_ROLE=legacy STRATEGY_COMMANDS_ENABLED=false \
    PYTHON_API_HOST="${PYTHON_API_HOST:-127.0.0.1}" \
    PYTHON_API_PORT="${BACKEND_PORT}" \
    PYTHON_API_DEBUG="${QD_PYTHON_API_DEBUG:-false}" \
    "${PYTHON_BIN}" "${BACKEND_DIR}/run.py"
}

start_frontend() {
  require_file "${FRONTEND_DIR}/package.json"
  require_file "${FRONTEND_DIR}/node_modules/.bin/vite"
  require_command pnpm

  start_process "frontend" "${FRONTEND_PID_FILE}" "${FRONTEND_LOG}" \
    env VITE_DEV_PROXY_TARGET="${VITE_DEV_PROXY_TARGET:-http://127.0.0.1:${BACKEND_PORT}}" \
    pnpm --dir "${FRONTEND_DIR}" exec vite --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}"
}

start_all() {
  prepare_dirs
  require_file "${ENV_FILE}"
  require_command pnpm
  [[ -x "${PYTHON_BIN}" ]] || fail "找不到 Python 解释器，请先创建 backend_api_python/.venv"

  cleanup_stale_pid "${BACKEND_PID_FILE}"
  cleanup_stale_pid "${FRONTEND_PID_FILE}"

  run_migration
  start_backend
  if ! wait_for_http "backend" "http://127.0.0.1:${BACKEND_PORT}/api/health" "${BACKEND_PID_FILE}" "${BACKEND_LOG}"; then
    stop_process "backend" "${BACKEND_PID_FILE}" || true
    exit 1
  fi

  start_frontend
  if ! wait_for_http "frontend" "http://${FRONTEND_HOST}:${FRONTEND_PORT}/" "${FRONTEND_PID_FILE}" "${FRONTEND_LOG}"; then
    stop_process "frontend" "${FRONTEND_PID_FILE}" || true
    stop_process "backend" "${BACKEND_PID_FILE}" || true
    exit 1
  fi

  echo
  echo "QuantDinger 已启动"
  echo "前端: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
  echo "后端: http://127.0.0.1:${BACKEND_PORT}/api/health"
  echo "环境文件: ${ENV_FILE}"
  echo "日志: ${LOG_DIR}"
}

stop_all() {
  prepare_dirs
  stop_process "frontend" "${FRONTEND_PID_FILE}"
  stop_process "backend" "${BACKEND_PID_FILE}"
}

status_all() {
  prepare_dirs
  local result=0
  process_status "backend" "${BACKEND_PID_FILE}" || result=1
  process_status "frontend" "${FRONTEND_PID_FILE}" || result=1
  return "${result}"
}

main() {
  local action="${1:-}"
  case "${action}" in
    start)
      start_all
      ;;
    stop)
      stop_all
      ;;
    restart)
      stop_all
      start_all
      ;;
    status)
      status_all
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"
