/**
 * mc_slab_pthreads.c
 *
 * Pthreads-parallel Monte Carlo slab simulator. Splits the n particle histories
 * across T worker threads. Each thread uses a thread-local RNG (rand_r) and
 * updates shared counters (r, b, t) under a mutex. Optional trace output is
 * supported: when --trace-file and --trace-every are provided threads will
 * append convergence lines to the CSV as the global processed count crosses
 * multiples of trace_every.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdbool.h>
#include <time.h>
#include <pthread.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

typedef struct {
    double C;
    double Cc;
    double H;
    long n_local;      // number of particles for this thread
    unsigned int seed; // thread-local seed
    long start_index;  // global starting index (1-based)
    int tid;
} thread_args_t;

// Shared counters
static long g_r = 0;
static long g_b = 0;
static long g_t = 0;
static long g_processed = 0; // total completed particles

static pthread_mutex_t counts_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t file_mutex = PTHREAD_MUTEX_INITIALIZER;

static FILE* trace_f = NULL;
static long trace_every = 0;

double rand_uniform_r(unsigned int *seedp) {
    return (double)rand_r(seedp) / ((double)RAND_MAX + 1.0);
}

void print_usage() {
    fprintf(stderr, "Usage: ./mc_slab_pthreads C Cc H n T [--seed S] [--trace-file path] [--trace-every m]\n");
    fprintf(stderr, "  C > 0         (total interaction coeff)\n");
    fprintf(stderr, "  Cc in [0,C)   (absorbing component)\n");
    fprintf(stderr, "  H > 0         (slab thickness)\n");
    fprintf(stderr, "  n >= 1        (number of particles)\n");
    fprintf(stderr, "  T >= 1        (number of threads)\n");
    fprintf(stderr, "  --seed S      (optional: random seed)\n");
    fprintf(stderr, "  --trace-file  (optional: path to CSV for convergence)\n");
    fprintf(stderr, "  --trace-every (optional: record every m-th iteration)\n");
    exit(EXIT_FAILURE);
}

void write_trace_line_if_needed() {
    if (!trace_f || trace_every <= 0) return;

    // If processed is an exact multiple of trace_every, write a line
    pthread_mutex_lock(&file_mutex);
    long p = g_processed;
    if (p > 0 && (p % trace_every == 0)) {
        // Take snapshot under counts mutex for consistency
        pthread_mutex_lock(&counts_mutex);
        long r = g_r, b = g_b, t = g_t;
        pthread_mutex_unlock(&counts_mutex);
        fprintf(trace_f, "%ld,%ld,%ld,%ld,%.8f,%.8f,%.8f\n",
                p, r, b, t,
                (double)r / p, (double)b / p, (double)t / p);
        fflush(trace_f);
    }
    pthread_mutex_unlock(&file_mutex);
}

void* worker(void* arg) {
    thread_args_t *ta = (thread_args_t*)arg;
    double C = ta->C;
    double Cc = ta->Cc;
    double H = ta->H;
    long local_n = ta->n_local;
    unsigned int seed = ta->seed;

    double prob_absorb = Cc / C;

    for (long i = 0; i < local_n; ++i) {
        double d = 0.0; // direction
        double x = 0.0; // position
        bool alive = true;

        while (alive) {
            double u_dist = rand_uniform_r(&seed);
            if (u_dist == 0.0) u_dist = 1.0e-10;
            double L = -(1.0 / C) * log(u_dist);
            x = x + L * cos(d);
            if (x < 0) {
                // Reflected
                pthread_mutex_lock(&counts_mutex);
                g_r++;
                pthread_mutex_unlock(&counts_mutex);
                alive = false;
            } else if (x >= H) {
                // Transmitted
                pthread_mutex_lock(&counts_mutex);
                g_t++;
                pthread_mutex_unlock(&counts_mutex);
                alive = false;
            } else {
                double u_event = rand_uniform_r(&seed);
                if (u_event < prob_absorb) {
                    pthread_mutex_lock(&counts_mutex);
                    g_b++;
                    pthread_mutex_unlock(&counts_mutex);
                    alive = false;
                } else {
                    double u_dir = rand_uniform_r(&seed);
                    d = u_dir * M_PI; // new direction 0..pi
                }
            }
        }

        // Update processed and possibly write trace
        pthread_mutex_lock(&counts_mutex);
        g_processed++;
        pthread_mutex_unlock(&counts_mutex);

        // Try writing trace if needed
        if (trace_f && trace_every > 0) {
            write_trace_line_if_needed();
        }
    }

    return NULL;
}

int main(int argc, char *argv[]) {
    if (argc < 6) {
        print_usage();
    }

    double C = atof(argv[1]);
    double Cc = atof(argv[2]);
    double H = atof(argv[3]);
    long n = atol(argv[4]);
    int T = atoi(argv[5]);

    // Defaults
    unsigned int seed = (unsigned int)time(NULL);
    char *trace_file_path = NULL;
    trace_every = 0;

    // Parse optional args
    for (int i = 6; i < argc; ++i) {
        if (strcmp(argv[i], "--seed") == 0) {
            if (i + 1 < argc) seed = (unsigned int)atoi(argv[++i]); else print_usage();
        } else if (strcmp(argv[i], "--trace-file") == 0) {
            if (i + 1 < argc) trace_file_path = argv[++i]; else print_usage();
        } else if (strcmp(argv[i], "--trace-every") == 0) {
            if (i + 1 < argc) trace_every = atol(argv[++i]); else print_usage();
        } else {
            fprintf(stderr, "Unknown arg: %s\n", argv[i]);
            print_usage();
        }
    }

    // Validate
    if (C <= 0) { fprintf(stderr, "Error: C must be > 0\n"); return EXIT_FAILURE; }
    if (Cc < 0 || Cc >= C) { fprintf(stderr, "Error: Cc must be in [0, C)\n"); return EXIT_FAILURE; }
    if (H <= 0) { fprintf(stderr, "Error: H must be > 0\n"); return EXIT_FAILURE; }
    if (n < 1) { fprintf(stderr, "Error: n must be >= 1\n"); return EXIT_FAILURE; }
    if (T < 1) { fprintf(stderr, "Error: T must be >= 1\n"); return EXIT_FAILURE; }
    if (trace_file_path && trace_every <= 0) { fprintf(stderr, "Error: --trace-every must be > 0 when using --trace-file\n"); return EXIT_FAILURE; }

    if (trace_file_path) {
        trace_f = fopen(trace_file_path, "w");
        if (!trace_f) { fprintf(stderr, "Error: could not open trace file %s\n", trace_file_path); return EXIT_FAILURE; }
        fprintf(trace_f, "k,r,b,t,r_frac,b_frac,t_frac\n");
    }

    // Thread setup
    pthread_t *threads = malloc(sizeof(pthread_t) * T);
    thread_args_t *targs = malloc(sizeof(thread_args_t) * T);
    if (!threads || !targs) { fprintf(stderr, "Allocation failure\n"); return EXIT_FAILURE; }

    long base = n / T;
    long rem = n % T;

    for (int ti = 0; ti < T; ++ti) {
        targs[ti].C = C;
        targs[ti].Cc = Cc;
        targs[ti].H = H;
        targs[ti].tid = ti;
        targs[ti].start_index = ti * base + (ti < rem ? ti : rem) + 1;
        targs[ti].n_local = base + (ti < rem ? 1 : 0);
        targs[ti].seed = seed + (unsigned int)(ti * 1315423911u);
    }

    // Launch threads
    for (int ti = 0; ti < T; ++ti) {
        if (targs[ti].n_local > 0) {
            int rc = pthread_create(&threads[ti], NULL, worker, &targs[ti]);
            if (rc != 0) {
                fprintf(stderr, "Error creating thread %d\n", ti);
                return EXIT_FAILURE;
            }
        } else {
            threads[ti] = 0; // mark unused
        }
    }

    // Join threads
    for (int ti = 0; ti < T; ++ti) {
        if (threads[ti]) pthread_join(threads[ti], NULL);
    }

    if (trace_f) fclose(trace_f);

    // Print final fractions
    printf("%.8f %.8f %.8f\n", (double)g_r / n, (double)g_b / n, (double)g_t / n);

    free(threads);
    free(targs);
    return EXIT_SUCCESS;
}
