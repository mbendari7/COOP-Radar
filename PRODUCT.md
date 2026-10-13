# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Canadian university and college students looking for co-op terms and internships. They usually sit at a laptop between classes, scan a lot of postings at once, and want to know quickly which ones they actually qualify for. The site is also a portfolio piece, so recruiters and interviewers looking at the builder's work are a second audience and need to get it within half a minute.

## Product Purpose
CoopRadar pulls real open jobs from about 120 employers' public career boards (Greenhouse, Lever, Ashby, SmartRecruiters) across Canada, plus US student roles. It reads each description for the programs and graduation years it asks for. A student drops in a resume with no sign up, the site reads their program, degree and grad year, and shows matching jobs with plain notes on why each one fits. Success means a student finds roles they qualify for faster than on a general job board, and applies on the employer's own site.

## Positioning
Matching runs in SQL against the student's real program, grad year and term, so it works with no AI at all. AI is optional and uses the visitor's own key. Jobs come straight from employer boards, not from a reposting aggregator.

## Operating Context
Job search list with a details panel and filters, resume upload and match results, an application tracker (drag between stages), an AI key page, account and temporary account flows, and an admin page for sources. Jobs refresh every 6 hours.

## Capabilities and Constraints
Sorting, filtering and pagination happen on the server. Visitors' AI keys are never stored. Matching must work with no AI key. Hosted free on Render plus Neon, with an optional Vercel front.

## Brand Commitments
Name: CoopRadar. Voice is plain and human: short sentences, simple words, minimal punctuation, no dashes, no emoji in the UI. Everything visual is open to change (confirmed 2026-10-13).

## Evidence on Hand
Real postings from the live import (about 2,800 jobs). No testimonials, user counts, or partner schools exist, so none may be shown.

## Product Principles
1. Show students what they qualify for, not just what exists.
2. Plain words over clever ones.
3. Works fully without AI or an account.
4. Always send people to the employer to apply.

## Accessibility & Inclusion
Keyboard reachable controls, visible focus, readable contrast. No specific standard was set.
