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

Pure stdlib + numpy (scipy only if available; degrade gracefully). Run: python3 injected_bug_recall.py
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # import the Stage-1 template
import mechanical_audit_template as T


# ---- helpers: turn each detector's output into a boolean "flagged as problematic" ----

def flagged_traintest_split(bug):
    """Bug: fit() call appears before split in source. Clean: fit after split."""
    import tempfile, shutil
    d = tempfile.mkdtemp(prefix="split_case_")
    try:
        if bug:
            # fit before split -> leakage
            src = ("from sklearn.preprocessing import StandardScaler\n"
                   "from sklearn.model_selection import train_test_split\n"
                   "scaler = StandardScaler()\n"
                   "X_scaled = scaler.fit(X, y)\n"      # fit before split
                   "X_train, X_test = train_test_split(X_scaled)\n")
        else:
            src = ("from sklearn.model_selection import train_test_split\n"
                   "X_train, X_test, y_train, y_test = train_test_split(X, y)\n"
                   "scaler = StandardScaler()\n"
                   "scaler.fit(X_train, y_train)\n")    # fit after split
        open(os.path.join(d, "model.py"), "w").write(src)
        r = T.check_traintest_split_order(d)
        return len(r["potential_leakage"]) > 0
    finally:
        shutil.rmtree(d)


def flagged_threshold_on_test(bug):
    """Bug: threshold tuned on y_test. Clean: threshold tuned on y_val."""
    import tempfile, shutil
    d = tempfile.mkdtemp(prefix="thresh_case_")
    try:
        src = ("best_thresh = find_best_threshold(y_test, proba)\n" if bug
               else "best_thresh = find_best_threshold(y_val, proba)\n")
        open(os.path.join(d, "eval.py"), "w").write(src)
        r = T.check_threshold_on_test(d)
        return len(r["suspects"]) > 0
    finally:
        shutil.rmtree(d)


def flagged_mean_of_means(bug):
    """Bug: unweighted mean of unequal subsets reported as overall accuracy."""
    # Subsets: [0.9, 0.5] with sizes [1000, 10] — unweighted macro = 0.70, micro = 0.896
    scores = [0.9, 0.5]
    sizes = [1000, 10]
    r = T.check_mean_of_means(scores, sizes)
    if bug:
        # bug: headline uses macro (0.70) for a size-imbalanced dataset -> big gap flagged
        return "RED_FLAG" in r["verdict"]
    else:
        # clean: equal-sized subsets -> gap is small
        r2 = T.check_mean_of_means([0.9, 0.85], [500, 500])
        return "RED_FLAG" not in r2["verdict"]  # clean case should NOT flag


def flagged_ci(bug):
    """Bug: CI overlaps baseline (no real improvement). Clean: clearly beats baseline."""
    rng = np.random.default_rng(2)
    vals = rng.normal(0.05, 0.5, size=8) if bug else rng.normal(1.2, 0.2, size=8)
    try:
        r = T.check_ci(vals, baseline=0.0)
    except Exception:
        return None   # scipy missing
    return "RED_FLAG" in r.get("verdict", "")


def flagged_selection_bias(bug):
    """Bug: best of 20 configs reported without correction. Clean: only 2 configs tried."""
    rng = np.random.default_rng(3)
    if bug:
        # 20 configs, best is well above mean
        scores = {f"cfg_{i}": float(rng.normal(0.7, 0.05)) for i in range(19)}
        scores["cfg_best"] = 0.95   # cherry-picked outlier
    else:
        scores = {"cfg_a": 0.82, "cfg_b": 0.80}
    try:
        r = T.check_metric_selection_bias(scores, n_tried=len(scores))
    except Exception:
        return None   # scipy missing
    return "RED_FLAG" in r["verdict"]


# ---- the test suite: (id, category, detector) ----
MECHANICAL = [
    ("traintest_split_order", "fit() 在 split 之前(訓練集污染)", flagged_traintest_split),
    ("threshold_on_test", "閾值在 test 上調(指標灌水)", flagged_threshold_on_test),
    ("mean_of_means_imbalance", "不等大小子集用 macro avg(分母錯)", flagged_mean_of_means),
    ("ci_overlaps_baseline", "CI 與基準重疊(無真改進)", flagged_ci),
    ("selection_bias_best_of_20", "20 個配置挑最好回報(多重比較)", flagged_selection_bias),
]
# reasoning-level bugs with NO deterministic detector in the floor:
REASONING_ONLY = ["恆真句 PASS(建構必然)", "把相關當獨立(混淆變數)",
                  "接受虛無當證據", "捏造/不可查證引用", "統計量在不同子集(選擇偏差)"]


def run():
    print("=" * 78)
    print("META-EVAL:validity-audit 確定性地板的植入-bug 偵測 recall")
    print("=" * 78)
    tp = fn = fp = tn = skipped = 0
    print(f"\n{'案例':<36}{'植入bug→抓到?(recall)':<26}{'乾淨→誤報?':<14}")
    for cid, cat, fn_det in MECHANICAL:
        got_bug = fn_det(True)
        got_clean = fn_det(False)
        if got_bug is None or got_clean is None:
            skipped += 1
            print(f"{cat:<36}{'(略過:缺 scipy)':<26}")
            continue
        tp += int(got_bug); fn += int(not got_bug)
        fp += int(got_clean); tn += int(not got_clean)
        caught = "✅ 抓到" if got_bug else "❌ 漏掉"
        alarm = "⚠️ 誤報" if got_clean else "✅ 未誤報"
        print(f"{cat:<36}{caught:<26}{alarm:<14}")

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
