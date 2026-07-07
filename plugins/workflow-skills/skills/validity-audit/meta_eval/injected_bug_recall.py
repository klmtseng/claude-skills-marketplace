#!/usr/bin/env python3
"""Meta-eval: quantify the DETERMINISTIC FLOOR's bug-detection recall (a proper eval of the evaluator).

We plant KNOWN bugs (from the ledger + Stage-1 template) into small fixtures, run the deterministic
detectors, and measure recall + false-alarm. Two honest properties this is built to surface:

  1. The floor catches mechanical/arithmetic bugs but is STRUCTURALLY BLIND to reasoning-level bugs
     (tautology, correlation-as-independence, accepting-the-null, fabricated citation). Those have no
     deterministic detector -> recall 0 -> which is exactly why the real ledger shows the independent
     reviewer catching ~7/9 misses. The floor is a lower bound; Stage 2 is not optional.
  2. Even the mechanical recall here is an UPPER bound: the planted bugs are blatant by construction
     ("easy mode"). Subtle real-world instances are harder and unmeasured. Don't read 100% as "solved".

Pure stdlib + numpy (scipy/pandas only if available; degrade gracefully). Run: python3 injected_bug_recall.py
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # import the Stage-1 template
import leak_audit_template as T


# ---- helpers: turn each detector's output into a boolean "flagged as problematic" ----
def flagged_oos(bug):
    r = T.check_oos_segmentation(("2015-01", "2026-03"),
                                 ("2015-01", "2021-12") if bug else ("2010-01", "2013-12"))
    return "RED_FLAG" in r["verdict"]

def flagged_survivorship(bug):
    last = ["2026-06-01"] * 50 if bug else (["2026-06-01"] * 40 + ["2017-03-01", "2019-08-01",
            "2020-01-01", "2021-06-01", "2022-11-01", "2018-02-01", "2023-04-01", "2016-07-01",
            "2024-01-01", "2015-05-01"])
    try:
        r = T.check_survivorship(last)
    except Exception as e:
        return None  # pandas missing
    return "RED_FLAG" in r["verdict"]

def flagged_label_shuffle(bug):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(300, 3))
    signal = X[:, 0] + 0.3 * rng.normal(size=300)
    y = rng.permutation(signal) if bug else signal          # bug: labels are noise, claimed as signal
    def fit_predict(Xtr, ytr):                              # score = |corr(feature0, y)|
        return abs(np.corrcoef(Xtr[:, 0], ytr)[0, 1])
    r = T.check_label_shuffle(X, y, fit_predict, n=500, alpha=0.01, seed=1)
    return "RED_FLAG" in r["verdict"]

def flagged_ci(bug):
    # claim: strategy mean beats baseline 0.0. bug: noisy values whose CI overlaps 0.
    rng = np.random.default_rng(2)
    vals = rng.normal(0.05, 0.5, size=8) if bug else rng.normal(1.2, 0.2, size=8)
    r = T.check_ci(vals, baseline=0.0)
    return "RED_FLAG" in r.get("verdict", "")

def flagged_mdd(bug):
    # up-trending curve: the global-peak bug overstates. "reported" = buggy if bug else correct.
    eq = [1.0, 1.4, 1.1, 1.7, 1.5, 2.0, 1.8]
    r = T.check_mdd_formula(eq)
    reported = r["bug_pointwise_over_global"] if bug else r["mdd_correct"]
    return abs(reported - r["mdd_correct"]) > 1e-6         # flagged iff reported != correct running-peak

def flagged_lookahead(bug):
    # isolate the fixture in its own dir — else the grep scans this harness's own source
    # (which literally contains "shift(-1)") and false-alarms. (meta-eval self-bug, fixed.)
    import tempfile, shutil
    d = tempfile.mkdtemp(prefix="la_case_")
    try:
        open(os.path.join(d, "case.py"), "w").write(
            "z = df['x'].shift(-1)\n" if bug else "z = df['x'].rolling(20).mean()\n")
        r = T.check_lookahead_grep(d)
        return len(r["DEFINITE_LEAK"]) > 0
    finally:
        shutil.rmtree(d)


# ---- the test suite: (id, category, detector, has_deterministic_detector) ----
MECHANICAL = [
    ("oos_in_sample_blend", "in-sample 混入", flagged_oos),
    ("survivorship", "倖存者偏誤", flagged_survivorship),
    ("label_shuffle_noise", "訊號=雜訊(label-shuffle)", flagged_label_shuffle),
    ("ci_overlaps_baseline", "CI 與基準重疊", flagged_ci),
    ("mdd_global_peak", "MDD 除全域高點", flagged_mdd),
    ("lookahead_shift", "未來洩漏(shift(-1))", flagged_lookahead),
]
# reasoning-level bugs from the ledger with NO deterministic detector in the floor:
REASONING_ONLY = ["恆真句 PASS(建構必然)", "把相關當獨立(混淆變數)",
                  "接受虛無當證據", "捏造/不可查證引用", "統計量在不同子集(選擇偏差)"]


def run():
    print("=" * 78)
    print("META-EVAL:validity-audit 確定性地板的植入-bug 偵測 recall")
    print("=" * 78)
    tp = fn = fp = tn = skipped = 0
    print(f"\n{'案例':<28}{'植入bug→抓到?(recall)':<26}{'乾淨→誤報?':<14}")
    for cid, cat, fn_det in MECHANICAL:
        got_bug = fn_det(True)
        got_clean = fn_det(False)
        if got_bug is None or got_clean is None:
            skipped += 1
            print(f"{cat:<28}{'(略過:缺 pandas/scipy)':<26}")
            continue
        tp += int(got_bug); fn += int(not got_bug)
        fp += int(got_clean); tn += int(not got_clean)
        print(f"{cat:<28}{('✅ 抓到' if got_bug else '❌ 漏掉'):<26}{('⚠️ 誤報' if got_clean else '✅ 未誤報'):<14}")

    n_mech = tp + fn
    recall = tp / n_mech if n_mech else float("nan")
    far = fp / (fp + tn) if (fp + tn) else float("nan")
    print("-" * 78)
    print(f"機械層 recall = {tp}/{n_mech} = {recall:.0%}   |   誤報率 = {fp}/{fp+tn} = {far:.0%}"
          + (f"   (略過 {skipped})" if skipped else ""))

    print("\n推理層 bug(地板無確定性偵測器 → 結構性漏掉,recall=0):")
    for r in REASONING_ONLY:
        print(f"  ❌ {r}  — 需 Stage 2 獨立 reviewer")
    print(f"推理層 recall = 0/{len(REASONING_ONLY)} = 0%")

    total_bugs = n_mech + len(REASONING_ONLY)
    floor_caught = tp
    print("=" * 78)
    print(f"全體:地板抓到 {floor_caught}/{total_bugs} = {floor_caught/total_bugs:.0%}(其餘要 Stage 2)")
    print("誠實界線:")
    print("  · 機械層案例是『明顯 bug』(easy mode)→ 這個 recall 是【上界】,真實細微 bug 更低、且未測。")
    print("  · 推理層 0% 正是真實 ledger『獨立 reviewer 抓 7、自審抓 2』的機械對應——地板是下界,Stage 2 扛主活。")
    print("  · false-negative 的真分母仍未知(只數造得出來的 bug);這是 recall 的下界性質,不是完整偵測率。")
    print("=" * 78)
    return dict(mech_recall=recall, far=far, floor_overall=floor_caught / total_bugs)


if __name__ == "__main__":
    run()
