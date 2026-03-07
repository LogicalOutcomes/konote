# Dev VPS Deploy

This is the fastest reliable way to deploy KoNote to the Dev instance.

## What Dev Means

- Host alias: `konote-vps`
- Server path: `/opt/konote-dev`
- Branch deployed: `origin/develop`
- Remote deploy script: `/opt/konote/scripts/deploy.sh --dev`

Do **not** manually SSH around the server first unless the deploy fails. The remote deploy script already handles the normal path.

## One Command

From the repo root on your Windows machine:

```powershell
.\scripts\deploy-vps.ps1 -Instance dev -ShowLogsOnFailure
```

That connects to `konote-vps` over SSH and runs:

```sh
sudo /opt/konote/scripts/deploy.sh --dev
```

## What The Remote Script Does

The remote script already knows the Dev setup. It:

1. Changes into `/opt/konote-dev`
2. Pulls the latest `origin/develop`
3. Rebuilds the web container
4. Restarts the Dev compose stack
5. Waits for the web container health check
6. If Dev migrations fail, it can reset the demo database and re-seed demo data

This is safe for Dev because the Dev instance only has demo data.

## Success Looks Like This

The command should end with output like:

```text
=== Dev: Deploy complete — web is healthy (...) ===
=== All deployments complete ===
```

If you see that and the command exits `0`, the Dev deploy succeeded.

## If It Fails

Run the same wrapper with `-ShowLogsOnFailure`:

```powershell
.\scripts\deploy-vps.ps1 -Instance dev -ShowLogsOnFailure
```

That prints the last 20 web-container log lines automatically after a failed deploy.

If you need to inspect the server manually after that, use:

```powershell
ssh konote-vps
```

Then on the server:

```sh
cd /opt/konote-dev
sudo docker compose -f docker-compose.yml -f docker-compose.override.yml ps
sudo docker compose -f docker-compose.yml -f docker-compose.override.yml logs web --tail=50
```

## Important Notes

- The Dev repo on the server is root-owned, so git and docker commands there usually need `sudo`.
- Keep `docker-compose.override.yml` on the server. It is expected and should not be deleted during normal deploys.
- Dev is behind `develop` until you merge your PR. Merge first, then deploy.
- Production and Dev both use the same VPS, but the Dev deploy target is `/opt/konote-dev`.