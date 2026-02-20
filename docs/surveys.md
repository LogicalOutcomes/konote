# Surveys -- Staff Guide

How to assign surveys to participants, enter responses on their behalf, and view results.

> **Looking for admin tasks?** Creating surveys, setting up trigger rules, shareable links, and CSV import are covered in the [Surveys Admin Guide](admin/surveys.md).

---

## Table of Contents

1. [What Are Surveys?](#what-are-surveys)
2. [Assigning a Survey to a Participant](#assigning-a-survey-to-a-participant)
3. [Entering a Response on Behalf of a Participant](#entering-a-response-on-behalf-of-a-participant)
4. [Viewing Responses](#viewing-responses)
5. [How Participants See Surveys (Portal)](#how-participants-see-surveys-portal)
6. [Tips & Common Questions](#tips--common-questions)

---

## What Are Surveys?

Surveys let you ask participants structured questions -- like satisfaction forms, intake questionnaires, or outcome measurement tools. Each survey has:

- **Sections** -- groups of related questions (e.g., "About Your Experience", "Suggestions")
- **Questions** -- the actual items participants answer
- **Responses** -- completed submissions, which you can review later

Surveys can be filled in three ways:
- **By the participant** through the portal (if they have a portal account)
- **By staff** on behalf of a participant (data entry on the participant's file)
- **Through a shareable link** -- a public URL anyone can use without logging in

---

## Assigning a Survey to a Participant

You can assign a survey to a participant so it shows up on their portal.

1. Open the participant's file
2. Go to the **Surveys** tab on their file
3. Click **Assign Survey**
4. Choose the survey and optionally set a due date
5. Click **Assign**

The participant will see the survey on their portal dashboard the next time they log in.

**Note:** The participant needs a portal account for this to work. If they don't have one, you'll see a message suggesting you enter the response on their behalf instead.

---

## Entering a Response on Behalf of a Participant

If a participant can't or doesn't want to use the portal, you can enter their responses directly:

1. Open the participant's file
2. Go to the **Surveys** tab
3. Under **Enter Survey on Behalf**, click the survey name
4. Answer each question based on the participant's input
5. Click **Submit Response**

The response is recorded as "Staff data entry" so you can tell it apart from portal responses.

### Conditional Sections

When entering survey responses on behalf of a participant, conditional sections work the same way as in the portal -- the form dynamically shows or hides sections based on the answers entered. Required fields in hidden sections are not enforced.

---

## Viewing Responses

### On a survey's detail page (admin view)

1. Go to **Admin -> Surveys**
2. Click on the survey name
3. Scroll down to **Recent Responses**
4. Click **View** to see a single response's answers

### On a participant's file

1. Open the participant's file
2. Go to the **Surveys** tab
3. Under **Completed Responses**, click **View** next to the response you want to see

Each response shows:
- When it was submitted
- How it was submitted (portal, staff entry, or link)
- All answers grouped by section
- Numeric scores (if the survey uses scoring)

---

## How Participants See Surveys (Portal)

When a survey is assigned to a participant:

1. They see a **"Surveys"** card on their portal dashboard with a count of pending surveys
2. They can click it to see all assigned surveys
3. They click **Start** to begin filling in a survey
4. They answer each question section by section (multi-page if the survey uses page breaks)
5. **Answers are auto-saved** as they go -- if they close the browser or lose connection, they can come back and pick up where they left off
6. They review their answers on a summary page before submitting
7. They click **Submit** when finished
8. They see a thank-you confirmation page (with section scores if the survey shows scores to participants)

Participants can also see a list of their completed surveys.

**Note:** Surveys only appear in the portal if:
- The **Surveys** feature is turned on
- The survey's **Visible in participant portal** setting is checked
- The survey has been assigned to that participant

---

## Tips & Common Questions

### Can a participant fill in the same survey more than once?

Staff can enter multiple responses on a participant's file. Through the portal, each assignment can only be completed once -- but you can assign the same survey again.

### Can I see scores or totals?

Yes. If a section has scoring enabled, numeric values are calculated for each response. You can view section scores on the response detail page.

### What happens if a participant closes the browser mid-survey?

Their answers are **auto-saved** as they go. When they return to the portal, they can pick up where they left off -- their partial answers will be pre-filled. Auto-save happens question by question, so even partially completed pages are preserved.

### I need to create a new survey or set up trigger rules

See the [Surveys Admin Guide](admin/surveys.md) for creating surveys, adding questions, CSV import, trigger rules, shareable links, and closing/archiving surveys.
