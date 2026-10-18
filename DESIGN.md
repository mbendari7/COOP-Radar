---
name: CoopRadar
description: Co-op and internship jobs from real employers, matched to your program, grad year and resume
colors:
  postal-red: "#c8281e"
  postal-red-deep: "#a81f17"
  airmail-blue: "#1e3a8a"
  airmail-blue-deep: "#1c3272"
  airmail-wash: "#eef2fb"
  airmail-tint: "#c3d0ee"
  letter-paper: "#ffffff"
  security-tint: "#eef1f6"
  ink: "#16181d"
  ink-soft: "#3a4150"
  ink-muted: "#4e5667"
  field-stroke: "#98a1b3"
  rule-faint: "#dde2eb"
typography:
  display:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "48px"
    fontWeight: 800
    lineHeight: 1.02
    letterSpacing: "-0.025em"
    fontVariation: "'wdth' 82"
  headline:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 800
    lineHeight: 1.25
    letterSpacing: "-0.025em"
    fontVariation: "'wdth' 82"
  title:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 700
    lineHeight: 1.375
  body:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "'tnum' 1"
  body-reading:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.625
  label:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
  wordmark:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 800
    letterSpacing: "0.03em"
    fontVariation: "'wdth' 75"
  stamp:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 800
    letterSpacing: "-0.025em"
    fontVariation: "'wdth' 75"
rounded:
  none: "0"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.postal-red}"
    textColor: "{colors.letter-paper}"
    typography: "{typography.title}"
    rounded: "{rounded.none}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.postal-red-deep}"
    textColor: "{colors.letter-paper}"
  button-secondary:
    backgroundColor: "{colors.letter-paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "8px 16px"
  button-secondary-hover:
    backgroundColor: "{colors.security-tint}"
    textColor: "{colors.ink}"
  button-quiet:
    backgroundColor: "{colors.letter-paper}"
    textColor: "{colors.airmail-blue}"
    rounded: "{rounded.none}"
    padding: "8px 16px"
  button-quiet-hover:
    backgroundColor: "{colors.airmail-wash}"
    textColor: "{colors.airmail-blue}"
  field:
    backgroundColor: "{colors.letter-paper}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "8px 12px"
  chip:
    backgroundColor: "{colors.letter-paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "4px 12px"
  chip-on:
    backgroundColor: "{colors.airmail-blue}"
    textColor: "{colors.letter-paper}"
    rounded: "{rounded.none}"
    padding: "4px 12px"
  tag:
    backgroundColor: "{colors.letter-paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "2px 8px"
  tag-accent:
    backgroundColor: "{colors.airmail-wash}"
    textColor: "{colors.airmail-blue-deep}"
    rounded: "{rounded.none}"
    padding: "2px 8px"
  nav-bar:
    backgroundColor: "{colors.postal-red}"
    textColor: "{colors.letter-paper}"
    height: "56px"
  job-row-selected:
    backgroundColor: "{colors.airmail-wash}"
    textColor: "{colors.airmail-blue}"
    padding: "12px 20px"
  postmark:
    textColor: "{colors.airmail-blue}"
    rounded: "{rounded.full}"
    size: "78px"
  postmark-selected:
    textColor: "{colors.postal-red}"
    rounded: "{rounded.full}"
    size: "68px"
---

# Design System: CoopRadar

## Overview

**A little more modern (2026-10-17)**

The user asked for the look to be slightly more modern. The red bar, airmail blue, the season dots and the postmark
stay. What changed: soft rounded corners (6px small, 8px default, 10px for buttons and fields, 14px for cards), pill
shaped filter chips, tags and role labels, 1px light grey borders with a small shadow instead of 2px ink borders, a
light grey page (`gray-50`) with the job list and the details panel as white cards, a focus ring of airmail tint
around fields and the search box, and Inter for reading text with Archivo kept for page titles and the wordmark.
Where the text below says square corners, 2px or 1.5px ink borders, a flat white page or Archivo for body text,
this paragraph wins.

**Creative North Star: "Registered Mail", toned down for reading (2026-10-13)**

The user asked for the theme to stay but be easier to read. So: labels are plain 13px sentence case instead of tiny
narrow capitals, page titles are wider (94%) and bold instead of extra bold, section rules are thin grey lines instead
of 1.5px ink, list rows are 17px titles with 15px lines, and the postmark lives on the job details only, not on every
row. Rows now lead with the term and length ("Summer 2027 · 4 months") with a small season dot: Winter sky, Spring
emerald, Summer amber, Fall dark orange. These dots are the only new colours and they are never used for actions,
links or selection, so the Two Stamps Rule still holds. Where the text below says uppercase labels, 1.5px ink
section rules or a postmark on every row, this paragraph wins.

**Original direction:**

Every application is a letter you send and every job wears a postmark. The site looks like a Canadian post office counter. A postal red bar runs across the top. Airmail blue marks links, fit notes and anything you picked. The ground is plain white letter paper, and the filter strip and picked rows take the pale blue grey of an envelope security tint. Headings and form labels are set in narrow capitals like the print on a customs slip.

The page is dense on purpose. Students scan many jobs at once between classes, so lists are rows split by thin rules and type size, not boxed cards. Ink rules at 1.5px frame each section. Corners are square everywhere except the round things a post office really has: postmarks and dots.

The signature is the postmark. Each job carries a round two ring stamp with its city, the day it was posted and its region, at its own small tilt so the list looks stamped by hand. The same mark comes back as cancellation stamps for tracker stages.

**Key Characteristics:**
- Postal red owns the top bar and the main action. Airmail blue owns links, fit and selection.
- White letter paper ground with an envelope tint for the filter strip and picked rows.
- Archivo at narrow widths for headings and labels, normal width for reading, tabular numbers.
- Square corners and 1.5px ink rules. Rows, not cards.
- The tilted postmark and stage stamp are the one round, playful element.

## Colors

Two strong postal colors on white paper, held in place by a cool ink grey.

### Primary
- **Postal Red** (postal-red): the full width top bar, the primary button, the Apply button, an offer stamp, urgent deadlines, the New label and the postmark of the picked job. The text caret in fields is red too. It marks where you act.
- **Postal Red Deep** (postal-red-deep): hover on red buttons, the text of white buttons on the red bar, and the Delete account heading.

### Secondary
- **Airmail Blue** (airmail-blue): links, the focus ring, picked filter chips, role labels, fit bullets, postmarks at rest, the days left fill and the browser accent color on checkboxes.
- **Airmail Blue Deep** (airmail-blue-deep): hover on picked chips and text on accent tags.
- **Airmail Wash** (airmail-wash): the picked row in the job list, keyboard focus on a row, quiet button hover and the temporary account strip.
- **Airmail Tint** (airmail-tint): text selection and the border of accent tags.

### Neutral
- **Letter Paper** (letter-paper): the page ground, fields, chips and secondary buttons.
- **Envelope Security Tint** (security-tint): the filter strip under the bar, tab rows, the secondary button hover and loading blocks.
- **Ink** (ink): body text, headings, the 1.5px section rules, secondary button borders and the filled state of segmented toggles.
- **Ink Soft** (ink-soft): secondary lines such as place and company context.
- **Ink Muted** (ink-muted): form labels and small meta text.
- **Field Stroke** (field-stroke): resting borders of fields and chips.
- **Faint Rule** (rule-faint): the thin rule between job rows and the empty track of the days left bar.

### Named Rules
**The Two Stamps Rule.** Red means act or urgent. Blue means link, fit or picked. Never swap them, and never add a third accent.

**The Region Rule.** Color owns whole regions, not small decorations. The red bar spans the full width and the tint fills the whole filter strip.

## Typography

**Display Font:** Archivo variable (with ui-sans-serif, system-ui)
**Body Font:** Archivo at normal width
**Label Font:** Archivo at 78% width, uppercase

**Character:** One family pulled to different widths. Narrow and heavy for headings, labels and stamps, normal width for reading. It reads like printed postal forms, not like a magazine.

### Hierarchy
- **Display** (800, 36px rising to 48px on wide screens, line height about 1, 82% width, tight tracking): page titles such as Find co-op jobs that fit you and Tracker. The picked job title in the details panel uses the same style at 28px to 34px.
- **Headline** (800, 24px, 82% width): section heads like About you and empty state lines. The list header uses 22px to 26px and names the range in view.
- **Title** (700, 16px, line height 1.375): job titles in list rows. Match titles and the days left line use 87% width at 18px to 20px.
- **Body** (400, 14px, line height 1.5, tabular numbers): most UI text. Reading text in the details panel is 15px at line height 1.625, capped at 70ch.
- **Label** (700, 11px, uppercase, 0.08em tracking, 78% width): form field labels, fact names in the ruled facts row, Sort by, Showing 1 to 25 of 168, and short headings over a list such as Skills it mentions.
- **Wordmark** (800, 19px to 22px, uppercase, 75% width): CoopRadar on the red bar only.
- **Stamp** (800, 17px at 75% width, with 9px bold ring lines): text inside postmarks and stage stamps.

### Named Rules
**The Customs Slip Rule.** Uppercase belongs to labels, the wordmark and stamps. Headings and body stay in sentence case.

**The Tabular Rule.** Numbers are tabular across the whole site so counts, dates and days left line up.

## Layout

The app shell is centered at 1280px with 16px side padding. The red bar is 56px tall. From 768px up the tabs sit in one row with the wordmark. On phones the tabs drop to a second 44px row that scrolls sideways, so nothing hides.

Find jobs is a split view from 1024px up: the job list on the left and a sticky details panel on the right, divided by a faint rule. Below 1024px a row opens the job on its own page. Single task pages such as Match my resume, AI key and Tracker use a narrower centered column.

Rhythm is tight. Job rows pad 12px top and bottom and 16px to 20px at the sides. Sections are separated by an ink rule and about 16px of space before the next heading. Facts sit in a two or three column grid between two ink rules.

## Elevation & Depth

The page is flat. Depth comes from rules, the security tint and the red bar, not from shadows. Soft ink shadows appear only on things that float above the page.

### Shadow Vocabulary
- **Overlay** (`box-shadow: 0 18px 40px rgba(22, 24, 29, 0.18)`): the sign in dialog and the filters drawer.
- **Lifted** (`box-shadow: 0 10px 24px rgba(22, 24, 29, 0.12)`): a tracker card being dragged, which also tilts 2 degrees.

### Named Rules
**The Flat Paper Rule.** Nothing resting on the page casts a shadow. A shadow means it floats or is in your hand.

## Shapes

Every corner is square (0): buttons, fields, chips, tags, dialogs and panels. Round (9999px) is kept for postmarks, stage stamps and status dots. Borders carry the structure: 1.5px ink rules for sections, 2px borders on buttons and the main search box, 1.5px on fields and chips, 1px faint rules between rows. A dashed red tilted box stands for the resume drop target, like a stamp space on an envelope.

## Components

### Buttons
Solid and firm, like a rubber stamp.
- **Shape:** square corners (0) with a 2px border.
- **Primary:** postal red fill and border, white bold 14px text, 8px by 16px padding.
- **Hover / Focus:** red deepens on hover. Focus shows the 2px airmail blue outline at 2px offset.
- **Secondary:** white with an ink border and ink text, tint on hover.
- **Quiet:** no border, airmail blue text, airmail wash on hover.
- **On the red bar:** white outlined button for the demo and sign out, solid white with red text for sign in.

### Chips
- **Style:** white, 1.5px field stroke border, semibold 14px ink text, 4px by 12px padding, square.
- **State:** picked chips fill airmail blue with white text. Counts sit inside in smaller muted type.

### Segmented Toggles
List and Table, Board and List, and the level picker sit in one bordered strip. The picked part fills ink with white text.

### Cards / Containers
- **Corner Style:** square (0).
- **Background:** letter paper.
- **Shadow Strategy:** none at rest (see Elevation).
- **Border:** job lists are rows with a 1px faint rule between them, opened and closed by 1.5px ink rules. Boxes appear only for real objects: the resume drop zone, the AI provider choices and a dragged tracker card.
- **Internal Padding:** 12px by 16px to 20px for rows.

### Inputs / Fields
- **Style:** white, 1.5px field stroke border, square, 8px by 12px padding, 14px text. The main search box uses a 2px ink border with the red Find jobs button joined to its right edge.
- **Focus:** the border turns airmail blue. The caret is postal red.
- **Disabled:** 50% opacity.

### Navigation
The postal red bar holds the white condensed wordmark and the tabs. Tabs are 15px semibold in a pale red tint, turning white on hover. The open tab is white with a 3px white bar under it. A thin white divider splits tabs from account buttons.

### Postmark
A round stamp, 78px (68px in list rows), with a 2px outer ring and a faint inner ring. City on top, day and month in the middle, region below, all in condensed caps. Each job tilts between about minus 10 and 4 degrees, picked from its id so it always tilts the same way. At rest it is airmail blue. When the job is picked it turns postal red and lands with a 260ms stamp motion, which is turned off under reduced motion.

### Stage Stamp
The same two ring mark at 60px for tracker stages, with the stage name on top and the day it changed. Early stages are grey, moving ahead is blue that darkens by stage, an offer is red. On the board each column head carries a stamp and a large count.

### Days Left Bar
A 10px bar drawn to scale from the posted day to the deadline. The part already gone fills airmail blue, or postal red in the last 7 days. Dates sit under each end, and a note says when the deadline is a guess.

## Do's and Don'ts

### Do:
- **Do** keep the red bar full width and the filter strip fully tinted.
- **Do** split lists into rows with faint rules and frame sections with 1.5px ink rules.
- **Do** set headings at 82% width, weight 800, tight tracking, in sentence case.
- **Do** use the 11px uppercase label style for form labels and fact names.
- **Do** reuse the postmark or stage stamp when a date or stage needs a mark.
- **Do** keep every corner square unless the thing is a stamp or a dot.
- **Do** write UI text in plain short words with no dashes and no emoji.

### Don't:
- **Don't** use rounded corners on buttons, fields, chips or panels.
- **Don't** box job rows as separate cards with shadows.
- **Don't** use red for links or blue for the main action.
- **Don't** add shadows to anything that rests on the page.
- **Don't** put a small uppercase line above a heading as a kicker. Labels name fields and lists, they do not introduce headlines.

## Open Items

- Closed 2026-10-13: list rows no longer carry a postmark, so the repeated date problem is gone. The postmark stays on the job details.
- Archivo loads from Google Fonts. Self hosting the font is still to do.
