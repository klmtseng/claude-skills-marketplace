#!/usr/bin/env python3
"""ILLUSTRATIVE Stage-1 scaffolding for software engineering audits — NOT a turnkey detector.

⚠️ These checks are heuristic and project-dependent. A clean Stage-1 run is near-zero evidence
on its own — its job is to *prompt the right questions on your actual project*.
The real assurance comes from Stage 2 (an independent reviewer) + the reproduction gate.
Adapt these checks to your codebase; don't trust them blind.

Each function returns a dict; verdicts are heuristic — read the NOTE fields.
"""
import re
import pathlib
import numpy as np


# ---------- A. Coverage inflation ----------
def check_coverage_scope(coveragerc_path=".coveragerc"):
    """Scan .coveragerc / pyproject.toml for accidental inclusion of test code in coverage report."""
    issues = []
    p = pathlib.Path(coveragerc_path)
    if p.exists():
        text = p.read_text(errors="ignore")
        if "omit" not in text and "source" not in text:
            issues.append("No [omit] or [source] in .coveragerc — test files may inflate coverage")
        if "tests" not in text and "test_" not in text:
            issues.append("Test directory not explicitly omitted — verify tests/ is excluded from source")
    else:
        issues.append(f"{coveragerc_path} not found — coverage scope unknown")
    return {"issues": issues,
            "NOTE": "ACTION: confirm `coverage run --source=src/` excludes test files. "
                    "Coverage of test code inflates the headline number."}


def check_traintest_split_order(src_dir="."):
    """Grep for scaler/encoder .fit() calls that may precede train/test split."""
    fit_before_split = []
    split_patterns = [r"train_test_split", r"TimeSeriesSplit", r"KFold", r"StratifiedKFold"]
    fit_patterns = [r"\.fit\(X[,\s]", r"\.fit_transform\(X[,\s]", r"StandardScaler\(\)\.fit\(",
                    r"LabelEncoder\(\)\.fit\(", r"PCA\(\)\.fit\("]
    for p in pathlib.Path(src_dir).rglob("*.py"):
        if ".venv" in str(p) or "site-packages" in str(p) or "test_" in p.name:
            continue
        text = p.read_text(errors="ignore")
        lines = text.splitlines()
        split_line = next((i for i, l in enumerate(lines)
                           if any(re.search(pt, l) for pt in split_patterns)), None)
        for i, line in enumerate(lines):
            if any(re.search(pt, line) for pt in fit_patterns):
                if split_line is not None and i < split_line:
                    fit_before_split.append(f"{p.name}:{i+1} — fit() before split at line {split_line+1}")
    return {"potential_leakage": fit_before_split,
            "NOTE": "Each hit requires manual inspection — the scaler may legitimately fit on train "
                    "only even if the line appears before the split call (e.g. inside a function)."}


# ---------- B. Benchmark selection bias ----------
def check_metric_selection_bias(results_dict, n_tried=None):
    """Estimate how much the reported metric benefits from selection across tried configs.

    Pass results_dict = {config_name: score} for all configs tried.
    n_tried defaults to len(results_dict).
    """
    scores = np.array(list(results_dict.values()), dtype=float)
    n = len(scores)
    if n < 2:
        return {"n": n, "NOTE": "need >=2 configs to assess selection bias"}
    n_tried = n_tried or n
    best = float(scores.max())
    mean = float(scores.mean())
    gap = best - mean
    # Approximate expected max under Gaussian null
    from scipy.special import ndtri  # may not be available
    expected_max_z = ndtri(1 - 1 / n_tried) if n_tried > 1 else 0.0
    return {
        "n_configs": n, "best": best, "mean": mean, "best_minus_mean": gap,
        "n_tried": n_tried,
        "verdict": (
            f"RED_FLAG: best score is {gap:.3f} above mean across {n_tried} trials — "
            "report with Bonferroni/BH correction or caveat selection bias"
            if gap > 0.05 else "OK-ish: small gap between best and mean"
        ),
        "NOTE": "This is a rough heuristic. Even a small gap can be significant if n_tried is large."
    }


# ---------- C. Arithmetic / metric formula bugs ----------
def check_mean_of_means(subset_scores, subset_sizes):
    """Detect micro vs macro averaging mismatch.

    Compares unweighted mean (macro) vs size-weighted mean (micro) of per-subset scores.
    A large gap means the two averages tell different stories.
    """
    scores = np.array(subset_scores, float)
    sizes = np.array(subset_sizes, float)
    macro = float(scores.mean())
    micro = float(np.average(scores, weights=sizes))
    gap = abs(macro - micro)
    return {
        "macro_avg": macro, "micro_avg": micro, "gap": gap,
        "verdict": (
            "RED_FLAG: macro vs micro differ by >5pp — specify which you mean and why"
            if gap > 0.05 else "OK: macro and micro averages are close"
        ),
        "NOTE": "ACTION: confirm your headline uses the right average. "
                "Unweighted macro inflates small-subset performance."}


def check_threshold_on_test(src_dir="."):
    """Grep for threshold/cutoff tuning that may use the test set."""
    suspects = []
    threshold_patterns = [r"threshold\s*=.*argmax", r"best_thresh", r"\.predict_proba.*test",
                          r"roc_curve.*y_test", r"precision_recall_curve.*y_test"]
    for p in pathlib.Path(src_dir).rglob("*.py"):
        if ".venv" in str(p) or "site-packages" in str(p):
            continue
        text = p.read_text(errors="ignore")
        for pat in threshold_patterns:
            if re.search(pat, text):
                suspects.append(f"{p.name}: {pat}")
    return {"suspects": sorted(set(suspects)),
            "NOTE": "Threshold tuning on test data inflates precision/recall/F1. "
                    "Tune on val; report fixed threshold on test."}


# ---------- D. Statistical validity ----------
def check_ci(values, baseline=None):
    """Small-n CI: t not z, ddof=1. Optionally test overlap with a baseline."""
    from scipy import stats
    v = np.asarray(values, float)
    n = len(v)
    if n < 2:
        return {"n": n, "NOTE": "need >=2 values"}
    ci = stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)
    out = {"n": n, "mean": float(v.mean()), "ci95_t": float(ci),
           "ci95_z_naive": float(1.96 * v.std(ddof=0) / np.sqrt(n)),
           "CAVEAT": "If these runs share binary/cache state (e.g. same compiled model, same warm JIT), "
                     "this CI is pseudo-replication — re-run from cold start with different seeds."}
    if baseline is not None:
        out["beats_baseline"] = bool(v.mean() - ci > baseline)
        out["verdict"] = ("clears baseline (CI lower bound > baseline)" if out["beats_baseline"]
                          else "RED_FLAG: CI overlaps baseline -> not a robust improvement -> default to retract")
    return out


# ---------- E. Reproducibility / environment ----------
def check_lockfile_present(project_root="."):
    """Check that a lockfile or pinned requirements file exists."""
    root = pathlib.Path(project_root)
    candidates = ["requirements.txt", "poetry.lock", "Pipfile.lock", "pdm.lock",
                  "uv.lock", "pyproject.toml"]
    found = [c for c in candidates if (root / c).exists()]
    pinned = any(f in found for f in ["poetry.lock", "Pipfile.lock", "pdm.lock", "uv.lock"])
    return {
        "found": found, "has_lockfile": pinned,
        "verdict": ("OK: lockfile present — build is reproducible" if pinned
                    else "RED_FLAG: no lockfile — benchmark results may not reproduce on a different machine"),
        "NOTE": "requirements.txt without pinned versions is not a lockfile. "
                "Use `pip freeze > requirements.txt` or a proper lockfile tool."}


if __name__ == "__main__":
    print(check_coverage_scope())
    print(check_traintest_split_order("."))
    print(check_mean_of_means([0.8, 0.9, 0.7], [1000, 10, 500]))
    print(check_ci([0.82, 0.85, 0.79, 0.88, 0.81], baseline=0.80))
    print(check_lockfile_present("."))
    print("Stage-1 is scaffolding (weak evidence). The assurance is Stage 2 + reproduction.")
