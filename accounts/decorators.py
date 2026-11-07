from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def role_required(*allowed_roles):
    """
    Decorator for views that checks whether the logged-in user
    has one of the specified roles or is a superuser.
    Redirects unauthenticated users to LOGIN_URL.
    Raises PermissionDenied (403) for authenticated users lacking the role.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in allowed_roles and not request.user.is_superuser:
                raise PermissionDenied("You do not have permission to access this page.")
            return view_func(request, *args, **kwargs)
        return login_required(_wrapped_view)
    return decorator
