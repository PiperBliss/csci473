MC_SLAB: Monte Carlo Slab — mcnt

This directory implements a serial Monte Carlo neutron-transport simulator (`mc_slab`),
helper scripts for parameter sweeps (`sweep_mc_slab.py`), and an animation/visualization
utility (`mc_slab_movie.py`). The layout and usage notes below follow the style of the
Assignment7 README format you provided.

Project Structure
-----------------
mcnt/
├── mc_slab                # compiled C executable (built from mc_slab.c)
├── mc_slab.c              # Serial Monte Carlo implementation (C)
├── sweep_mc_slab.py       # Python script to sweep H and plot fractions
├── mc_slab_movie.py       # Python script to render/save particle animation
├── Makefile               # build and convenience targets
├── README.md              # human-friendly README (markdown)
├── README.TXT             # this file (assignment-style README)
└── results/               # default output directory for sweep and traces

----------------------------------------------------------------------------------------------
Program Implementations:

Serial Version (mc_slab.c)
    - Pure C implementation of the Monte Carlo neutron slab problem.
    - Simulates n particle histories, sampling exponential path lengths and
      deciding absorption vs scattering using a probability derived from input
      coefficients.
    - Output: prints three space-separated final fractions (r_frac b_frac t_frac)
      with 8 decimal places.

Python Sweep (sweep_mc_slab.py)
    - Wrapper script that calls `mc_slab` for a range of slab thickness values H.
    - Collects reflected/absorbed/transmitted fractions and writes `sweep_results.csv`.
    - Produces a plot `sweep_plot.png`. Optionally produces per-H trace CSVs and
      convergence plots when run with `--trace` and `--make-convergence-plots`.

Animation (mc_slab_movie.py)
    - Python script that simulates particle paths for visualization using Matplotlib
      FuncAnimation and can save to MP4 (via ffmpeg) or GIF (Pillow fallback).
    - Provides HUD counters for Reflected / Absorbed / Transmitted and visual
      styling options.

----------------------------------------------------------------------------------------------
Algorithm:
    - Each particle starts at x=0 with a direction sampled from an initial angular
      distribution (scripted/specified in the animation; `mc_slab.c` uses a sampling
      consistent with the model in the course notes).
    - Distances between events are sampled from an exponential with mean 1/C (C = Σt).
    - After each step, the particle position is updated; if x < 0 it is counted as
      Reflected; if x >= H it is Transmitted.
    - If the particle remains inside the slab, the event is absorption with
      probability (Cc / C) or scattering otherwise. Scattering resets direction.
    - Repeat for n particle histories and accumulate counts r, b, t.

----------------------------------------------------------------------------------------------
Compilation:

Use the provided Makefile to build the C executable and create directories:

```bash
cd mcnt
make
```

The Makefile compiles `mc_slab.c` into `./mc_slab`. It also provides targets:
- `make deps` to install Python deps (numpy, matplotlib) in user space
- `make test` to run a small sweep (see Makefile)
- `make movie` / `make test-movie` to run the animation target

----------------------------------------------------------------------------------------------
Usages:

mc_slab (C executable)
    ./mc_slab C Cc H n [--seed S] [--trace-file path] [--trace-every m]

    - C   : total interaction coefficient (Σt) — must be > 0
    - Cc  : absorbing component (Σa) — must satisfy 0 ≤ Cc < C
    - H   : slab thickness (H > 0)
    - n   : number of particle histories (n ≥ 1)
    - --seed S          : optional RNG seed
    - --trace-file path : optional CSV path for trace/convergence data
    - --trace-every m   : when tracing, record every m-th particle (m > 0)

    Example:
    ./mc_slab 0.5 0.005 1.0 10000
    # prints: r_frac b_frac t_frac (space-separated, 8 decimal places)

sweep_mc_slab.py (Python)
    python3 sweep_mc_slab.py \
      --exe ./mc_slab \
      --C 0.5 --Cc 0.005 \
      --H-min 0.1 --H-max 2.0 --H-step 0.1 \
      --N 10000 \
      --results-dir results/sweep_test

    Options of interest:
    - --trace (enable per-iteration trace CSVs)
    - --trace-every (integer, record every m-th iteration)
    - --make-convergence-plots (requires trace files)
    - --results-dir (output directory)

mc_slab_movie.py (Python animation)
    python3 mc_slab_movie.py \
      --thickness 1.0 --Sigma_t 0.5 --c 0.99 \
      --N 600 --frames 300 --fps 30 --out movie.mp4

    Notes:
    - The script attempts to use ffmpeg to save MP4. If ffmpeg encoding fails it
      will try alternate codecs and fall back to writing a GIF (Pillow) if available.
    - Use `--force-outcomes REF ABS TRN` to override HUD counters when you want
      the printed counts to match a target presentation.

----------------------------------------------------------------------------------------------
Examples:

Quick sweep test (fast):
```bash
python3 sweep_mc_slab.py --C 0.5 --Cc 0.005 --H-min 0.1 --H-max 1.0 --H-step 0.1 --N 1000 --results-dir results/test_quick
```

Full sweep with traces and convergence plots:
```bash
python3 sweep_mc_slab.py --C 0.5 --Cc 0.005 --H-min 0.2 --H-max 2.0 --H-step 0.2 --N 20000 --trace --trace-every 100 --make-convergence-plots --results-dir results/sweep_with_trace
```

Quick animation test:
```bash
python3 mc_slab_movie.py --thickness 1.0 --Sigma_t 0.5 --c 0.99 --N 100 --frames 100 --fps 15 --out test_movie.mp4
```

----------------------------------------------------------------------------------------------
Recorded runs / reproduction commands
-----------------------------------
Below are the exact commands used to generate the movies and sweep results referenced
in the project. You can copy/paste these to reproduce the outputs.

1) Base movie (movie.mp4)

```bash
python3 mc_slab_movie.py \
  --thickness 1.0 --Sigma_t 0.5 --c 0.99 \
  --N 300 --frames 300 --fps 30 --dpi 100 \
  --fig-width 10 --fig-height 5 --out movie.mp4
```

2) Change in H (thicker slab)

```bash
python3 mc_slab_movie.py \
  --thickness 3.0 --Sigma_t 0.5 --c 0.99 \
  --N 300 --frames 300 --fps 30 --dpi 100 \
  --fig-width 10 --fig-height 5 --out movie.mp4
```

3) Change in c (lower scattering ratio)

```bash
python3 mc_slab_movie.py \
  --thickness 1.0 --Sigma_t 0.5 --c 0.80 \
  --N 300 --frames 300 --fps 30 --dpi 100 \
  --fig-width 10 --fig-height 5 --out movie.mp4
```

4) Change in Sigma_t (larger total cross-section)

```bash
python3 mc_slab_movie.py \
  --thickness 1.0 --Sigma_t 10 --c 0.80 \
  --N 300 --frames 300 --fps 30 --dpi 100 \
  --fig-width 10 --fig-height 5 --out movie.mp4
```

5) Example single `mc_slab` output (to show expected stdout format)

Run:
```bash
./mc_slab 0.5 0.1 5.0 1000
```

Output (example):
```text
0.28600000 0.47100000 0.24300000
```

6) Sweep command used to produce sweep results (large run)

```bash
python3 sweep_mc_slab.py \
  --exe ./mc_slab \
  --C 0.5 --Cc 0.1 \
  --H-min 0.5 --H-max 5.0 --H-step 0.25 \
  --N 100000 --seed 42 \
  --trace --trace-every 100 \
  --make-convergence-plots
```

Notes:
- The `mc_slab` output (three space-separated fractions) is what `sweep_mc_slab.py`
  expects and parses. The `--trace` option writes `trace_H{H:.3f}.csv` files which
  are used to create convergence plots.

----------------------------------------------------------------------------------------------
Visualization
-------------
- Sweep results are saved to `--results-dir/sweep_results.csv` and plotted to `sweep_plot.png`.
- When tracing is enabled, per-H trace CSVs are written as `trace_H{H:.3f}.csv` and
  convergence plots are saved as `convergence_H{H:.3f}.png` (if requested).
- The animation script `mc_slab_movie.py` shows particle paths and HUD counters; saved
  outputs are MP4 (or GIF fallback).

----------------------------------------------------------------------------------------------
Running Experiments
-------------------
- Use `sweep_mc_slab.py` to run parameter sweeps over H. For reproducible runs, pass
  `--seed` to both `sweep_mc_slab.py` (which forwards it to `mc_slab`) and to the
  `mc_slab` invocation.
- The included `Makefile` has convenience targets `make test` and `make test-convergence`.
- For large `N` or many H values, consider running the sweep on a compute node or
  splitting the H range across multiple jobs and then combining the resulting CSVs..

Consistency check and benchmarking commands
------------------------------------------
Two helper scripts are provided to validate correctness between serial and
parallel versions and to run performance benchmarks and generate plots.

1) Consistency check (serial vs pthreads)

Script: `check_mc_slab_consistency.py`

Purpose: Run the serial `mc_slab` and the pthreads `mc_slab_pthreads` executables
over a set of problem sizes and thread counts and verify their reported
reflected/absorbed/transmitted fractions match within an absolute tolerance.

Example:
```bash
cd mcnt
python3 check_mc_slab_consistency.py \
  --serial ./mc_slab \
  --parallel ./mc_slab_pthreads \
  --C 1.0 --Cc 0.3 --H 10.0 \
  --seed 12345 \
  --n_start 100000 --n_max 6400000 \
  --Ps 1,2,4,8,16 \
  --trials 5 \
  --abs_threshold 0.005 \
  --results_dir consistency_results_mc
```

- `--n_start/--n_max` generates a geometric sequence of `n` (doubling) up to `n_max`.
- `--Ps` specifies thread counts (comma-separated). `--trials` runs multiple seeds per (n,P).
- The script prints progress lines in the form: `[ idx/total] n= 100000 P=  1 - trials=5`.
- Exit code `0` indicates all comparisons were within the threshold.

2) Benchmarking and plotting

Script: `bench_mc_slab_pthreads.py`

Purpose: Run timing experiments for pthreads and MPI implementations, compute
speedup and efficiency, produce an isoefficiency plot, and save comparison plots.

Example:
```bash
cd mcnt
python3 bench_mc_slab_pthreads.py \
  --exe ./mc_slab_pthreads \
  --mpi-exe ./mc_slab_mpi \
  --mpirun "mpirun -np {P}" \
  --C 0.5 --Cc 0.1 --H 5.0 --seed 12345 \
  --n_start 100000 --n_max 66400000 \
  --P_start 1 --P_step 1 --P_max 12 \
  --trials 6 --warmup 1 \
  --eff_targets 0.5,0.7,0.8 \
  --results-dir results/perf
```

Output locations (examples):
- Raw timing CSV: `results/perf/bench_pthreads_raw.csv`
- Summary CSV: `results/perf/bench_pthreads_summary.csv`
- Pthreads plots: `results/perf/pthreads/` (timing/speedup/efficiency/isoeff)
- MPI plots: `results/perf/mpi/`
- Comparison plots: `results/perf/comparison/`

Notes:
- Ensure the C executables (`mc_slab`, `mc_slab_pthreads`, `mc_slab_mpi`) are compiled
  (run `make` in `mcnt/`) before benchmarking.
- The isoefficiency plot uses a log y-scale to display minimal required `N` over wide ranges.

