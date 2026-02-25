"""
Tests for permission validation.

This module contains tests for the permission checking system.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.auth_app.checks import (
    PermissionLevel,
    has_permission_level,
    is_permanent_p5,
    can_access_organization,
)

User = get_user_model()


@pytest.mark.django_db
class TestPermissionLevel:
    """Tests for PermissionLevel constants."""

    def test_permission_level_constants_exist(self):
        """Test that all permission level constants are defined."""
        assert PermissionLevel.ADMIN == "admin"
        assert PermissionLevel.P5 == "p5"
        assert PermissionLevel.P5_PERMANENT == "p5_permanent"
        assert PermissionLevel.P4 == "p4"
        assert PermissionLevel.P3 == "p3"
        assert PermissionLevel.P2 == "p2"
        assert PermissionLevel.P1 == "p1"


@pytest.mark.django_db
class TestIsPermanentP5:
    """Tests for is_permanent_p5 function."""

    def test_permanent_p5_user_returns_true(self, permanent_p5_user):
        """Test that a permanent P5 user returns True."""
        assert is_permanent_p5(permanent_p5_user) is True

    def test_regular_p5_user_returns_false(self, p5_user):
        """Test that a regular P5 user returns False."""
        assert is_permanent_p5(p5_user) is False

    def test_p4_user_returns_false(self, p4_user):
        """Test that a P4 user returns False."""
        assert is_permanent_p5(p4_user) is False

    def test_anonymous_user_returns_false(self, anonymous_user):
        """Test that an anonymous user returns False."""
        assert is_permanent_p5(anonymous_user) is False

    def test_none_user_returns_false(self):
        """Test that None returns False."""
        assert is_permanent_p5(None) is False


@pytest.mark.django_db
class TestHasPermissionLevel:
    """Tests for has_permission_level function."""

    def test_superuser_has_all_permissions(self, superuser):
        """Test that a superuser has all permission levels."""
        assert has_permission_level(superuser, PermissionLevel.P5) is True
        assert has_permission_level(superuser, PermissionLevel.P4) is True
        assert has_permission_level(superuser, PermissionLevel.P1) is True

    def test_permanent_p5_has_all_permissions(self, permanent_p5_user):
        """Test that a permanent P5 user has all permission levels."""
        assert has_permission_level(permanent_p5_user, PermissionLevel.P5) is True
        assert has_permission_level(permanent_p5_user, PermissionLevel.P4) is True
        assert has_permission_level(permanent_p5_user, PermissionLevel.P1) is True

    def test_p5_user_has_p5_permission(self, p5_user):
        """Test that a P5 user has P5 permission."""
        assert has_permission_level(p5_user, PermissionLevel.P5) is True

    def test_p5_user_has_lower_permissions(self, p5_user):
        """Test that a P5 user has all lower permissions."""
        assert has_permission_level(p5_user, PermissionLevel.P4) is True
        assert has_permission_level(p5_user, PermissionLevel.P3) is True
        assert has_permission_level(p5_user, PermissionLevel.P2) is True
        assert has_permission_level(p5_user, PermissionLevel.P1) is True

    def test_p4_user_lacks_p5_permission(self, p4_user):
        """Test that a P4 user lacks P5 permission."""
        assert has_permission_level(p4_user, PermissionLevel.P5) is False

    def test_p4_user_has_p4_permission(self, p4_user):
        """Test that a P4 user has P4 permission."""
        assert has_permission_level(p4_user, PermissionLevel.P4) is True

    def test_anonymous_user_has_no_permissions(self, anonymous_user):
        """Test that an anonymous user has no permissions."""
        assert has_permission_level(anonymous_user, PermissionLevel.P1) is False


# Fixtures
@pytest.fixture
def superuser():
    """Create a superuser."""
    return User.objects.create_user(
        username="superuser",
        email="superuser@example.com",
        is_superuser=True,
    )


@pytest.fixture
def permanent_p5_user():
    """Create a user with permanent P5 permission."""
    user = User.objects.create_user(
        username="permanent_p5",
        email="permanent_p5@example.com",
    )
    user.permission_level = PermissionLevel.P5_PERMANENT
    user.save()
    return user


@pytest.fixture
def p5_user():
    """Create a user with P5 permission."""
    user = User.objects.create_user(
        username="p5_user",
        email="p5@example.com",
    )
    user.permission_level = PermissionLevel.P5
    user.save()
    return user


@pytest.fixture
def p4_user():
    """Create a user with P4 permission."""
    user = User.objects.create_user(
        username="p4_user",
        email="p4@example.com",
    )
    user.permission_level = PermissionLevel.P4
    user.save()
    return user


@pytest.fixture
def anonymous_user():
    """Return an anonymous user (not authenticated)."""
    from django.contrib.auth.models import AnonymousUser

    return AnonymousUser()
