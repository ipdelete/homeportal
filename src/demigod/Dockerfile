FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# docker CLI + compose plugin, to drive the host daemon through a mounted socket
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:cli /usr/local/libexec/docker/cli-plugins /usr/local/lib/docker/cli-plugins

# tailscale CLI, to configure Funnel through the host's tailscaled socket
COPY --from=tailscale/tailscale:latest /usr/local/bin/tailscale /usr/local/bin/tailscale

WORKDIR /app

# dependencies first for layer caching (build context is the repo root)
COPY src/demigod/pyproject.toml src/demigod/uv.lock ./
RUN uv sync --frozen --no-install-project

COPY src/demigod/demigod.py .

# deployment config travels with the deployer: no repo needed at runtime
COPY docker-compose.yml .

CMD ["/app/.venv/bin/python", "demigod.py"]
