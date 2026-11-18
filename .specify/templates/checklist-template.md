# [CHECKLIST TYPE] Checklist: [FEATURE NAME]

**Purpose**: [What this checklist reviews, in one line]
**Created**: [DATE]
**Feature**: [Link to spec.md or other docs]

**Note**: `/speckit-checklist` writes this file from the feature's spec, plan and tasks.
**Review Ownership**: The reviewer owns this checklist. Mark an item `[x]` only when the reviewer decides the
requirement is written well enough.
**Marker Semantics**: `[x]` means the requirement was reviewed and is clear, complete and testable. It does not
mean the code is done.

<!--
  The items below are examples only. /speckit-checklist MUST replace them with real items from:
  - what the user asked the checklist to focus on
  - the requirements in spec.md
  - the technical context in plan.md
  - the tasks in tasks.md

  Each item tests the WRITING of a requirement, like a unit test for the spec. It asks "does the spec say
  this clearly" and not "does the code do this".

  Focus areas that have been useful in CoopRadar before:
  - Filter and sort combinations, and filter state kept in the URL
  - Empty, loading and error states, and what shows while the free server wakes up
  - Users only ever seeing their own saved jobs and resume
  - Source terms and robots.txt, re running an import twice, duplicates
  - AI keys never stored or echoed, what happens with no key or a bad key
  - Keyboard use, focus, labels and contrast, and the 375 px layout
  - The 300 ms performance budget

  Do not keep these example items in the real checklist.
-->

## [Category 1]

- [ ] CHK001 Is [requirement] written so it can be tested? [Clarity, Spec §FR-001]
- [ ] CHK002 Does the spec say what happens when [edge case]? [Coverage, Edge Cases]
- [ ] CHK003 Are [term] and [term] used the same way everywhere? [Consistency]

## [Category 2]

- [ ] CHK004 Is the number in [success criterion] something you can measure? [Measurability, Spec §SC-001]
- [ ] CHK005 Does the spec say what a student sees when [error]? [Coverage, Gap]
- [ ] CHK006 Is [assumption] written down? [Assumption]

## Notes

- Mark items `[x]` only after review finds the requirement clear and complete
- Leave items unchecked when they still need a question answered, a fix, or a reviewer to look
- `/speckit-implement` reads these boxes as a gate and does not change them
- `checklists/requirements.md` is kept by `/speckit-specify` and `/speckit-clarify` and has its own rules
- Add findings next to the item they are about
- Link to the doc or section that answers an item
- Items are numbered in order so they are easy to point to
