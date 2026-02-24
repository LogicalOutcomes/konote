---
name: requirements-interview
description: Conduct in-depth requirements interviews to define features or applications. Use when the user wants to explore, define, or refine requirements for a project, feature, or app. Triggers on requests to interview about a plan, document requirements, define specifications, explore feature scope, clarify project needs, or when the user says they have an idea they want to flesh out. Also use when given a plan or document to review and the user wants thorough questioning about implementation details.
---

# Requirements Interview Skill

Conduct thorough requirements interviews to help define features, applications, or project specifications through structured questioning.

## Process

### 1. Identify the Starting Point

Determine what material exists:

- **Plan or document provided**: Read the document first to understand the current state
- **Verbal description**: Capture the initial concept through opening questions
- **Existing codebase**: Review relevant code to understand current implementation

### 2. Interview Structure

Ask questions using AskUserQuestion tool. Structure the interview in phases:

**Phase 1: Core Understanding**
- What problem does this solve? For whom?
- What does success look like?
- What are the boundaries of this feature/app?

**Phase 2: User Experience**
- Walk through specific user scenarios
- Edge cases and error states
- Accessibility and internationalisation needs

**Phase 3: Technical Considerations**
- Integration points with existing systems
- Data requirements and persistence
- Performance expectations and constraints

**Phase 4: Trade-offs and Priorities**
- What can be deferred vs. must-have?
- Acceptable compromises
- Known risks or concerns

### 3. Question Quality Guidelines

**Ask non-obvious questions.** Avoid questions with self-evident answers. Focus on:

- Ambiguities that could lead to different implementations
- Assumptions that haven't been validated
- Edge cases that could break the happy path
- Trade-offs between competing concerns
- Dependencies on external factors

**Go deep on specifics.** Instead of "How should errors be handled?", ask "When a user submits invalid data in field X, should they see the error inline, in a toast, or blocking the form submission?"

**Challenge assumptions.** If the plan says "users can export data," ask what formats, what data volume, what happens during export, can they cancel, do they get notified when complete?

**Probe for constraints.** Ask about timeline pressures, budget limitations, technical debt, team capabilities, regulatory requirements.

### 4. Interview Rhythm

- Ask 2-3 related questions at a time, not a wall of questions
- Acknowledge and build on previous answers
- Circle back to earlier topics when new information reveals gaps
- Note contradictions and ask for clarification
- Continue until no significant ambiguities remain

### 5. Writing the Specification

When the interview is complete, write a specification document that captures:

1. **Overview**: Problem statement and solution summary
2. **User Stories**: Who does what and why
3. **Functional Requirements**: Specific behaviours and features
4. **Non-Functional Requirements**: Performance, security, accessibility
5. **UI/UX Specifications**: Interface details and interactions
6. **Technical Specifications**: Architecture, integrations, data models
7. **Out of Scope**: Explicitly excluded items
8. **Open Questions**: Any unresolved items for future consideration
9. **Assumptions**: Decisions made based on reasonable assumptions

Write the spec to the file path specified by the user, or ask where they want it saved.

## Example Question Patterns

**Instead of**: "What features should it have?"
**Ask**: "If a user opens this app for the first time, what's the very first thing they should be able to accomplish?"

**Instead of**: "How should the UI look?"
**Ask**: "When a user completes the main action, what visual feedback tells them it worked? What if it failed?"

**Instead of**: "Any security requirements?"
**Ask**: "Who should NOT be able to access this feature? What happens if they try?"

**Instead of**: "What data do you need?"
**Ask**: "If I showed you the data from this feature in six months, what would you want to see? What decisions would that data inform?"

## Completion Criteria

The interview is complete when:

- All major user flows are understood end-to-end
- Edge cases and error states have been addressed
- Technical constraints and integrations are clear
- Priorities and trade-offs have been explicitly discussed
- The user confirms no remaining questions or concerns
