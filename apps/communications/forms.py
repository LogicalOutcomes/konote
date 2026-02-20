"""Communication log forms."""
from django import forms
from django.utils.translation import gettext_lazy as _


class QuickLogForm(forms.Form):
    """Minimal form for the quick-log buttons — under 10 seconds to fill.

    Channel and direction are pre-filled from the button clicked.
    Staff just types optional notes and clicks save.
    """
    CHANNEL_CHOICES = [
        ("phone", _("Phone Call")),
        ("sms", _("Text Message")),
        ("email", _("Email")),
        ("in_person", _("In Person")),
    ]

    PHONE_OUTCOME_CHOICES = [
        ("", _("— Select —")),
        ("reached", _("Reached")),
        ("voicemail", _("Voicemail")),
        ("no_answer", _("No Answer")),
        ("left_message", _("Left Message")),
        ("wrong_number", _("Wrong Number")),
    ]

    NON_PHONE_OUTCOME_CHOICES = [
        ("", _("— Select —")),
        ("reached", _("Reached")),
        ("left_message", _("Left Message")),
        ("no_answer", _("No Response")),
    ]

    channel = forms.ChoiceField(
        choices=CHANNEL_CHOICES,
        label=_("Channel"),
    )
    direction = forms.CharField(widget=forms.HiddenInput, initial="outbound")
    notes = forms.CharField(
        required=False,
        label=_("Notes (optional)"),
        widget=forms.Textarea(attrs={
            "rows": 2,
            "placeholder": _("e.g. Confirmed for tomorrow"),
        }),
    )
    outcome = forms.ChoiceField(
        required=False,
        label=_("Outcome"),
        choices=PHONE_OUTCOME_CHOICES,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        channel = None
        if self.is_bound:
            channel = self.data.get("channel")
        if not channel:
            channel = self.initial.get("channel")
        self.fields["outcome"].choices = self._get_outcome_choices(channel)

    def _get_outcome_choices(self, channel):
        return self.PHONE_OUTCOME_CHOICES if channel == "phone" else self.NON_PHONE_OUTCOME_CHOICES

    def clean_channel(self):
        channel = self.cleaned_data["channel"]
        valid = ["email", "sms", "phone", "in_person", "portal", "whatsapp"]
        if channel not in valid:
            raise forms.ValidationError(_("Invalid channel."))
        return channel

    def clean_direction(self):
        direction = self.cleaned_data["direction"]
        if direction not in ("outbound", "inbound"):
            raise forms.ValidationError(_("Invalid direction."))
        return direction

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("channel") == "sms" and cleaned.get("outcome") == "voicemail":
            self.add_error("outcome", _("Voicemail is not a valid outcome for text messages."))
        return cleaned


class PersonalNoteForm(forms.Form):
    """Validates the personal note field on the send-reminder preview."""
    personal_note = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 2}),
    )


class SendEmailForm(forms.Form):
    """Form for composing and sending a free-form email to a participant."""
    subject = forms.CharField(
        max_length=255,
        label=_("Subject"),
        widget=forms.TextInput(attrs={
            "placeholder": _("e.g. Follow-up from today's session"),
        }),
    )
    message = forms.CharField(
        label=_("Message"),
        widget=forms.Textarea(attrs={
            "rows": 6,
            "placeholder": _("Type your message here..."),
        }),
    )


class CommunicationLogForm(forms.Form):
    """Full form for detailed communication logging — all fields available."""
    PHONE_OUTCOME_CHOICES = [
        ("", _("— Select —")),
        ("reached", _("Reached")),
        ("voicemail", _("Voicemail")),
        ("no_answer", _("No Answer")),
        ("left_message", _("Left Message")),
        ("wrong_number", _("Wrong Number")),
    ]

    NON_PHONE_OUTCOME_CHOICES = [
        ("", _("— Select —")),
        ("reached", _("Reached")),
        ("left_message", _("Left Message")),
        ("no_answer", _("No Response")),
    ]

    direction = forms.ChoiceField(
        choices=[
            ("outbound", _("Outgoing (we contacted them)")),
            ("inbound", _("Incoming (they contacted us)")),
        ],
        label=_("Direction"),
    )
    channel = forms.ChoiceField(
        choices=[
            ("phone", _("Phone Call")),
            ("sms", _("Text Message")),
            ("email", _("Email")),
            ("in_person", _("In Person")),
            ("portal", _("Portal Message")),
            ("whatsapp", _("WhatsApp")),
        ],
        label=_("Channel"),
    )
    subject = forms.CharField(
        max_length=255, required=False,
        label=_("Subject"),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Appointment reminder")}),
    )
    content = forms.CharField(
        required=False,
        label=_("Notes"),
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": _("Details of the communication..."),
        }),
    )
    outcome = forms.ChoiceField(
        required=False,
        label=_("Outcome"),
        choices=PHONE_OUTCOME_CHOICES,
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("channel") == "sms" and cleaned.get("outcome") == "voicemail":
            self.add_error("outcome", _("Voicemail is not a valid outcome for text messages."))
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        channel = None
        if self.is_bound:
            channel = self.data.get("channel")
        if not channel:
            channel = self.initial.get("channel")
        self.fields["outcome"].choices = self._get_outcome_choices(channel)

    def _get_outcome_choices(self, channel):
        return self.PHONE_OUTCOME_CHOICES if channel == "phone" else self.NON_PHONE_OUTCOME_CHOICES


class StaffMessageForm(forms.Form):
    """Form for leaving messages for case workers."""

    message = forms.CharField(
        label=_("Message"),
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": _("e.g. Sarah called, wants to reschedule Thursday appointment"),
        }),
        max_length=500,
    )

    is_urgent = forms.BooleanField(
        required=False,
        label=_("Mark as urgent"),
        help_text=_("Urgent messages appear at the top of the inbox."),
    )

    for_user = forms.IntegerField(
        required=False,
        widget=forms.Select(),
        label=_("For"),
    )

    def __init__(self, *args, staff_choices=None, worker_term=None, **kwargs):
        super().__init__(*args, **kwargs)
        label = _("— Any %(worker)s —") % {"worker": worker_term or _("worker")}
        choices = [("", label)]
        if staff_choices:
            choices.extend(staff_choices)
        self.fields["for_user"].widget = forms.Select(choices=choices)

    def clean_for_user(self):
        user_id = self.cleaned_data.get("for_user")
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                return User.objects.get(pk=user_id)
            except User.DoesNotExist:
                raise forms.ValidationError(_("Selected staff member not found."))
        return None
