# Surveys — User Guide

How to create, manage, and use surveys to gather structured feedback from participants.

> **Who is this for?** Admins and program managers who want to set up surveys, and front-line staff who enter survey responses on behalf of participants.
>
> **What you need:** Admin access or the "Manage Note Templates" permission. (To enter survey responses on a participant's file, any staff member with access to that participant can do so.)

---

## Table of Contents

1. [What Are Surveys?](#what-are-surveys)
2. [Turning On Surveys](#turning-on-surveys)
3. [Creating a Survey](#creating-a-survey)
4. [Adding Questions](#adding-questions)
5. [Question Types](#question-types)
6. [Activating a Survey](#activating-a-survey)
7. [Importing a Survey from CSV](#importing-a-survey-from-csv)
8. [Assigning a Survey to a Participant](#assigning-a-survey-to-a-participant)
9. [Entering a Response on Behalf of a Participant](#entering-a-response-on-behalf-of-a-participant)
10. [Viewing Responses](#viewing-responses)
11. [How Participants See Surveys (Portal)](#how-participants-see-surveys-portal)
12. [Closing or Archiving a Survey](#closing-or-archiving-a-survey)
13. [Tips & Common Questions](#tips--common-questions)

---

## What Are Surveys?

Surveys let you ask participants structured questions — like satisfaction forms, intake questionnaires, or outcome measurement tools. Each survey has:

- **Sections** — groups of related questions (e.g., "About Your Experience", "Suggestions")
- **Questions** — the actual items participants answer
- **Responses** — completed submissions, which you can review later

Surveys can be filled in three ways:
- **By the participant** through the portal (if they have a portal account)
- **By staff** on behalf of a participant (data entry on the participant's file)
- **Through a shareable link** (planned for a future release)

---

## Turning On Surveys

Surveys are turned off by default. An admin needs to enable them:

1. Go to **Admin → Settings** (or **Manage → Settings** if you see "Manage" instead of "Admin")
2. Find the **Features** section
3. Turn on **Surveys**
4. Click **Save**

Once enabled, "Surveys" will appear in the Admin/Manage dropdown menu in the navigation bar.

---

## Creating a Survey

1. In the navigation bar, open the **Admin** (or **Manage**) dropdown
2. Click **Surveys**
3. Click the **New Survey** button
4. Fill in the details:

| Field | What to enter |
|-------|---------------|
| **Survey name** | A clear name, e.g., "Client Satisfaction Survey 2025" |
| **Survey name (French)** | Optional French translation of the name |
| **Description** | A brief explanation of the survey's purpose (participants see this) |
| **Description (French)** | Optional French translation |
| **Anonymous survey** | Check this if responses should never be linked to a participant file |
| **Show scores to participant** | Check this if you want participants to see their scores after submitting |
| **Visible in participant portal** | Uncheck to hide this survey from the portal (staff-only) |

5. **Add at least one section.** Every survey needs at least one section. A section is just a group of related questions.

    - Give the section a **title** (e.g., "General Feedback")
    - Optionally add **instructions** that appear at the top of the section
    - Set the **display order** (lower numbers appear first)
    - Turn on **Start new page** if you want this section on its own page

6. Click **Create Survey**

Your survey is now saved as a **Draft**. You'll be taken to the Questions page to add questions.

---

## Adding Questions

After creating a survey, you'll see the **Questions** page. Each section is shown with its existing questions and an "Add question" area.

1. Click the **Add question** dropdown under the section where you want the question
2. Fill in:
   - **Question text** — the question as participants will see it
   - **Question text (French)** — optional French translation
   - **Question type** — see [Question Types](#question-types) below
   - **Display order** — controls the order of questions within the section
   - **Required** — check this if the question must be answered
   - **Options** — for choice or rating questions, type one option per line
3. Click **Add Question**

Repeat for each question you want to add. You can remove a question by clicking the **✕** button next to it.

---

## Question Types

| Type | What it looks like | When to use it |
|------|-------------------|----------------|
| **Short text** | A single-line text box | Names, brief answers |
| **Long text** | A large text area | Detailed comments, feedback |
| **Single choice** | Radio buttons — pick one | "How satisfied are you?" with options like Very Satisfied, Satisfied, etc. |
| **Multiple choice** | Checkboxes — pick any number | "Which services did you use?" (select all that apply) |
| **Rating scale** | A row of labelled options | Likert scales (1–5, Strongly Disagree to Strongly Agree) |
| **Yes / No** | A dropdown with Yes and No | Simple binary questions |

### Adding Options for Choice Questions

For **single choice**, **multiple choice**, and **rating scale** questions, you need to provide the answer options. Type them in the **Options** box, **one per line**:

```
Strongly agree
Agree
Neutral
Disagree
Strongly disagree
```

The system will automatically assign numeric scores (0, 1, 2, 3, 4) to the options in order. If your survey uses scoring, the first option gets score 0, the second gets score 1, and so on.

---

## Activating a Survey

A new survey starts as a **Draft**. While it's a draft, you can edit sections, add/remove questions, and make changes freely.

When you're ready for the survey to be used:

1. Go to the survey's **Questions** page
2. Click **Activate this survey**

Or from the survey's detail page:

1. Click the **Activate** button

Once active, the survey:
- Appears in the list of available surveys for staff to assign
- Can be assigned to participants
- Shows up in the participant portal (if portal-visible)

**Tip:** You can still edit questions on an active survey, but be careful — changing questions after people have already responded can make the data harder to compare.

---

## Importing a Survey from CSV

If you have a survey prepared in a spreadsheet, you can import it all at once instead of adding questions one by one.

1. Go to **Admin → Surveys** (or **Manage → Surveys**)
2. Click **Import from CSV**
3. Enter a **Survey name** (and optional French name)
4. Upload your CSV file
5. Click **Import**

### CSV File Format

Your CSV file should have these columns:

| Column | Required? | What to put in it |
|--------|-----------|-------------------|
| section | Yes | Section name — rows with the same section name are grouped together |
| question | Yes | The question text |
| type | No | `short_text`, `long_text`, `single_choice`, `multiple_choice`, `rating_scale`, or `yes_no` (defaults to `short_text`) |
| required | No | `yes` or `no` |
| options | No | For choice questions, separate options with semicolons: `Agree;Neutral;Disagree` |
| score_values | No | Scores matching each option: `3;2;1` |
| instructions | No | Instructions shown at the top of a section |
| page_break | No | `yes` to start a new page at this section |
| section_fr | No | French section name |
| question_fr | No | French question text |
| options_fr | No | French options, semicolon-separated |

### Example CSV

```csv
section,question,type,required,options,score_values
General Feedback,How satisfied are you with our services?,single_choice,yes,Very satisfied;Satisfied;Neutral;Dissatisfied;Very dissatisfied,5;4;3;2;1
General Feedback,What did you find most helpful?,long_text,no,,
Suggestions,Would you recommend us to others?,yes_no,yes,,
Suggestions,Any suggestions for improvement?,long_text,no,,
```

The imported survey will be created as a **Draft** so you can review the questions before activating it.

---

## Assigning a Survey to a Participant

You can assign a survey to a participant so it shows up on their portal, or enter the responses yourself.

### To assign a survey (so the participant fills it in through the portal):

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

---

## Viewing Responses

### On a survey's detail page (admin view)

1. Go to **Admin → Surveys**
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
4. They answer each question section by section
5. They click **Submit** when finished
6. They see a thank-you confirmation page

Participants can also see a list of their completed surveys.

**Note:** Surveys only appear in the portal if:
- The **Surveys** feature is turned on
- The survey's **Visible in participant portal** setting is checked
- The survey has been assigned to that participant

---

## Closing or Archiving a Survey

When you're done collecting responses:

1. Go to **Admin → Surveys**
2. Click on the survey name
3. Click **Close**

A closed survey:
- Can no longer receive new responses
- No longer appears in the portal or assignment lists
- All its automatic trigger rules are deactivated
- Existing responses are still viewable

You can also archive a survey from the survey's edit page by changing the status. Archived surveys are hidden from the main list but their data is preserved.

---

## Tips & Common Questions

### Can I edit a survey after participants have responded?

Yes, but be cautious. If you change question text or options, it may be harder to compare responses from before and after the change.

### Can a participant fill in the same survey more than once?

Staff can enter multiple responses on a participant's file. Through the portal, each assignment can only be completed once — but you can assign the same survey again.

### Can I see scores or totals?

If a section uses scoring (set during section creation), numeric values are recorded for each answer. You can view these in the response detail view. A scored summary per section is planned for a future release.

### What happens to responses if I delete a survey?

Responses are deleted along with the survey. If you want to stop collecting responses but keep the data, **close** the survey instead of deleting it.

### Can I make a survey bilingual?

Yes. When creating questions, there are French translation fields for the survey name, section titles, question text, and answer options. Participants who use KoNote in French will see the French versions.

### I have lots of questions — is there a faster way than adding them one by one?

Yes! Use the **Import from CSV** feature. Prepare your questions in a spreadsheet, save it as CSV, and import it. See [Importing a Survey from CSV](#importing-a-survey-from-csv) for the format.
