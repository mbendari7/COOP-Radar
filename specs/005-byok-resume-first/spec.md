# Feature Specification: Bring Your Own AI Key and a Resume First Site

**Feature Branch**: `005-byok-resume-first`

**Created**: 2026-10-11 (spec written 2026-11-17 from the finished code)

**Status**: Built

**Input**: User description: "Hosting AI for everyone costs the owner money, and students should not need an
account just to see which jobs fit them. Let visitors use their own Claude, ChatGPT or Gemini key, make matching
work with no key at all, and make dropping in a resume the main thing the site does."

<!--
  Written after the code. The work happened on 2026-10-11 in commits d04f31c, 553c266, 7b2c1e6, bb888fa,
  efe60c5, d47396d, 2772bb0, 1d465c2 and 032d196. See docs/agentic-workflow.md for the session notes.
-->

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get matches from a resume with no account and no key (Priority: P1)

A second year computer science student hears about CoopRadar from a friend. They open the site, drop their resume
PDF on the Match my resume page and right away see the skills the site found, the skills employers ask for that
the resume does not mention, and a ranked list of open jobs with a short reason for each. They never made an
account and never pasted a key.

**Why this priority**: This is the whole point of the site. If matching only works with an account and an AI key,
most students leave before they see anything.

**Independent Test**: Sign out, clear site data, upload a text PDF with a Skills line. Matches show up with
reasons like "You have Python, SQL; it also asks for Go." and the header shows a temporary account.

**Acceptance Scenarios**:

1. **Given** a visitor who is signed out, **When** they drop a PDF or DOCX resume, **Then** a temporary account is
   made for them and they see skills found, skills worth adding and ranked matches
2. **Given** no AI key anywhere, **When** the resume is uploaded, **Then** matching still works and nothing says
   it failed
3. **Given** a scanned resume with no text in it, **When** it is uploaded, **Then** the site says it could not
   read any text and the old resume (if any) is kept

---

### User Story 2 - Add my own AI key and use it (Priority: P2)

The same student wants a real review of their resume. They open the AI key page, pick Claude, ChatGPT or Gemini,
follow the short steps to get a key, paste it, and the site checks it and offers only the models that key can use.
Then they click Get my AI review, Re-rank with my AI, or Tailor my resume on a match and the answer streams in.

**Why this priority**: AI is what makes the results feel personal, but it has to be the visitor's own spend.

**Independent Test**: Paste a real key on the AI key page. The check passes and a model is picked. Click Get my
AI review and a summary, strengths and improvements appear. Paste a fake key and the page says the key was
rejected without showing the key.

**Acceptance Scenarios**:

1. **Given** a valid key, **When** the visitor checks it, **Then** the page lists the models it can use and picks a
   sensible one
2. **Given** a key in the browser, **When** the visitor asks for an AI review, re-rank, tailoring, a cover letter
   or a question, **Then** the request uses their key and the answer appears
3. **Given** a rejected key, an unknown model, or no credit left, **When** an AI action runs, **Then** a clear
   message says which one it was and the free results stay on screen
4. **Given** any AI request, **When** it is handled, **Then** the key is never saved on the server, written to a
   log, or included in an error

---

### User Story 3 - Try the site with a demo account (Priority: P3)

Someone looking at the project for the first time (a recruiter, a classmate) clicks Try the demo and lands in a
private account with a filled in tracker, a resume and matches, so they can click around without uploading
anything.

**Why this priority**: Useful for showing the project off, but students get value without it.

**Independent Test**: Click Try the demo. The tracker has cards in several statuses and the resume page has
matches.

**Acceptance Scenarios**:

1. **Given** the demo is turned on, **When** a visitor clicks Try the demo, **Then** they get their own private demo
   account and nobody else sees their changes
2. **Given** a temporary or demo account, **When** the visitor chooses Keep my account and gives an email and
   password, **Then** the account becomes a normal one and is not deleted

---

### User Story 4 - The owner can offer a few free AI actions (Priority: P4)

The owner can set their own Anthropic key so people without a key can try the AI a few times a day.

**Why this priority**: Nice to have. The site works fine without it.

**Independent Test**: Set `ANTHROPIC_API_KEY` and `AI_DAILY_LIMIT=2`, then run three AI actions with no visitor
key. The third one says the daily limit is reached.

**Acceptance Scenarios**:

1. **Given** an owner key and a daily limit, **When** a visitor with no key uses AI, **Then** it works until the
   limit and then says so
2. **Given** a visitor with their own key, **When** they use AI, **Then** the owner's limit never applies to them

---

### Edge Cases

- A Google key that is wrong comes back as a 400 with `API_KEY_INVALID` instead of a 401. It must still read as
  "key rejected"
- New models answer with thinking blocks before the text. Reading only the first block would break
- The AI sends back posting ids that were never in the shortlist, the same id twice, or scores over 100
- The AI stream fails after it has already started sending, so the HTTP status is already 200
- A visitor opens two tabs and uploads two resumes at once
- Lots of temporary accounts made from one network
- Resume or posting text that says "ignore your instructions and..."

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The site MUST let a signed out visitor upload a resume by making a temporary account for them
- **FR-002**: The site MUST rank jobs against a resume with no AI key, using the skills the resume and the job have
  in common, and give a reason for each match
- **FR-003**: The site MUST show skills found on the resume and the most asked for skills it is missing, for free
- **FR-004**: Visitors MUST be able to add a Claude, ChatGPT or Gemini key, check it, and pick a model from the ones
  it can use
- **FR-005**: The key MUST stay in the visitor's browser and be sent only with the request that needs it. The server
  MUST NOT store it, log it or echo it
- **FR-006**: With a key, visitors MUST be able to get an AI resume review, re-rank their matches, tailor their
  resume to one job, draft a cover letter for one job, and ask questions about one job
- **FR-007**: Answers to questions MUST cite the resume or the posting, and MUST say "I don't have enough
  information to answer that." when the text does not say
- **FR-008**: AI errors MUST be shown as one of: key rejected, model not available, provider rate limit, provider
  error. The free results MUST stay usable
- **FR-009**: Temporary and demo accounts MUST be deleted after 7 days unless kept, and MUST be limited to 10 per
  network per hour
- **FR-010**: A temporary account MUST be able to become a normal account with an email and password
- **FR-011**: The owner MAY set their own key with a daily limit per person. Visitors with their own key MUST NOT
  be limited by it
- **FR-012**: The site MUST tell the frontend which features are on (demo, owner AI, smart search, daily limit)
  without sharing any secret
- **FR-013**: Student roles MUST rank above senior ones, and the jobs list MUST have a way to hide senior roles

### Key Entities *(include if feature involves data)*

- **Temporary account**: a user flagged as demo or guest, with a random password nobody knows, deleted after 7 days
- **AI credentials**: provider, key and model for one request. Never stored
- **Resume insights**: the free skill summary plus a cached AI review (summary, strengths, improvements, tailoring
  tips, roles, keywords)
- **AI usage counter**: how many AI actions a person used today on the owner's key

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A signed out visitor sees ranked matches within 10 seconds of dropping a resume, with no key
- **SC-002**: A fake key for each of the three providers comes back as "key rejected" and the key text never appears
  in the reply or the logs (checked live on 2026-10-11)
- **SC-003**: The owner pays nothing for AI unless they choose to set their own key
- **SC-004**: Every AI reply that names a posting names one that was in the visitor's matches

## Assumptions

- Most visitors do not have an AI key. The free path has to be good on its own
- Visitors who do have a key are fine with it living in their own browser storage
- One resume per account. A new upload replaces the old one
- Only the text of a resume is kept, never the file
- Smart search (embeddings) stays an owner only option because it needs an OpenAI key for every posting
