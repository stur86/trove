# Trove — Ubuntu-based Docker image.
#
# Build prerequisites (run on the host before `docker build`):
#
#   cd frontend && bun install && bun run build && cd ..
#   uv build --wheel
#
# Both steps are already part of the GitHub release workflow, so on CI
# the wheel is available in dist/ before this file is ever evaluated.
#
# Build:
#   docker build -t trove .
#
# Run (setup wizard):
#   docker run -it --rm \
#     -p 7071:7071 \
#     -v trove-ollama:/root/.ollama \
#     -v trove-config:/root/.config/trove \
#     trove
#
# Run (app mode, after setup is complete):
#   docker run -it --rm \
#     -p 7770:7770 \
#     -v trove-ollama:/root/.ollama \
#     -v trove-config:/root/.config/trove \
#     trove start
#
# GPU passthrough (NVIDIA — recommended for inference speed):
#   docker run ... --gpus all trove
#
# GPU passthrough (AMD ROCm):
#   docker run ... --device /dev/kfd --device /dev/dri trove

FROM ubuntu:latest

LABEL org.opencontainers.image.title="Trove" \
      org.opencontainers.image.description="Local LLM platform for non-technical users"

ENV DEBIAN_FRONTEND=noninteractive

# curl + ca-certificates: needed by install.sh (downloads uv) and by Trove at
# runtime (Ollama installer, model pulls via the setup UI).
# socat: forwards the container's external port to 127.0.0.1 so Trove's own
# bind address and localhost-based security checks are preserved as-is.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        bash \
        socat \
        zstd \
    && rm -rf /var/lib/apt/lists/*

# Copy the install script and the pre-built wheel from dist/.
# The wheel must exist before `docker build` is run (see prerequisites above).
COPY install.sh /tmp/install.sh
COPY dist/ /tmp/dist/

# Run the installer as root → Trove lands in /opt/trove, wrapper at /usr/local/bin/trove.
RUN bash /tmp/install.sh --local "$(ls /tmp/dist/*.whl)" \
    && rm -rf /tmp/install.sh /tmp/dist

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Ollama model data — mount a named volume to persist models across runs.
VOLUME /root/.ollama

# Trove config (admin password, model selection, context window).
# Mount a named volume to survive container restarts after setup.
VOLUME /root/.config/trove

# 7071 — setup wizard   7770 — app mode (user task runner + admin panel)
EXPOSE 7071 7770

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
