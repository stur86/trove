#!/bin/bash
# Trove Docker entrypoint.
#
# Usage inside the container:
#   setup   — start the setup wizard  (socat + trove setup,  port 7071)
#   start   — start the app           (socat + trove start,  port 7770)
#   <none>  — drop to a bash shell
#
# socat listens on the public port (e.g. 7071) and forwards to an internal
# port where Trove binds (e.g. 17071). Using different port numbers avoids
# the conflict that would occur if both tried to bind the same port —
# socat's 0.0.0.0:PORT bind subsumes 127.0.0.1:PORT on the same number.
# Trove sees all connections as originating from 127.0.0.1, preserving its
# localhost security checks.
set -euo pipefail

case "${1:-}" in
  setup)
    socat TCP-LISTEN:7071,fork,reuseaddr TCP:127.0.0.1:17071 &
    exec /usr/local/bin/trove setup --port 17071
    ;;
  start)
    socat TCP-LISTEN:7770,fork,reuseaddr TCP:127.0.0.1:17770 &
    exec /usr/local/bin/trove start --host 127.0.0.1 --port 17770
    ;;
  "")
    exec /bin/bash
    ;;
  *)
    exec /usr/local/bin/trove "$@"
    ;;
esac
