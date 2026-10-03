# Foliolet design system

> Source of truth for Foliolet's visual and interaction language. Tokens live in
> `django-service/dashboard/static/wallet/wallet.css` (`:root`); components are the
> classes documented here. If a screen needs something this file does not define,
> add the rule here and to the shared stylesheet. Don't patch one template.

---

## 1. What the interface has to make obvious

Foliolet holds a private document and lets its holder prove **one fact from it**
without handing over the rest. Every screen answers some of these questions:

| Question | Where it is answered |
|---|---|
| Which private documents do I hold, and what state is each in? | Document register (home) |
| What facts exist in this document, and who stated each one? | The sheet (document page) |
| Which facts leave, and which stay private? | The slip preview (compose) |
| Who is the disclosure for, why, for how long, how many times? | Terms block (compose, share receipt, sharing) |
| What exactly has been checked, and by whom? | Check ledger (verify) |
| How strong is the source assurance? | Assurance ladder |
| Is this credential version current? | Lifecycle line + check ledger |

The design avoids two failures: burying people in cryptography, and hiding everything
behind one green tick. Plain language comes first. Every plain-language claim opens
onto the technical record that justifies it.

## 2. Visual philosophy: sheets, slips and a ledger

The interface borrows from **paper records**, because the product is about paper
records. Three objects carry the whole metaphor:

1. **The sheet.** An enrolled document is shown as a white sheet resting on a
   warm-grey desk. Its facts are *ruled lines*: label on the left, value on the
   right in the document serif, with an origin mark beneath. A sheet is the only
   raised surface in the product.
2. **The slip.** A disclosure is a narrower sheet cut from the original. Disclosed
   lines are printed in full. Every withheld line becomes a solid **redaction bar**.
   The count of bars is real: it is the number of committed facts not disclosed
   (`leafCount − disclosed`), which the proof bundle already reveals. That is
   exactly the correlation limit the product documents, so the metaphor stays honest.
   The redaction bar is Foliolet's signature mark. It is never decoration.
3. **The ledger.** Verification is a ruled table of separate checks. Each row says
   what was checked, its result *in words*, and **who checked it** (the
   Foliolet service, this browser, or nobody). Rows that the system cannot establish
   (holder authorization against a malicious platform, issuer authenticity) remain
   visible as "Not established" rather than disappearing.

Atmosphere: a registry office rather than a crypto app. Calm, legible and exact.
There are no gradients, glows, glass, illustrations or decorative icons, and no
statistics that exist only to fill space.

## 3. Information density

Medium-high, like a well-set form rather than a marketing page.

- Authenticated screens open straight into content. There are no heroes; a page head
  is a title, one sentence and the primary action.
- Lists are **ruled rows**, not card grids. A document register row carries name,
  category, version, state, assurance, fact count and next action on one line at desktop.
- Technical values (roots, addresses, hashes, paths) are always one disclosure away,
  never deleted and never in the first reading line.

## 4. Color roles

Two themes share every role: **light** (paper on a desk) and **dark** (the same desk at night,
not a neon inversion). The masthead switch offers Light / Dark / Auto; Auto follows the
system. The choice is stored per browser (`theme.js`, loaded in `<head>` so there is no flash).
Light values are below; the dark set redefines the same tokens under `:root[data-theme="dark"]`
and `prefers-color-scheme: dark`. Colors are roles, not decoration; the CSS custom properties
are canonical.

| Token | Value | Role |
|---|---|---|
| `--desk` | `#EEECE7` | Page background, the desk the sheets rest on |
| `--desk-deep` | `#E4E1DA` | Recessed wells: code blocks, the redaction tray, table headers |
| `--sheet` | `#FFFFFF` | Raised documents, slips, forms |
| `--ink` | `#1B1D21` | Text, redaction bars, primary button fill |
| `--ink-2` | `#454A52` | Secondary text |
| `--ink-3` | `#5D626A` | Tertiary text and captions (≥ 4.5:1 on desk and sheet) |
| `--rule` | `#D8D4CB` | Hairlines between lines and rows |
| `--rule-strong` | `#A9A498` | Sheet and table edges, section rules (decorative boundaries) |
| `--control-edge` | `#88837A` | Borders of interactive controls: inputs, selects, outline buttons, segmented control (≥ 3:1 on sheet and desk) |
| `--seal` | `#283C8E` | **The only accent.** Links, focus, selected state, the commit action |
| `--seal-ink` | `#1E2E70` | Hover and pressed seal |
| `--seal-wash` | `#E7EAF5` | Selected rows, the current step |
| `--pass` / `--pass-wash` | `#1D6A41` / `#E2F0E7` | A check that passed |
| `--caution` / `--caution-wash` | `#7E5300` / `#FAF0D9` | Limits, pending, holder-controlled assurance |
| `--fail` / `--fail-wash` | `#A1241E` / `#FAE5E2` | Failed checks, revocation, destructive actions |
| `--quiet` / `--quiet-wash` | `#5D626A` / `#E8E6E0` | Not checked, not available, inactive |

Foreground tokens (`--on-ink`, `--on-seal`, `--on-status`) carry text placed on solid fills,
so buttons and marks stay legible in both themes. Dark accents are lightened (seal `#9DB0F5`,
pass `#6CCB98`, caution `#E8B85A`, fail `#F29488`) and all text pairs stay ≥ 6:1.

**Category hues** (`--cat-education`, `-employment`, `-finance`, `-identity`, `-purchase`,
`-other`) are the only extra colors. They appear as a 4px spine on document rows and a small
square before the category kicker. They help you scan and recognize a document; they never carry status.

Rules:
- `--seal` never means "success". Green means one specific check passed, and only that.
- Status is never color-only. Every mark pairs a glyph shape with a word.
- Redaction bars use `--ink`, so withheld lines read as printed-over, not as errors.

## 5. Typography

Self-hosted (strict `font-src 'self'` CSP); all OFL licensed.

| Family | Use |
|---|---|
| **Source Serif 4** | The *document voice*: page titles, document names, fact values, the wordmark |
| **Public Sans** | The *interface voice*: labels, controls, body, navigation |
| **IBM Plex Mono** | The *record voice*: fact paths, hashes, addresses, IDs, chain values |

Scale (rem at 16px root):

| Token | Size / line | Weight | Use |
|---|---|---|---|
| `--t-title` | 2.125rem / 1.15 | Serif 500 | Page title (`h1`) |
| `--t-heading` | 1.25rem / 1.3 | Serif 500 | Section heading (`h2`) |
| `--t-sub` | 1rem / 1.4 | Sans 650 | Sub-heading (`h3`), row titles |
| `--t-body` | 0.9375rem / 1.6 | Sans 400 | Body |
| `--t-small` | 0.8125rem / 1.5 | Sans 400 | Captions, helper text |
| `--t-label` | 0.8125rem / 1.3 | Sans 600 | Form labels, ledger column heads |
| `--t-mono` | 0.8125rem / 1.55 | Mono 400 | Technical values |
| `--t-value` | 1.0625rem / 1.4 | Serif 500 | Fact values on sheets and slips |

Rules: the serif is never used for controls; the sans is never used for fact values;
mono is never used for prose. No all-caps tracked eyebrows; kickers are sentence case.
Titles use weight 500, never bold.

## 6. Spacing and layout

4px base: `--s1 4` · `--s2 8` · `--s3 12` · `--s4 16` · `--s5 24` · `--s6 32` · `--s7 48` · `--s8 64`.

- App column: max 1120px, centred, 24px gutters (16px under 600px).
- Two-column work layouts (sheet + rail; composer + slip) use a 7/5 split with a 32px
  gap, collapsing to one column under 900px. On mobile the rail moves *above* the
  sheet when it holds the primary action.
- Vertical rhythm: 48px between page sections, 24px between blocks inside a section,
  12px between lines in a list.

## 7. Geometry, surfaces and depth

- **Radius:** sheets, slips, lists and the ledger `10px`; controls `6px`; mark glyphs and
  redaction bars `3–5px`. Softened, never pill-shaped: status marks stay glyph-plus-word, not
  capsules. Circles are reserved for the stepper dot.
- **Levels:**
  - 0 desk: flat, no border.
  - 1 sheet: `--sheet` fill, 1px `--rule-strong` edge, shadow `0 1px 0 rgb(27 29 33 / 5%), 0 2px 6px rgb(27 29 33 / 5%)`.
  - Wells: `--desk-deep` fill, no shadow (recessed).
  - Nothing floats above a sheet. There are no modals; confirmation happens inline with
    `<details>` or a dedicated step.
- A section that isn't a document (forms, ledgers, explanations) sits on the sheet
  level only when it is a unit of work. Explanatory text lives directly on the desk.

## 8. Navigation

- A sticky **masthead** strip with a 3px seal rule along its top edge, not a sidebar. Three destinations matter: **Documents**,
  **Shared**, **First-seen**. The wordmark is on the left and the account on the right.
  Current page uses `aria-current` with a 2px seal underline.
- Under 720px the destinations sit in a scrollable row beneath the wordmark. All three
  stay visible; there is no hamburger.
- Detail pages carry a single breadcrumb link back to their list.
- Public verification uses a stripped masthead: wordmark plus "Disclosure verification",
  and no account navigation.

## 9. Components

### Buttons (`.btn`)
| Variant | Look | Use |
|---|---|---|
| `.btn` (primary) | `--ink` fill, white text | The one forward action per view |
| `.btn.seal` | `--seal` fill | Commit actions: anchor, create link, check proof |
| `.btn.line` | Sheet fill, 1px `--rule-strong` | Secondary actions |
| `.btn.quiet` | Text-only, seal color, underline on hover | Tertiary/navigation |
| `.btn.danger` | `--fail` 1px outline → fill on hover | Revocation, inside a `<details>` confirmation |

Height ≥ 44px (40px for `.btn.small` in dense rows that have ≥ 8px separation).
Labels are verbs naming the result ("Create proof link", "Revoke this link").
No arrow glyphs on every button; an arrow means navigation only.

### Inputs (`.field`)
Label above, helper below, error below helper with `aria-describedby`. 1px
`--rule-strong` border, `--sheet` fill, 3px radius, 44px height. Focus: 2px `--seal`
outline, 2px offset. Required fields are not starred; optional ones say "(optional)".

### Choices
- `.choice` rows: full-width selectable lines (checkbox or radio + content).
  Selected = `--seal-wash` fill + 2px seal left edge.
- `.segmented`: radio group drawn as joined rectangles, used for short exclusive
  options (expiry).

### The sheet (`.sheet`) and fact lines (`.lines` / `.line`)
Each line: label (sans 600), value (serif), **origin mark** underneath. The same
two phrases are used on every screen, holder and verifier alike:
- **Holder-authored statement** (hollow square): a fact the holder confirmed or typed.
- **Platform-derived threshold** (filled seal diamond): a value the platform computed from a
  holder-confirmed fact ("CGPA at least 8.5"). Its derivation path is shown in mono with
  "not a zero-knowledge range proof" stated inline.
On the verifier page a holder-authored label is always prefixed **"Custom label:"**, and
only a recognized derived leaf may print the platform wording. A holder cannot type a
label that looks like a platform claim. Paths and types are mono, ink-3, shown below the value.
One partial (`_fact_line.html`) renders every fact line so this rule can't drift.

### The slip (`.slip`) and redaction (`.redacted`)
A slip has a perforated top edge (a short dashed rule, the only patterned line in the
system, marking that it was cut from a sheet), a header (who it's for, purpose),
disclosed lines, then a tray of redaction bars with the caption "N facts withheld".
In the composer the slip is a live preview: lines appear as facts are checked and
bars disappear one-for-one. Bars have varied widths derived
from position (never random per render) and `aria-hidden`. The caption carries the meaning.

### Check ledger (`.ledger`)
Table with columns **Check · Foliolet service · This browser**. Cells hold a
**mark**:
| Mark | Glyph | Word |
|---|---|---|
| `.mark.pass` | ✓ | Passed |
| `.mark.fail` | ✕ | Failed / Not accepted |
| `.mark.caution` | ! | Limited / Service-reported |
| `.mark.quiet` | – | Not run / Not checked |
| `.mark.none` | ○ | Not established |
Each row has a one-line plain description; a `<details>` reveals the technical meaning.
On mobile the ledger becomes stacked rows, with the column name repeated beside each mark.

### Assurance ladder (`.ladder`)
Three rungs, always all shown: **Self-enrolled → First-seen tracked → Issuer-verified**.
Horizontal when it spans a page (First-seen explainer); `.ladder.vertical` in rails.
The achieved rung is filled; higher rungs are outlined. Issuer-verified is marked
"Not available in this version". Never hide the rungs above the achieved one, because the
gap is the information.

### Lifecycle (`.lifecycle`)
Horizontal steps: **Uploaded · Facts confirmed · Anchored · Shareable**. Terminal states
replace the last step: *Revoked* (fail), *Superseded* (quiet, with link to replacement).
The current step uses a seal dot; completed steps use a filled ink dot.

### Notices (`.notice`)
Inline, full-width, 3px left edge in the status color, wash fill, text in ink. `.info`
(seal) is for explanations of platform behavior, never for results.
`role="status"` for results and `role="alert"` for errors. The variants are `.success`,
`.warning`, `.error` and a neutral base. Notices explain consequences ("Revocation is
permanent for this version"), not feelings.

### Technical record (`.record`)
`<details>` with summary "Technical record". Inside: a `dl.kv` grid of mono values that
wrap with `overflow-wrap:anywhere`, and copyable `<pre>` blocks in a `--desk-deep` well
with horizontal scroll and a max-height.

### Register rows (`.register`)
Document list rows: serif name, then a meta line, a state mark, assurance and the next action.
Row is a single link target (name) plus an explicit action button. No nested
links. Hover adds the `--seal-wash` fill.

### Empty states
One sentence on what is missing, one on what to do, and one action. No illustration.

### Loading
Server-rendered pages have no skeletons. In-page async work (independent check) sets
the trigger button to `aria-busy="true"` with a verb in progress ("Reading the
registry…") and disables inputs it depends on.

## 10. Status vocabulary

Backend states are translated, never shown raw as the only label:

| Backend | Holder-facing words |
|---|---|
| `DRAFT` (no facts) | Needs fact review |
| `DRAFT` (facts confirmed) | Ready to anchor |
| `ANCHOR_PENDING` | Anchoring incomplete, retry safely |
| `ACTIVE` | Anchored, ready to share |
| `REVOKED` | Revoked |
| `SUPERSEDED` | Replaced by a newer version |
| grant `ACTIVE` / `CONSUMED` / `EXPIRED` / `REVOKED` / `CREDENTIAL_UNAVAILABLE` | Open · Used (one-time) · Expired · Revoked · Source credential no longer current |

Trust words are exact: *passed*, *failed*, *not run*, *service-reported*,
*not established*. Banned: "secure", "trustless", "guaranteed", "tamper-proof",
"verified identity", "zero-knowledge" (except to say it is **not** one).

## 11. Motion

Motion explains change; it never loops or decorates.
- **Arrival:** the page rises 8px and fades in once (360ms). List rows, fact lines, grants
  and ledger rows follow in a short stagger (40ms steps, capped at 320ms).
- **Progress:** completed lifecycle segments draw left-to-right in seal.
- **State:** ledger marks pop (scale) when the browser check sets them; the composer's
  slip lines slide in and redaction bars collapse one-for-one as facts are chosen.
- **Hover:** open link cards lift 2px with a deeper shadow; register rows tint and the
  category spine extends to full height; nav underline grows from the centre.
- **Theme change:** colors cross-fade for 280ms.
- Durations stay 140–520ms with ease-out curves. All animations use `backwards` fill, so no
  final state is held after they finish. `prefers-reduced-motion: reduce` removes every
  transition and animation.

## 12. Responsive behavior

| Width | Behavior |
|---|---|
| ≥ 1024 | Two-column work layouts; register as one-line rows |
| 720–1023 | Work layouts stack; rail first when it holds the primary action |
| < 720 | Masthead nav becomes a scroll row; register rows wrap to 2–3 lines; ledger stacks; segmented control wraps to 2×2 |
| < 400 | Gutters 16px; buttons full width in forms |

Long content: names wrap; mono values use `overflow-wrap:anywhere`; tables live in
`.scroll-x` wrappers with a visible edge; `pre` blocks scroll inside a max-height well.

### Assets
Stylesheets and scripts are linked through the `{% asset %}` tag, which appends a content
hash so a design change is never served stale. Fonts are self-hosted woff2 (latin subset).

## 13. Accessibility

- WCAG 2.2 AA contrast for all text: ink-3 is 5.2:1 on desk, 4.7:1 on desk-deep; every
  status color is ≥ 5.5:1 on its wash. Control borders are ≥ 3:1 (`--control-edge`).
- Visible 2px seal focus ring with offset on every interactive element; never removed.
- Skip link; one `h1` per page; landmark `header`/`nav`/`main`/`footer`.
- Every input has a `<label>`; helpers and errors are tied with `aria-describedby`.
- Grouped choices use `fieldset`/`legend`.
- Live results use `role="status"`; blocking errors use `role="alert"`.
- Touch targets are ≥ 44×44 (choice rows are fully clickable labels).
- Status never relies on color alone (glyph + word).
- Redaction bars are `aria-hidden`; the caption states the count.

## 14. Writing

- Address the holder as "you"; the recipient is "the verifier".
- Say what happens and what doesn't: "The original file is not sent."
- Prefer "fact" over "claim" in holder flows; prefer "proof" over "bundle" except
  in the technical record and download filename.
- One limitation sentence beats three disclaimers; the rest go in the technical record.

## 15. Do and don't

**Do**
- Show every distinct check as its own ledger row with who checked it.
- Keep the assurance ladder complete, including the unavailable top rung.
- Mark every fact's origin (holder statement vs platform-derived).
- Keep technical detail one disclosure away and copyable.
- Use the redaction tray to show how much stays private.

**Don't**
- Don't put a single "VERIFIED" badge on the verifier page.
- Don't use green for anything but a passed check, or category hues for status.
- Don't use pills, gradients, glows, glass, decorative icons or stat tiles.
- Don't introduce a second accent color.
- Don't show raw backend enums as the only status text.
- Don't claim issuer authenticity, holder authorization or zero-knowledge.
- Don't add inline styles or scripts (CSP: `style-src 'self'`, `script-src 'self'`).
- Don't offer an action that can't change anything (e.g. revoking an already-closed link).
- Don't print raw ISO timestamps; use the `wallet_time` filter.
