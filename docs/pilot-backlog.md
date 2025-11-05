# Pilot Session Plan & Shared Backlog

To support the user-testing requirement, this document outlines how the team can
run 5–8 pilot sessions, collect feedback, and maintain a living backlog of
issues discovered during the exercises.

## Pilot Session Logistics

| Item | Details |
| --- | --- |
| Target participants | 5–8 privacy-conscious students or interns familiar with document-heavy workflows |
| Session format | 45-minute remote or in-person walkthrough of the setup wizard followed by open Q&A |
| Environment | Local build of the RAG assistant with the new guided wizard and API gateway |
| Roles | **Facilitator**: guides the script · **Observer**: captures notes and timestamps · **Participant**: completes tasks |
| Schedule window | Week 4 of the project timeline (see README) |

### Milestones

1. **Recruitment (Week 3):** identify candidates, confirm availability, send
   consent and confidentiality guidelines.
2. **Session dry run (Week 3):** team-only rehearsal to validate scripts and
   data capture templates.
3. **Pilot execution (Week 4):** run individual sessions, screen-record UI,
   collect API logs.
4. **Synthesis (Week 4):** tag findings, prioritise backlog items, assign
   owners.

## Feedback Capture Template

Each session should use the following template (stored in the shared drive or
notion board) to keep feedback structured and comparable:

- **Participant ID** (anonymised)
- **Scenario coverage** (Setup · Upload · Query · Review)
- **Delight moments**
- **Friction / confusion**
- **Bugs observed**
- **Follow-up questions**
- **Suggested improvements**

## Shared Backlog Structure

Track issues discovered during the pilots using the table below. Copy the table
into the issue tracker of your choice (Notion, Jira, GitHub Projects) so the
team can update it collaboratively.

| ID | Title | Category | Severity | Source session | Owner | Status | Notes |
| -- | --- | --- | --- | --- | --- | --- | --- |
| PILOT-01 | Wizard copy is unclear about IVF requirements | UX Content | Medium | Session 2 | TBD | New | Clarify why IVF needs ≥ *n_lists* chunks |
| PILOT-02 | Upload of >10MB DOCX stalls | Reliability | High | Session 4 | TBD | New | Investigate streaming ingestion + progress UI |
| PILOT-03 | Answer page lacks “ask another” CTA | UX Flow | Low | Session 5 | TBD | New | Add primary action to loop users back to Step 3 |

Update the backlog status after each triage meeting so the entire team and
stakeholders can monitor progress.

## Next Steps

1. Confirm the tooling for storing recordings and notes (e.g. shared drive or
   secure SharePoint folder).
2. Automate log capture from the API gateway to correlate issues with request
   payloads.
3. Schedule a debrief workshop after all sessions to decide which feedback
   feeds into the next development sprint.
