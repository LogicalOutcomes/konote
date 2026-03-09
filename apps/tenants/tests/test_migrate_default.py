from importlib import import_module

from django.db import connection
from django.test import TestCase

from apps.tenants.management.commands.migrate_default import Command


class MigrateDefaultSchemaDetectionTests(TestCase):
	"""Regression tests for migrate_default schema detection helpers."""

	databases = {"default"}

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		migration_module = import_module(
			"apps.admin_settings.migrations.0011_taxonomy_exactly_one_fk_constraint"
		)
		cls.add_constraint_operation = migration_module.Migration.operations[0]

	def test_operation_schema_exists_detects_existing_constraint(self):
		"""AddConstraint operations should be recognised when the DB already has them."""
		command = Command()

		with connection.cursor() as cursor:
			self.assertTrue(
				command._operation_schema_exists(
					cursor,
					"admin_settings",
					self.add_constraint_operation,
				)
			)
