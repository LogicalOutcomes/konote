"""Forms for user management and invite registration."""
from django import forms

from apps.programs.models import Program

from .models import Invite, User


class UserCreateForm(forms.ModelForm):
    """Form for creating a new user."""

    password = forms.CharField(
        widget=forms.PasswordInput,
        min_length=8,
        help_text="Minimum 8 characters.",
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password",
    )
    email = forms.EmailField(required=False, label="Email")

    class Meta:
        model = User
        fields = ["username", "display_name", "is_admin"]

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        pw2 = cleaned.get("password_confirm")
        if pw and pw2 and pw != pw2:
            self.add_error("password_confirm", "Passwords do not match.")
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
    """Form for editing an existing user."""

    email = forms.EmailField(required=False, label="Email")
    new_password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        min_length=8,
        label="New Password",
        help_text="Leave blank to keep current password.",
    )

    class Meta:
        model = User
        fields = ["display_name", "is_admin", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["email"].initial = self.instance.email

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

    role = forms.ChoiceField(choices=Invite.ROLE_CHOICES, label="Role")
    programs = forms.ModelMultipleChoiceField(
        queryset=Program.objects.filter(status="active"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Assign to Programs",
        help_text="Select which programs this person will be assigned to. Not needed for administrators.",
    )
    expires_days = forms.IntegerField(
        initial=7, min_value=1, max_value=30,
        label="Link expires in (days)",
    )


class InviteAcceptForm(forms.Form):
    """Form for new users to register via an invite link."""

    username = forms.CharField(
        max_length=150,
        help_text="Choose a username for signing in.",
    )
    display_name = forms.CharField(
        max_length=255,
        label="Your Name",
        help_text="How your name will appear to others.",
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        min_length=8,
        help_text="Minimum 8 characters.",
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password",
    )
    email = forms.EmailField(required=False, label="Email (optional)")

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        pw2 = cleaned.get("password_confirm")
        if pw and pw2 and pw != pw2:
            self.add_error("password_confirm", "Passwords do not match.")
        return cleaned
