# Feature Specification: Browse & Search Postings

**Feature Branch**: `001-browse-search-postings`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "Students need one place to browse co-op postings instead of checking many sites."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse the Postings List (Priority: P1)

A student opens CoopRadar and immediately sees a paginated list of active co-op postings. Each
row shows the title, company, city/province, work mode, term, duration, deadline, and posted date.
Expired deadlines are hidden by default. The student can page through results and change page size.

**Why this priority**: Browsing is the entry point for every other action. Without a working list
there is nothing to search or filter. This story alone constitutes a usable MVP.

**Independent Test**: Navigate to the home page without logging in. A table of postings loads
within 2 seconds. Pagination controls change the visible rows. Toggling "Show expired" reveals
postings with passed deadlines.

**Acceptance Scenarios**:

1. **Given** the app is open, **When** the page loads, **Then** a list of postings is shown with title, company, city/province, work mode, term, duration, deadline, and posted date columns.
2. **Given** the list is loaded, **When** the student clicks "Next page", **Then** the next page of results is shown and the URL updates to reflect the new page.
3. **Given** active postings and expired postings exist, **When** the page first loads, **Then** only postings with a future deadline are shown; a "Show expired" toggle is visible and unchecked.
4. **Given** the "Show expired" toggle is off, **When** the student turns it on, **Then** expired postings appear in the list alongside active ones.
5. **Given** the list is loaded, **When** the student selects page size 25, **Then** up to 25 rows appear and the URL reflects `page_size=25`.

---

### User Story 2 - Search and Filter Postings (Priority: P2)

A student types a keyword (e.g., "software") and applies filters for city, term, work mode,
duration range, and one or more required skills. The list updates to show only matching postings.
All active filters and the search query are visible and can be cleared individually or all at once.

**Why this priority**: Search and filter are the core productivity gain — without them the student
must scan 60+ rows manually. This story directly drives the 30-second success criterion.

**Independent Test**: Enter "Python" in the search box. Observe only postings mentioning Python
appear. Then add a "Remote" work mode filter. Observe results narrow further. Click "Clear all
filters" and observe the full list returns.

**Acceptance Scenarios**:

1. **Given** a keyword "Python" is entered, **When** the student submits the search, **Then** only postings whose title, company, skills, or description contain "Python" (case-insensitive, prefix match) are shown.
2. **Given** filters for city "Waterloo" and term "Summer 2027" are applied, **When** results load, **Then** only Waterloo Summer 2027 postings appear, and each active filter is shown as a removable chip or badge.
3. **Given** skills filter "React" and "TypeScript" are both selected, **When** results load, **Then** only postings that list both React AND TypeScript as required skills appear.
4. **Given** multiple filters are active, **When** the student clicks "Clear all", **Then** all filters and the search query are removed and the full list reloads.
5. **Given** no postings match the current filters, **When** results load, **Then** an empty state reads "No postings match — clear filters" with a visible "Clear all" action.

---

### User Story 3 - Sort Postings (Priority: P3)

A student clicks a column header (posted date, deadline, company, or title) to sort the list
ascending or descending. The chosen sort direction is reflected in the URL.

**Why this priority**: Sorting complements filtering and lets students quickly find the most
recent or most urgent postings. Useful but not a blocker for the core browsing and filtering
experience.

**Independent Test**: Click the "Deadline" column header once; verify rows are sorted by deadline
ascending. Click again; verify descending. Refresh the page; verify sort state is preserved via
URL.

**Acceptance Scenarios**:

1. **Given** the list is loaded, **When** the student clicks "Posted Date", **Then** postings are sorted newest-first (default) and a sort indicator appears on the column.
2. **Given** the list is sorted ascending by deadline, **When** the student clicks "Deadline" again, **Then** the order reverses to descending.
3. **Given** a sort is active, **When** the student refreshes the page, **Then** the same sort is restored from the URL.

---

### User Story 4 - View Posting Detail (Priority: P4)

A student clicks a posting row to open its detail view, which shows the full description, all
required skills, and a link to the original posting source. The browser back button returns to the
filtered/sorted list.

**Why this priority**: The detail view completes the browsing loop. A student cannot decide
whether to apply without reading the full description. Lower priority than list/search because the
list alone delivers partial value.

**Independent Test**: Click any row. The detail page shows a full description and required skills.
Clicking the "Original posting" link opens a new tab. Pressing browser back returns to the list
with filters intact (via URL state).

**Acceptance Scenarios**:

1. **Given** the list is displayed, **When** the student clicks a posting row, **Then** a detail view shows title, company, location, work mode, term, duration, deadline, full description, required skills list, and a link to the original posting.
2. **Given** the student is on a detail page, **When** they press the browser back button, **Then** the list is restored to the same filters, sort, and page they left.
3. **Given** a detail page is open, **When** the student clicks "Original posting", **Then** the source URL opens in a new tab.

---

### User Story 5 - Shareable / Bookmarkable Views (Priority: P5)

Any combination of search, filters, sort, and page state is encoded in the URL. Copying and
sharing that URL reproduces the exact view for another user.

**Why this priority**: URL state is a low-cost implementation that dramatically improves
usability. Lower priority than core list features but should ship with this feature to avoid a
painful retrofit later.

**Independent Test**: Apply a keyword search + two filters + a sort + page 2. Copy the URL and
paste it in an incognito window. Verify the identical list state loads.

**Acceptance Scenarios**:

1. **Given** a search query, filters, sort, and page are active, **When** the student copies the URL and opens it in a new browser, **Then** the identical state is reproduced.
2. **Given** a URL with query parameters, **When** the page loads, **Then** all parameters are parsed and applied before the first data fetch.

---

### Edge Cases

- What happens when all 60 postings expire? The list shows the empty state and the "Show expired" toggle is still functional.
- What happens if the student enters a keyword with no matches while filters are also active? The same "No postings match — clear filters" empty state appears.
- What happens when the student selects a page beyond the last page (e.g., via URL manipulation)? The last available page of results is shown.
- What happens if the "Original posting" URL is missing for a posting? The link is hidden rather than showing a broken link.
- What happens when the student resizes the browser to mobile width? The table collapses to a card layout; filters move to a collapsible panel.
- What happens if the data fetch fails? An error state is shown with a "Try again" button; the previous data is not wiped.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a paginated list of co-op postings with title, company, city/province, work mode, term, duration in months, application deadline, and posted date.
- **FR-002**: System MUST hide postings whose deadline has passed by default, and MUST provide a "Show expired" toggle that reveals them.
- **FR-003**: System MUST support keyword search across title, company, skills, and description fields; matching MUST be case-insensitive and support prefix matching; title matches MUST rank above description matches.
- **FR-004**: System MUST support filtering by city, province, term, work mode, duration, and one or more required skills; filters MUST be combinable; city and province MUST be independent (non-hierarchical) dropdowns; the duration filter MUST offer fixed checkboxes for 4, 8, 12, and 16 months; selecting multiple skills MUST require ALL selected skills to be present (AND logic).
- **FR-004a**: Remote postings MUST always appear in city-filtered results (because they are not tied to a city); users who want to exclude remote postings MUST be able to do so by selecting "Onsite" or "Hybrid" in the work mode filter — there is no separate "Exclude remote" toggle.
- **FR-005**: System MUST allow filters to be cleared individually and all at once with a single "Clear all" action.
- **FR-006**: System MUST support sorting by posted date (default: newest first), application deadline, company name, and title, in ascending or descending order.
- **FR-007**: System MUST support pagination with page sizes of 10, 25, and 50 results; the default page size MUST be 25.
- **FR-008**: All search terms, active filters, sort field, sort direction, page number, and page size MUST be reflected in the URL query string so views are shareable and survive page refresh.
- **FR-009**: System MUST display a posting detail view with full description, complete required skills list, and a link to the original posting source (opened in a new tab).
- **FR-010**: System MUST display a loading state while data is being fetched, an empty state reading "No postings match — clear filters" when no results exist, and an error state with a "Try again" action when the fetch fails.
- **FR-011**: The UI MUST be usable on mobile screens (minimum 375 px width); the table MUST collapse to a card layout below the medium breakpoint.
- **FR-012**: System MUST be seeded with approximately 60 realistic sample co-op postings covering Toronto, Mississauga, Waterloo, Kitchener, Guelph, Hamilton, Ottawa, and Vancouver for Winter 2027, Summer 2027, and Fall 2027 terms.

### Key Entities

- **Posting**: A co-op job opportunity. Key attributes: title, company name, city, province, work mode (onsite/hybrid/remote), term label (e.g., "Summer 2027"), duration in months, application deadline date, posted date, full description text, required skills list, original source URL. A posting may be active (deadline in the future) or expired.
- **Skill**: A tag on a posting representing a required competency (e.g., "Python", "React"). A posting has zero or more skills.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A student can narrow 60 sample postings down to 3–5 relevant results in under 30 seconds using search and filters.
- **SC-002**: The postings list loads and displays results within 2 seconds on a standard laptop internet connection.
- **SC-003**: All active filters and the search query are visible to the user at all times; removing all filters with one click restores the full unfiltered list.
- **SC-004**: Copying and sharing a URL with an active filter/sort/page state reproduces the identical view for any other user who opens that URL.
- **SC-005**: The UI is fully operable by keyboard alone, with every interactive element reachable via Tab and activated via Enter/Space, and visible focus indicators on all controls.
- **SC-006**: The interface is usable at 375 px viewport width without horizontal scrolling or overlapping elements.

## Assumptions

- No user authentication is required; all postings are publicly browsable.
- The approximately 60 seed postings are sufficient to demonstrate all filter, sort, and pagination behaviors without importing real data.
- Remote postings always appear in city-filtered results because they have no city. Exclusion is achieved via the work mode filter (select Onsite or Hybrid), not a separate toggle.
- Default sort is newest posted first; this is applied when no sort parameter is present in the URL.
- The duration filter offers four fixed checkboxes: 4, 8, 12, and 16 months. Multiple values are OR'd (show postings of any selected duration).
- The skills taxonomy is a fixed list for this feature; free-text skill entry is out of scope.
- Mobile support means a responsive layout at 375 px; a native mobile app is out of scope.
- The original posting source URL may not exist for all seed postings; the link is conditionally rendered.

## Clarifications

### Session 2026-10-09

- Q: How should keyword search matching work? → A: Case-insensitive, prefix matching; title/company/skills matches rank above description matches.
- Q: When multiple skills are selected in the filter, what logic applies? → A: AND logic — a posting must list ALL selected skills.
- Q: What is the default sort order? → A: Newest posted first (applied when no sort param present in URL).
- Q: How should remote postings behave when a city filter is active? → A: Remote postings always appear regardless of city filter; exclusion is via work mode filter (not a separate toggle).
- Q: What are the exact values for the duration filter? → A: Fixed checkboxes: 4, 8, 12, 16 months; multiple selections are OR'd.
- Q: Are city and province filters hierarchical or independent? → A: Independent dropdowns; selecting a province does not narrow city options.
