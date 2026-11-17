# Phase 6 chunk 2 review: variance/floor and split-half

**Verdict**: APPROVED

Scope: brief decision 8 (variance identifiability, floor arithmetic, split-half reliability). Evidence read: `phase6_chunk2_verification.md`, `phase6_variance_floor_investigation.md`, `config/phase6_selection_criteria_v1.json`, grep of `app/phase6/*`. No suites re-run.

## Summary
Chunk 2 compares variance-component estimators on three noise bases, a model-free split-covariance estimator, a detectability simulation and a flag table fixed in the criteria file before results. The report states the result honestly: the data weakly identify between-player variance (5 of 48 contexts identified positive, 42 weak, 1 not estimable), and the sign flips with the noise basis (0/48 positive under Kish, 39/48 under independent balls). No gate, threshold or Phase 4/5 artifact changed. No TEST rows enter, and no definition was selected.

Watch for: the `H-C_SUPPORTED` and `MIXED` labels (36 of 48 contexts carry H-C) rest partly on E6 and the cluster basis. The report says so and does not present them as evidence of positive variance (confirmed).

## High-level view
Identifiability is treated as a finding, not hidden. Model-free E7 is called the only estimator that does not depend on a noise model, and the weaker E6 and cluster-basis evidence is flagged as upward-biased (E6 median above point estimate in 47/47). The open decision on the noise basis is recorded and nothing was changed.

The floor arithmetic matches `k_for`: the multiplier is applied after the floor, so tau4 gives k=25. This is verified in 14/14 branch rows and in a hand spot-check of the IPL batter context.

Split-half reliability is reported with Spearman-Brown, bootstrap intervals and reproduction of the 128 Phase 5 rows. The report discloses that match-bootstrap intervals are not centred. Reliability is low overall (median SB about 0.26 to 0.30), and the report does not oversell it.

<details>
<summary>Issues (3)</summary>

1. **E6 upward shift** (confirmed, disclosed) — keep the report caveat when later chunks cite H-C labels. Do not use H-C as positive-variance evidence in the summary.
2. **Un-centred match-bootstrap intervals** (confirmed, disclosed) — the split-half interval lower bound is conservative or inconsistent in 250/286 units. State this wherever the "lower bound above 0" counts are quoted downstream.
3. **H-A_SUPPORTED unreachable** (confirmed, disclosed) — the pre-declared H-A null can never fire because E6 positive-draw share is at least 0.9 in 47/47 contexts. Mention this in the final user summary.

None of these blocks approval. All are non-blocking carry-forward notes.
</details>

<details>
<summary>Details</summary>

### Statistical correctness
The verification reports independent reproduction of one split-half cell (r 0.243385, SB 0.391487, difference 1.4e-16) and one variance component (sigma2 3.122743, between -1.084302, k 25.0). The module also reproduces 48/48 `p5_context_fit` records and 128/128 Phase 5 split rows. Both scripts give byte-identical CSVs on a second run, so seeding is sound.

### Honesty about identifiability
The report separates "model-free" from "noise-model-dependent" evidence and says the H-C and MIXED labels do not show positive between-player variance. The recommendation direction (wider uncertainty, shorter lists, restricted contexts) is consistent with the brief.

### TEST and tuning
`assert_no_test_rows` guards the frames. The Phase 4 lock log hash is unchanged, Phase 5 shows 0 events, and an AST test excludes Cricsheet. The criteria file forbids player identity, rank, score level and Top-10 membership as inputs. A word-filter test in `criteria.py` enforces this. Chunk 2 selects no definition; the selection rule is for a later chunk.

### Reports derived from code
Verdict counts, flag tables and the estimator table are generated from the run. The report text says "the text is not hand-written".
</details>

## File map
<details><summary>Files</summary>

Reviewed: `data/reports/phase6_variance_floor_investigation.md`, `config/phase6_selection_criteria_v1.json`, `app/phase6/*`, `phase6_chunk2_verification.md`.
</details>
