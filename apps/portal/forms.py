"""Forms for the participant portal.

All forms use Django's Form class (not ModelForm) because portal models
use encrypted fields with property accessors — raw form→model binding
would skip the encryption layer.
"""
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# Authentication forms
# ---------------------------------------------------------------------------


class PortalLoginForm(forms.Form):
    """Email + password login for participants."""

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            "autofocus": True,
            "autocomplete": "email",
            "placeholder": _("you@example.com"),
        }),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={
            "autocomplete": "current-password",
        }),
    )


class MFAVerifyForm(forms.Form):
    """Six-digit TOTP code for multi-factor authentication."""

    code = forms.CharField(
        label=_("Verification code"),
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={
            "inputmode": "numeric",
            "pattern": "[0-9]{6}",
            "autocomplete": "one-time-code",
            "autofocus": True,
            "placeholder": "000000",
        }),
        help_text=_("Enter the 6-digit code from your authenticator app."),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit():
            raise forms.ValidationError(_("The code must be 6 digits."))
        return code


class EmailCodeForm(forms.Form):
    """Six-digit code sent via email (password reset, email verification)."""

    code = forms.CharField(
        label=_("Verification code"),
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={
            "inputmode": "numeric",
            "pattern": "[0-9]{6}",
            "autocomplete": "one-time-code",
            "autofocus": True,
            "placeholder": "000000",
        }),
        help_text=_("Enter the 6-digit code we sent to your email."),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit():
            raise forms.ValidationError(_("The code must be 6 digits."))
        return code


# ---------------------------------------------------------------------------
# Password forms
# ---------------------------------------------------------------------------


class PortalPasswordChangeForm(forms.Form):
    """Change password — requires current password for safety."""

    current_password = forms.CharField(
        label=_("Current password"),
        widget=forms.PasswordInput(attrs={
            "autocomplete": "current-password",
        }),
    )
    new_password = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
        }),
        help_text=_("Must be at least 8 characters."),
    )
    confirm_password = forms.CharField(
        label=_("Confirm new password"),
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
        }),
    )

    def clean_new_password(self):
        password = self.cleaned_data.get("new_password")
        if password:
            # Run Django's built-in password validators (length, common, etc.)
            try:
                validate_password(password)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned = super().clean()
        new_pw = cleaned.get("new_password")
        confirm = cleaned.get("confirm_password")
        if new_pw and confirm and new_pw != confirm:
            self.add_error("confirm_password", _("Passwords do not match."))
        return cleaned


class PortalPasswordResetRequestForm(forms.Form):
    """Request a password reset — just needs the email address."""

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            "autofocus": True,
            "autocomplete": "email",
            "placeholder": _("you@example.com"),
        }),
        help_text=_("Enter the email address you used to create your account."),
    )


class PortalPasswordResetConfirmForm(forms.Form):
    """Enter the reset code + new password."""

    code = forms.CharField(
        label=_("Reset code"),
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={
            "inputmode": "numeric",
            "pattern": "[0-9]{6}",
            "autocomplete": "one-time-code",
            "autofocus": True,
            "placeholder": "000000",
        }),
    )
    new_password = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
        }),
        help_text=_("Must be at least 8 characters."),
    )
    confirm_password = forms.CharField(
        label=_("Confirm new password"),
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
        }),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit():
            raise forms.ValidationError(_("The code must be 6 digits."))
        return code

    def clean_new_password(self):
        password = self.cleaned_data.get("new_password")
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned = super().clean()
        new_pw = cleaned.get("new_password")
        confirm = cleaned.get("confirm_password")
        if new_pw and confirm and new_pw != confirm:
            self.add_error("confirm_password", _("Passwords do not match."))
        return cleaned


# ---------------------------------------------------------------------------
# Invite / registration
# ---------------------------------------------------------------------------


class InviteAcceptForm(forms.Form):
    """Registration form shown when a participant accepts a portal invite."""

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            "autocomplete": "email",
        }),
        help_text=_("This will be your login email."),
    )
    display_name = forms.CharField(
        label=_("What should we call you?"),
        max_length=255,
        widget=forms.TextInput(attrs={
            "autocomplete": "name",
            "placeholder": _("Your first name or nickname"),
        }),
        help_text=_("This is how your name will appear in the portal."),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
        }),
        help_text=_("Must be at least 8 characters."),
    )
    confirm_password = forms.CharField(
        label=_("Confirm password"),
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
        }),
    )

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        confirm = cleaned.get("confirm_password")
        if pw and confirm and pw != confirm:
            self.add_error("confirm_password", _("Passwords do not match."))
        return cleaned


class ConsentScreenForm(forms.Form):
    """Tracks which consent screen the participant has acknowledged."""

    screen_id = forms.CharField(widget=forms.HiddenInput())


# ---------------------------------------------------------------------------
# Participant content forms (Phase B + C)
# ---------------------------------------------------------------------------


class JournalEntryForm(forms.Form):
    """Private journal entry — optionally linked to a plan target."""

    content = forms.CharField(
        label=_("What's on your mind?"),
        widget=forms.Textarea(attrs={
            "rows": 5,
            "placeholder": _("Write anything you'd like to remember..."),
        }),
        required=True,
    )
    plan_target = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
        help_text=_("Optionally link this entry to one of your goals."),
    )

    def clean_content(self):
        text = self.cleaned_data.get("content", "").strip()
        if not text:
            raise forms.ValidationError(_("Please write something before saving."))
        return text


class MessageForm(forms.Form):
    """Message to the participant's worker."""

    content = forms.CharField(
        label=_("Your message"),
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": _("Write a message to your worker..."),
        }),
        required=True,
    )
    message_type = forms.CharField(
        initial="general",
        widget=forms.HiddenInput(),
    )

    def clean_content(self):
        text = self.cleaned_data.get("content", "").strip()
        if not text:
            raise forms.ValidationError(_("Please write something before sending."))
        return text


class PreSessionForm(forms.Form):
    """'What I want to discuss next time' — appears in staff client view."""

    content = forms.CharField(
        label=_("What would you like to discuss next time?"),
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": _("Anything you'd like to bring up at your next meeting..."),
        }),
        required=True,
    )

    def clean_content(self):
        text = self.cleaned_data.get("content", "").strip()
        if not text:
            raise forms.ValidationError(_("Please write something before saving."))
        return text


class CorrectionRequestForm(forms.Form):
    """Request to correct information in the participant's file.

    Implements a two-step flow: the template first shows a 'soft step'
    suggesting the participant discuss the concern with their worker.
    If they still want to submit formally, this form handles the request.
    """

    DATA_TYPE_CHOICES = [
        ("goal", _("A goal or plan target")),
        ("metric", _("A score or measurement")),
        ("reflection", _("Something recorded about what I said")),
    ]

    data_type = forms.ChoiceField(
        label=_("What would you like corrected?"),
        choices=DATA_TYPE_CHOICES,
    )
    object_id = forms.IntegerField(
        widget=forms.HiddenInput(),
    )
    description = forms.CharField(
        label=_("What needs to be changed?"),
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": _("Describe what you think is incorrect and what it should say..."),
        }),
    )

    def clean_description(self):
        text = self.cleaned_data.get("description", "").strip()
        if not text:
            raise forms.ValidationError(
                _("Please describe what needs to be corrected.")
            )
        return text
