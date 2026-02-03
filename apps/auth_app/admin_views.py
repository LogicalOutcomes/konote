"""User management views — admin only."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import UserCreateForm, UserEditForm
from .models import User


def admin_required(view_func):
    """Decorator: 403 if user is not an admin."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin:
            return HttpResponseForbidden("Access denied. Admin privileges required.")
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@login_required
@admin_required
def user_list(request):
    users = User.objects.all().order_by("-is_admin", "display_name")
    return render(request, "auth_app/user_list.html", {"users": users})


@login_required
@admin_required
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "User created.")
            return redirect("auth_app:user_list")
    else:
        form = UserCreateForm()
    return render(request, "auth_app/user_form.html", {"form": form, "editing": False})


@login_required
@admin_required
def user_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "User updated.")
            return redirect("auth_app:user_list")
    else:
        form = UserEditForm(instance=user)
    return render(request, "auth_app/user_form.html", {
        "form": form, "editing": True, "edit_user": user,
    })


@login_required
@admin_required
def user_deactivate(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        if user == request.user:
            messages.error(request, "You cannot deactivate your own account.")
        else:
            user.is_active = False
            user.save()
            messages.success(request, f"User '{user.display_name}' deactivated.")
    return redirect("auth_app:user_list")
