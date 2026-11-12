---
name: BioFlux Lab
description: A molecular atlas for inspecting computational metabolic interventions.
colors:
  primary: "#176d5b"
  primary-hover: "#115a4a"
  atlas-ground: "#f5f7f6"
  sidebar-ground: "#edf2f0"
  control-ground: "#ffffff"
  ink: "#213544"
  muted: "#5b6f7a"
  evidence-ink: "#536b75"
  line: "#dce5e5"
  navy: "#101f30"
  graph-text: "#9eb5c7"
  graph-edge: "#3c566d"
  metabolite: "#87a8c8"
  reaction: "#9bd9c9"
  target: "#e7c087"
  disabled-reaction: "#f29c86"
  focus: "#378e7a"
  segmented-ground: "#e9eeec"
  segmented-ink: "#4f6862"
  tag-ground: "#d8e8df"
  tag-ink: "#285b4b"
  chart-random: "#748fa8"
  chart-greedy: "#886f9f"
  chart-tree: "#bd784e"
  chart-graph: "#177764"
typography:
  headline:
    fontFamily: "Manrope, system-ui, sans-serif"
    fontSize: "35px"
    fontWeight: 650
    lineHeight: 1.23
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Manrope, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 650
    lineHeight: 1.4
    letterSpacing: "-0.03em"
  body:
    fontFamily: "Manrope, system-ui, sans-serif"
    fontSize: "13px"
    lineHeight: 1.55
  button:
    fontFamily: "Manrope, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 550
  metric:
    fontFamily: "Manrope, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 500
    letterSpacing: "-0.5px"
rounded:
  tag: "4px"
  segmented: "6px"
  control: "7px"
  research: "12px"
  network: "13px"
spacing:
  action-gap: "9px"
  control-padding: "10px 15px"
  region-gap: "25px"
  research-padding: "25px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.control-ground}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "{spacing.control-padding}"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-secondary:
    backgroundColor: "{colors.control-ground}"
    textColor: "#41645b"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "{spacing.control-padding}"
  select:
    backgroundColor: "{colors.control-ground}"
    textColor: "#334e57"
    rounded: "{rounded.control}"
    padding: "8px 28px 8px 10px"
  gene-tag:
    backgroundColor: "{colors.tag-ground}"
    textColor: "{colors.tag-ink}"
    rounded: "{rounded.tag}"
    padding: "4px 7px"
  research-card:
    backgroundColor: "{colors.control-ground}"
    rounded: "{rounded.research}"
    padding: "{spacing.research-padding}"
  network-panel:
    backgroundColor: "{colors.navy}"
    rounded: "{rounded.network}"
    padding: "20px 20px 14px"
---

# Design System: BioFlux Lab

## Overview

**Creative North Star: "The Molecular Atlas"**

Light sage working surfaces, deep navy topology and precise categorical marks give this local research application the character of a structural biology atlas. Compact controls and aligned numerical comparisons support inspection; biological imagery adds context without substituting for model evidence.

This records the primary React/TypeScript interface and local FastAPI integration. The optional legacy Streamlit interface is not the source of these tokens. The approved direction is code-led: built components, rather than a raster UI comp, define the system.

**Key Characteristics:**
- Light working surfaces beside a dark scientific topology canvas.
- Self-hosted Manrope, compact labels and tabular numerical results.
- Categorical graph shapes, explicit source labels and recorded research tables.
- Brief state transitions and clearly labeled conceptual cell art.

## Colors

The palette combines restrained green actions with cool neutral surfaces; graph and chart categories retain their own identities.

### Primary
- **Laboratory Green** (`primary`): solver actions, active navigation, links and native input accents. Its deeper hover variant supports pointer feedback.

### Secondary
- **Atlas Blue** (`metabolite`) and **Seafoam** (`reaction`): metabolite circles and reaction squares on navy.
- **Chart categories** (`chart-random`, `chart-greedy`, `chart-tree`, `chart-graph`): random, local greedy, tree search and graph ensemble. The envelope uses chart green for forced minimum and chart blue for potential maximum.

### Tertiary
- **Succinate Amber** (`target`): target metabolites and their neighborhood connections.
- **Disabled Coral** (`disabled-reaction`): reactions disabled by gene rules; distinct from disabled form controls.

### Neutral
- **Atlas Ground**, **Sidebar Ground** and **Control Ground** separate page, parameter rail and fields/research containers.
- **Ink**, **Muted** and **Evidence Ink** carry headings, helper text and result/evidence labels. Individual small-label colors remain source-specific; these roles do not imply every caption shares one color.
- **Navy**, **Graph Text** and **Graph Edge** support topology contrast. Fine dividing lines organize light surfaces without shadows.

**The Explicit Evidence Rule.** Pair color with source labels, units and explanatory text; never let an accent imply biological validation.

## Typography

Manrope uses system-ui and sans-serif fallbacks. Its variable font is self-hosted at `frontend/public/fonts/manrope.ttf`, registered for weights (200–800) with swap display. `OFL.txt` and `provenance.json` retain its Google Fonts official-repository source and SHA-256. No runtime font service is required.

Frontmatter records the desktop headline, section title, body, action label and outcome metric. Headings use tightened tracking; numerical results and tables use tabular numerals. The headline's secondary span uses weight (450). Dense explanatory text commonly uses (10–12px). Trailing stylesheet rules raise graph notes, legends, graph descriptions and inspection text to (10px), and scenario/result labels to (11px), overriding earlier breakpoint sizes.

Page headlines reduce to (30px) at (1000px) and (27px) at (760px); outcome values reduce to (19px) on mobile. Checksums use native monospace. There is no separate decorative display face.

## Layout

The desktop shell has a sticky topbar (76px) and fixed scrollable parameter rail (260px). Main content offsets the rail, uses padding (25px 38px 0) and maximum width (1790px). The graph/outcome grid is (1.65fr / 1fr), with minimum outcome width (270px). The trade-off region is (1fr / 1.9fr); research sections stack. Tables scroll inside their wrappers.

- At widths at least (1700px), main horizontal padding becomes (50px), graph height is capped at (490px), and result rows gain space.
- At widths at most (1200px), main padding becomes (22px 24px 0), grid proportions become (1.4fr / 1fr) with a (240px) outcome minimum, and organism label/drag hint disappear.
- At widths at most (1000px), the rail becomes (230px); graph/outcome, trade-off and method grids stack. Actions share a row, results form three columns, and research filters wrap.
- At widths at most (760px), the topbar is (66px), navigation becomes a fixed bottom bar (62px), and parameters become a toggled drawer of width `min(300px,85vw)`. A scrim closes it. Main has no rail offset and padding (19px 18px 62px); actions stack at minimum height (44px), research filters span the width, and legends wrap.

Charts occupy height (310px), reduced to (300px) on mobile, and resize with containers. Keep this dense working rhythm rather than adding marketing-page spacing.

## Elevation & Depth

The application stylesheet defines no box shadows. Surface tone, fine borders and navy/light separation establish hierarchy. Header, rail, scrim and bottom navigation use stacking order for interaction rather than visual lift. The mobile scrim is translucent navy (`#142b3b66`). Library tooltip presentation is not an application shadow token.

## Shapes

Gently rounded controls, compact tags and larger scientific containers form the vocabulary recorded in frontmatter. Segmented selections use inset radius (4px); cell artwork clips to corners (9px). Outcomes and trade-off explanations remain open on the page ground.

Graph marks are semantic: reactions are rounded squares (7.6px), metabolites circles (3.3px radius), and succinate circles larger (7px radius), with labels. Legends repeat the circle/square distinction.

## Components

### Buttons

Solver verification is green primary; graph prediction and trade-off calculation are white secondary actions with fine green-gray borders. Desktop minimum height is (41px). Fine-pointer hover lifts by (1px), deepens primary green or softens secondary fill; press scales to (.98). Disabled controls use opacity (.48) and a not-allowed cursor. Busy actions show a loading icon. Text actions underline on fine-pointer hover.

All focusable controls use a green outline (2px), offset (4px); retain the skip link. Do not conflate graph-disabled coral with form-disabled opacity.

### Inputs, tags and navigation

Native ranges set nutrients; selects choose deletions, graph inspection and research views. Selects have fine borders, white fill and minimum height (41px). Selected genes become removable pale-green tags. Topbar text/icon buttons use a thin green active underline; mobile moves that underline above bottom navigation. Segmented controls use `aria-pressed`, muted ground and white selection; the graph variant uses navy tones.

### Outcomes and evidence

Empty outcomes show dashes and action guidance. Prediction and solver answers keep explicit sources; comparison tables preserve units. Success/warning strips use pale green/amber; errors use pale coral with an alert role. Scenario changes clear stale results. Research combines labeled charts with inspectable numeric tables and source manifests; animation does not imply new experiment execution.

Outcome changes use Motion opacity and (8px) vertical arrival over (240ms), easing `cubic-bezier(.23,1,.32,1)`. Reduced motion removes translation while preserving short opacity changes. CSS reduced motion disables spinner rotation and button transforms; remaining CSS transitions are limited to opacity/visibility (160ms).

### Molecular topology

The SVG graph supports drag, bounded zoom, reset, whole-network/succinate scope, hover inspection and native-select inspection for keyboard users. Connected edges brighten while unrelated marks dim over (180ms). The legend and caption explain that connections are model topology, not measured flux. No perpetual graph animation ships.

### Scientific charts

Apache ECharts uses SVG rendering, labeled axes, meaningful units, legends and numeric tooltips. Methods use stable colors; random search also uses a dashed line. Envelope lines preserve missing endpoints as gaps. Bar labels provide explicit errors. Reveal lasts (240ms), updates (180ms), easing `cubicOut`; reduced motion disables ECharts animation. Tables remain the exact-value path.

### Imagery

`frontend/public/cell-study.png` is conceptual AI-generated bacterial-cell art, shown in the rail with an explicit AI caption and descriptive alt text. Its exact generation prompt is embedded and retained in `cell-study.png.json`. It is not microscopy or experimental evidence. Review screenshots under `.impeccable/review/react` document inspection; scientific report plots retain separate experiment provenance.

## Do's and Don'ts

### Do:
- **Do** retain source labels and units beside scientific values.
- **Do** pair graph colors with marker shapes, legends and topology captions.
- **Do** preserve visible keyboard focus, native fields and responsive drawer/navigation behavior.
- **Do** retain conceptual AI labeling and asset/font provenance.

### Don't:
- **Don't** present a learned estimate or solver simulation as experimental biological validation.
- **Don't** describe ensemble disagreement as a calibrated confidence interval.
- **Don't** animate graph connections as if they were measured flux.
- **Don't** replace exact-value tables with charts alone.
