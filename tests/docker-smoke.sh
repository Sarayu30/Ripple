#!/usr/bin/env bash
# Uses the CI PostgreSQL service and disposable credentials, never live secrets.
set -euo pipefail
docker build -t ripple-startup-test .
cleanup() {
  docker logs ripple-startup-test 2>/dev/null || true
  docker rm -f ripple-startup-test >/dev/null 2>&1 || true
}
trap cleanup EXIT
for port in 10000 10001; do
  port_args=()
  if [ "$port" = 10001 ]; then port_args=(-e PORT=10001); fi
  docker run -d --name ripple-startup-test --network host \
    -e DATABASE_URL -e DATABASE_SCHEMA=ripple_container_test \
    -e APP_ENV=production -e AUTH_MODE=local \
    -e APP_PASSWORD=disposable-ci-password-not-a-real-secret \
    -e ORIGIN_SECRET=disposable-ci-origin-not-a-real-secret \
    -e PUBLIC_ORIGIN=https://fixture.example.com -e ALLOWED_HOSTS=127.0.0.1 \
    -e DATA_DIR=/app/data -e JOB_MODE=durable -e MAX_RUNNING_JOBS=1 \
    "${port_args[@]}" ripple-startup-test
  ready=0
  for attempt in {1..45}; do
    if curl --fail --silent --max-time 3 "http://127.0.0.1:$port/healthz" > /tmp/ripple-startup-health.json; then
      ready=1
      break
    fi
    sleep 2
  done
  test "$ready" = 1
  python -c 'import json; assert json.load(open("/tmp/ripple-startup-health.json")) == {"status": "ready"}'
  test "$(docker exec ripple-startup-test id -u)" != 0
  test "$(curl --silent --output /dev/null --write-out '%{http_code}' "http://127.0.0.1:$port/")" = 403
  # Graceful shutdown must release ownership before the next startup.
  docker stop --time 30 ripple-startup-test
  case "$(docker inspect --format '{{.State.ExitCode}}' ripple-startup-test)" in
    0|143) ;; # Uvicorn may propagate SIGTERM after graceful cleanup.
    *) exit 1 ;;
  esac
  docker rm ripple-startup-test
done
