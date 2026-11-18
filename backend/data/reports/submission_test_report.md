# Submission test report

Run stamp (UTC): 2026-11-18T05:45:11+00:00. Platform: Windows 10, Python 3.11.0. Commands were run from the stated directory; outputs below are the real outputs (the last lines, where long).

## Summary

| check | result | exit |
|---|---|---|
| pytest (backend, full suite) | 1442 passed, 4 warnings in 664.95s (0:11:04) | pass |
| ruff check | All checks passed! | 0 |
| ruff format --check | 429 files already formatted | 0 |
| npm run build (tsc -b && vite build) | - Adjust chunk size limit for this warning via build.chunkSizeWarningLimit. | 0 |
| npm run lint (oxlint) | src/context/AppContext.tsx:92:14: warning react(only-export-components): Fast refresh only works when a file only exports components. Use a new file to share constants or functions between components. | 0 |
| protected files (SHA-256 against recorded hashes) | checked 234, ok True | pass |

Tool versions: ruff 0.17.5; node v22.20.0; npm 11.8.0.

## pytest

Command: `python -m pytest -q` (cwd `d:/Data/backend`).

Parsed counts: passed 1442, failed 0, errors 0, skipped 0, warnings 4, duration 665 s.

```
........................................................................ [ 69%]
........................................................................ [ 74%]
........................................................................ [ 79%]
........................................................................ [ 84%]
........................................................................ [ 89%]
........................................................................ [ 94%]
........................................................................ [ 99%]
..                                                                       [100%]
============================== warnings summary ===============================
C:\Users\ASUS\AppData\Local\Programs\Python\Python311\Lib\site-packages\starlette\testclient.py:41
  C:\Users\ASUS\AppData\Local\Programs\Python\Python311\Lib\site-packages\starlette\testclient.py:41: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    [], typing.ContextManager[anyio.abc.BlockingPortal]
tests/test_phase4_par.py::test_lomo_is_labelled_descriptive_and_guard_rejects_it
  D:\Data\backend\app\analytics\pressure_features.py:293: RuntimeWarning: invalid value encountered in divide
    par.loc[rmask, "par_runs_lomo"] = (sums[np.clip(b, 0, 120)] - own_val) / (cnt - has)
tests/test_phase4_par.py::test_lomo_is_labelled_descriptive_and_guard_rejects_it
  D:\Data\backend\app\analytics\pressure_features.py:295: RuntimeWarning: invalid value encountered in divide
    par.loc[rmask, "par_total_lomo"] = (tot.sum() - own_t) / (cnt - has)
tests/test_phase8_ai_pipeline.py::test_artefact_predictions_come_from_the_stored_predictor_object
  C:\Users\ASUS\AppData\Local\Programs\Python\Python311\Lib\site-packages\joblib\externals\loky\backend\context.py:136: UserWarning: Could not find the number of physical cores for the following reason:
  [WinError 2] The system cannot find the file specified
  Returning the number of logical cores instead. You can silence this warning by setting LOKY_MAX_CPU_COUNT to the number of cores you want to use.
    warnings.warn(
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1442 passed, 4 warnings in 664.95s (0:11:04)
```

## ruff check

Command: `C:\Users\ASUS\AppData\Local\Programs\Python\Python311\python.exe -m ruff check .` (cwd `D:\Data\backend`), exit code 0.

```
All checks passed!
```

## ruff format --check

Command: `C:\Users\ASUS\AppData\Local\Programs\Python\Python311\python.exe -m ruff format --check .` (cwd `D:\Data\backend`), exit code 0.

```
429 files already formatted
```

## npm run build

Command: `npm.cmd run build` (cwd `D:\Data\frontend`), exit code 0.

```
> frontend@0.0.0 build
> tsc -b && vite build
vite v8.3.8 building client environment for production...
transforming...
✓ 2478 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.94 kB │ gzip:   0.52 kB
dist/assets/index-DGepR2Jh.css   19.39 kB │ gzip:   4.84 kB
dist/assets/index-PCDxXTGo.js   709.09 kB │ gzip: 207.28 kB
✓ built in 1.52s
[plugin builtin:vite-reporter]
(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
```

## npm run lint

Command: `npm.cmd run lint` (cwd `D:\Data\frontend`), exit code 0.

```
> frontend@0.0.0 lint
> oxlint
src/hooks/useApi.ts:11:3: warning react-hooks(exhaustive-deps): React Hook useEffect contains a call to setState. Without a list of dependencies, this can lead to an infinite chain of updates. help: Consider adding an empty list of dependencies to make it clear which values are intended to be stable.
src/components/layout/Sidebar.tsx:6:14: warning react(only-export-components): Fast refresh only works when a file only exports components. Use a new file to share constants or functions between components.
src/context/AppContext.tsx:92:14: warning react(only-export-components): Fast refresh only works when a file only exports components. Use a new file to share constants or functions between components.
```

## Protected files

A SHA-256 comparison over the recorded manifest `phase8_prehash.json`: {"checked": 234, "ok": true, "unexpected_changes": [], "documented_changes": [{"file": "d:/Data/backend/data/reports/phase7_model_registry.json", "state": "changed", "note": "intentional Phase 8 chunk 6 change: output keys renamed to the preserved *_phase7_aborted.csv names (content hashes of those files verified equal); see phase8_chunk6_verification.md"}]}. The source CSVs, `superr.duckdb`, `exploratory.duckdb` and the Phase 2 to 7 reports recorded there are byte-identical to their pre-Phase 8 hashes, except for the documented intentional change(s): `phase7_model_registry.json` (intentional Phase 8 chunk 6 change: output keys renamed to the preserved *_phase7_aborted.csv names (content hashes of those files verified equal); see phase8_chunk6_verification.md).
## What the tests cover

Calculations, win-probability attribution (striker, bowler, wicket, extras, run-out), eligibility, missing-data handling, ranking determinism and tie-breaks, leakage (truncation and mutation of future rows, chronological split integrity, model trained on TRAIN only), calibration function on synthetic data, criteria-hash predeclaration, TEST-lock preservation, no external ball-by-ball source in scoring modules, protected-file preservation, API schema and status labels on every submission endpoint, token protection of `/internal/*`, descriptive-only `/players`, a scan for hardcoded player names and random scores in backend production code and frontend source, and the earlier phases' suites unchanged.

## Not covered by automated tests

The frontend has no unit tests; it is checked by the type-check and build, the linter and the earlier Playwright pass (ten pages at 375, 768, 1024 and 1440 px, no horizontal scroll, no console errors). The unlocked state of the Experimental AI page, a keyboard-only walkthrough and automated contrast tooling were not run.
