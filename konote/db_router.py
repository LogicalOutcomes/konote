"""Database routers for KoNote multi-tenancy.

AuditRouter — directs audit app models to the 'audit' database.
NoOpTenantRouter — pass-through used in test settings when running on
SQLite, which doesn't support PostgreSQL schemas. This avoids crashes
from TenantSyncRouter accessing connection.schema_name on SQLite.
"""


class NoOpTenantRouter:
    """Pass-through router that satisfies django-tenants' config check.

    Used in test.py with TENANT_SYNC_ROUTER pointed here so that
    django_tenants.apps.ready() passes validation without requiring
    the real TenantSyncRouter (which crashes on SQLite).
    """

    def db_for_read(self, model, **hints):
        return None

    def db_for_write(self, model, **hints):
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return None


class AuditRouter:
    """Route audit app models to the 'audit' database."""

    audit_app = "audit"

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.audit_app:
            return "audit"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.audit_app:
            return "audit"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations within the same database
        if obj1._meta.app_label == self.audit_app or obj2._meta.app_label == self.audit_app:
            return obj1._meta.app_label == obj2._meta.app_label
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == self.audit_app:
            return db == "audit"
        if db == "audit":
            return False
        return None
