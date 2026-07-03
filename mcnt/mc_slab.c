/**
 * mc_slab.c
 *
 * Serial Monte Carlo neutron transport simulation based on the
 * pseudocode from "Monte Carlo Neutron Transport: Overview and Serial Implementation"
 * by Dr. William Jones (CSCI 473, Fall 2025).
 *
 * Implements the algorithm from Page 16 .
 * Accepts command-line arguments as specified on Page 17[cite: 290].
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdbool.h>
#include <time.h>

// For M_PI, which isn't in strict c99
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/**
 * @brief Prints the usage instructions for the program and exits.
 * [cite: 290-297]
 */
void print_usage() {
    fprintf(stderr, "Usage: ./mc_slab C Cc H n [--seed S] [--trace-file path] [--trace-every m]\n");
    fprintf(stderr, "  C > 0         (total interaction coeff) [cite: 291]\n");
    fprintf(stderr, "  Cc in [0,C)   (absorbing component) [cite: 293]\n");
    fprintf(stderr, "  H > 0         (slab thickness) [cite: 294]\n");
    fprintf(stderr, "  n >= 1        (number of particles) [cite: 296]\n");
    fprintf(stderr, "  --seed S      (optional: random seed) [cite: 335]\n");
    fprintf(stderr, "  --trace-file  (optional: path to CSV for convergence) [cite: 290, 341]\n");
    fprintf(stderr, "  --trace-every (optional: record every m-th particle) [cite: 290, 343]\n");
    exit(EXIT_FAILURE);
}

/**
 * @brief Generates a uniform random number in [0, 1).
 * [cite: 38]
 */
double rand_uniform() {
    return (double)rand() / ((double)RAND_MAX + 1.0);
}


int main(int argc, char *argv[]) {
    // --- 1. Parameter Initialization ---
    double C, Cc, H;
    long n;
    
    // Optional parameter defaults
    unsigned int seed = time(NULL);
    char* trace_file_path = NULL;
    long trace_every = 0;
    FILE* trace_f = NULL;

    // --- 2. Argument Parsing ---
    if (argc < 5) {
        print_usage();
    }

    C = atof(argv[1]);
    Cc = atof(argv[2]);
    H = atof(argv[3]);
    n = atol(argv[4]);

    // Parse optional arguments
    for (int i = 5; i < argc; i++) {
        if (strcmp(argv[i], "--seed") == 0) {
            if (i + 1 < argc) {
                seed = (unsigned int)atoi(argv[++i]);
            } else {
                print_usage();
            }
        } else if (strcmp(argv[i], "--trace-file") == 0) {
            if (i + 1 < argc) {
                trace_file_path = argv[++i];
            } else {
                print_usage();
            }
        } else if (strcmp(argv[i], "--trace-every") == 0) {
            if (i + 1 < argc) {
                trace_every = atol(argv[++i]);
            } else {
                print_usage();
            }
        } else {
            fprintf(stderr, "Error: Unknown argument '%s'\n", argv[i]);
            print_usage();
        }
    }

    // --- 3. Input Validation ---
    if (C <= 0) { // [cite: 291]
        fprintf(stderr, "Error: C must be > 0\n");
        exit(EXIT_FAILURE);
    }
    if (Cc < 0 || Cc >= C) { // [cite: 293]
        fprintf(stderr, "Error: Cc must be in [0, C)\n");
        exit(EXIT_FAILURE);
    }
    if (H <= 0) { // [cite: 294]
        fprintf(stderr, "Error: H must be > 0\n");
        exit(EXIT_FAILURE);
    }
    if (n < 1) { // [cite: 296]
        fprintf(stderr, "Error: n must be >= 1\n");
        exit(EXIT_FAILURE);
    }
    if (trace_file_path && trace_every <= 0) {
        fprintf(stderr, "Error: --trace-every must be > 0 when using --trace-file\n");
        exit(EXIT_FAILURE);
    }
    
    // --- 4. Simulation Setup ---
    srand(seed); // Seed the random number generator
    
    long r = 0, b = 0, t = 0; // [cite: 260] (reflected, absorbed, transmitted counts)
    double prob_absorb = Cc / C; // [cite: 274]

    if (trace_file_path) {
        trace_f = fopen(trace_file_path, "w");
        if (trace_f == NULL) {
            fprintf(stderr, "Error: Could not open trace file '%s'\n", trace_file_path);
            exit(EXIT_FAILURE);
        }
        // Write CSV header for convergence plots [cite: 344, 499]
        fprintf(trace_f, "k,r,b,t,r_frac,b_frac,t_frac\n");
    }

    // --- 5. Main Simulation Loop ---
    // [cite: 261]
    for (long i = 1; i <= n; i++) {
        double d = 0;       // [cite: 262] (direction)
        double x = 0;       // [cite: 263] (x-position)
        bool a = true;      // [cite: 264] (alive flag)

        // [cite: 265]
        while (a) {
            // Get distance L
            // [cite: 266]
            double u_dist = rand_uniform();
            // Avoid log(0) which is -infinity.
            if (u_dist == 0.0) {
                u_dist = 1.0e-10; 
            }
            double L = -(1.0 / C) * log(u_dist);

            // Update position
            // [cite: 267]
            x = x + L * cos(d);

            // Check for event
            if (x < 0) { // Reflected [cite: 268]
                r++;     // [cite: 269]
                a = false; // [cite: 270]
            } else if (x >= H) { // Transmitted [cite: 271]
                t++;         // [cite: 272]
                a = false;     // [cite: 273]
            } else {
                // Still in slab, check for absorption vs. scattering
                double u_event = rand_uniform();
                if (u_event < prob_absorb) { // Absorbed [cite: 274]
                    b++;     // [cite: 275]
                    a = false; // [cite: 276]
                } else { // Scattered [cite: 277]
                    double u_dir = rand_uniform();
                    d = u_dir * M_PI; // [cite: 278] (New direction 0 to pi)
                }
            }
        } // end while(a)

        // Record trace data if specified [cite: 354]
        if (trace_f && (i % trace_every == 0)) {
            fprintf(trace_f, "%ld,%ld,%ld,%ld,%.8f,%.8f,%.8f\n",
                    i, r, b, t,
                    (double)r / i, (double)b / i, (double)t / i);
        }
    } // end for(i)

    // --- 6. Final Output ---
    if (trace_f) {
        fclose(trace_f);
    }

    // Print final fractions, space-separated, 8 decimal places
    // [cite: 282, 302]
    printf("%.8f %.8f %.8f\n", (double)r / n, (double)b / n, (double)t / n);

    return EXIT_SUCCESS;
}