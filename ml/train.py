"""Train a small classifier on logged attempts. Labels: `true_label` (set by agents / ?label=) else the rule verdict.

    python ml/train.py            # then the running server picks up ml/model.joblib automatically
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import joblib  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import cross_val_score  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from app import config, db  # noqa: E402
from app.classifier import vector, MODEL_FEATURES  # noqa: E402


def main():
    X, y = [], []
    for r in db.training_rows():
        label = r["true_label"] or (r["label"] if r["label"] != "UNCERTAIN" else None)
        if not label:
            continue
        X.append(vector(json.loads(r["features"]), r["correct"], r["elapsed"], r["trap"]))
        y.append(label)
    counts = Counter(y)
    print(f"{len(y)} labelled attempts: {dict(counts)}")
    if len(counts) < 2 or len(y) < 8:
        print("Need at least 8 attempts across 2+ classes. Play some more!")
        return
    folds = max(2, min(5, min(counts.values())))
    best = None
    for name, m in [("RandomForest", RandomForestClassifier(n_estimators=200, max_depth=6, random_state=0)),
                    ("LogReg", make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)))]:
        acc = cross_val_score(m, X, y, cv=folds).mean()
        print(f"  {name:12s} {folds}-fold CV accuracy {acc:.2f}")
        if best is None or acc > best[2]:
            best = (name, m, acc)
    name, model, acc = best
    model.fit(X, y)
    joblib.dump({"model": model, "name": name, "features": MODEL_FEATURES}, config.MODEL_PATH)

    if name == "RandomForest":
        imp = model.feature_importances_
    else:
        coef = model[-1].coef_
        imp = abs(coef).mean(axis=0)
        imp = imp / imp.sum()
    ranked = sorted(zip(MODEL_FEATURES, map(float, imp)), key=lambda t: -t[1])
    with open(config.IMPORTANCES_PATH, "w") as fh:
        json.dump({"model": name, "accuracy": acc, "n": len(y), "classes": dict(counts), "features": ranked}, fh, indent=2)
    print(f"Saved {name} -> {config.MODEL_PATH}")
    for f, w in ranked[:10]:
        print(f"  {f:22s} {w:.3f} " + "#" * int(w * 60))


if __name__ == "__main__":
    main()
