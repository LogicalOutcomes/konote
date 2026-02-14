"""Communication log forms."""
from django import forms
from django.utils.translation import gettext_lazy as _


class QuickLogForm(forms.Form):
    """Minimal form for the quick-log buttons — under 10 seconds to fill.

    Channel and direction are pre-filled from the button clicked.
    Staff just types optional notes and clicks save.
    """
    channel = forms.CharField(widget=forms.HiddenInput)
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
        choices=[
            ("", _("\u2014 Select \u2014")),
            ("reached", _("Reached")),
            ("voicemail", _("Voicemail")),
            ("no_answer", _("No Answer")),
            ("left_message", _("Left Message")),
            ("wrong_number", _("Wrong Number")),
        ],
    )

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


class PersonalNoteForm(forms.Form):
    """Validates the personal note field on the send-reminder preview."""
    personal_note = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 2}),
    )


class CommunicationLogForm(forms.Form):
    """Full form for detailed communication logging — all fields available."""
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
        choices=[
            ("", _("\u2014 Select \u2014")),
            ("reached", _("Reached")),
            ("voicemail", _("Voicemail")),
            ("no_answer", _("No Answer")),
            ("left_message", _("Left Message")),
            ("wrong_number", _("Wrong Number")),
        ],
    )
