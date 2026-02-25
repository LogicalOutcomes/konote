"""
Permission checks for KoNote.

This module provides functions to check user permissions for various actions.
"""

from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


# Permission levels
class PermissionLevel:
    """Permission level constants."""

    ADMIN = "admin"
    P5 = "p5"
    P5_PERMANENT = "p5_permanent"
    P4 = "p4"
    P3 = "p3"
    P2 = "p2"
    P1 = "p1"


def is_permanent_p5(user):
    """
    Check if user has permanent P5 permission level.

    This is a special permission level that cannot be revoked by normal means.
    It's used for system administrators and emergency access.

    Args:
        user: The user to check

    Returns:
        bool: True if user has permanent P5 permission
    """
    if not user or not user.is_authenticated:
        return False

    # Check if user has the p5_permanent permission level
    return hasattr(user, "permission_level") and user.permission_level == PermissionLevel.P5_PERMANENT


def has_permission_level(user, required_level):
    """
    Check if user has at least the required permission level.

    Args:
        user: The user to check
        required_level: The minimum required permission level

    Returns:
        bool: True if user has sufficient permissions
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    # Permanent P5 has all permissions
    if is_permanent_p5(user):
        return True

    # Get user's permission level
    user_level = getattr(user, "permission_level", None)
    if not user_level:
        return False

    # Define level hierarchy
    levels = {
        PermissionLevel.P5: 5,
        PermissionLevel.P5_PERMANENT: 5,
        PermissionLevel.P4: 4,
        PermissionLevel.P3: 3,
        PermissionLevel.P2: 2,
        PermissionLevel.P1: 1,
    }

    user_rank = levels.get(user_level, 0)
    required_rank = levels.get(required_level, 0)

    return user_rank >= required_rank


def can_access_organization(user, organization):
    """
    Check if user can access a specific organization.

    Args:
        user: The user to check
        organization: The organization to check access for

    Returns:
        bool: True if user can access the organization
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if is_permanent_p5(user):
        return True

    # Check if user is a member of the organization
    return organization.members.filter(user=user).exists()
