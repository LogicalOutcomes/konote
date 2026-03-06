# Deploy to VPS

Deploys the latest `develop` branch to the OVHcloud VPS. Supports both production and dev instances.

## Instances

| Instance | URL | Directory | Deploy command |
|----------|-----|-----------|----------------|
| Production | konote.llewelyn.ca | `/opt/konote` | `ssh konote-vps /opt/konote/deploy.sh` |
| Dev | konote-dev.llewelyn.ca | `/opt/konote-dev` | `ssh konote-vps /opt/konote/deploy.sh --dev` |

## Steps

1. Ask the user which instance to deploy (or deploy both if they say "both"):
   - **Production only**: `ssh konote-vps /opt/konote/deploy.sh`
   - **Dev only**: `ssh konote-vps /opt/konote/deploy.sh --dev`
   - **Both**: `ssh konote-vps /opt/konote/deploy.sh --all`

2. The script pulls `develop`, rebuilds the web container, restarts, and waits for the health check.
   - Timeout: 5 minutes (build ~30s, migrations can take longer).
   - For dev: if migrations fail, the script auto-resets the database (drop, recreate, re-migrate, re-seed demo data). This is safe because dev only has demo data.

3. If the script exits 0 and prints "Deploy complete", tell the user the deploy succeeded.

4. If the script exits non-zero or prints "WARNING", show the user the last 20 lines of web container logs:
   ```
   ssh konote-vps "docker compose -f /opt/konote/docker-compose.yml logs web --tail=20"
   ```
   For dev instance:
   ```
   ssh konote-vps "docker compose -f /opt/konote-dev/docker-compose.yml logs web --tail=20"
   ```
   Then help diagnose the issue.

## Notes

- The VPS deploy script lives at `/opt/konote/deploy.sh` on the server.
- This only deploys what's on `develop` in GitHub. Make sure your changes are pushed and merged before running.
- Migrations run automatically on container startup via `entrypoint.sh`.
- The dev instance uses `DEMO_MODE=true` — all data is demo data and safe to reset.
- Both instances share the same Caddy container (from `/opt/konote`) for TLS termination.
