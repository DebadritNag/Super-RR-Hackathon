# Pressure format-weight sensitivity (Phase 3, Stage 6, EXPLORATORY)

Status `EXPLORATORY_NOT_VALIDATED`, official_ranking `False`, not_for_publication `True`. Source numbers: `pressure_format_weight_sensitivity.json`.

## 1. Status: exploratory proxy versus validated

- **Validated numbers in this report: none.** Format scores are the shrunk actual-minus-expected proxy on pressure deliveries (`PROXY_ACTUAL_MINUS_EXPECTED_NOT_A_PRESSURE_SCORE`), not validated pressure scores.
- 70:30 is a PROVISIONAL default, not a validated optimum. The eight configurations measure how much results move when the weighting changes.
- No official Top 10 is published. Rankings in the JSON are technical (player ids, trimmed, no names). Nothing is imputed: a missing format score stays missing.

## 2. Inputs

Provisional pressure definition `chase|q0.9` and thresholds from the Stage 5 experiment (pressure_threshold_experiment.json provisional_recommendation). Format-weight config version `format_weights_v1`, config hash `a77cb111d1efe20e2637fed21f528bb5ee2d4e627e0963338b73d64ef1ec7417`; every ranked row in the JSON carries `config_id` and `config_hash`.

| Format | Role | Primary min balls | Stricter (robustness) | Looser (robustness) |
|---|---|---|---|---|
| IPL | batter | 24 | 30 | 18 |
| IPL | bowler | 32 | 36 | 24 |
| T20I | batter | 24 | 24 | 18 |
| T20I | bowler | 36 | 36 | 24 |

| Config | IPL weight | T20I weight | Default |
|---|---|---|---|
| w100_0 | 1.00 | 0.00 | no |
| w85_15 | 0.85 | 0.15 | no |
| w80_20 | 0.80 | 0.20 | no |
| w70_30 | 0.70 | 0.30 | yes |
| w60_40 | 0.60 | 0.40 | no |
| w55_45 | 0.55 | 0.45 | no |
| w50_50 | 0.50 | 0.50 | no |
| w0_100 | 0.00 | 1.00 | no |

## 3. Eligible populations and population changes

### batter

| Eligibility | IPL eligible | T20I eligible | Both formats (combined) |
|---|---|---|---|
| pressure primary | 56 | 61 | 8 |
| STRICTER_highest_sufficient_pool | 37 | 61 | 6 |
| LOOSER_previous_rung | 71 | 84 | 12 |
| Phase 2.5 all-situation (P25) | 257 | 506 | 133 |

Players by combined status at the primary threshold: both formats 8, IPL only 48, T20I only 53, neither 345.

**Fewer than ten players (8) are eligible in both formats; the combined list is short and is not padded.**

### bowler

| Eligibility | IPL eligible | T20I eligible | Both formats (combined) |
|---|---|---|---|
| pressure primary | 43 | 32 | 6 |
| STRICTER_highest_sufficient_pool | 34 | 32 | 4 |
| LOOSER_previous_rung | 65 | 56 | 10 |
| Phase 2.5 all-situation (P25) | 202 | 374 | 114 |

Players by combined status at the primary threshold: both formats 6, IPL only 37, T20I only 26, neither 292.

**Fewer than ten players (6) are eligible in both formats; the combined list is short and is not padded.**

## 4. IPL-only and T20I-only results

Format-specific lists are independent of the weights. Only counts are shown; trimmed technical ids are in the JSON (`format_rankings`).

| Role | IPL-only eligible and ranked | T20I-only eligible and ranked |
|---|---|---|
| batter | 56 | 61 |
| bowler | 43 | 32 |

## 5. Combined results by weight configuration

### batter (combined population 8)

| Config | IPL w | T20I w | Ranked | Top 10 overlap vs 70:30 | Spearman vs 70:30 | Mean abs rank change | Max abs rank change | Entering Top 10 | Leaving Top 10 |
|---|---|---|---|---|---|---|---|---|---|
| w100_0 | 1.00 | 0.00 | 8 | 8 | 0.95 | 0.50 | 1 | 0 | 0 |
| w85_15 | 0.85 | 0.15 | 8 | 8 | 0.95 | 0.50 | 1 | 0 | 0 |
| w80_20 | 0.80 | 0.20 | 8 | 8 | 0.95 | 0.50 | 1 | 0 | 0 |
| w70_30 | 0.70 | 0.30 | 8 | 8 | 1.00 | 0.00 | 0 | 0 | 0 |
| w60_40 | 0.60 | 0.40 | 8 | 8 | 0.98 | 0.25 | 1 | 0 | 0 |
| w55_45 | 0.55 | 0.45 | 8 | 8 | 0.90 | 0.75 | 2 | 0 | 0 |
| w50_50 | 0.50 | 0.50 | 8 | 8 | 0.88 | 0.75 | 2 | 0 | 0 |
| w0_100 | 0.00 | 1.00 | 8 | 8 | 0.12 | 2.25 | 6 | 0 | 0 |

Eligible population is identical across the eight configurations (yes), including 100:0 and 0:100, which rank the same combined population by one format's z-score.

Pairwise Top 10 overlap:

| config | w100_0 | w85_15 | w80_20 | w70_30 | w60_40 | w55_45 | w50_50 | w0_100 |
|---|---|---|---|---|---|---|---|---|
| w100_0 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |
| w85_15 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |
| w80_20 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |
| w70_30 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |
| w60_40 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |
| w55_45 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |
| w50_50 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |
| w0_100 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |

Pairwise Spearman rank correlation:

| config | w100_0 | w85_15 | w80_20 | w70_30 | w60_40 | w55_45 | w50_50 | w0_100 |
|---|---|---|---|---|---|---|---|---|
| w100_0 | 1.00 | 1.00 | 1.00 | 0.95 | 0.93 | 0.83 | 0.81 | -0.07 |
| w85_15 | 1.00 | 1.00 | 1.00 | 0.95 | 0.93 | 0.83 | 0.81 | -0.07 |
| w80_20 | 1.00 | 1.00 | 1.00 | 0.95 | 0.93 | 0.83 | 0.81 | -0.07 |
| w70_30 | 0.95 | 0.95 | 0.95 | 1.00 | 0.98 | 0.90 | 0.88 | 0.12 |
| w60_40 | 0.93 | 0.93 | 0.93 | 0.98 | 1.00 | 0.95 | 0.90 | 0.14 |
| w55_45 | 0.83 | 0.83 | 0.83 | 0.90 | 0.95 | 1.00 | 0.98 | 0.38 |
| w50_50 | 0.81 | 0.81 | 0.81 | 0.88 | 0.90 | 0.98 | 1.00 | 0.45 |
| w0_100 | -0.07 | -0.07 | -0.07 | 0.12 | 0.14 | 0.38 | 0.45 | 1.00 |

### bowler (combined population 6)

| Config | IPL w | T20I w | Ranked | Top 10 overlap vs 70:30 | Spearman vs 70:30 | Mean abs rank change | Max abs rank change | Entering Top 10 | Leaving Top 10 |
|---|---|---|---|---|---|---|---|---|---|
| w100_0 | 1.00 | 0.00 | 6 | 6 | 0.71 | 1.00 | 2 | 0 | 0 |
| w85_15 | 0.85 | 0.15 | 6 | 6 | 0.94 | 0.33 | 1 | 0 | 0 |
| w80_20 | 0.80 | 0.20 | 6 | 6 | 1.00 | 0.00 | 0 | 0 | 0 |
| w70_30 | 0.70 | 0.30 | 6 | 6 | 1.00 | 0.00 | 0 | 0 | 0 |
| w60_40 | 0.60 | 0.40 | 6 | 6 | 0.94 | 0.33 | 1 | 0 | 0 |
| w55_45 | 0.55 | 0.45 | 6 | 6 | 0.89 | 0.67 | 1 | 0 | 0 |
| w50_50 | 0.50 | 0.50 | 6 | 6 | 0.89 | 0.67 | 1 | 0 | 0 |
| w0_100 | 0.00 | 1.00 | 6 | 6 | 0.60 | 1.33 | 2 | 0 | 0 |

Eligible population is identical across the eight configurations (yes), including 100:0 and 0:100, which rank the same combined population by one format's z-score.

Pairwise Top 10 overlap:

| config | w100_0 | w85_15 | w80_20 | w70_30 | w60_40 | w55_45 | w50_50 | w0_100 |
|---|---|---|---|---|---|---|---|---|
| w100_0 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| w85_15 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| w80_20 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| w70_30 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| w60_40 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| w55_45 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| w50_50 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| w0_100 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |

Pairwise Spearman rank correlation:

| config | w100_0 | w85_15 | w80_20 | w70_30 | w60_40 | w55_45 | w50_50 | w0_100 |
|---|---|---|---|---|---|---|---|---|
| w100_0 | 1.00 | 0.83 | 0.71 | 0.71 | 0.54 | 0.37 | 0.37 | 0.09 |
| w85_15 | 0.83 | 1.00 | 0.94 | 0.94 | 0.83 | 0.71 | 0.71 | 0.37 |
| w80_20 | 0.71 | 0.94 | 1.00 | 1.00 | 0.94 | 0.89 | 0.89 | 0.60 |
| w70_30 | 0.71 | 0.94 | 1.00 | 1.00 | 0.94 | 0.89 | 0.89 | 0.60 |
| w60_40 | 0.54 | 0.83 | 0.94 | 0.94 | 1.00 | 0.94 | 0.94 | 0.77 |
| w55_45 | 0.37 | 0.71 | 0.89 | 0.89 | 0.94 | 1.00 | 1.00 | 0.89 |
| w50_50 | 0.37 | 0.71 | 0.89 | 0.89 | 0.94 | 1.00 | 1.00 | 0.89 |
| w0_100 | 0.09 | 0.37 | 0.60 | 0.60 | 0.77 | 0.89 | 0.89 | 1.00 |

## 6. Single-format adjusted estimates (separate section)

ADJUSTED_ESTIMATE renormalises the weights over the formats in which a player is eligible. It is not a combined score, is never part of the default ranking, and is not comparable between single-format and two-format players.

| Role | Players with an adjusted estimate | IPL only | T20I only | Both formats |
|---|---|---|---|---|
| batter | 109 | 48 | 53 | 8 |
| bowler | 69 | 37 | 26 | 6 |

## 7. Missing-format audit

| Role | Players not eligible in both formats | Combined scores present for them (must be 0) | Z-scores present for a non-eligible format (must be 0) |
|---|---|---|---|
| batter | 446 | 0 | 0 |
| bowler | 355 | 0 | 0 |


Robustness: the same eight configurations were rerun at the stricter and looser thresholds listed in section 2; see `robustness` in the JSON.


Official data preservation: unchanged = yes.

Reproduce: `python scripts/run_pressure_eligibility.py` then `python scripts/run_pressure_format_sensitivity.py`.
