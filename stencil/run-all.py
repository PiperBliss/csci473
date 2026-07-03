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
    print(f"Config: {ROWS}x{COLS} grid, {ITERS} iterations")
    print("Note: Performance testing will run after the main simulation")
    
    # --- File Names (all in current directory) ---
    INITIAL_FILE = f"initial.{ROWS}x{COLS}.dat"
    FINAL_FILE = f"final.{ROWS}x{COLS}x{ITERS}.dat"
    STACK_FILE = f"all.{ROWS}x{COLS}x{ITERS}.dat"
    MOVIE_FILE = f"stencil.{ROWS}x{COLS}x{ITERS}.mp4"

    # --- Executable Paths (all in current directory) ---
    MAKE_2D_EXE = "./make-2d"
    STENCIL_2D_EXE = "./pth-stencil-2d"  # Changed to pthread version
    
    # --- Python Script Paths (all in current directory) ---
    DISPLAY_PY = "./display_image.py"
    MAKE_MOVIE_PY = "./make-movie.py"
    PERFORMANCE_TEST_PY = "./performance_test.py"

    # Add thread count parameter
    NUM_THREADS = 4  # Default number of threads
    
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

    # --- Step 6: Run Performance Tests ---
    print("\n[Step 6/6] Running performance tests...")
    print("This may take a while as it tests multiple problem sizes and thread counts...")
    run_command(["python3", "performance_test.py"])

    print("\n===== All steps completed successfully! =====")
    print(f"Visualization outputs are in the current directory.")
    print(f"Performance test results and graphs are in the 'results' directory.")

if __name__ == "__main__":
    main()