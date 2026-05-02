#!/bin/bash
# Trove Docker entrypoint.
#
# Usage inside the container:
#   setup   — start the setup wizard  (socat + trove setup,  port 7071)
#   start   — start the app           (socat + trove start,  port 7770)
#   <none>  — drop to a bash shell
#
# socat forwards 0.0.0.0:PORT → 127.0.0.1:PORT so Docker port-mapping works
# while Trove itself binds only to 127.0.0.1. This means request.client.host
# is always 127.0.0.1 inside Trove, preserving its localhost security checks.
set -euo pipefail

case "${1:-}" in
  setup)
    socat TCP-LISTEN:7071,fork,reuseaddr TCP:127.0.0.1:7071 &
    exec /usr/local/bin/trove setup
    ;;
  start)
    socat TCP-LISTEN:7770,fork,reuseaddr TCP:127.0.0.1:7770 &
    exec /usr/local/bin/trove start --host 127.0.0.1
    ;;
  "")
    exec /bin/bash
    ;;
  *)
    exec /usr/local/bin/trove "$@"
    ;;
esac
