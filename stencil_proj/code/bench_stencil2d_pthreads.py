#!/usr/bin/env python3
import subprocess
import csv
import time
import matplotlib.pyplot as plt
import numpy as np
import os
import argparse
from matplotlib.ticker import ScalarFormatter

# Create results directory if it doesn't exist
if not os.path.exists('results'):
    os.makedirs('results')

# Style settings for plots
plt.style.use('seaborn')  # Use seaborn style for older matplotlib versions (3.4.x)
MARKERS = ['o', 's', '^', 'D', 'v', '>', '<', 'p']
COLORS = plt.cm.get_cmap('tab20', 20).colors

def run_stencil(rows, cols, iters, threads, make_exe, pth_exe):
    """Run stencil program and return execution time."""
    initial_file = f"initial.{rows}x{cols}.dat"
    final_file = f"final.{rows}x{cols}x{iters}.dat"
    
    # Create initial conditions
    try:
        subprocess.run([make_exe, str(rows), str(cols), initial_file], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {make_exe}: {e.stderr}")
        return None
    
    # Run the stencil program (no stack file for performance test)
    try:
        # Note: The -s argument is removed for benchmarking as per the assignment
        result = subprocess.run([pth_exe, "-n", str(iters), "-I", initial_file, 
                               "-o", final_file, "-t", str(threads)],
                              capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {pth_exe}: {e.stderr}")
        return None
    
    # Extract time from output
    for line in result.stdout.split('\n'):
        if "Stencil operation took" in line and "seconds" in line:
            try:
                return float(line.split()[3])
            except (IndexError, ValueError):
                pass
    
    print(f"Warning: Could not parse time from output for {rows}x{cols} @ {threads} threads.")
    print(result.stdout)
    return None

def create_plots(results, problem_sizes, all_threads, iterations, results_dir, label):
    """Generates all plots and saves them to the results directory."""

    # --- Setup ---
    # Use the first iteration count for labeling, as plots are per-iteration
    I_label = iterations[0]
    plot_suffix = f"_I{I_label}{'_' + label if label else ''}.png"
    
    organized_data = {}
    for size in problem_sizes:
        size_str = f"{size}x{size}"
        organized_data[size] = {
            'threads': [],
            'times': [],
            'speedups': [],
            'efficiency': []
        }
        
        for r in results:
            # Filter results for the first iteration count for these plots
            if r['size'] == size_str and r['iterations'] == I_label:
                organized_data[size]['threads'].append(r['threads'])
                organized_data[size]['times'].append(r['time'])
                organized_data[size]['speedups'].append(r['speedup'])
                organized_data[size]['efficiency'].append(r['efficiency'])

    # --- 1. Execution Time vs Number of Threads ---
    plt.figure(figsize=(10, 6))
    for i, size in enumerate(problem_sizes):
        plt.plot(organized_data[size]['threads'], 
                organized_data[size]['times'],
                marker=MARKERS[i], color=COLORS[i % len(COLORS)],
                label=f'N={size}', linewidth=2, markersize=8)
    plt.xlabel('Number of Threads (P)')
    plt.ylabel('Execution Time (seconds)')
    plt.title(f'Execution Time vs. Number of Threads (I={I_label})')
    plt.legend(title='Problem Size')
    plt.grid(True, linestyle=':')
    plt.xticks(all_threads)
    plt.savefig(os.path.join(results_dir, f'timing_vs_P_by_N{plot_suffix}'), dpi=300, bbox_inches='tight')
    plt.close()

    # --- 2. Speedup vs Number of Threads ---
    plt.figure(figsize=(10, 6))
    max_threads = max(all_threads)
    plt.plot([1, max_threads], [1, max_threads], 'k--', label='Ideal Speedup', linewidth=2)
    for i, size in enumerate(problem_sizes):
        plt.plot(organized_data[size]['threads'],
                organized_data[size]['speedups'],
                marker=MARKERS[i], color=COLORS[i % len(COLORS)],
                label=f'N={size}', linewidth=2, markersize=8)
    plt.xlabel('Number of Threads (P)')
    plt.ylabel('Speedup')
    plt.title(f'Speedup vs. Number of Threads (I={I_label})')
    plt.legend(title='Problem Size')
    plt.grid(True, linestyle=':')
    plt.xticks(all_threads)
    plt.savefig(os.path.join(results_dir, f'speedup_vs_P_by_N{plot_suffix}'), dpi=300, bbox_inches='tight')
    plt.close()

    # --- 3. Efficiency vs Number of Threads ---
    plt.figure(figsize=(10, 6))
    for i, size in enumerate(problem_sizes):
        plt.plot(organized_data[size]['threads'],
                organized_data[size]['efficiency'],
                marker=MARKERS[i], color=COLORS[i % len(COLORS)],
                label=f'N={size}', linewidth=2, markersize=8)
    plt.xlabel('Number of Threads (P)')
    plt.ylabel('Efficiency')
    plt.title(f'Efficiency vs. Number of Threads (I={I_label})')
    plt.legend(title='Problem Size')
    plt.grid(True, linestyle=':')
    plt.xticks(all_threads)
    plt.savefig(os.path.join(results_dir, f'efficiency_vs_P_by_N{plot_suffix}'), dpi=300, bbox_inches='tight')
    plt.close()

    # --- 4. Isoefficiency Graph ---
    # This plot only makes sense if there are multiple problem sizes
    if len(problem_sizes) < 2:
        print("Skipping Isoefficiency plot: only one problem size tested.")
        return

    plt.figure(figsize=(12, 8))
    
    # Create a list of target efficiencies (e.g., 0.29, 0.34, 0.39...)
    # This matches the 'eff_range' argument '0.29 0.05' from the assignment
    efficiencies = [0.29, 0.34, 0.39, 0.44, 0.49, 0.54, 0.59, 0.64, 
                   0.69, 0.74, 0.79, 0.84, 0.89, 0.94, 0.99]
    
    sorted_problem_sizes = sorted(problem_sizes)
    base_size = min(problem_sizes)

    # For each efficiency target
    for eff_idx, eff in enumerate(efficiencies):
        plot_threads = []  # X-values for this line
        plot_n_values = [] # Y-values for this line
        last_n_found = None
        
        # For each thread count
        for thread_num in all_threads:
            min_n_for_p = None
            
            # Find minimum N that achieves target E for this P
            for n_size in sorted_problem_sizes:
                eff_val = None
                for r in results:
                    if r['size'] == f"{n_size}x{n_size}" and \
                       r['threads'] == thread_num and \
                       r['iterations'] == I_label:
                        eff_val = r['efficiency']
                        break
                
                if eff_val is not None and eff_val >= eff:
                    min_n_for_p = n_size
                    break  # Found the minimal N for this P
            
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
            plot_threads.append(all_threads[-1])
            plot_n_values.append(last_n_found)

        if plot_threads:
            plt.plot(plot_threads, plot_n_values, '-',
                    color=COLORS[eff_idx % len(COLORS)],
                    label=f'E ≥ {eff:.2f}',
                    linewidth=2)
            plt.plot(plot_threads, plot_n_values, 'o',
                    color=COLORS[eff_idx % len(COLORS)],
                    markersize=6)

    plt.xlabel('Threads (P)')
    plt.ylabel('Minimal N achieving target E')
    plt.title(f'Isoefficiency Surface — I={I_label}')
    plt.legend(title='Targets', bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.grid(True, linestyle=':')
    plt.xticks(all_threads)
    
    tick_values = sorted_problem_sizes
    tick_labels = [f'{n/base_size:.2f}x ({n})' for n in tick_values]
    plt.yticks(tick_values, tick_labels)
    
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, f'isoefficiency_surface{plot_suffix}'), dpi=300, bbox_inches='tight')
    plt.close()

def main():
    # --- 1. Parse Command-Line Arguments ---
    # These arguments are defined in the assignment document 
    parser = argparse.ArgumentParser(description="Benchmark pthreads stencil-2d over N, P, and I (no stacks).")
    
    # Executable paths
    parser.add_argument('--make_exe', default='./make-2d', help='path to make-2d')
    parser.add_argument('--pth_exe', default='./pth-stencil-2d', help='path to pth-stencil-2d')

    # Problem Size (N) arguments
    parser.add_argument('--N1', type=int, default=128, help='min N (evenly spaced)')
    parser.add_argument('--N2', type=int, default=256, help='max N (evenly spaced)')
    parser.add_argument('--num_Ns', type=int, default=3, help='number of N points (evenly spaced)')

    # Thread (P) arguments
    parser.add_argument('--P_start', type=int, default=1, help='P range start')
    parser.add_argument('--P_step', type=int, default=1, help='P range step')
    parser.add_argument('--P_max', type=int, default=12, help='P range max (inclusive)')

    # Iteration (I) arguments
    parser.add_argument('--I1', type=int, default=10, help='iterations min')
    parser.add_argument('--I2', type=int, default=200, help='iterations max')
    parser.add_argument('--Istep', type=int, default=20, help='iterations step')
    
    # Trial control
    parser.add_argument('--warmup', type=int, default=1, help='warmup runs per (N,P,I) not timed')
    parser.add_argument('--trials', type=int, default=4, help='timed trials per (N,P,I)')
    
    # Other
    parser.add_argument('--results-dir', default='perf_results', help='folder for outputs')
    parser.add_argument('--label', default='', help='optional label suffix for filenames')
    
    # Arguments from assignment doc that are not used in this simplified script,
    # but are included for compatibility with the 'run-all.py' command:
    parser.add_argument('--timeout_sec', type=int, default=600)
    parser.add_argument('--eff_range', default='') 

    args = parser.parse_args()

    # --- 2. Build C programs first ---
    print("--- Building C executables... ---")
    try:
        subprocess.run(["make", "all"], check=True, capture_output=True, text=True)
        print("Build successful.")
    except subprocess.CalledProcessError as e:
        print("Error: 'make all' failed. Aborting.")
        print(e.stderr)
        return

    # --- 3. Generate Test Parameters ---
    problem_sizes = np.linspace(args.N1, args.N2, args.num_Ns, dtype=int)
    thread_counts = list(range(args.P_start, args.P_max + 1, args.P_step))
    iterations = list(range(args.I1, args.I2 + 1, args.Istep))

    # Create results directory
    if not os.path.exists(args.results_dir):
        os.makedirs(args.results_dir)
    
    # Results storage
    results = []
    
    # --- 4. Run tests ---
    print("\n--- Running performance tests... ---")
    serial_times = {} # Store serial time (P=1) per (N, I) pair
    
    total_runs = len(problem_sizes) * len(thread_counts) * len(iterations)
    current_run = 0

    for iters in iterations:
        for size in problem_sizes:
            serial_time = None
            for threads in thread_counts:
                current_run += 1
                print(f"[{current_run:4d}/{total_runs:4d}] N={size:4d} I={iters:4d} P={threads:2d} — trials={args.trials}...")
                
                # Warmup runs
                for _ in range(args.warmup):
                    run_stencil(size, size, iters, threads, args.make_exe, args.pth_exe)
                
                # Timed trials
                times = []
                for _ in range(args.trials):
                    run_time = run_stencil(size, size, iters, threads, args.make_exe, args.pth_exe)
                    if run_time is None:
                        print(f"Run failed. Skipping.")
                        continue
                    times.append(run_time)
                
                if not times:
                    print("All trials failed for this configuration. Skipping.")
                    continue
                    
                avg_time = sum(times) / len(times)
                
                if threads == 1:
                    serial_time = avg_time
                    serial_times[(size, iters)] = avg_time
                
                current_serial_time = serial_times.get((size, iters)) 
                
                if current_serial_time is None:
                    print(f"Error: Serial time (P=1) for N={size}, I={iters} not found. Can't calculate speedup.")
                    speedup = 0
                    efficiency = 0
                else:
                    speedup = current_serial_time / avg_time
                    efficiency = speedup / threads
                
                results.append({
                    'size': f"{size}x{size}",
                    'N': size,
                    'threads': threads,
                    'iterations': iters,
                    'time': avg_time,
                    'speedup': speedup,
                    'efficiency': efficiency
                })

    print("\n--- Saving results to CSV... ---")
    
    # --- 5. Save Raw CSV ---
    csv_label = f"_{args.label}" if args.label else ""
    raw_csv_file = os.path.join(args.results_dir, f"raw_runs{csv_label}.csv")
    with open(raw_csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['size', 'N', 'threads', 'iterations', 'time', 'speedup', 'efficiency'])
        writer.writeheader()
        writer.writerows(results)
    print(f"Raw CSV : {raw_csv_file}")
    
    # --- 6. Save Summary CSV ---
    summary_results = []
    for res in results:
        summary_results.append({
            'Problem Size': res['size'],
            'Threads': res['threads'],
            'Iterations': res['iterations'],
            'Time(s)': f"{res['time']:.4f}",
            'Speedup': f"{res['speedup']:.4f}",
            'Efficiency': f"{res['efficiency']:.4f}"
        })
    
    summary_csv_file = os.path.join(args.results_dir, f"summary{csv_label}.csv")
    with open(summary_csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Problem Size', 'Threads', 'Iterations', 'Time(s)', 'Speedup', 'Efficiency'])
        writer.writeheader()
        writer.writerows(summary_results)
    print(f"Summary : {summary_csv_file}")
    
    # --- 7. Generate plots ---
    print("--- Generating plots... ---")
    # Generate one set of plots for each iteration count
    for iters in iterations:
        iter_results = [r for r in results if r['iterations'] == iters]
        if iter_results:
            create_plots(iter_results, problem_sizes, thread_counts, [iters], args.results_dir, args.label)
    
    print(f"Plots   : See '{args.results_dir}' directory.")
    print("\n--- All done. ---")

if __name__ == "__main__":
    main()