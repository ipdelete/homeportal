FROM python:3.14-slim

# docker CLI + compose plugin, to drive the host daemon through a mounted socket
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:cli /usr/local/libexec/docker/cli-plugins /usr/local/lib/docker/cli-plugins

# tailscale CLI, to configure Funnel through the host's tailscaled socket
COPY --from=tailscale/tailscale:latest /usr/local/bin/tailscale /usr/local/bin/tailscale

WORKDIR /app
COPY src/demigod/demigod.py .

# deployment config travels with the deployer: no repo needed at runtime
COPY docker-compose.yml .

CMD ["python3", "demigod.py"]
