# Railway demo reset job

KoNote's staging and production Railway environments are disposable demo
instances. Configure a separate cron service in **each** environment. Never
put a cron schedule on the web service: Railway cron services run their start
command and exit instead of serving requests.

## Create the service

1. In the Railway project, open the staging environment and add a service from
   the same GitHub repository and branch as the staging web service. Name it
   `demo-reset` (or another unambiguous name). Repeat in production using the
   production web service's branch. Railway's GitHub integration auto deploys
   each connected service when its branch changes; a GitHub Action is not
   needed.
2. Use the same Dockerfile and root directory as the web service. Set the
   service **Start Command** to `python manage.py reset_demo_data`. This
   overrides the Dockerfile's web entrypoint; the job must exit on completion.
3. Supply the job with its environment's `DATABASE_URL`,
   `AUDIT_DATABASE_URL`, `SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, `EMAIL_HASH_KEY`,
   `DJANGO_SETTINGS_MODULE`, and any other variables used by that web service.
   Prefer Railway shared or reference variables so keys remain in sync. Set
   `DEMO_MODE=true`. Do not attach a public domain.
4. Leave **Cron Schedule** unset until the reset command has been deployed and
   verified. Run it manually from the Railway service, inspect its exit code
   and logs, and verify that an edited demo record returned to baseline. Check
   that the web service continued serving requests.
5. Set **Cron Schedule** in Railway Settings to the desired five-field cron
   expression. Railway uses UTC. Change the expression there whenever the
   frequency changes; no code edit is needed. Check Cron Runs after the first
   scheduled execution. Railway skips a tick if the previous run is active.

The command refuses non-demo mode and non-PostgreSQL databases, rejects a
concurrent reset, and reports a nonzero exit on failure. The reset rebuilds
demo clients and users via `seed` and reports named client, user, and note
counts without personal information. It runs in a transaction on the app
database. The audit database is separate, so audit records are not part of
that transaction.

If a run fails, inspect the Railway deployment log and leave the schedule
disabled until the problem is corrected. A successful manual run can be
triggered after the fix. Do not run the job against an agency database that
contains real participant data.
