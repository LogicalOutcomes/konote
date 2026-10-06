# LTE Privacy Officer Guide

This short guide describes what the designated privacy officer for
Longitudinal Trajectory Export (LTE) is responsible for. LTE is
KoNote's small-population evaluation export tier — for programs with
fewer than 15 participants, where the standard Evaluator Export is
blocked.

LTE is **for program evaluation, not research**. It drops demographic
fields entirely and substitutes fuzzed longitudinal metric
trajectories. The full rationale is in
[`tasks/design-rationale/evaluation-microdata-export.md`](../tasks/design-rationale/evaluation-microdata-export.md).

## Who should hold this role

A KoNote admin grants the LTE permission to one user per agency —
typically the privacy officer, board data steward, or equivalent
role. The grant is a strictly separate permission from the standard
Evaluator Export — holding one does not confer the other.

If your agency does not have a designated privacy officer, **LTE is
unreachable** until one is appointed. This is enforced in code: the
form will 403 with a message directing the admin to designate a
privacy officer first.

## Your responsibilities

### 1. Decide whether a requested export meets the preconditions

When a staff member submits an LTE request, you'll receive two
touchpoints:

- **Email notification at submission time** (goes to all agency
  admins), with a signed "Flag concerns" link you can click to freeze
  the review-and-cancel countdown.
- **Post-hoc review task** on your dashboard — auto-created at
  submission time. This task must be resolved before the agency can
  submit another LTE request (rate limit is agency-wide).

Use the 5-business-day review-and-cancel window to verify:

- **REB approval exists** and matches a recognised research ethics
  board. The LTE form captures the approval number as a string;
  verification is a human step.
- **Evaluator credentials are plausible** — degree, years of
  experience, prior programs evaluated. The prior programs field
  must be at least 50 characters and is preserved in the audit log.
- **Data sharing agreement is signed and in force.** The DSA is
  captured for audit; it does not on its own unlock anything.
- **Community governance signoff** (if applicable). Programs flagged
  OCAP, EGAP, or "other small-population community review" require
  a community reviewer's name, affiliation, and signoff date on top
  of the usual preconditions. Agency ED authorisation is not a
  substitute for community review — this is a hard rule from the
  DRR.
- **Purpose statement** is evaluation, not research. If the request
  looks like it needs complete microdata, demographic detail, or
  unrounded values, it's research and should go through the research
  workflow (outside KoNote's scope).

### 2. Flag or cancel if anything is wrong

During the review-and-cancel window, any agency admin (including you)
may:

- **Flag concerns** — freezes the countdown until you (or another
  privacy officer) resolve the flag. Dismissing the flag resumes the
  countdown from where it froze, not from zero. Cancelling the
  request discards the prepared file and the pipeline work.
- **Cancel outright** — discards the file, ends the lifecycle, and
  requires re-submission if the evaluation is still needed. The
  request stays in the audit log marked "cancelled", including who
  cancelled and when.

If the export has been activated (window elapsed, download link is
live) and you notice a problem before download, you can still cancel.

### 3. Confirm destruction attestation after download

After the evaluator downloads the file, the destruction window
(30, 60, or 90 days) begins. At the end of the window KoNote sends
a reminder email. The agency contacts the evaluator, confirms the
file has been destroyed, and records the attestation manually on the
LTE request detail page. This is a v1 limitation — there is no
automated evaluator acknowledgement UI.

If no attestation is recorded by the deadline, a follow-up task is
auto-created for you.

### 4. Resolve the post-hoc review task

Once you've reviewed the request (either during the window or after
download), mark the post-hoc review task as resolved from the LTE
detail page. Until you resolve it, the agency cannot submit another
LTE request. This creates a natural per-agency rate limit based on
your review throughput.

## Things you cannot do

- **You cannot approve an LTE early.** There is no "fast-path early
  approval" button. The 5-business-day pause is part of the design,
  not a delay to be worked around.
- **You cannot waive the population floor.** The LTE floor is 10
  participants (or 15 for OCAP/EGAP programs), and the system will
  refuse to generate below that. Funder pressure to waive it is
  expected; the refusal is part of the safeguard.
- **You cannot grant LTE access to another user.** Grant management
  is an admin function — ask a KoNote admin to add a second designee
  if your agency needs one.
- **You cannot add demographic fields to the output.** The absence of
  demographics is LTE's primary re-identification defence. Adding
  "just age band" or "just urban/rural" is an anti-pattern —
  implementers are explicitly prohibited from building it.

## Escalation

If an evaluator insists on complete microdata, unfuzzed metric values,
or demographic detail:

- They are **doing research**, not program evaluation.
- Direct them to the research-grade data access workflow (REB
  approval + legal review + institutional data sharing agreement +
  case-by-case governance). That workflow is out of scope for KoNote
  itself and sits with your agency's legal or research office.

If you see repeated LTE requests from the same evaluator with
different purpose statements, or any pattern that looks like attempts
to circumvent the safeguards, contact GK (evaluation methodology lead)
via the consultation gate.

## Audit log

Every LTE lifecycle event (submitted, flagged, cancelled, activated,
downloaded, expired, post-hoc review resolved, destruction confirmed)
writes to the immutable audit log with the category
`longitudinal_trajectory_export`. The audit log is separate from the
EME category — you can filter on LTE events independently.
