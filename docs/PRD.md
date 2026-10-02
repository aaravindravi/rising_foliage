# Fall Colour Trip Planner
## Product Requirements & Initial System Specification

**Document status:** Draft v0.1
**Project type:** Open-source project
**Initial test region:** Kelso Summit / Milton, Ontario
**Target region:** Southern Ontario initially; geographically extensible
**Implementation preference:** Python/Python-friendly ecosystem where practical
**Repository:** Intended to be publicly available on GitHub

---

## 1. Project Vision

Create an open-source tool that helps users decide **where and when to visit an area to experience their preferred fall foliage colours**.

Rather than relying only on generalized fall-colour reports, the system should estimate the actual distribution of foliage colours at specific locations using recent observations and provide short-term forecasts.

The eventual user experience should answer questions such as:

> "I live near Milton and can drive for one hour. I want to see forests that are mostly yellow, orange, or red this Saturday. Where should I go?"

or:

> "I want to visit Kelso Summit. Which day during the next week is likely to have the colours I want?"

---

# 2. Problem Statement

Fall foliage changes rapidly and varies considerably by location.

A destination may still be predominantly green while another nearby area is already showing significant yellow, orange, or red foliage.

Existing fall-colour reports may:

- cover large geographic regions;
- use subjective categories such as "30% change" or "peak";
- be updated infrequently;
- not represent conditions at a particular trail or destination;
- provide current conditions but limited forecasting;
- not allow users to specify the colours they personally want to see.

This creates uncertainty when planning a fall-colour trip.

The proposed system should combine multiple forms of evidence to estimate current foliage conditions and forecast how those conditions are likely to evolve.

---

# 3. Primary User Question

The fundamental question the system should answer is:

> **Given my location, travel constraints, intended visit date, and preferred foliage colours, where should I go to maximize my likelihood of seeing those conditions?**

A second important question is:

> **Given a particular destination, when during the next several days should I visit to see my preferred foliage conditions?**

---

# 4. Target Users

### Primary User

Someone planning a local or regional recreational trip specifically to experience fall foliage.

### Example User

**Starting location:** Milton, Ontario
**Destination of interest:** Kelso Summit
**Maximum drive:** 1 hour
**Desired colours:** Yellow through orange/red
**Desired foliage coverage:** ≥60%
**Planning horizon:** Today through approximately 7 days

---

# 5. Core User Modes

## 5.1 Destination Mode

The user already knows where they want to go.

Example:

> "I want to visit Kelso Summit. When should I go?"

The system should display current estimated foliage conditions and predicted conditions over the following days.

---

## 5.2 Discovery Mode

The user does not have a specific destination.

Example:

> "Where can I drive within one hour this Saturday to see mostly yellow and orange foliage?"

The system should identify candidate destinations satisfying the user's travel and foliage preferences.

---

# 6. User Inputs

The eventual system should support the following inputs.

### Location

User's current location or manually selected starting location.

### Travel Constraint

Examples:

- 30-minute drive
- 60-minute drive
- 90-minute drive
- distance radius

Driving time should ultimately be more useful than straight-line distance.

### Visit Date

Examples:

- Today
- Tomorrow
- This Saturday
- Specific calendar date

Initial target forecasting horizon:

**0–7 days**

### Destination

Optional.

Example:

**Kelso Summit**

If specified, the system enters Destination Mode.

### Desired Colour Range

Users should be able to select foliage colours visually rather than relying entirely on textual categories.

Conceptual scale:

**Green → Yellow-green → Yellow → Orange → Red → Brown/Bare**

A graphical selector should eventually allow the user to choose a range.

Example:

**Yellow → Red**

### Desired Coverage

The user should be able to specify how much foliage should fall within their selected colour range.

Example:

> At least **60%** yellow/orange/red.

---

# 7. Fundamental Foliage Representation

The system should not internally represent foliage simply as:

- early;
- changing;
- peak;
- past peak.

Instead, the primary representation should be a **colour distribution**.

Example:

| Foliage state | Estimated coverage |
|---|---:|
| Green | 22% |
| Yellow-green | 10% |
| Yellow | 31% |
| Orange | 22% |
| Red | 8% |
| Brown/Bare | 7% |

These values should approximately sum to 100% of the foliage/canopy area being evaluated.

Simpler categories such as **Peak** or **Near Peak** may later be derived from this underlying representation.

---

# 8. Current Condition Requirement

For a selected destination, the system should estimate the most recent foliage colour distribution available.

The result should contain at minimum:

- estimated colour distribution;
- date/time represented;
- date of most recent supporting observation;
- observation freshness;
- confidence/uncertainty;
- geographic area represented.

The system must clearly distinguish between an actual recent observation and an inferred current state.

---

# 9. Forecasting Requirement

The system should predict foliage conditions into the near future.

### Minimum target

**3-day forecast**

### Desired target

**7-day forecast**

The output should provide predicted foliage colour distributions for individual future dates.

Example:

| Date | Green | Yellow | Orange | Red | Brown/Bare |
|---|---:|---:|---:|---:|---:|
| Today | 42% | 31% | 16% | 4% | 7% |
| +3 days | 27% | 36% | 23% | 7% | 7% |
| +5 days | 16% | 32% | 31% | 10% | 11% |
| +7 days | 9% | 23% | 30% | 11% | 27% |

Forecast uncertainty should generally be allowed to increase with forecast horizon.

---

# 10. Historical Requirement

The system should support retrospective analysis.

A user or developer should be able to request:

**Location + historical date**

Example:

> Kelso Summit — October 5, 2025

and reconstruct an estimate of foliage conditions for that period when suitable data exist.

This capability is particularly important for system development and validation.

---

# 11. Potential Evidence Sources

The system should be designed to accommodate multiple evidence categories.

Specific technologies and providers are intentionally **not fixed at this stage**.

## 11.1 Remote Sensing

Potential sources include freely available satellite observations.

Potential information:

- visible colour;
- vegetation state;
- temporal change;
- canopy characteristics;
- historical seasonal progression.

---

## 11.2 Crowdsourced Observations

Users may eventually contribute:

- photographs;
- location;
- observation date/time;
- optional foliage classification;
- optional comments.

Crowdsourced observations may be used both to improve current estimates and to validate remotely sensed estimates.

---

## 11.3 Existing Public Ground Evidence

Potential sources to investigate include:

- Google reviews;
- Google user photographs;
- publicly posted geotagged photographs;
- park/conservation-area reports;
- webcams;
- tourism reports;
- other public observations.

These sources should initially be considered **potential validation evidence**, not mandatory system dependencies.

Availability, licensing, API restrictions, timestamps, geographic reliability, and terms of use must be evaluated before incorporating any source.

---

## 11.4 Historical Observations

Historical information may provide:

- typical timing of colour transition;
- year-to-year variability;
- previous peak periods;
- historical imagery;
- historical ground observations.

---

## 11.5 Environmental Information

Potential environmental predictors may eventually include:

- temperature;
- accumulated temperature;
- frost;
- precipitation;
- wind;
- daylight;
- elevation;
- forest composition;
- geographic position.

These are candidate inputs rather than fixed requirements.

---

# 12. Evidence Fusion Requirement

The system should eventually support multiple independent sources of evidence rather than treating any one source as absolute ground truth.

Conceptually:

**Remote observations + Ground observations + Historical behaviour + Environmental conditions → Foliage estimate**

The contribution of each evidence source should remain identifiable where possible.

---

# 13. Confidence and Uncertainty

Every foliage estimate or forecast should have an associated measure of confidence or uncertainty.

Factors may include:

- age of most recent observation;
- observation quality;
- cloud obstruction;
- agreement between evidence sources;
- number of ground observations;
- geographic coverage;
- forecast horizon;
- historical variability.

The interface should not present uncertain estimates as precise facts.

For example:

**Estimated orange/red coverage: 68%**
**Confidence: Moderate**

may be preferable to presenting **68%** without qualification.

---

# 14. Data Freshness

The system should record when each piece of evidence was obtained.

Users should be able to distinguish between:

**Observed yesterday**

and

**Estimated from an observation seven days ago**

even if both generate similar foliage predictions.

---

# 15. Geographic Representation

A named destination should correspond to a defined geographic area rather than a single coordinate.

For example:

**Kelso Summit**

may include a defined forested region surrounding relevant trails/viewpoints.

The exact method for defining destination boundaries remains an open design question.

---

# 16. Foliage Definition

The system must eventually establish a consistent definition of what is included in foliage calculations.

Questions requiring formal definition include:

- Are evergreen trees excluded?
- Are shrubs included?
- Are bare branches considered foliage?
- Is the denominator total vegetation or deciduous canopy?
- Are water, buildings, roads and exposed soil excluded?
- How are mixed forests handled?

These definitions must be resolved before quantitative percentages can be considered meaningful.

---

# 17. Colour Definition

Colour categories must eventually have reproducible definitions.

Initial conceptual categories:

1. Green
2. Yellow-green / transitioning
3. Yellow
4. Orange
5. Red
6. Brown
7. Bare/no foliage

The project should investigate whether some categories should be merged or represented continuously.

The user's visual colour selector should eventually correspond to these underlying definitions.

---

# 18. Validation Requirement

Validation is a core project requirement.

The system must provide a way to compare estimated foliage conditions against independent observations.

Example:

**Prediction**

Kelso Summit
October 5, 2025

Estimated:

- Green: 14%
- Yellow: 37%
- Orange: 31%
- Red: 10%
- Brown/Bare: 8%

**Independent evidence**

Ground-level photographs, reports, reviews or other observations from approximately the same place and date.

The project should quantify agreement rather than relying only on visual inspection.

---

# 19. Ground Truth

No single source should automatically be considered perfect ground truth.

Potential ground-truth evidence may have limitations.

For example:

- photographs may show only one viewpoint;
- photographs may be edited;
- upload date may differ from capture date;
- reviews may describe subjective impressions;
- satellite observations see canopy from above;
- crowdsourced classifications may vary between users.

Therefore, the project should distinguish between:

**reference observations**

and

**absolute ground truth**.

---

# 20. Recommendation Requirement

Once foliage estimation and forecasting have been validated, the system should support destination recommendations.

Conceptually:

**User location**
+ **maximum travel time**
+ **visit date**
+ **desired colour range**
+ **minimum coverage**
↓
**Recommended destinations**

A destination should not be recommended solely because it is geographically close.

The recommendation should consider how well the predicted foliage matches the user's preference.

---

# 21. Map Requirement

The eventual interface should provide a geographic visualization.

The map should allow users to understand where preferred foliage conditions are expected.

Potential visualization:

**Green → Yellow → Orange → Red → Brown**

The map should eventually support filtering according to the user's selected colour range and date.

---

# 22. Temporal Interface Requirement

The user should be able to move through time visually.

Conceptually:

**Today ─ +1 ─ +2 ─ +3 ─ +4 ─ +5 ─ +6 ─ +7**

Moving the control should update:

- foliage map;
- destination estimates;
- colour percentages;
- recommendations;
- confidence.

---

# 23. Transparency Requirement

The system should provide enough information for users to understand why an estimate exists.

Where practical, a result should expose:

- source observation dates;
- evidence types;
- forecast horizon;
- confidence;
- geographic coverage.

The project should avoid creating a black-box number without supporting context.

---

# 24. Open-Source Requirement

The project is intended to be publicly available.

The repository should eventually contain:

- source code;
- documentation;
- methodology;
- data-source documentation;
- reproducible examples;
- validation procedures;
- contribution instructions;
- known limitations.

Other developers should be able to reproduce or extend the project.

---

# 25. Technology Constraints

Technology decisions remain deliberately open.

One current preference is:

> Use Python and Python-compatible tools wherever they provide a reasonable solution.

Potential architecture, databases, frontend frameworks, APIs, hosting platforms and machine-learning frameworks should be selected only after the requirements and feasibility study are complete.

The specification should therefore remain **implementation-independent wherever possible**.

---

# 26. MVP / Prototype Scope

The first prototype should answer one narrow question:

> **Can we estimate the foliage colour distribution at Kelso Summit with sufficient accuracy to be useful?**

### Prototype location

**Kelso Summit / Milton, Ontario**

### Prototype capabilities

The prototype should:

1. Accept a date.
2. Define a geographic area representing Kelso Summit.
3. Retrieve or ingest relevant observations.
4. Estimate foliage colour distribution.
5. Report the evidence date and freshness.
6. Produce an uncertainty/confidence estimate.
7. Support historical dates where data are available.
8. Compare estimates against independent ground/reference observations.
9. Produce short-term forecasts once current/historical estimation is sufficiently validated.

The prototype does **not** initially need:

- automatic destination recommendations;
- province-wide coverage;
- user accounts;
- social functionality;
- sophisticated mobile UI;
- machine learning;
- production-scale infrastructure.

---

# 27. Initial Success Criteria

Before expanding the project, the prototype should demonstrate:

### SC-01 — Current-condition feasibility

The system can derive a meaningful foliage distribution for Kelso.

### SC-02 — Historical reproducibility

Historical foliage conditions can be reconstructed for multiple dates.

### SC-03 — Independent validation

Estimated foliage conditions show meaningful agreement with independent ground/reference observations.

### SC-04 — Temporal sensitivity

The system detects the seasonal transition from predominantly green foliage through autumn colours and eventually leaf loss.

### SC-05 — Short-term forecasting feasibility

Current observations combined with historical/environmental information provide useful information about conditions approximately 1–3 days ahead.

### SC-06 — Extended forecasting assessment

The project determines whether a 7-day forecast is sufficiently reliable for user-facing recommendations.

---

# 28. Non-Functional Requirements

### Cost

The core system should preferably operate using free/open data and services.

Paid services should not be fundamental requirements for reproducing the open-source project.

### Reproducibility

Another developer should be able to reproduce the analysis.

### Extensibility

A system developed for Kelso should eventually generalize to additional destinations without requiring a complete redesign.

### Interpretability

Outputs should remain understandable and traceable to supporting evidence.

### Privacy

Precise user location should only be used when necessary for trip planning and should not need to be permanently stored.

### Performance

Interactive components should eventually respond quickly enough for normal trip-planning use.

---

# 29. Key Open Questions

These questions should be answered during feasibility testing rather than assumed.

### Foliage measurement
- Can satellite observations distinguish yellow, orange and red reliably enough?
- What spatial resolution is necessary?
- How should mixed deciduous/evergreen forest be handled?
- What exactly constitutes the denominator when reporting "60% orange"?

### Temporal resolution
- How frequently can useful observations be obtained?
- What happens during several consecutive cloudy days?
- What should qualify as "real-time" or "near-real-time"?

### Forecasting
- Is 1–3 day forecasting meaningfully better than seasonal climatology?
- Is 7-day forecasting sufficiently reliable?
- Which environmental variables provide useful predictive information?

### Ground validation
- What historical ground-level data are available?
- Can Google reviews/photos be accessed legally and reproducibly?
- Can actual photograph capture dates be determined?
- Are webcams or crowdsourced submissions better reference sources?

### Geographic representation
- What geographic area should represent a park or trail?
- Should foliage be evaluated along trails, around viewpoints, across the entire park, or some combination?

### User experience
- Do users think in terms of percentages?
- Would a colour-range selector be intuitive?
- Should users choose "yellow or above," a continuous hue range, or named foliage stages?
- How should uncertainty be communicated without making the interface complicated?

---

# 30. Proposed Development Stages

### Phase 0 — Requirements

Define the problem, terminology, user expectations, outputs and success criteria.

**Current stage.**

### Phase 1 — Data Feasibility

Determine whether available historical and recent data can meaningfully represent foliage colour at Kelso.

### Phase 2 — Retrospective Prototype

Select several historical autumn dates and determine whether the system can reconstruct observed foliage progression.

### Phase 3 — Current Conditions

Generate a current foliage estimate for Kelso and compare it with contemporary ground observations.

### Phase 4 — Forecasting

Evaluate 1-, 3-, 5- and 7-day foliage forecasting.

### Phase 5 — User Prototype

Create a simple interface containing:

- location;
- date;
- colour selector;
- desired coverage;
- foliage estimate;
- confidence;
- map.

### Phase 6 — Destination Discovery

Expand from:

> "When should I visit Kelso?"

to:

> "Where should I go this weekend?"

### Phase 7 — Crowdsourcing

Allow users to contribute geolocated, timestamped foliage observations and photographs.

### Phase 8 — Regional Expansion

Expand beyond Kelso to Southern Ontario and eventually other regions.

---

# 31. Example Final User Experience

A user opens the application near Milton.

**Where are you starting?**
Milton, Ontario

**How far will you drive?**
≤ 60 minutes

**When?**
Saturday, October 10

**What colours do you want?**

Green ── Yellow ── **[ Yellow → Orange → Red ]** ── Brown

**Minimum preferred-colour coverage:**
60%

The system evaluates candidate destinations.

Example result:

### Kelso Summit

**Predicted foliage**

Green: 14%
Yellow: 32%
Orange: 31%
Red: 12%
Brown/Bare: 11%

**Your selected colours:** 75%

**Forecast confidence:** Moderate–High

**Latest supporting observation:** 2 days old

**Predicted viewing quality:** Matches user's specified foliage criteria.

The user can then compare Kelso against other destinations within the selected travel time.

---

# 32. Guiding Principle

The project should not attempt to tell users simply:

> **"Fall colours are at peak."**

It should answer the more useful and personalized question:

> **"What does the foliage likely look like at this place on the day I want to visit, how certain are we, and does it match the colours I want to see?"**
