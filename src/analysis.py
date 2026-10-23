from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


def load_all(data_dir: str | Path = "data") -> pd.DataFrame:
    files = sorted(Path(data_dir).glob("*/trials.csv"))
    frames = []
    for f in files:
        # Skip development/test sessions so a smoke test does not pollute the
        # analysis of real participants.
        if f.parent.name.startswith(("SMOKE_", "FLOW_")):
            continue
        df = pd.read_csv(f)
        if len(df) == 0:
            continue
        df["session"] = f.parent.name
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"No non-empty trials.csv under {data_dir}")
    return pd.concat(frames, ignore_index=True)


def compute_trial_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Discard the first 2 s of each trial (adaptation to the controls/mask).
    df = df[df["t"] >= 2.0]

    rows = []
    for (session, condition, trial), g in df.groupby(["session", "condition", "trial"]):
        g = g.sort_values("t")
        duration = float(g["t"].max() - g["t"].min())
        rms_x = float(np.sqrt(np.mean(g["x"].to_numpy() ** 2)))
        off_road = float(g["off_road"].mean())

        steer = g["steer"].to_numpy()
        signed = np.sign(steer)
        signed[np.abs(steer) < 0.01] = 0
        nz = signed[signed != 0]
        reversals = int(np.sum(nz[1:] * nz[:-1] < 0)) if len(nz) > 1 else 0
        reversal_rate = reversals / max(duration, 1e-6)

        rows.append({
            "session": session,
            "condition": condition,
            "trial": trial,
            "rms_x": rms_x,
            "off_road": off_road,
            "reversal_rate": reversal_rate,
            "duration": duration,
        })
    cols = ["session", "condition", "trial", "rms_x", "off_road", "reversal_rate", "duration"]
    return pd.DataFrame(rows, columns=cols)


def summarize(trial_metrics: pd.DataFrame) -> pd.DataFrame:
    if trial_metrics.empty:
        return pd.DataFrame(columns=["session", "condition", "rms_x", "off_road", "reversal_rate", "n_trials"])
    return (
        trial_metrics.groupby(["session", "condition"])
        .agg(
            rms_x=("rms_x", "mean"),
            off_road=("off_road", "mean"),
            reversal_rate=("reversal_rate", "mean"),
            n_trials=("trial", "nunique"),
        )
        .reset_index()
    )


def paired_tests(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric in ["rms_x", "off_road", "reversal_rate"]:
        pivot = summary.pivot(index="session", columns="condition", values=metric)
        if "tangent" not in pivot or "control" not in pivot:
            continue
        a = pivot["tangent"].dropna()
        b = pivot["control"].dropna()
        common = a.index.intersection(b.index)
        if len(common) < 2:
            continue
        t, p = stats.ttest_rel(a.loc[common], b.loc[common])
        rows.append({
            "metric": metric,
            "n": len(common),
            "mean_tangent_minus_control": float((a.loc[common] - b.loc[common]).mean()),
            "t": float(t),
            "p": float(p),
        })
    return pd.DataFrame(rows)


def plot_summary(summary: pd.DataFrame, out_dir: str | Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics = [
        ("rms_x", "RMS lateral error (m)"),
        ("off_road", "Off-road proportion"),
        ("reversal_rate", "Steering reversals / s"),
    ]
    order = [c for c in ["full", "tangent", "control"] if c in set(summary["condition"])]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, (metric, label) in zip(axes, metrics):
        data = [summary.loc[summary["condition"] == c, metric].dropna().to_numpy() for c in order]
        ax.boxplot(data, showmeans=True)
        for i, vals in enumerate(data, start=1):
            ax.scatter(np.full(len(vals), i), vals, alpha=0.65, s=18)
        ax.set_xticks(range(1, len(order) + 1))
        ax.set_xticklabels(order)
        ax.set_title(label)
        ax.set_ylabel(metric)
    fig.tight_layout()
    fig.savefig(out_dir / "summary.png", dpi=150)
    plt.close(fig)


def main(data_dir: str | Path = "data") -> None:
    df = load_all(data_dir)
    trial_metrics = compute_trial_metrics(df)
    summary = summarize(trial_metrics)
    if summary.empty:
        print("No data after excluding the first 2 s of each trial; nothing to analyze.")
        return
    out_dir = Path(data_dir) / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    trial_metrics.to_csv(out_dir / "trial_metrics.csv", index=False)
    summary.to_csv(out_dir / "summary.csv", index=False)
    tests = paired_tests(summary)
    if len(tests):
        tests.to_csv(out_dir / "paired_tests.csv", index=False)
        print(tests.to_string(index=False))
    plot_summary(summary, out_dir)
    print(f"Saved analysis to {out_dir}")


if __name__ == "__main__":
    main()
