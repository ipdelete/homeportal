FROM python:3.14-slim

# tailscale CLI to talk to the host's tailscaled socket
COPY --from=tailscale/tailscale:latest /usr/local/bin/tailscale /usr/local/bin/tailscale

WORKDIR /app
COPY server.py .
COPY services.json .
COPY static/ static/

EXPOSE 8080
CMD ["python3", "server.py"]
