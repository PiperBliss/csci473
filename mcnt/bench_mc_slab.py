#!/usr/bin/env python3
"""
bench_mc_slab.py

Benchmark mc_slab (serial), mc_slab_pthreads, and mc_slab_mpi across a range of
problem sizes and thread/process counts. Produces timing, speedup, efficiency, and
iso-efficiency plots for pthreads and MPI, and a comparison set.

Usage: run from the `mcnt` directory. See CLI args for options.
"""

import argparse
import subprocess
import time
import os
import csv
import math
import numpy as np
import matplotlib.pyplot as plt


def run_cmd(cmd):
    t0 = time.perf_counter()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    t1 = time.perf_counter()
    elapsed = t1 - t0
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nstdout:\n{p.stdout}\nstderr:\n{p.stderr}")
    # Expect three floats in stdout (r_frac b_frac t_frac)
    out = p.stdout.strip()
    parts = out.split()
    if len(parts) < 3:
        raise RuntimeError(f"Unexpected output from {' '.join(cmd)}: '{out}'")
    return elapsed, tuple(float(x) for x in parts[:3])


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def mean_std(lst):
    if not lst:
        return None, None
    a = np.array(lst)
    return float(a.mean()), float(a.std())


def find_isoefficiency(ns, effs, target_e):
    # ns: list of n values
    # effs: list of efficiency values for corresponding ns
    # find minimal n where eff >= target_e
    for n, e in zip(ns, effs):
        if e >= target_e:
            return n
    return math.nan


def plot_strong_scaling(data_by_n, impl_name, outdir):
    # data_by_n: dict n -> dict P -> {'time': mean}
    ensure_dir(outdir)
    Ps = sorted({P for n in data_by_n for P in data_by_n[n]})
    Ns = sorted(data_by_n.keys())

    # Timing: for each n, time vs P
    plt.figure()
    for n in Ns:
        times = [data_by_n[n].get(P, {}).get('time', math.nan) for P in Ps]
        plt.plot(Ps, times, marker='o', label=f'n={n}')
    plt.xlabel('P (threads/processes)')
    plt.ylabel('Time (s)')
    plt.xscale('log', base=2)
    plt.legend()
    plt.title(f'{impl_name} Timing')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f'{impl_name}_timing.png'))
    plt.close()

    # Speedup and Efficiency: need serial baseline times per n
    serial_times = {n: data_by_n[n][1]['time'] for n in Ns if 1 in data_by_n[n]}

    # Speedup
    plt.figure()
    for n in Ns:
        times = [data_by_n[n].get(P, {}).get('time', math.nan) for P in Ps]
        speedups = [serial_times[n] / t if (n in serial_times and t and not math.isnan(t)) else math.nan for t in times]
        plt.plot(Ps, speedups, marker='o', label=f'n={n}')
    plt.xlabel('P')
    plt.ylabel('Speedup')
    plt.xscale('log', base=2)
    plt.legend()
    plt.title(f'{impl_name} Speedup')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f'{impl_name}_speedup.png'))
    plt.close()

    # Efficiency
    plt.figure()
    for n in Ns:
        times = [data_by_n[n].get(P, {}).get('time', math.nan) for P in Ps]
        speedups = [serial_times[n] / t if (n in serial_times and t and not math.isnan(t)) else math.nan for t in times]
        effs = [s / P if (s and not math.isnan(s)) else math.nan for s, P in zip(speedups, Ps)]
        plt.plot(Ps, effs, marker='o', label=f'n={n}')
    plt.xlabel('P')
    plt.ylabel('Efficiency')
    plt.xscale('log', base=2)
    plt.legend()
    plt.title(f'{impl_name} Efficiency')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f'{impl_name}_efficiency.png'))
    plt.close()

    # Isoefficiency: for a set of target efficiencies, find minimal n achieving it for each P
    targets = [0.5, 0.6, 0.7, 0.8]
    plt.figure()
    for target in targets:
        ns_for_P = []
        for P in Ps:
            effs_for_P = []
            for n in Ns:
                t = data_by_n[n].get(P, {}).get('time', math.nan)
                if P == 1:
                    eff = 1.0
                else:
                    if n in serial_times and not math.isnan(t) and t>0:
                        eff = (serial_times[n] / t) / P
                    else:
                        eff = math.nan
                effs_for_P.append(eff)
            n_iso = find_isoefficiency(Ns, effs_for_P, target)
            ns_for_P.append(n_iso)
        plt.plot(Ps, ns_for_P, marker='o', label=f'e={target}')
    plt.xlabel('P')
    plt.ylabel('Minimum n for target efficiency')
    plt.xscale('log', base=2)
    plt.yscale('log')
    plt.legend()
    plt.title(f'{impl_name} Isoefficiency')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f'{impl_name}_isoefficiency.png'))
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Benchmark mc_slab implementations (serial, pthreads, MPI)')
    parser.add_argument('--C', type=float, default=0.5)
    parser.add_argument('--Cc', type=float, default=0.005)
    parser.add_argument('--H', type=float, default=1.0)
    parser.add_argument('--ns', default='100000,500000,1000000', help='comma list of n values')
    parser.add_argument('--Ps', default='1,2,4,8', help='comma list of P (threads/processes)')
    parser.add_argument('--trials', type=int, default=3, help='repeats per point')
    parser.add_argument('--serial', default='./mc_slab')
    parser.add_argument('--pthreads', default='./mc_slab_pthreads')
    parser.add_argument('--mpi', default='./mc_slab_mpi')
    parser.add_argument('--mpirun', default='mpirun -np {P}', help='mpirun command template; {P} will be replaced')
    parser.add_argument('--outdir', default='results/bench', help='output directory for CSVs and plots')
    parser.add_argument('--tol', type=float, default=0.005)
    args = parser.parse_args()

    Ns = [int(x) for x in args.ns.split(',') if x.strip()]
    Ps = [int(x) for x in args.Ps.split(',') if x.strip()]

    outdir = args.outdir
    ensure_dir(outdir)

    # CSV to record raw timings
    csv_path = os.path.join(outdir, 'bench_results.csv')
    with open(csv_path, 'w', newline='') as csvf:
        writer = csv.writer(csvf)
        writer.writerow(['impl','n','P','trial','time_s','r_frac','b_frac','t_frac'])

    # Run serial baseline for each n
    serial_times = {}
    print('Running serial baseline...')
    for n in Ns:
        times = []
        for trial in range(args.trials):
            cmd = [args.serial, str(args.C), str(args.Cc), str(args.H), str(n), '--seed', str(1000+trial)]
            elapsed, _ = run_cmd(cmd)
            times.append(elapsed)
            with open(csv_path, 'a', newline='') as csvf:
                writer = csv.writer(csvf)
                writer.writerow(['serial', n, 1, trial, elapsed, 'NA','NA','NA'])
        mean_t, std_t = mean_std(times)
        serial_times[n] = mean_t
        print(f'  n={n} serial mean={mean_t:.4f}s std={std_t:.4f}s')

    # Helper to collect data for an implementation
    def collect_impl(impl, run_fn):
        data = {n: {} for n in Ns}
        for n in Ns:
            for P in Ps:
                times = []
                fracs = None
                for trial in range(args.trials):
                    elapsed, fracs = run_fn(n, P, trial)
                    times.append(elapsed)
                    with open(csv_path, 'a', newline='') as csvf:
                        writer = csv.writer(csvf)
                        writer.writerow([impl, n, P, trial, elapsed, fracs[0], fracs[1], fracs[2]])
                mean_t, std_t = mean_std(times)
                data[n][P] = {'time': mean_t, 'std': std_t}
                print(f'  {impl} n={n} P={P} mean={mean_t:.4f}s std={std_t:.4f}s')
        return data

    # Define run functions
    def run_pthreads(n, P, trial):
        cmd = [args.pthreads, str(args.C), str(args.Cc), str(args.H), str(n), str(P), '--seed', str(2000+trial)]
        return run_cmd(cmd)

    def run_mpi(n, P, trial):
        mpiruncmd = args.mpirun.format(P=P).split()
        cmd = mpiruncmd + [args.mpi, str(args.C), str(args.Cc), str(args.H), str(n), '--seed', str(3000+trial)]
        return run_cmd(cmd)

    # Collect data for pthreads
    print('\nCollecting pthreads data...')
    pthreads_data = collect_impl('pthreads', run_pthreads)

    # Collect data for MPI
    print('\nCollecting MPI data...')
    mpi_data = collect_impl('mpi', run_mpi)

    # Post-process: compute speedup/efficiency relative to serial baseline and write summary CSVs
    summary_path = os.path.join(outdir, 'bench_summary.csv')
    with open(summary_path, 'w', newline='') as sf:
        writer = csv.writer(sf)
        writer.writerow(['impl','n','P','time_s','speedup','efficiency'])
        for impl, data in (('pthreads', pthreads_data), ('mpi', mpi_data)):
            for n in Ns:
                for P in Ps:
                    t = data[n].get(P, {}).get('time', math.nan)
                    if n in serial_times and not math.isnan(t) and t>0:
                        speedup = serial_times[n] / t
                        efficiency = speedup / P
                    else:
                        speedup = math.nan
                        efficiency = math.nan
                    writer.writerow([impl, n, P, t, speedup, efficiency])

    # Produce plots
    print('\nGenerating plots...')
    out_pthreads = os.path.join(outdir, 'pthreads')
    out_mpi = os.path.join(outdir, 'mpi')
    out_comp = os.path.join(outdir, 'comparison')
    plot_strong_scaling(pthreads_data, 'pthreads', out_pthreads)
    plot_strong_scaling(mpi_data, 'mpi', out_mpi)

    # Comparison plots: timing/speedup for both on same axes
    ensure_dir(out_comp)
    Ps_sorted = sorted(Ps)
    Ns_sorted = sorted(Ns)

    # Timing comparison per n
    for n in Ns_sorted:
        plt.figure()
        times_p = [pthreads_data[n].get(P, {}).get('time', math.nan) for P in Ps_sorted]
        times_m = [mpi_data[n].get(P, {}).get('time', math.nan) for P in Ps_sorted]
        plt.plot(Ps_sorted, times_p, marker='o', label='pthreads')
        plt.plot(Ps_sorted, times_m, marker='s', label='mpi')
        plt.xlabel('P')
        plt.ylabel('Time (s)')
        plt.xscale('log', base=2)
        plt.title(f'Comparison Timing n={n}')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(out_comp, f'compare_timing_n{n}.png'))
        plt.close()

    # Speedup comparison per n
    for n in Ns_sorted:
        plt.figure()
        t_ser = serial_times[n]
        speed_p = [t_ser / pthreads_data[n].get(P, {}).get('time', math.nan) for P in Ps_sorted]
        speed_m = [t_ser / mpi_data[n].get(P, {}).get('time', math.nan) for P in Ps_sorted]
        plt.plot(Ps_sorted, speed_p, marker='o', label='pthreads')
        plt.plot(Ps_sorted, speed_m, marker='s', label='mpi')
        plt.xlabel('P')
        plt.ylabel('Speedup')
        plt.xscale('log', base=2)
        plt.title(f'Comparison Speedup n={n}')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(out_comp, f'compare_speedup_n{n}.png'))
        plt.close()

    print(f'Benchmarks complete. Results and plots in: {outdir}')


if __name__ == '__main__':
    main()
