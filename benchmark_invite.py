import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'konote.settings')
os.environ.setdefault('FIELD_ENCRYPTION_KEY', 'x'*44)
os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('AUDIT_DATABASE_URL', 'sqlite:///:memory:')

django.setup()

from django.test.utils import setup_test_environment, teardown_test_environment
from django.core.management import call_command
from apps.auth_app.models import Invite, User
from apps.programs.models import Program, UserProgramRole
from django.utils import timezone
from datetime import timedelta

call_command('migrate', verbosity=0)

# Create an admin user
admin = User.objects.create_user(username="admin", password="password", display_name="Admin", is_admin=True)

# Create multiple programs
programs = []
for i in range(100):
    programs.append(Program.objects.create(name=f"Program {i}"))

# Create an invite
invite = Invite.objects.create(
    role="staff",
    created_by=admin,
    expires_at=timezone.now() + timedelta(days=7),
)
invite.programs.set(programs)
invite.save()

# Simulate the invite accept part
user = User.objects.create_user(username="newuser", password="password", display_name="New User")

start_time = time.time()

# The original code we want to optimize
if invite.role != "admin":
    for program in invite.programs.all():
        UserProgramRole.objects.create(
            user=user, program=program, role=invite.role,
        )

end_time = time.time()
print(f"Execution time: {end_time - start_time:.6f} seconds")
