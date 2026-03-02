import os
import sys

def main():
    os.environ["DATABASE_URL"] = "sqlite:///db.sqlite3"
    os.environ["AUDIT_DATABASE_URL"] = "sqlite:///audit.sqlite3"
    os.environ["DJANGO_SETTINGS_MODULE"] = "konote.settings.test"

    # Read the default DB engine from settings and override it
    os.environ["USE_SQLITE_FOR_TESTS"] = "1"

    os.system("python manage.py test tests.test_security tests.test_programs")

if __name__ == "__main__":
    main()
