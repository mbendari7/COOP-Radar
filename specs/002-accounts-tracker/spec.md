# Feature Specification: Accounts & Application Tracker

**Feature Branch**: `002-accounts-tracker`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "Students need accounts so they can save postings and track where they've applied, with statuses like applied, interviewing, offer, and rejected."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Register & Log In (Priority: P1)

A student creates an account with their email address and a password. On subsequent
visits they log in and their session is remembered until they explicitly log out or
the session expires. Logging out ends the session immediately on all devices.

**Why this priority**: Without an account there is nothing to save or track. Every
other story in this feature depends on an authenticated user.

**Independent Test**: POST to the register endpoint with a valid email and password;
receive a success response and a session cookie. POST to the login endpoint; receive
a new session cookie. Call a protected endpoint without the cookie; receive 401.
POST to logout; cookie is cleared and the session is invalidated server-side.

**Acceptance Scenarios**:

1. **Given** a valid email and password (≥ 10 characters), **When** the student submits the registration form, **Then** an account is created, the student is logged in, and a session cookie is set in the browser.
2. **Given** an email already registered, **When** a student tries to register with the same email, **Then** a clear error "An account with this email already exists" is shown and no duplicate account is created.
3. **Given** a registered account, **When** the student submits the correct email and password, **Then** a new session is created and a session cookie is set.
4. **Given** an incorrect password, **When** the student tries to log in, **Then** an error "Invalid email or password" is shown; the error message must not reveal whether the email exists.
5. **Given** a logged-in session, **When** the student clicks "Log out", **Then** the session cookie is cleared and the server-side session is invalidated; subsequent requests with the old cookie return 401.
6. **Given** a session that has expired (after 7 days of inactivity), **When** the student makes any authenticated request, **Then** they receive a 401 and are prompted to log in again.

---

### User Story 2 — Save & Unsave Postings (Priority: P2)

A logged-in student can bookmark any posting from the list or detail page with a single
click. Saved postings are accessible from a "Saved" tab/page. Clicking the same
bookmark icon again removes the posting from their saved list.

**Why this priority**: Saving postings is the simplest way a logged-in student gets
value beyond browsing. It requires minimal UI change and makes the tracker possible.

**Independent Test**: Log in. Bookmark a posting from the list. Navigate to /saved;
the posting appears. Click the bookmark icon again; the posting is removed from /saved
and the icon returns to its unfilled state.

**Acceptance Scenarios**:

1. **Given** the student is logged in and viewing the postings list, **When** they click the bookmark icon on a row, **Then** the posting is added to their saved list and the icon changes to indicate it is saved.
2. **Given** the student has saved a posting, **When** they navigate to their Saved Postings page, **Then** all saved postings are listed with the same columns as the main list, ordered by most recently saved.
3. **Given** the student has saved a posting, **When** they click the bookmark icon again (unsave), **Then** the posting is removed from the saved list immediately and the icon returns to its default state.
4. **Given** the student is not logged in, **When** they click the bookmark icon, **Then** they are prompted to log in; after logging in they are returned to their previous page.
5. **Given** the student has no saved postings, **When** they navigate to /saved, **Then** an empty state reads "You haven't saved any postings yet — browse postings to get started."

---

### User Story 3 — Track Application Status (Priority: P3)

A student can assign a status to any saved posting: **Applied**, **Interviewing**,
**Offer**, or **Rejected**. They can update the status as their application progresses.
The Saved Postings page shows the current status for each posting and can be filtered
by status.

**Why this priority**: The status tracker is the core productivity feature beyond a
simple bookmark list. It turns CoopRadar into a personal application CRM.

**Independent Test**: Save a posting. Set its status to "Applied". Confirm the status
badge appears on the Saved Postings page. Change status to "Interviewing". Confirm the
badge updates. Filter saved postings by "Interviewing"; only that posting appears.

**Acceptance Scenarios**:

1. **Given** a saved posting with no status, **When** the student selects "Applied" from the status dropdown, **Then** the posting shows an "Applied" badge on the Saved Postings page.
2. **Given** a posting with status "Applied", **When** the student changes it to "Interviewing", **Then** the badge updates immediately without a full page reload.
3. **Given** saved postings with mixed statuses, **When** the student filters by "Interviewing", **Then** only postings with that status are shown.
4. **Given** a saved posting, **When** the student removes the status (sets to "No status"), **Then** the badge is cleared and the posting still appears in the saved list.
5. **Given** the student has postings across all four statuses, **When** they view the Saved Postings page, **Then** a status summary (count per status) is shown at the top.

---

### User Story 4 — Account Management (Priority: P4)

A logged-in student can change their password and permanently delete their account.
Deleting an account removes all personal data — saved postings, statuses — immediately
and irreversibly.

**Why this priority**: Required by the privacy principle (Constitution V): users must
be able to delete their data at any time. Password change is standard account hygiene.

**Independent Test**: Log in. Navigate to account settings. Change password; log out;
log back in with the new password — succeeds. Delete account; attempt to log in with
the old credentials — fails with "Invalid email or password".

**Acceptance Scenarios**:

1. **Given** a logged-in student, **When** they submit a password change with the correct current password and a valid new password (≥ 10 characters), **Then** the password is updated and they remain logged in.
2. **Given** an incorrect current password, **When** the student tries to change their password, **Then** an error "Current password is incorrect" is shown and the password is not changed.
3. **Given** a logged-in student, **When** they confirm account deletion (two-step confirmation), **Then** all their data is deleted immediately, their session is ended, and they are redirected to the home page.
4. **Given** a deleted account, **When** anyone tries to log in with those credentials, **Then** they receive "Invalid email or password" with no indication the account existed.

---

### Edge Cases

- What happens if a student saves a posting that expires before they check it? The posting stays in their saved list but shows an "Expired" badge alongside its status.
- What happens if two browser tabs are open and the student logs out in one? The next request in the other tab returns 401 and the UI redirects to the login page.
- What happens if the student tries to save the same posting twice? Silently returns the existing saved record — no duplicate, no error shown.
- What happens if Redis is temporarily unavailable? Sessions cannot be validated; all authenticated requests return 503 with a retry message. The postings list (unauthenticated) continues to work.
- What happens when a student registers with an email that has mixed case (e.g. "User@Example.com")? Emails are normalised to lowercase before storage and comparison.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow students to register with a unique email address and a password of at least 10 characters.
- **FR-002**: Passwords MUST be hashed using argon2 before storage; plaintext passwords MUST never be persisted or logged.
- **FR-003**: Emails MUST be normalised to lowercase before storage and used as the login identifier.
- **FR-004**: System MUST issue a session after successful registration or login; the session MUST be stored in Redis with a 7-day rolling expiry.
- **FR-005**: The session identifier MUST be transmitted only via an HTTP-only, Secure, SameSite=Lax cookie; it MUST NOT be accessible via JavaScript.
- **FR-006**: Any endpoint that reads or writes user-specific data MUST return 401 if the request does not carry a valid session.
- **FR-007**: System MUST allow a logged-in student to save any posting; saving the same posting a second time MUST be idempotent (no duplicate, no error).
- **FR-008**: System MUST allow a logged-in student to remove a saved posting.
- **FR-009**: System MUST return a student's saved postings ordered by most recently saved, with the same pagination as the main postings list.
- **FR-010**: System MUST allow a student to assign one of four statuses to a saved posting: `applied`, `interviewing`, `offer`, `rejected`; status is optional (may be unset).
- **FR-011**: System MUST allow a student to update or clear the status on a saved posting.
- **FR-012**: System MUST allow a logged-in student to change their password after verifying their current password.
- **FR-013**: System MUST allow a logged-in student to permanently delete their account; deletion MUST remove all associated saved postings and statuses immediately and irreversibly.
- **FR-014**: Login error messages MUST NOT distinguish between "email not found" and "wrong password" to prevent account enumeration.
- **FR-015**: The postings list and detail page MUST remain fully accessible to unauthenticated users; authentication gates only the save and status features.

### Key Entities

- **User**: A registered student. Key attributes: unique email (normalised), hashed password, registration date. A user has zero or more saved postings.
- **SavedPosting**: A bookmark linking a user to a posting. Key attributes: the user who saved it, the posting that was saved, the current application status (one of four values or unset), the date it was saved. A saved posting belongs to exactly one user and references exactly one posting.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A student can register, log in, and save their first posting within 60 seconds of arriving at the app for the first time.
- **SC-002**: The Saved Postings page loads and displays all saved postings within 2 seconds.
- **SC-003**: A status change on a saved posting is reflected in the UI within 1 second of the student's action, without a full page reload.
- **SC-004**: All personal data (saved postings, statuses) is permanently removed within 5 seconds of a student confirming account deletion.
- **SC-005**: An unauthenticated student can still browse, search, filter, and view the full postings list without any degradation compared to before this feature.
- **SC-006**: Session cookies are never accessible via JavaScript; confirmed by browser DevTools (HttpOnly flag set).

---

## Assumptions

- Email is the only supported login method; OAuth and SSO are out of scope for this feature.
- Session expiry is 7 days of inactivity (rolling); absolute session limits are out of scope.
- The Redis instance in the existing Docker Compose stack (Feature 001) is used for sessions; no new infrastructure is required.
- Password reset ("forgot my password") requires email sending, which is out of scope; users who forget their password must delete and re-register.
- Notes or free-text fields on saved postings are out of scope; the tracker covers status only.
- The Saved Postings page reuses the existing PostingsTable/PostingCard components from Feature 001; no new table design is needed.
- A student can only have one saved record per posting; the saved list is not shareable with other students.
