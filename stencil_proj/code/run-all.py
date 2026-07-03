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
    
    args = parser.parse_args()

    # --- 2. Use Parsed Arguments ---
    ROWS = args.rows
    COLS = args.cols
    ITERS = args.iters

    print(f"===== Stencil Project Runner =====")
    print(f"Config: {ROWS}x{COLS} grid, {ITERS} iterations")
    
    # --- File Names (all in current directory) ---
    INITIAL_FILE = f"initial.{ROWS}x{COLS}.dat"
    FINAL_FILE = f"final.{ROWS}x{COLS}x{ITERS}.dat"
    STACK_FILE = f"all.{ROWS}x{COLS}x{ITERS}.dat"
    MOVIE_FILE = f"stencil.{ROWS}x{COLS}x{ITERS}.mp4"

    # --- Executable Paths (all in current directory) ---
    MAKE_2D_EXE = "./make-2d"
    STENCIL_2D_EXE = "./stencil-2d"

    # --- Python Script Paths (all in current directory) ---
    DISPLAY_PY = "./display_image.py"
    MAKE_MOVIE_PY = "./make-movie.py"

    # --- Step 1: Build C programs ---
    print("\n[Step 1/5] Building C programs...")
    run_command(["make", "clean"])
    run_command(["make", "all"])
    
    # --- Step 2: Create initial conditions ---
    print(f"\n[Step 2/5] Creating initial file: {INITIAL_FILE}")
    run_command([MAKE_2D_EXE, str(ROWS), str(COLS), INITIAL_FILE])

    # --- Step 3: Run stencil simulation ---
    print(f"\n[Step 3/5] Running stencil simulation for {ITERS} iterations...")
    run_command([STENCIL_2D_EXE, str(ITERS), INITIAL_FILE, FINAL_FILE, STACK_FILE])

    # --- Step 4: Visualize initial and final states ---
    print("\n[Step 4/5] Generating PNGs for initial and final states...")
    run_command(["python3", DISPLAY_PY, INITIAL_FILE])
    run_command(["python3", DISPLAY_PY, FINAL_FILE])

    # --- Step 5: Generate movie ---
    print(f"\n[Step 5/5] Generating movie: {MOVIE_FILE}")
    run_command(["python3", MAKE_MOVIE_PY, STACK_FILE, MOVIE_FILE])

    print("\n===== All steps completed successfully! =====")
    print(f"All output files are in the current directory.")

if __name__ == "__main__":
    main()