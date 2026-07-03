import subprocess
import os
import sys
import argparse

# --- Helper Function ---
def run_command(cmd_list):
    """Runs a shell command and exits if it fails."""
    print(f"\n--- Running: {' '.join(cmd_list)} ---")
    try:
        subprocess.run(cmd_list, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with return code {e.returncode}")
        print(f"Command: {' '.join(e.cmd)}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: Command not found. Is '{e.filename}' in your PATH or built correctly?")
        sys.exit(1)

# --- Main Execution ---
def main():
    # --- 1. Set up Argument Parser ---
    parser = argparse.ArgumentParser(description="Builds and runs the stencil project.")
    
    parser.add_argument('--rows', type=int, default=100,
                       help='Number of rows for the grid (default: 100)')
    parser.add_argument('--cols', type=int, default=100,
                       help='Number of columns for the grid (default: 100)')
    parser.add_argument('--iters', type=int, default=500,
                       help='Number of iterations for the stencil (default: 500)')
    parser.add_argument('--threads', type=int, default=4,
                       help='Number of threads for parallel execution (default: 4)')
    
    args = parser.parse_args()

    # --- 2. Use Parsed Arguments ---
    ROWS = args.rows
    COLS = args.cols
    ITERS = args.iters
    NUM_THREADS = args.threads

    print(f"===== Stencil Project Runner =====")
    print(f"Config: {ROWS}x{COLS} grid, {ITERS} iterations, {NUM_THREADS} threads")
    print("Note: Performance testing will run after the main simulation")
    
    # --- File Names (all in current directory) ---
    INITIAL_FILE = f"initial.{ROWS}x{COLS}.dat"
    FINAL_FILE = f"final.{ROWS}x{COLS}x{ITERS}.dat"
    STACK_FILE = f"all.{ROWS}x{COLS}x{ITERS}.dat"
    MOVIE_FILE = f"stencil.{ROWS}x{COLS}x{ITERS}.mp4"

    # --- Executable Paths (all in current directory) ---
    MAKE_2D_EXE = "./make-2d"
    # Use the pthreads version for the main run
    STENCIL_2D_EXE = "./pth-stencil-2d" 
    
    # --- Python Script Paths (all in current directory) ---
    DISPLAY_PY = "./display_image.py"
    MAKE_MOVIE_PY = "./make-movie.py"
    # This is the script the assignment calls 'bench_stencil2d_pthreads.py'
    PERFORMANCE_TEST_PY = "./performance_test.py" 

    # --- Step 1: Build C programs ---
    print("\n[Step 1/5] Building C programs...")
    run_command(["make", "clean"])
    run_command(["make", "all"])
    
    # --- Step 2: Create initial conditions ---
    print(f"\n[Step 2/5] Creating initial file: {INITIAL_FILE}")
    run_command([MAKE_2D_EXE, str(ROWS), str(COLS), INITIAL_FILE])

    # --- Step 3: Run stencil simulation ---
    print(f"\n[Step 3/5] Running parallel stencil simulation with {NUM_THREADS} threads for {ITERS} iterations...")
    run_command([STENCIL_2D_EXE, "-n", str(ITERS), "-I", INITIAL_FILE, 
                "-o", FINAL_FILE, "-s", STACK_FILE, "-t", str(NUM_THREADS)])

    # --- Step 4: Visualize initial and final states ---
    print("\n[Step 4/5] Generating PNGs for initial and final states...")
    run_command(["python3", DISPLAY_PY, INITIAL_FILE])
    run_command(["python3", DISPLAY_PY, FINAL_FILE])

    # --- Step 5: Generate movie ---
    print(f"\n[Step 5/6] Generating movie: {MOVIE_FILE}")
    run_command(["python3", MAKE_MOVIE_PY, STACK_FILE, MOVIE_FILE])

    # --- Step 6: Run Performance Tests (MODIFIED) ---
    print("\n[Step 6/6] Running performance tests as specified in assignment...")
    print("This may take a while as it tests multiple problem sizes and thread counts...")
    
    # This command is taken directly from your assignment brief 
    # It assumes 'performance_test.py' is your name for 'bench_stencil2d_pthreads.py'
    # and that it accepts these command-line arguments.
    run_command([
        "python3", PERFORMANCE_TEST_PY,
        "--make_exe", MAKE_2D_EXE,
        "--pth_exe", STENCIL_2D_EXE,  # Use the executable name from Step 3
        "--N1", "128",
        "--N2", "256",
        "--num_Ns", "3",
        "--P_start", "1",
        "--P_step", "1",
        "--P_max", "12",
        "--I1", "10",
        "--I2", "200",
        "--Istep", "20",
        "--warmup", "1",
        "--trials", "4",
        "--timeout_sec", "600",
        "--eff_range", "0.29 0.05",
        "--results-dir", "./perf_results", # Note: assignment has ./perf_results
        "--label", "bench_run1"
    ])

    print("\n===== All steps completed successfully! =====")
    print(f"Main simulation outputs are in the current directory.")
    print(f"Performance test results and graphs are in the 'perf_results' directory.")

if __name__ == "__main__":
    main()