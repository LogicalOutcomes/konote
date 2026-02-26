"""Forms for user management and invite registration."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.programs.models import Program, UserProgramRole

from .models import AccessGrant, AccessGrantReason, Invite, User


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
        # Guard: prevent the last active admin from removing their own admin status
        if (
            self.instance
            and self.instance.pk
            and self.instance.is_admin
            and not cleaned.get("is_admin", True)
        ):
            remaining_admins = (
                User.objects.filter(is_admin=True, is_active=True)
                .exclude(pk=self.instance.pk)
                .count()
            )
            if remaining_admins == 0:
                raise forms.ValidationError({
                    "is_admin": _("Cannot remove admin status from the last active admin user."),
                })
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


class MFAVerifyForm(forms.Form):
    """6-digit TOTP code entry for login verification or MFA setup confirmation."""
    code = forms.CharField(
        max_length=6, min_length=6,
        label=_("Verification code"),
        widget=forms.TextInput(attrs={
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
            "pattern": "[0-9]{6}",
            "autofocus": True,
        }),
    )


DURATION_CHOICES = [
    (1, _("1 day")),
    (3, _("3 days")),
    (7, _("7 days")),
    (14, _("14 days")),
    (30, _("30 days")),
]


class AccessGrantForm(forms.ModelForm):
    """Form for requesting GATED clinical access at Tier 3."""

    duration_days = forms.TypedChoiceField(
        choices=DURATION_CHOICES,
        coerce=int,
        label=_("How long do you need access?"),
    )

    class Meta:
        model = AccessGrant
        fields = ["reason", "justification"]
        widgets = {
            "justification": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "reason": _("Reason for access"),
            "justification": _("Brief explanation"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active reasons
        self.fields["reason"].queryset = AccessGrantReason.objects.filter(
            is_active=True
        )

        # Set defaults from InstanceSettings
        from apps.admin_settings.models import InstanceSetting

        default_days = int(InstanceSetting.get("access_grant_default_days", "7"))
        max_days = int(InstanceSetting.get("access_grant_max_days", "30"))

        # Filter duration choices to those <= max_days
        self.fields["duration_days"].choices = [
            (d, label) for d, label in DURATION_CHOICES if d <= max_days
        ]
        self.fields["duration_days"].initial = min(default_days, max_days)

    def clean_duration_days(self):
        """Validate duration against max_days setting."""
        from apps.admin_settings.models import InstanceSetting

        value = self.cleaned_data["duration_days"]
        max_days = int(InstanceSetting.get("access_grant_max_days", "30"))
        if value > max_days:
            raise forms.ValidationError(
                _("Maximum duration is %(max)s days.") % {"max": max_days}
            )
        return value
