"""Role-based access decorators for views."""
from functools import wraps

from django.http import HttpResponseForbidden

# Higher number = more access
ROLE_RANK = {"receptionist": 1, "staff": 2, "program_manager": 3}


def minimum_role(min_role):
    """Decorator: require at least this program role to access the view.

    Relies on ProgramAccessMiddleware setting request.user_program_role
    for client-scoped routes. Returns 403 if the user's role is too low.
    """
    min_rank = ROLE_RANK.get(min_role, 0)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_role = getattr(request, "user_program_role", None)
            if user_role is None or ROLE_RANK.get(user_role, 0) < min_rank:
                return HttpResponseForbidden(
                    "Access denied. You do not have the required role for this action."
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
