#!/usr/bin/env python3
"""
test_mpi_matrix_vector_mult.py

Usage:
  python3 test_mpi_matrix_vector_mult.py starting_n ending_n n_increment starting_p ending_p p_increment

What it does:
  - For each n in [start..end] step n_increment:
      * makes A: n x n, B: n x 1 once via ./make-matrix
      * for each p in [p_start..p_end] step p_increment:
          - runs: mpirun -np p ./mpi-matrix-vector-multiply A.bin B.bin C.bin
          - parses: TIMING total_s=... gflops_compute=... etc.
  - Writes CSV to ./mpi_results/mpi_results.csv
  - Produces 8 combined plots (one curve per n):
      * overall_times_vs_p.png, overall_speedup_vs_p.png, overall_efficiency_vs_p.png
      * compute_times_vs_p.png, compute_speedup_vs_p.png, compute_efficiency_vs_p.png
      * compute_gflops_vs_p.png, overall_gflops_vs_p.png
"""

import sys
import os
import subprocess
import tempfile
import re
import csv
from pathlib import Path
from math import isfinite

import matplotlib.pyplot as plt

MAKE_MATRIX = "./make-matrix"
MPI_MATVEC  = "./mpi-matrix-vector-multiply"
MPIRUN      = os.environ.get("MPIRUN", "mpirun")

TIMING_RE = re.compile(
    r"TIMING\s+total_s=(?P<total>\d+\.\d+)\s+read_s=(?P<read>\d+\.\d+)\s+compute_s=(?P<compute>\d+\.\d+)\s+write_s=(?P<write>\d+\.\d+)\s+gflops_total=(?P<gflops_total>\d+\.\d+)\s+gflops_compute=(?P<gflops_compute>\d+\.\d+)\s+m=(?P<m>\d+)\s+n=(?P<n>\d+)\s+p=(?P<p>\d+)"
)

def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def run_cmd(cmd, cwd=None):
    res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.stdout, res.stderr, res.returncode

def check_tools():
    for exe in (MAKE_MATRIX, MPI_MATVEC):
        if not (os.path.isfile(exe) and os.access(exe, os.X_OK)):
            die(f"Required executable not found or not executable: {exe}")
    # Best-effort mpirun check
    _o, _e, rc = run_cmd([MPIRUN, "--version"])
    if rc != 0:
        print("WARNING: 'mpirun --version' failed; ensure MPI is available (set MPIRUN env if needed).", file=sys.stderr)

def ensure_results_dir():
    d = Path("./mpi_results")
    d.mkdir(parents=True, exist_ok=True)
    return d

def parse_timing(text_out):
    for line in text_out.splitlines():
        m = TIMING_RE.search(line)
        if m:
            d = m.groupdict()
            return {
                "total": float(d["total"]),
                "read": float(d["read"]),
                "compute": float(d["compute"]),
                "write": float(d["write"]),
                "gflops_total": float(d["gflops_total"]),
                "gflops_compute": float(d["gflops_compute"]),
                "m": int(d["m"]),
                "n": int(d["n"]),
                "p": int(d["p"]),
            }
    return None

def make_matrix(path, rows, cols, lower=-1.0, upper=1.0):
    cmd = [MAKE_MATRIX, "-rows", str(rows), "-cols", str(cols),
           "-l", str(lower), "-u", str(upper), "-o", str(path)]
    out, err, rc = run_cmd(cmd)
    if rc != 0:
        raise RuntimeError(f"make-matrix failed\nCMD: {' '.join(cmd)}\nSTDOUT:\n{out}\nSTDERR:\n{err}")

def run_mpi_matvec(p, A_path, B_path, C_path):
    cmd = [MPIRUN, "-np", str(p), MPI_MATVEC, str(A_path), str(B_path), str(C_path)]
    out, err, rc = run_cmd(cmd)
    if rc != 0:
        raise RuntimeError(f"mpi-matrix-vector-multiply failed (p={p})\nCMD: {' '.join(cmd)}\nSTDOUT:\n{out}\nSTDERR:\n{err}")
    timing = parse_timing(out) or parse_timing(err)
    if timing is None:
        raise RuntimeError(f"Could not parse TIMING line for p={p}\nSTDOUT:\n{out}\nSTDERR:\n{err}")
    return timing

# ---------- plotting helpers ----------

def per_n_series(rows, key):
    """
    Build per-n series: {n: (ps_sorted, vals_sorted)} using key.
    rows: list of dicts with keys n, p, and the specified key.
    """
    by_n = {}
    for r in rows:
        n = r["n"]; p = r["p"]; val = r[key]
        by_n.setdefault(n, []).append((p, val))
    series = {}
    for n, lst in by_n.items():
        lst_sorted = sorted(lst, key=lambda x: x[0])
        ps = [p for p,_ in lst_sorted]
        vals = [v for _,v in lst_sorted]
        series[n] = (ps, vals)
    return series

def plot_multi_times(series_by_n, title, ylabel, outpath):
    plt.figure()
    for n in sorted(series_by_n.keys()):
        ps, ts = series_by_n[n]
        plt.plot(ps, ts, marker="o", linewidth=2, label=f"n={n}")
    plt.title(title)
    plt.xlabel("Processes (p)")
    plt.ylabel(ylabel)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend(title="Matrix size", ncol=2)
    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close()

def plot_multi_flops(series_by_n, title, ylabel, outpath):
    # This is identical to plot_multi_times, just renamed for clarity
    plot_multi_times(series_by_n, title, ylabel, outpath)

def build_speedup_efficiency(ps, ts, n, label_for_warning):
    """Given vectors p, time, compute speedup & efficiency with per-n baseline."""
    if 1 in ps:
        base_idx = ps.index(1)
        base_p = 1
    else:
        base_idx = 0
        base_p = ps[0]
        print(f"NOTE: p=1 not sampled for n={n} ({label_for_warning}); using p={base_p} as baseline.", file=sys.stderr)
    base_t = ts[base_idx]
    speedup = []
    efficiency = []
    for p, t in zip(ps, ts):
        s = (base_t / t) if t > 0 and isfinite(t) else 0.0
        e = (s / p) if p > 0 else 0.0
        speedup.append(s)
        efficiency.append(e)
    return speedup, efficiency, base_p

def plot_multi_speedup(series_by_n, title, outpath, label_for_warning):
    plt.figure()
    for n in sorted(series_by_n.keys()):
        ps, ts = series_by_n[n]
        s, _e, base_p = build_speedup_efficiency(ps, ts, n, label_for_warning)
        plt.plot(ps, s, marker="o", linewidth=2, label=f"n={n} (base p={base_p})")
    plt.title(title)
    plt.xlabel("Processes (p)")
    plt.ylabel("Speedup")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend(title="Matrix size", ncol=2)
    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close()

def plot_multi_efficiency(series_by_n, title, outpath, label_for_warning):
    plt.figure()
    for n in sorted(series_by_n.keys()):
        ps, ts = series_by_n[n]
        _s, e, base_p = build_speedup_efficiency(ps, ts, n, label_for_warning)
        plt.plot(ps, e, marker="o", linewidth=2, label=f"n={n} (base p={base_p})")
    plt.title(title)
    plt.xlabel("Processes (p)")
    plt.ylabel("Efficiency (Speedup / p)")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend(title="Matrix size", ncol=2)
    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close()

# ---------- main ----------

def main():
    if len(sys.argv) != 7:
        print(__doc__)
        sys.exit(2)

    try:
        n_start = int(sys.argv[1]); n_end   = int(sys.argv[2]); n_step  = int(sys.argv[3])
        p_start = int(sys.argv[4]); p_end   = int(sys.argv[5]); p_step  = int(sys.argv[6])
    except ValueError:
        die("All parameters must be integers.")

    if n_start <= 0 or n_end <= 0 or n_step <= 0 or p_start <= 0 or p_end <= 0 or p_step <= 0:
        die("All parameters must be positive integers.")
    if n_start > n_end: die("starting_n must be <= ending_n")
    if p_start > p_end: die("starting_p must be <= ending_p")

    check_tools()
    outdir = ensure_results_dir()
    csv_path = outdir / "mpi_results.csv"

    ns = list(range(n_start, n_end + 1, n_step))

    #added to fix the time issue on the debug node
    #previously: ps = list(range(p_start, p_end + 1, p_step))
    if p_end == 128:
        # For the special case of p_end=128, use a specific hardcoded list.
        # Note: This overrides p_start and p_step for this case.
        ps = [1, 2, 4, 8, 16, 32, 48, 64, 80, 96, 112, 128]
    else:
        # For all other cases, use the original behavior.
        ps = list(range(p_start, p_end + 1, p_step))


    print(f"Sweep: n in {ns}, p in {ps}")

    # Gather all rows
    rows = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        for n in ns:
            A_path = tmpdir / f"A_{n}.bin"
            B_path = tmpdir / f"B_{n}.bin"
            C_path = tmpdir / f"C_{n}.bin"

            print(f"\n[ n = {n} ] Building inputs ... ", end="", flush=True)
            make_matrix(A_path, n, n, -1.0, 1.0)
            make_matrix(B_path, n, 1, -1.0, 1.0)
            print("done.")

            for p in ps:
                print(f"  p={p:<4} running ... ", end="", flush=True)
                t = run_mpi_matvec(p, A_path, B_path, C_path)
                print(f"total={t['total']:.4f}s, compute_gflops={t['gflops_compute']:.2f}")
                rows.append({
                    "n": t["n"], "p": t["p"],
                    "total_s": t["total"], "read_s": t["read"],
                    "compute_s": t["compute"], "write_s": t["write"],
                    "gflops_total": t["gflops_total"],
                    "gflops_compute": t["gflops_compute"],
                })

    # Write CSV
    csv_fields = ["n", "p", "total_s", "read_s", "compute_s", "write_s", "gflops_total", "gflops_compute"]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader(); w.writerows(rows)

    # Build per-n series for plotting
    overall_series        = per_n_series(rows, key="total_s")
    compute_series        = per_n_series(rows, key="compute_s")
    compute_gflops_series = per_n_series(rows, key="gflops_compute")
    overall_gflops_series = per_n_series(rows, key="gflops_total")


    # Produce plots
    # Overall times / speedup / efficiency
    plot_multi_times(
        overall_series,
        title="Overall time vs processes (p) — one curve per n",
        ylabel="Time (seconds)",
        outpath=outdir / "overall_times_vs_p.png",
    )
    plot_multi_speedup(
        overall_series,
        title="Overall speedup vs processes (p) — one curve per n",
        outpath=outdir / "overall_speedup_vs_p.png",
        label_for_warning="total",
    )
    plot_multi_efficiency(
        overall_series,
        title="Overall efficiency vs processes (p) — one curve per n",
        outpath=outdir / "overall_efficiency_vs_p.png",
        label_for_warning="total",
    )

    # Compute-only times / speedup / efficiency
    plot_multi_times(
        compute_series,
        title="Compute-only time vs processes (p) — one curve per n",
        ylabel="Time (seconds)",
        outpath=outdir / "compute_times_vs_p.png",
    )
    plot_multi_speedup(
        compute_series,
        title="Compute-only speedup vs processes (p) — one curve per n",
        outpath=outdir / "compute_speedup_vs_p.png",
        label_for_warning="compute",
    )
    plot_multi_efficiency(
        compute_series,
        title="Compute-only efficiency vs processes (p) — one curve per n",
        outpath=outdir / "compute_efficiency_vs_p.png",
        label_for_warning="compute",
    )

    # GFLOPS plots
    plot_multi_flops(
        compute_gflops_series,
        title="Compute GFLOPS vs processes (p) — one curve per n",
        ylabel="Performance (GFLOPS/sec)",
        outpath=outdir / "compute_gflops_vs_p.png"
    )
    plot_multi_flops(
        overall_gflops_series,
        title="Overall GFLOPS vs processes (p) — one curve per n",
        ylabel="Performance (GFLOPS/sec)",
        outpath=outdir / "overall_gflops_vs_p.png"
    )


    print("\nDone.")
    print(f"- Results CSV: {csv_path}")
    print(f"- Plots written to: {outdir}/")
    for fn in [
        "overall_times_vs_p.png", "overall_speedup_vs_p.png", "overall_efficiency_vs_p.png",
        "compute_times_vs_p.png", "compute_speedup_vs_p.png", "compute_efficiency_vs_p.png",
        "compute_gflops_vs_p.png", "overall_gflops_vs_p.png", # New plot
    ]:
        print(f"  - {fn}")

if __name__ == "__main__":
    main()