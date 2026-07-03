#!/usr/bin/env python3
import subprocess
import numpy as np
import matplotlib.pyplot as plt
import argparse
import csv
import os
from datetime import datetime

def run_mc_slab(exe, C, Cc, H, N, seed=None, trace_file=None, trace_every=None):
    """Run mc_slab with given parameters and return results."""
    cmd = [exe, str(C), str(Cc), str(H), str(N)]
    if seed is not None:
        cmd.extend(['--seed', str(seed)])
    if trace_file is not None and trace_every is not None:
        cmd.extend(['--trace-file', trace_file, '--trace-every', str(trace_every)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Parse space-separated output (r_frac b_frac t_frac)
        r, b, t = map(float, result.stdout.strip().split())
        return r, b, t
    except subprocess.CalledProcessError as e:
        print(f"Error running {exe}: {e.stderr}")
        return None, None, None

def sweep_parameter(args):
    """Perform parameter sweep and generate plots."""
    # Create results directory if it doesn't exist
    os.makedirs(args.results_dir, exist_ok=True)
    
    # Generate H values for sweep
    H_values = np.arange(args.H_min, args.H_max + args.H_step, args.H_step)
    
    # Storage for results
    results = []
    
    # Perform sweep
    print(f"\nStarting parameter sweep:")
    print(f"H: {args.H_min} to {args.H_max} step {args.H_step}")
    print(f"C: {args.C}, Cc: {args.Cc}, N: {args.N}\n")
    
    total_runs = len(H_values)
    for i, H in enumerate(H_values, 1):
        print(f"Progress: [{i}/{total_runs}] Running H = {H:.3f}")
        
        # Create trace file path if tracing enabled
        trace_file = None
        if args.trace:
            trace_file = os.path.join(args.results_dir, f"trace_H{H:.3f}.csv")
        
        # Run simulation
        r, b, t = run_mc_slab(
            args.exe, args.C, args.Cc, H, args.N,
            seed=args.seed,
            trace_file=trace_file,
            trace_every=args.trace_every
        )
        
        if r is not None:
            results.append({
                'H': H,
                'reflected': r,
                'absorbed': b,
                'transmitted': t
            })
    
    # Save results to CSV
    csv_path = os.path.join(args.results_dir, "sweep_results.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['H', 'reflected', 'absorbed', 'transmitted'])
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResults saved to: {csv_path}")
    
    # Create plots
    results_array = np.array([(r['H'], r['reflected'], r['absorbed'], r['transmitted']) 
                            for r in results])
    H_vals = results_array[:, 0]
    r_vals = results_array[:, 1]
    b_vals = results_array[:, 2]
    t_vals = results_array[:, 3]
    
    # Plot fractions vs H
    plt.figure(figsize=(10, 6))
    
    # Plot lines with specific colors and labels
    plt.plot(H_vals, r_vals, '-', color='#1f77b4', label='Reflected (r/n)', linewidth=2)
    plt.plot(H_vals, b_vals, '-', color='#ff7f0e', label='Absorbed (b/n)', linewidth=2)
    plt.plot(H_vals, t_vals, '-', color='#2ca02c', label='Transmitted (t/n)', linewidth=2)
    
    # Set axis labels and title
    plt.xlabel('H (slab thickness)')
    plt.ylabel('Fraction')
    plt.title(f'Fractions vs H (C={args.C}, Cc={args.Cc}, N={args.N})')
    
    # Configure grid
    plt.grid(True, linestyle='-', alpha=0.2, color='gray')
    
    # Set axis limits
    plt.ylim(0, 0.9)
    plt.xlim(args.H_min, args.H_max)
    
    # Configure legend
    plt.legend(frameon=True)
    
    # Make plot clean and professional
    plt.tight_layout()
    
    plot_path = os.path.join(args.results_dir, "sweep_plot.png")
    plt.savefig(plot_path, dpi=args.dpi, bbox_inches='tight')
    print(f"Plot saved to: {plot_path}")
    
    if args.make_convergence_plots and args.trace:
        print("\nGenerating convergence plots...")
        for H in H_vals:
            trace_file = os.path.join(args.results_dir, f"trace_H{H:.3f}.csv")
            if os.path.exists(trace_file):
                # Read convergence data
                data = np.genfromtxt(trace_file, delimiter=',', skip_header=1)
                k = data[:, 0]  # particle count
                fracs = data[:, 4:]  # r_frac, b_frac, t_frac
                
                # Plot convergence
                plt.figure(figsize=(10, 6))
                plt.plot(k, fracs[:, 0], '-', color='#1f77b4', label='Reflected')    # Blue
                plt.plot(k, fracs[:, 1], '-', color='#ff7f0e', label='Absorbed')     # Orange
                plt.plot(k, fracs[:, 2], '-', color='#2ca02c', label='Transmitted')  # Green
                
                # Set axis labels and title
                plt.xlabel('Samples k')
                plt.ylabel('Running fraction')
                plt.title(f'Convergence (H={H}, C={args.C}, Cc={args.Cc}, N={args.N})')
                
                # Configure grid
                plt.grid(True, linestyle='-', alpha=0.2, color='gray')
                
                # Set y-axis limits
                plt.ylim(0.20, 0.50)
                
                # Configure legend
                plt.legend(frameon=True)
                
                # Make plot clean and professional
                plt.tight_layout()
                
                conv_plot_path = os.path.join(args.results_dir, f"convergence_H{H:.3f}.png")
                plt.savefig(conv_plot_path, dpi=args.dpi, bbox_inches='tight')
                plt.close()
        
        print(f"Convergence plots saved in: {args.results_dir}")

def main():
    parser = argparse.ArgumentParser(description="Sweep H for mc_slab and plot results.")
    parser.add_argument('--exe', default='./mc_slab', help='Path to mc_slab executable')
    parser.add_argument('--C', type=float, required=True, help='Total interaction coefficient')
    parser.add_argument('--Cc', type=float, required=True, help='Absorption coefficient')
    parser.add_argument('--H-min', type=float, required=True, help='Minimum H value')
    parser.add_argument('--H-max', type=float, required=True, help='Maximum H value')
    parser.add_argument('--H-step', type=float, required=True, help='H step size')
    parser.add_argument('--N', type=int, required=True, help='Number of particles')
    parser.add_argument('--seed', type=int, help='Random seed')
    parser.add_argument('--timeout', type=int, default=600, help='Timeout in seconds')
    parser.add_argument('--trace', action='store_true', help='Enable per-iteration tracing to CSV')
    parser.add_argument('--trace-every', type=int, default=1000, 
                        help='Record every m-th iteration')
    parser.add_argument('--make-convergence-plots', action='store_true',
                        help='When tracing, also render convergence plots per H')
    parser.add_argument('--results-dir', default='results',
                        help='Directory for output files')
    parser.add_argument('--dpi', type=int, default=300, help='DPI for output plots')
    parser.add_argument('--title', help='Optional title for plots')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.C <= 0:
        parser.error("C must be > 0")
    if args.Cc < 0 or args.Cc >= args.C:
        parser.error("Cc must be in [0, C)")
    if args.H_min <= 0:
        parser.error("H_min must be > 0")
    if args.H_max <= args.H_min:
        parser.error("H_max must be > H_min")
    if args.H_step <= 0:
        parser.error("H_step must be > 0")
    if args.N < 1:
        parser.error("N must be >= 1")
    
    # Run parameter sweep
    sweep_parameter(args)

if __name__ == "__main__":
    main()