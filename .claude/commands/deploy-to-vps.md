# Deploy to VPS

Deploys the latest `develop` branch to the OVHcloud VPS. Supports both production and dev instances.

## Default Behaviour

Use the remote deploy script first. Do not inspect git state, docker state, or server directories before the first deploy attempt unless the user specifically asks.

Preferred local wrapper:

- `./scripts/deploy-vps.ps1 -Instance dev -ShowLogsOnFailure`
- `./scripts/deploy-vps.ps1 -Instance prod -ShowLogsOnFailure`
- `./scripts/deploy-vps.ps1 -Instance all -ShowLogsOnFailure`

If the wrapper script is unavailable, fall back to the direct SSH commands below.

## Instances

| Instance | URL | Directory | Deploy command |
|----------|-----|-----------|----------------|
| Production | konote.llewelyn.ca | `/opt/konote` | `ssh konote-vps "sudo /opt/konote/scripts/deploy.sh"` |
| Dev | konote-dev.llewelyn.ca | `/opt/konote-dev` | `ssh konote-vps "sudo /opt/konote/scripts/deploy.sh --dev"` |

## Steps

1. Ask the user which instance to deploy only if they did not already say.
   - **Production only**: `ssh konote-vps "sudo /opt/konote/scripts/deploy.sh"`
   - **Dev only**: `ssh konote-vps "sudo /opt/konote/scripts/deploy.sh --dev"`
   - **Both**: `ssh konote-vps "sudo /opt/konote/scripts/deploy.sh --all"`

2. Run the deploy command immediately.

3. The script pulls `develop`, rebuilds the web container, restarts, and waits for the health check.
   - Timeout: 5 minutes (build ~30s, migrations can take longer).
   - For dev: if migrations fail, the script auto-resets the database (drop, recreate, re-migrate, re-seed demo data). This is safe because dev only has demo data.

4. If the script exits `0` and prints `Deploy complete`, verify the site is reachable:

   ```
   curl -sI --max-time 10 https://konote.llewelyn.ca/auth/login/ 2>&1 | head -1
   ```

   For dev:
   ```
   curl -sI --max-time 10 https://konote-dev.llewelyn.ca/auth/login/ 2>&1 | head -1
   ```

   If curl returns `HTTP/1.1 200 OK` or a `302` redirect, the deploy succeeded. Tell the user.

   If curl returns `404 Not Found` despite healthy containers, **Caddy is routing to the wrong container** (Docker DNS conflict). Check that the Caddyfile uses explicit container names (`konote-web-1`, `konote-dev-web-1`), not bare service names (`web`). See the troubleshooting section of `docs/deploy-ovhcloud.md` for the fix.

5. Only if the deploy fails or prints a warning, inspect logs.

   For production:
   ```
   ssh konote-vps "cd /opt/konote && sudo docker compose -f docker-compose.yml logs web --tail=20"
   ```

   For dev:
   ```
   ssh konote-vps "cd /opt/konote-dev && sudo docker compose -f docker-compose.yml -f docker-compose.override.yml logs web --tail=20"
   ```

   Then help diagnose the issue.

## Notes

- The VPS deploy script lives at `/opt/konote/scripts/deploy.sh` on the server.
- This only deploys what's on `develop` in GitHub. Make sure your changes are pushed and merged before running.
- Migrations run automatically on container startup via `entrypoint.sh`.
- The dev instance uses `DEMO_MODE=true` — all data is demo data and safe to reset.
- Both instances share the same Caddy container (from `/opt/konote`) for TLS termination.
- The Dev repo is root-owned on the server, so ad hoc git and docker commands usually need `sudo`.
- The Dev instance keeps a `docker-compose.override.yml` on the server; do not treat that as an unexpected repo problem during normal deploys.
