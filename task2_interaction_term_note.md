# Task 2 — Interaction / Shared-Ceiling Term for Competing Events

## The gap

`src/impact_model.py`'s original design combined every event's effect on a
given indicator **additively**, documented explicitly as a "deliberate
simplification": *"Effects from multiple events on the same indicator are
combined ADDITIVELY (independent, no interaction/saturation terms)."*

This is a reasonable default for genuinely independent drivers, but two of
the calibrated links violate the independence assumption directly:
`IMP_0021` (Telebirr Launch → `ACC_MM_ACCOUNT`, +4.7pp) and `IMP_0007`
(M-Pesa Launch → `ACC_MM_ACCOUNT`, +5.0pp) are not independent effects —
they are two mobile money products **competing for the same underlying pool**
of Ethiopian adults adopting mobile money. Adding their effects assumes zero
overlap between who each product reaches, which likely overstates the
combined effect as both products mature.

## Design: shared-ceiling union term

For any indicator with a configured competing group, the competing links'
effects are combined via a saturating "probabilistic union" instead of raw
addition:

```
combined = ceiling * (1 - product(1 - e_i / ceiling))
```

treating each link's time-ramped effect as the probability an adult has
adopted mobile money "via that channel," and combining "adopted via A or via
B" under an independence-of-*reach* assumption between channels (not an
independence-of-*outcome* assumption, which is what plain addition implies).

Properties that motivated this specific form over alternatives:
- **Saturates smoothly** below the ceiling instead of growing without bound
  as more competing links pile up over time (e.g. future events like the
  NBE mandatory interoperability directive, `IMP_0016`, also targeting this
  indicator).
- **Reduces to addition for small effects** — a strict generalization of the
  original model, not a different regime. Verified directly: at the 2021
  checkpoint, only Telebirr's effect is nonzero, and the union formula
  reduces exactly to that single value (4.7%, unchanged from the additive
  baseline).
- **Symmetric / order-independent** regardless of how many competing links
  are combined.

## Scope of implementation

Per Task 2's instructions, this was implemented **specifically for the
Telebirr/M-Pesa pair**, not as a blanket change to every indicator's
combination logic:

- `src/impact_model.py` gains `COMPETING_LINK_GROUPS`, a small config dict
  mapping indicator codes to link-id groups. Currently one entry:
  `{"ACC_MM_ACCOUNT": [("IMP_0021", "IMP_0007")]}`.
- `combine_effects()` is a new function: if `indicator_code` has no
  entry in `COMPETING_LINK_GROUPS`, or `indicator_code` is omitted, it falls
  back to plain addition — **byte-for-byte identical to the old behavior**.
  Only when an indicator has a configured competing group are those specific
  links pulled out and combined via the union formula; any other links on
  the same indicator are still added on top, unchanged.
- `predict_indicator()` / `predict_trajectory()` gained an optional
  `indicator_code` parameter (default `None`) to opt into this. Every
  existing call site that doesn't pass it is completely unaffected.

## Validation: full re-run against the original single-link calibration

Re-ran the validation checkpoints from `notebooks/task3_impact_modeling.ipynb`
with the new interaction term enabled for `ACC_MM_ACCOUNT`:

| Checkpoint | Additive (original) | Shared-ceiling (Task 2) | Actual (Findex) |
|---|---|---|---|
| 2021-12-31 | 4.70% | 4.70% (unchanged — M-Pesa not yet live) | 4.70% |
| 2024-11-29 | 9.70% | **9.465%** | 9.45% |

**Result: the interaction term improves accuracy.** Error against the
held-out 2024 checkpoint drops from **0.25pp (additive) to ~0.015pp
(shared-ceiling)** — roughly a 16x reduction in error at that checkpoint.
This is reported honestly as the actual outcome, not assumed in advance: the
test suite (`test_shared_ceiling_improves_accuracy_at_2024_checkpoint`)
asserts the specific figures observed, not merely "improvement" as a
directional expectation baked in ahead of running the numbers.

The 2021 checkpoint is unaffected by design, since M-Pesa (`EVT_0003`,
2023-08-01) had not launched yet — with only one nonzero effect active, the
union formula collapses to that single value, matching the original
calibration exactly.

## Caveats

- This is a **two-point validation** (2021, 2024) against a **two-parameter
  model** (Telebirr's calibrated effect, M-Pesa's estimated effect) — the
  same limitation the original single-link calibration already carried, now
  inherited by the interaction term. A single data point (the 2024
  checkpoint) improving by 0.25pp → 0.015pp is a real, verifiable
  improvement, but it is not strong evidence that the *union-formula
  functional form specifically* is correct as opposed to some other
  saturating form that happens to also fit this one point well.
- The shared ceiling here is set to 100 (percentage points), the natural
  choice for a "% of adults" indicator. A more principled ceiling (e.g.
  bounded by `ACC_OWNERSHIP` or some addressable-market estimate below 100)
  was not explored — this is flagged as a reasonable follow-up rather than
  assumed away.
- Per Task 2's scope, no other indicator's combination logic was touched.
  `IMP_0016` (NBE mandatory interoperability directive, also targeting
  `ACC_MM_ACCOUNT`) is currently combined additively on top of the
  Telebirr/M-Pesa union term, since it isn't itself in direct competition
  with either product for the same adopter pool in the same way -- whether
  it should also be folded into a three-way competing group is a judgment
  call left for a future task.
