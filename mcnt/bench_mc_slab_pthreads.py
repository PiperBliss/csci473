#!/usr/bin/env python3
"""
bench_mc_slab_pthreads.py

Benchmark the pthreads `mc_slab_pthreads` implementation using the CLI format
requested. The script sweeps problem sizes (n) and thread counts (P), measures
timings, computes speedup/efficiency/isoefficiency, and can optionally run an
MPI executable for comparison.

Example usage (your provided command):
python3 bench_mc_slab_pthreads.py \
  --exe ./mc_slab_pthreads \
  --C 0.5 --Cc 0.1 --H 5.0 --seed 12345 \
  --n_start 100000 --n_max 66400000 \
  --P_start 1 --P_step 1 --P_max 12 \
  --trials 6 --warmup 1 \
  --eff_targets 0.5,0.7,0.8 \
  --results-dir perf_results_mc

"""

import argparse
import subprocess
import time
import os
import csv
import math
import numpy as np
import matplotlib.pyplot as plt


def ensure_dir(p):
    os.makedirs(p, exist_ok=True)


def parse_list(s):
    return [float(x) for x in s.split(',') if x.strip()]


def run_cmd(cmd):
    t0 = time.perf_counter()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    t1 = time.perf_counter()
    elapsed = t1 - t0
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nstdout:\n{p.stdout}\nstderr:\n{p.stderr}")
    out = p.stdout.strip()
    parts = out.split()
    if len(parts) < 3:
        raise RuntimeError(f"Unexpected output from {' '.join(cmd)}: '{out}'")
    return elapsed, tuple(float(x) for x in parts[:3])


def geom_seq(start, stop):
    # generate geometric sequence doubling until exceed stop
    vals = []
    v = int(start)
    while v <= stop:
        vals.append(v)
        v = v * 2
    if vals[-1] < stop:
        vals.append(int(stop))
    return vals


def linear_range(start, step, stop):
    vals = []
    v = int(start)
    while v <= stop:
        vals.append(v)
        v += int(step)
    return vals


def mean_std(lst):
    a = np.array(lst)
    return float(a.mean()), float(a.std())


def plot_results(data, serial_times, outdir, impl_name, eff_targets):
    ensure_dir(outdir)
    Ns = sorted(list(data.keys()))
    Ps = sorted({p for n in Ns for p in data[n].keys()})

    # force integer x-axis ticks from min P to max P (step 1)
    if Ps:
        P_min = int(min(Ps))
        P_max = int(max(Ps))
        x_ticks = list(range(P_min, P_max + 1))
    else:
        P_min = 1
        P_max = 1
        x_ticks = [1]

    # Timing
    plt.figure()
    for n in Ns:
        ys = [data[n].get(p, {}).get('time', math.nan) for p in Ps]
        plt.plot(Ps, ys, marker='o', label=f'n={n}')
    plt.xlabel('P')
    plt.ylabel('Time (s)')
    # use linear integer x-axis with ticks at every integer
    plt.xticks(x_ticks)
    plt.xlim(P_min, P_max)
    plt.title(f'{impl_name} Timing')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f'{impl_name}_timing.png'))
    plt.close()

    # Speedup
    plt.figure()
    for n in Ns:
        times = [data[n].get(p, {}).get('time', math.nan) for p in Ps]
        speedups = [serial_times[n] / t if (n in serial_times and t and not math.isnan(t)) else math.nan for t in times]
        plt.plot(Ps, speedups, marker='o', label=f'n={n}')
    plt.xlabel('P')
    plt.ylabel('Speedup')
    plt.xticks(x_ticks)
    plt.xlim(P_min, P_max)
    plt.title(f'{impl_name} Speedup')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f'{impl_name}_speedup.png'))
    plt.close()

    # Efficiency
    plt.figure()
    for n in Ns:
        times = [data[n].get(p, {}).get('time', math.nan) for p in Ps]
        speedups = [serial_times[n] / t if (n in serial_times and t and not math.isnan(t)) else math.nan for t in times]
        effs = [s / p if (s and not math.isnan(s)) else math.nan for s, p in zip(speedups, Ps)]
        plt.plot(Ps, effs, marker='o', label=f'n={n}')
    plt.xlabel('P')
    plt.ylabel('Efficiency')
    plt.xticks(x_ticks)
    plt.xlim(P_min, P_max)
    plt.title(f'{impl_name} Efficiency')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f'{impl_name}_efficiency.png'))
    plt.close()

    # Isoefficiency: build stepwise minimal-N curves per target efficiency
    # This implements the approach from the provided snippet: for each target
    # efficiency, find the minimal problem size N that achieves at least that
    # efficiency for each P, then plot a step-like curve.
    if len(Ns) < 2:
        print('Skipping Isoefficiency plot: only one problem size tested.')
    else:
        plt.figure()
        # fixed efficiency targets from the assignment snippet
        efficiencies = [0.29, 0.34, 0.39, 0.44, 0.49, 0.54, 0.59, 0.64,
                        0.69, 0.74, 0.79, 0.84, 0.89, 0.94, 0.99]

        sorted_problem_sizes = sorted(Ns)
        base_size = min(sorted_problem_sizes)

        # color cycle
        COLORS = plt.rcParams.get('axes.prop_cycle').by_key().get('color', ['b','g','r','c','m','y','k'])

        for eff_idx, eff in enumerate(efficiencies):
            plot_threads = []
            plot_n_values = []
            last_n_found = None

            for thread_num in Ps:
                min_n_for_p = None
                for n_size in sorted_problem_sizes:
                    t = data[n_size].get(thread_num, {}).get('time', math.nan)
                    eff_val = None
                    if n_size in serial_times and not math.isnan(t) and t > 0:
                        eff_val = (serial_times[n_size] / t) / thread_num
                    if eff_val is not None and not math.isnan(eff_val) and eff_val >= eff:
                        min_n_for_p = n_size
                        break

                if min_n_for_p is not None:
                    if last_n_found is None:
                        plot_threads.append(thread_num)
                        plot_n_values.append(min_n_for_p)
                    elif min_n_for_p != last_n_found:
                        plot_threads.append(thread_num - 1)
                        plot_n_values.append(last_n_found)
                        plot_threads.append(thread_num)
                        plot_n_values.append(min_n_for_p)
                    last_n_found = min_n_for_p

            if last_n_found is not None:
                plot_threads.append(Ps[-1])
                plot_n_values.append(last_n_found)

            if plot_threads:
                plt.plot(plot_threads, plot_n_values, '-',
                         color=COLORS[eff_idx % len(COLORS)],
                         label=f'E ≥ {eff:.2f}', linewidth=2)
                plt.plot(plot_threads, plot_n_values, 'o',
                         color=COLORS[eff_idx % len(COLORS)], markersize=6)

        plt.xlabel('P')
        plt.ylabel('Minimal N achieving target E')
        plt.title(f'{impl_name} Isoefficiency')
        plt.legend(title='Targets', bbox_to_anchor=(1.02, 1), loc='upper left')
        plt.grid(True, linestyle=':')
        plt.xticks(Ps)

        # Use log scale on the y-axis for isoefficiency to span wide N ranges
        plt.yscale('log')

        tick_values = sorted_problem_sizes
        tick_labels = [f'{n/base_size:.2f}x ({n})' for n in tick_values]
        plt.yticks(tick_values, tick_labels)

        plt.tight_layout()
        plt.savefig(os.path.join(outdir, f'{impl_name}_isoeff.png'))
        plt.close()

    


def main():
    parser = argparse.ArgumentParser(description='Benchmark mc_slab pthreads implementation')
    parser.add_argument('--exe', required=True, help='path to pthreads executable')
    parser.add_argument('--mpi-exe', default='./mc_slab_mpi', help='path to MPI executable for comparison')
    parser.add_argument('--mpirun', default='mpirun -np {P}', help='mpirun template')
    parser.add_argument('--C', type=float, required=True)
    parser.add_argument('--Cc', type=float, required=True)
    parser.add_argument('--H', type=float, required=True)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--n_start', type=int, required=True)
    parser.add_argument('--n_max', type=int, required=True)
    parser.add_argument('--P_start', type=int, required=True)
    parser.add_argument('--P_step', type=int, required=True)
    parser.add_argument('--P_max', type=int, required=True)
    parser.add_argument('--trials', type=int, default=3)
    parser.add_argument('--warmup', type=int, default=0)
    parser.add_argument('--eff_targets', default='0.5,0.7,0.8')
    parser.add_argument('--results-dir', default='results/perf')
    args = parser.parse_args()

    eff_targets = [float(x) for x in args.eff_targets.split(',') if x.strip()]
    Ns = geom_seq(args.n_start, args.n_max)
    Ps = linear_range(args.P_start, args.P_step, args.P_max)

    outdir = args.results_dir
    ensure_dir(outdir)
    csv_path = os.path.join(outdir, 'bench_pthreads_raw.csv')

    # Serial baseline: run single-threaded serial mc_slab (assume in repo)
    serial_exec = './mc_slab'
    serial_times = {}
    print('Running serial baseline...')
    total_serial = len(Ns)
    for idx, n in enumerate(Ns, start=1):
        times = []
        # Print progress matching pthreads format
        print(f"[ {idx:3d}/{total_serial:3d}] n={n:7d} P={1:2d} - trials={args.trials}")
        for t in range(args.warmup):
            _ = run_cmd([serial_exec, str(args.C), str(args.Cc), str(args.H), str(n), '--seed', str(args.seed)])[0]
        for trial in range(args.trials):
            elapsed, fracs = run_cmd([serial_exec, str(args.C), str(args.Cc), str(args.H), str(n), '--seed', str(args.seed + trial)])
            times.append(elapsed)
            with open(csv_path, 'a', newline='') as cf:
                writer = csv.writer(cf)
                writer.writerow(['serial', n, 1, trial, elapsed, fracs[0], fracs[1], fracs[2]])
        mean_t, _ = mean_std(times)
        serial_times[n] = mean_t
        print(f'  serial n={n} mean={mean_t:.4f}s')

    # Run pthreads
    pthreads_data = {n: {} for n in Ns}
    print('\nRunning pthreads benchmarks...')
    total_runs = len(Ns) * len(Ps)
    run_idx = 0
    for n in Ns:
        for p in Ps:
            run_idx += 1
            # Print progress in the requested format: [ idx/total] n= N P= p - trials=T
            print(f"[ {run_idx:3d}/{total_runs:3d}] n={n:7d} P={p:2d} - trials={args.trials}")
            # warmup
            for w in range(args.warmup):
                _ = run_cmd([args.exe, str(args.C), str(args.Cc), str(args.H), str(n), str(p), '--seed', str(args.seed)])[0]
            times = []
            for trial in range(args.trials):
                elapsed, fracs = run_cmd([args.exe, str(args.C), str(args.Cc), str(args.H), str(n), str(p), '--seed', str(args.seed + trial)])
                times.append(elapsed)
                with open(csv_path, 'a', newline='') as cf:
                    writer = csv.writer(cf)
                    writer.writerow(['pthreads', n, p, trial, elapsed, fracs[0], fracs[1], fracs[2]])
            mean_t, std_t = mean_std(times)
            pthreads_data[n][p] = {'time': mean_t, 'std': std_t}
            print(f'  pthreads n={n} P={p} mean={mean_t:.4f}s')

    # Run MPI for comparison
    mpi_data = {n: {} for n in Ns}
    print('\nRunning MPI benchmarks (comparison)...')
    total_mpi = len(Ns) * len(Ps)
    mpi_idx = 0
    for n in Ns:
        for p in Ps:
            mpi_idx += 1
            # Print progress matching pthreads format
            print(f"[ {mpi_idx:3d}/{total_mpi:3d}] n={n:7d} P={p:2d} - trials={args.trials}")
            mpicmd = args.mpirun.format(P=p).split() + [args.mpi_exe, str(args.C), str(args.Cc), str(args.H), str(n), '--seed', str(args.seed)]
            # warmup
            for w in range(args.warmup):
                _ = run_cmd(mpicmd)[0]
            times = []
            for trial in range(args.trials):
                elapsed, fracs = run_cmd(args.mpirun.format(P=p).split() + [args.mpi_exe, str(args.C), str(args.Cc), str(args.H), str(n), '--seed', str(args.seed + trial)])
                times.append(elapsed)
                with open(csv_path, 'a', newline='') as cf:
                    writer = csv.writer(cf)
                    writer.writerow(['mpi', n, p, trial, elapsed, fracs[0], fracs[1], fracs[2]])
            mean_t, std_t = mean_std(times)
            mpi_data[n][p] = {'time': mean_t, 'std': std_t}
            print(f'  mpi n={n} P={p} mean={mean_t:.4f}s')

    # Summaries and plots
    summary_csv = os.path.join(outdir, 'bench_pthreads_summary.csv')
    with open(summary_csv, 'w', newline='') as sf:
        writer = csv.writer(sf)
        writer.writerow(['impl','n','P','time_s','speedup','efficiency'])
        for impl_name, data in [('pthreads', pthreads_data), ('mpi', mpi_data)]:
            for n in Ns:
                for p in Ps:
                    t = data[n].get(p, {}).get('time', math.nan)
                    if n in serial_times and not math.isnan(t) and t>0:
                        speedup = serial_times[n] / t
                        eff = speedup / p
                    else:
                        speedup = math.nan
                        eff = math.nan
                    writer.writerow([impl_name, n, p, t, speedup, eff])

    # Plot per-implementation
    plot_results(pthreads_data, serial_times, os.path.join(outdir, 'pthreads'), 'pthreads', eff_targets)
    plot_results(mpi_data, serial_times, os.path.join(outdir, 'mpi'), 'mpi', eff_targets)

    # Comparison plots
    cmpdir = os.path.join(outdir, 'comparison')
    ensure_dir(cmpdir)
    for n in Ns:
        plt.figure()
        ps = Ps
        t1 = [pthreads_data[n].get(p, {}).get('time', math.nan) for p in ps]
        t2 = [mpi_data[n].get(p, {}).get('time', math.nan) for p in ps]
        plt.plot(ps, t1, marker='o', label='pthreads')
        plt.plot(ps, t2, marker='s', label='mpi')
        plt.xlabel('P')
        plt.ylabel('Time (s)')
        # comparison: use linear x-axis with integer ticks
        plt.title(f'Comparison Timing n={n}')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(cmpdir, f'compare_n{n}_timing.png'))
        plt.close()

    print(f'Benchmark complete. Results in {outdir}')


if __name__ == '__main__':
    main()