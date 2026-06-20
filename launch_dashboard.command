#!/bin/zsh

set -e

cd "$(dirname "$0")"

if ! python3 -c "import flask" >/dev/null 2>&1; then
  echo "Installing dashboard dependencies..."
  python3 -m pip install -r requirements.txt
fi

URL_FILE="$(mktemp -t grant_dashboard_url.XXXXXX)"

cleanup() {
  rm -f "${URL_FILE}"
}
trap cleanup EXIT

DASHBOARD_URL_FILE="${URL_FILE}" python3 run_dashboard.py &
SERVER_PID=$!

for _ in {1..50}; do
  if [[ -s "${URL_FILE}" ]]; then
    DASHBOARD_URL="$(<"${URL_FILE}")"
    echo "Opening dashboard at ${DASHBOARD_URL}"
    ( sleep 1; open "${DASHBOARD_URL}" ) >/dev/null 2>&1 &
    wait "${SERVER_PID}"
    exit $?
  fi

  if ! kill -0 "${SERVER_PID}" >/dev/null 2>&1; then
    wait "${SERVER_PID}"
    exit $?
  fi

  sleep 0.2
done

echo "Dashboard started, but the URL could not be resolved automatically."
echo "Check the terminal output above for the exact address."
wait "${SERVER_PID}"
