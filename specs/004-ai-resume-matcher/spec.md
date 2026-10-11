# Feature Specification: AI Resume Matcher

**Feature ID**: 004
**Short name**: ai-resume-matcher
**Date**: 2026-10-10
**Status**: Draft

---

## Overview

Students upload their resume to CoopRadar and receive a ranked list of co-op postings that match their skills, experience, and preferences. An AI assistant explains why each posting matches or doesn't match, and students can ask follow-up questions about any posting. The feature replaces manual browsing with a personalised, conversational experience.

---

## Problem Statement

Students currently browse hundreds of postings manually, applying keyword filters that require them to already know what to search for. They miss relevant postings because job titles vary ("Software Developer Co-op" vs. "Software Engineering Intern") and they don't always know which skills employers are looking for. The result is wasted time and missed opportunities.

---

## Goals

1. Reduce the time a student spends finding relevant postings from 30+ minutes to under 5 minutes.
2. Surface postings the student would not have found through keyword search alone.
3. Give honest, cite-grounded explanations of match quality — never hallucinated claims.

---

## User Stories

### US1 — Upload Resume and Get Ranked Matches (Priority: P1) 🎯 MVP

**As a** registered student,
**I want to** upload my resume (PDF or Word document),
**So that** I receive a ranked list of co-op postings that fit my background.

**Acceptance criteria:**
- Student can upload a PDF or `.docx` resume from the My Profile page.
- Within 30 seconds of upload, the page shows a ranked list of up to 20 matching postings.
- Each result displays a match score (0–100 %), a one-sentence match reason, and the posting's key details (title, company, city, term, deadline).
- Postings are ranked by match score descending.
- Re-uploading a new resume replaces the previous one and triggers a fresh match run.
- Upload rejects files that are not PDF or DOCX, or that exceed 5 MB.

---

### US2 — Ask Follow-up Questions about a Match (Priority: P2)

**As a** registered student,
**I want to** ask the AI questions about a specific matched posting,
**So that** I can understand whether the role is right for me before applying.

**Acceptance criteria:**
- On the match results page, each posting card has a "Ask about this role" button.
- Clicking it opens a conversation panel (inline or modal) pre-loaded with the posting's details and the student's resume summary.
- The student can type free-text questions (e.g. "Do I have enough Python experience for this?", "What am I missing?").
- The AI answers using only information from the posting text and the resume — it cites the specific resume section or posting sentence it draws from.
- The AI says "I don't have enough information to answer that" rather than guessing.
- Conversation history is preserved within the session; navigating away clears it (no persistent chat history required for MVP).
- Response to each question streams to the UI (text appears word by word, not all at once).

---

### US3 — View and Delete Stored Resume (Priority: P3)

**As a** registered student,
**I want to** view which resume is currently stored and delete it,
**So that** I control what personal data CoopRadar holds about me.

**Acceptance criteria:**
- My Profile page shows the file name, file size, and upload date of the stored resume (if one exists).
- A "Delete resume" button permanently removes the file and its extracted text from all storage.
- After deletion, the match results page shows a prompt to upload a resume instead of results.
- Deletion is confirmed with a modal ("Are you sure? This will remove your resume and match results.").

---

## Functional Requirements

| ID     | Requirement                                                                                      | Story |
|--------|--------------------------------------------------------------------------------------------------|-------|
| FR-001 | Accept PDF and DOCX resume files up to 5 MB; reject other formats with a clear error.           | US1   |
| FR-002 | Extract text from the uploaded resume without storing the raw file longer than needed to parse. | US1   |
| FR-003 | Produce a ranked list of up to 20 matching postings within 30 seconds of upload.                | US1   |
| FR-004 | Each match result includes: posting ID, match score (0–100), one-sentence match reason.         | US1   |
| FR-005 | Match score and reasons are grounded in extractable skills from both resume and posting.         | US1   |
| FR-006 | Re-uploading replaces the previous resume and clears prior match results.                        | US1   |
| FR-007 | The conversation panel for a posting is pre-loaded with context (posting + resume summary).      | US2   |
| FR-008 | AI responses cite the specific source text they draw from (resume section or posting sentence).  | US2   |
| FR-009 | AI responses MUST NOT make claims that cannot be backed by posting or resume text.               | US2   |
| FR-010 | Each question-answer exchange streams progressively to the UI.                                   | US2   |
| FR-011 | My Profile page shows file name, size, and upload date for the stored resume.                    | US3   |
| FR-012 | A confirmed delete action permanently removes resume text and match results from storage.        | US3   |
| FR-013 | After deletion, match results page shows an upload prompt rather than an empty list.             | US3   |
| FR-014 | All resume data is scoped to the authenticated user; no cross-user access.                       | US1–3 |

---

## Out of Scope

- Cover letter generation or editing.
- Job application submission through CoopRadar.
- Persistent multi-session chat history (conversations clear on navigation).
- Resume editing or improvement suggestions.
- Matching against postings the user has already applied to.
- Automated email or notification when new matching postings arrive.

---

## User Scenarios & Testing

### Scenario A — Happy path upload

1. Student logs in and navigates to My Profile.
2. Student uploads a valid PDF resume (< 5 MB).
3. Within 30 s: match results page shows up to 20 ranked postings.
4. Each card shows a score, a one-sentence reason, and posting details.

**Expected**: Student sees ranked results with legible match reasons.

### Scenario B — Oversized or invalid file

1. Student uploads a `.png` image or a 10 MB PDF.
2. The upload form immediately rejects the file with a descriptive error.

**Expected**: Clear error message; no upload attempted.

### Scenario C — Ask a follow-up question

1. Student clicks "Ask about this role" on a match card.
2. Student types "What Python skills from my resume match this job?"
3. The AI responds, citing the resume section listing Python projects and the posting's requirement.

**Expected**: Response includes verbatim or paraphrased quotes from both resume and posting.

### Scenario D — AI says it doesn't know

1. Student asks "Will this company hire someone with a 2.5 GPA?"
2. The posting doesn't mention GPA requirements.

**Expected**: AI responds "The posting doesn't mention GPA requirements. I can't answer that."

### Scenario E — Delete resume

1. Student navigates to My Profile; sees stored resume metadata.
2. Student clicks "Delete resume" and confirms in the modal.
3. My Profile shows the upload prompt; match results page shows the upload prompt.

**Expected**: All resume data removed; student is prompted to upload again.

---

## Key Entities

| Entity            | Description                                                       |
|-------------------|-------------------------------------------------------------------|
| `Resume`          | Uploaded file metadata + extracted text, scoped to one user      |
| `MatchResult`     | Ranked posting match for a specific resume version (score, reason)|
| `ConversationTurn`| One Q&A exchange in a posting-specific session (ephemeral)        |

---

## Success Criteria

| SC  | Criterion                                                                                                     |
|-----|---------------------------------------------------------------------------------------------------------------|
| SC1 | 90% of uploads (valid PDF/DOCX ≤ 5 MB) produce ranked results within 30 seconds.                             |
| SC2 | Match results contain at least 5 postings for resumes with ≥ 3 listed skills.                                |
| SC3 | AI responses cite a resume or posting excerpt in ≥ 80% of follow-up answers (measured in eval suite).        |
| SC4 | AI produces zero factually incorrect answers in a 25-case eval suite (answers either correct or "don't know"). |
| SC5 | Students can delete their resume and confirm removal within 3 clicks from My Profile.                         |
| SC6 | The match page loads stored results (no re-upload needed) within 2 seconds on return visits.                  |

---

## Assumptions

- The postings database already contains embeddings (Feature 003) which can assist matching.
- An AI provider API key is available in the environment (same provider as Feature 003 skill extraction).
- Students are already registered and authenticated (Feature 002).
- "Match score" is computed server-side; the method (embedding cosine similarity + re-ranking) is an implementation detail.
- Resume text is extracted server-side; the client never processes resume content.
- Conversation context is passed per-request; no server-side session state is needed for chat.

---

## Dependencies

- Feature 002: User authentication (students must be logged in).
- Feature 003: Postings with embeddings (improves match quality; feature degrades gracefully without embeddings).
