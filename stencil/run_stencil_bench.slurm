#!/bin/bash

#SBATCH --job-name="hello_openmp"
#SBATCH --output="/scratch/.%j.%N.out"
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=249000M
#SBATCH --account=<<project*>>
#SBATCH --export=ALL
#SBATCH -t 01:30:00

-----------------------------------------------------

#SBATCH --job-name=stencil_bench      # Job name
#SBATCH --nodes=1                     # Run on 1 node
#SBATCH --ntasks=1                    # Run a single task
#SBATCH --cpus-per-task=16           # Request up to 16 CPU cores (for testing up to 12 threads)
#SBATCH --time=02:00:00              # Time limit hrs:min:sec
#SBATCH --output=stencil_%j.log      # Standard output log
#SBATCH --error=stencil_%j.err       # Standard error log
#SBATCH --mail-type=END,FAIL         # Mail events (NONE, BEGIN, END, FAIL, ALL)
#SBATCH --mail-user=your.email@msu.edu   # Where to send mail

# Load any necessary modules (adjust as needed for your cluster)
module purge
module load gcc/12.2.0
module load python/3.11.3
module load py-matplotlib/3.4.3/yi6zmvu

# Print some debug information
echo "Starting job on node: $(hostname)"
echo "Number of CPU cores allocated: $SLURM_CPUS_PER_TASK"
echo "Current working directory: $(pwd)"

# Compile the code
make clean
make all

# Create results directory if it doesn't exist
mkdir -p perf_results

# Run the benchmark
python bench_stencil2d_pthreads.py \
    --make_exe ./make-2d \
    --pth_exe ./pth-stencil-2d \
    --N1 128 \
    --N2 256 \
    --num_Ns 3 \
    --P_start 1 \
    --P_step 1 \
    --P_max 12 \
    --I1 10 \
    --I2 200 \
    --Istep 20 \
    --warmup 1 \
    --trials 4 \
    --timeout_sec 600 \
    --eff_range "0.29 0.05" \
    --results-dir ./perf_results \
    --label bench_run1

# Print completion message
echo "Job completed at: $(date)"