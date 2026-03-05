# Deploy to VPS

Deploys the latest `develop` branch to the OVHcloud VPS (konote.llewelyn.ca).

## Steps

1. Run: `ssh konote-vps /opt/konote/deploy.sh`
   - This pulls `develop`, rebuilds the web container, restarts, and waits for the health check.
   - Timeout: 5 minutes (the build step takes ~30s but migrations can take longer).

2. If the script exits 0 and prints "Deploy complete", tell the user the deploy succeeded.

3. If the script exits non-zero or prints "WARNING", show the user the last 20 lines of web container logs:
   ```
   ssh konote-vps "docker compose -f /opt/konote/docker-compose.yml logs web --tail=20"
   ```
   Then help diagnose the issue.

## Notes

- The VPS deploy script lives at `/opt/konote/deploy.sh` on the server.
- This only deploys what's on `develop` in GitHub. Make sure your changes are pushed and merged before running.
- Migrations run automatically on container startup via `entrypoint.sh`.
