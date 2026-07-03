#!/usr/bin/env python3
import subprocess
import os
import numpy as np
import sys
import argparse

def run_stencil(make_exe, exe_path, N, P, I, testing_dir, is_parallel=False):
    """Run stencil program and return output file paths"""
    initial_file = os.path.join(testing_dir, f"initial.{N}x{N}.dat")
    final_file = os.path.join(testing_dir, f"final.{N}x{N}x{I}.dat")
    stack_file = os.path.join(testing_dir, f"stack.{N}x{N}x{I}.dat")
    
    # Create testing directory if it doesn't exist
    os.makedirs(testing_dir, exist_ok=True)
    
    # Create initial conditions
    subprocess.run([make_exe, str(N), str(N), initial_file], 
                  check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Run stencil program
    if is_parallel:
        cmd = [exe_path, "-n", str(I), "-I", initial_file, "-o", final_file, "-s", stack_file, "-t", str(P)]
    else:
        cmd = [exe_path, str(I), initial_file, final_file, stack_file]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"Error running stencil: {e}")
        return None, None
    
    return final_file, stack_file

def read_data_file(filename):
    """Read binary data file and return as numpy array"""
    with open(filename, 'rb') as f:
        # Read dimensions
        rows = int.from_bytes(f.read(4), byteorder='little')
        cols = int.from_bytes(f.read(4), byteorder='little')
        
        # Read data
        data = np.fromfile(f, dtype=np.float64)
        
        # Check if this is a stack file by looking at file basename
        if os.path.basename(filename).startswith('stack'):
            # Stack file has multiple frames
            frames = len(data) // (rows * cols)
            return data.reshape((frames, rows, cols))
        else:
            # Final or initial file
            return data.reshape((rows, cols))

def compare_results(serial_file, parallel_file, tolerance=0.0, return_diff=True):
    """Compare two result files and return max difference if return_diff=True"""
    serial_data = read_data_file(serial_file)
    parallel_data = read_data_file(parallel_file)
    
    if serial_data.shape != parallel_data.shape:
        print(f"Shape mismatch: Serial {serial_data.shape} vs Parallel {parallel_data.shape}")
        return float('inf') if return_diff else False
    
    max_diff = np.max(np.abs(serial_data - parallel_data))
    if return_diff:
        return max_diff
    else:
        return max_diff <= tolerance

def main():
    parser = argparse.ArgumentParser(description="Test serial vs parallel stencil implementations")
    parser.add_argument("--testing-dir", help="Directory for test output")
    parser.add_argument("--make", default="./make-2d", help="Path to make-2d executable")
    parser.add_argument("--serial", default="./stencil-2d", help="Path to serial executable")
    parser.add_argument("--pth", default="./pth-stencil-2d", help="Path to parallel executable")
    parser.add_argument("--N1", type=int, required=True, help="Starting size")
    parser.add_argument("--N2", type=int, required=True, help="Ending size")
    parser.add_argument("--Nstep", type=int, required=True, help="Size step")
    parser.add_argument("--I1", type=int, required=True, help="Starting iterations")
    parser.add_argument("--I2", type=int, required=True, help="Ending iterations")
    parser.add_argument("--Istep", type=int, required=True, help="Iteration step")
    parser.add_argument("--T1", type=int, required=True, help="Starting threads")
    parser.add_argument("--T2", type=int, required=True, help="Ending threads")
    parser.add_argument("--Tstep", type=int, required=True, help="Thread step")
    parser.add_argument("--tol", type=float, default=0.0, help="Tolerance for comparison")
    parser.add_argument("--keep", action="store_true", help="Keep output files")
    
    args = parser.parse_args()
    
    # Test each combination
    total_tests = 0
    failed_tests = 0
    
    # Create testing directory if specified
    testing_dir = args.testing_dir if args.testing_dir else "."
    
    for N in range(args.N1, args.N2 + 1, args.Nstep):
        for I in range(args.I1, args.I2 + 1, args.Istep):
            
            serial_final, serial_stack = run_stencil(args.make, args.serial, N, 1, I, testing_dir, False)
            if not serial_final or not serial_stack:
                print("Serial run failed!")
                failed_tests += 1
                continue
            
            # Test with different thread counts
            for P in range(args.T1, args.T2 + 1, args.Tstep):
                total_tests += 2  # One for final, one for stack
                
                parallel_final, parallel_stack = run_stencil(args.make, args.pth, N, P, I, testing_dir, True)
                if not parallel_final or not parallel_stack:
                    print("Failed to run parallel version!")
                    failed_tests += 2
                    continue
                
                # Compare results and format output
                final_diff = compare_results(serial_final, parallel_final, return_diff=True)
                stack_diff = compare_results(serial_stack, parallel_stack, return_diff=True)
                
                print(f"[N={N:3d} I={I:3d} T={P:2d}] ", end='')
                print(f"FINAL={'OK' if final_diff < 1e-10 else 'FAIL'} (max|Δ|={final_diff:.3e}); ", end='')
                print(f"STACK={'OK' if stack_diff < 1e-10 else 'FAIL'} (max|Δ|={stack_diff:.3e})")
                
                # Clean up files if not keeping them
                if not args.keep:
                    for f in [parallel_final, parallel_stack]:
                        try:
                            os.remove(f)
                        except:
                            pass
            
            # Clean up serial files if not keeping them
            if not args.keep:
                for f in [serial_final, serial_stack]:
                    try:
                        os.remove(f)
                        initial_file = os.path.join(testing_dir, f"initial.{N}x{N}.dat")
                        os.remove(initial_file)
                    except:
                        pass
    
    if failed_tests > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()