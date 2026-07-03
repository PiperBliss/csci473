# Makefile for Monte Carlo Neutron Transport Simulation
# Handles C program, sweep script, and animation

# Compiler and flags
CC = gcc
CFLAGS = -std=c99 -O2 -Wall -Wextra -pedantic
LDFLAGS = -lm

# Python interpreter
PYTHON = python3

# Executables
TARGET = mc_slab
SWEEP_SCRIPT = sweep_mc_slab.py
MOVIE_SCRIPT = mc_slab_movie.py

# Default animation parameters
THICKNESS = 1.0
SIGMA_T = 0.5
C_RATIO = 0.99
N_PARTICLES = 600
FRAMES = 300
FPS = 30
DPI = 200
FIG_WIDTH = 10
FIG_HEIGHT = 5
OUTPUT = movie.mp4

# Directories
RESULTS_DIR = results

# Default parameters for testing
TEST_C = 1.0
TEST_CC = 0.5
TEST_H_MIN = 0.1
TEST_H_MAX = 2.0
TEST_H_STEP = 0.1
TEST_N = 10000

# Default target
all: $(TARGET) mc_slab_pthreads mc_slab_mpi dirs

# Rule to build the C executable
$(TARGET): $(TARGET).c
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

# Rule to build the pthreads version
mc_slab_pthreads: mc_slab_pthreads.c
	$(CC) $(CFLAGS) $< -o $@ -pthread $(LDFLAGS)

# Rule to build the MPI version
mc_slab_mpi: mc_slab_mpi.c
	mpicc -std=c99 -O2 -Wall -Wextra -pedantic $< -o $@ $(LDFLAGS)

# Create necessary directories
dirs:
	mkdir -p $(RESULTS_DIR) $(PLOTS_DIR)

# Make the Python script executable
chmod:
	chmod +x $(SWEEP_SCRIPT)

# Run a test sweep
test: all chmod
	./$(SWEEP_SCRIPT) \
		--C $(TEST_C) \
		--Cc $(TEST_CC) \
		--H-min $(TEST_H_MIN) \
		--H-max $(TEST_H_MAX) \
		--H-step $(TEST_H_STEP) \
		--N $(TEST_N) \
		--results-dir $(RESULTS_DIR)

# Run a test with convergence plotting
test-convergence: all chmod
	./$(SWEEP_SCRIPT) \
		--C $(TEST_C) \
		--Cc $(TEST_CC) \
		--H-min $(TEST_H_MIN) \
		--H-max $(TEST_H_MAX) \
		--H-step $(TEST_H_STEP) \
		--N $(TEST_N) \
		--trace \
		--trace-every 1000 \
		--make-convergence-plots \
		--results-dir $(RESULTS_DIR)

# Clean up build files and results
clean:
	rm -f $(TARGET)
	rm -rf $(RESULTS_DIR)/* $(PLOTS_DIR)/*

# Deep clean - removes directories too
distclean: clean
	rm -rf $(RESULTS_DIR) $(PLOTS_DIR)

# Install python dependencies (if needed)
deps:
	$(PYTHON) -m pip install --user numpy matplotlib

# Animation target
movie: all
	$(PYTHON) $(MOVIE_SCRIPT) \
		--thickness $(THICKNESS) \
		--Sigma_t $(SIGMA_T) \
		--c $(C_RATIO) \
		--N $(N_PARTICLES) \
		--frames $(FRAMES) \
		--fps $(FPS) \
		--dpi $(DPI) \
		--fig-width $(FIG_WIDTH) \
		--fig-height $(FIG_HEIGHT) \
		--out $(OUTPUT)

# Quick test animation
test-movie: all
	$(PYTHON) $(MOVIE_SCRIPT) \
		--thickness 1.0 \
		--Sigma_t 0.5 \
		--c 0.99 \
		--N 100 \
		--frames 100 \
		--fps 30 \
		--dpi 150 \
		--out test_movie.mp4

# Help target
help:
	@echo "Available targets:"
	@echo "  all              : Build executable and create directories"
	@echo "  test            : Run a basic parameter sweep"
	@echo "  test-convergence: Run sweep with convergence plotting"
	@echo "  movie           : Generate full animation (use parameters in Makefile)"
	@echo "  test-movie      : Generate quick test animation"
	@echo "  clean           : Remove executable and result files"
	@echo "  distclean       : Remove executable, results, and directories"
	@echo "  deps            : Install Python dependencies"
	@echo "  chmod           : Make Python scripts executable"
	@echo "  help            : Show this help message"

.PHONY: all dirs clean distclean deps help test test-convergence chmod movie test-movie