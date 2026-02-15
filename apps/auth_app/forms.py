"""Forms for user management and invite registration."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.programs.models import Program, UserProgramRole

from .models import Invite, User


class LoginForm(forms.Form):
    """Form for local username/password login."""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"autofocus": True}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
    )


class UserCreateForm(forms.ModelForm):
    """Form for creating a new user.

    Pass requesting_user to restrict is_admin for non-admin users.
    """

    password = forms.CharField(
        widget=forms.PasswordInput,
        min_length=8,
        help_text=_("Minimum 8 characters."),
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label=_("Confirm Password"),
    )
    email = forms.EmailField(required=False, label=_("Email"))

    class Meta:
        model = User
        fields = ["username", "display_name", "is_admin"]

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._requesting_user = requesting_user
        # Non-admin users cannot create admin accounts — hide the field
        # (use HiddenInput, not del, to avoid Django _post_clean crash)
        if requesting_user and not requesting_user.is_admin:
            self.fields["is_admin"].widget = forms.HiddenInput()
            self.fields["is_admin"].initial = False

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        pw2 = cleaned.get("password_confirm")
        if pw and pw2 and pw != pw2:
            self.add_error("password_confirm", _("Passwords do not match."))
        # Server-side enforcement: non-admins cannot set is_admin
        if self._requesting_user and not self._requesting_user.is_admin:
            cleaned["is_admin"] = False
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if self.cleaned_data.get("email"):
            user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    """Form for editing an existing user.

    Pass requesting_user to restrict is_admin and is_active for non-admin users.
    """

    email = forms.EmailField(required=False, label=_("Email"))
    new_password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        min_length=8,
        label=_("New Password"),
        help_text=_("Leave blank to keep current password."),
    )

    class Meta:
        model = User
        fields = ["display_name", "is_admin", "is_active"]

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._requesting_user = requesting_user
        if self.instance and self.instance.pk:
            self.fields["email"].initial = self.instance.email
        # Non-admin users cannot toggle admin status or deactivate accounts
        # (PMs must use the dedicated deactivate view instead).
        # Use HiddenInput, not del, to avoid Django _post_clean crash.
        if requesting_user and not requesting_user.is_admin:
            self.fields["is_admin"].widget = forms.HiddenInput()
            self.fields["is_admin"].initial = False
            self.fields["is_active"].widget = forms.HiddenInput()
            if self.instance and self.instance.pk:
                self.fields["is_active"].initial = self.instance.is_active

    def clean(self):
        cleaned = super().clean()
        # Server-side enforcement: non-admins cannot set is_admin or is_active
        if self._requesting_user and not self._requesting_user.is_admin:
            cleaned["is_admin"] = False
            if self.instance and self.instance.pk:
                cleaned["is_active"] = self.instance.is_active
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("email"):
            user.email = self.cleaned_data["email"]
        if self.cleaned_data.get("new_password"):
            user.set_password(self.cleaned_data["new_password"])
        if commit:
            user.save()
        return user


class InviteCreateForm(forms.Form):
    """Form for admins to create an invite link."""

    role = forms.ChoiceField(choices=Invite.ROLE_CHOICES, label=_("Role"))
    programs = forms.ModelMultipleChoiceField(
        queryset=Program.objects.filter(status="active"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_("Assign to Programs"),
        help_text=_("Select which programs this person will be assigned to. Not needed for administrators."),
    )
    expires_days = forms.IntegerField(
        initial=7, min_value=1, max_value=30,
        label=_("Link expires in (days)"),
    )


class InviteAcceptForm(forms.Form):
    """Form for new users to register via an invite link."""

    username = forms.CharField(
        max_length=150,
        help_text=_("Choose a username for signing in."),
    )
    display_name = forms.CharField(
        max_length=255,
        label=_("Your Name"),
        help_text=_("How your name will appear to others."),
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        min_length=8,
        help_text=_("Minimum 8 characters."),
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label=_("Confirm Password"),
    )
    email = forms.EmailField(required=False, label=_("Email (optional)"))

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(_("This username is already taken."))
        return username

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        pw2 = cleaned.get("password_confirm")
        if pw and pw2 and pw != pw2:
            self.add_error("password_confirm", _("Passwords do not match."))
        return cleaned


class UserProgramRoleForm(forms.Form):
    """Form for assigning a user to a program with a specific role."""

    program = forms.ModelChoiceField(
        queryset=Program.objects.filter(status="active"),
        label=_("Program"),
    )
    role = forms.ChoiceField(
        choices=UserProgramRole.ROLE_CHOICES,
        label=_("Role"),
    )
