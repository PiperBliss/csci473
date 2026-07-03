
/*
 * mc_slab_mpi.c
 *
 * MPI-parallel Monte Carlo slab simulator. Each MPI rank simulates a portion
 * of the total number of particle histories and contributes local counts which
 * are reduced to rank 0 for final output.
 *
 * Usage (run via mpirun):
 *   mpirun -np P ./mc_slab_mpi C Cc H n [--seed S]
 */

/* Enable POSIX feature test so rand_r is declared on some systems */
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200112L
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdbool.h>
#include <time.h>
#include <mpi.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

double rand_uniform_r(unsigned int *seedp) {
    return (double)rand_r(seedp) / ((double)RAND_MAX + 1.0);
}

void print_usage_root() {
    fprintf(stderr, "Usage: mpirun -np P ./mc_slab_mpi C Cc H n [--seed S]\n");
    fprintf(stderr, "  C > 0         (total interaction coeff)\n");
    fprintf(stderr, "  Cc in [0,C)   (absorbing component)\n");
    fprintf(stderr, "  H > 0         (slab thickness)\n");
    fprintf(stderr, "  n >= 1        (number of particles)\n");
    fprintf(stderr, "  --seed S      (optional: random seed)\n");
}

int main(int argc, char *argv[]) {
    int provided = 0;
    MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED, &provided);

    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (argc < 5) {
        if (rank == 0) print_usage_root();
        MPI_Finalize();
        return EXIT_FAILURE;
    }

    double C = atof(argv[1]);
    double Cc = atof(argv[2]);
    double H = atof(argv[3]);
    long n = atol(argv[4]);

    unsigned int seed = (unsigned int)time(NULL);
    // Optional: parse --seed
    for (int i = 5; i < argc; ++i) {
        if (strcmp(argv[i], "--seed") == 0) {
            if (i + 1 < argc) seed = (unsigned int)atoi(argv[++i]);
        }
    }

    // Basic validation (only rank 0 prints usage/errors)
    if (rank == 0) {
        if (C <= 0) { fprintf(stderr, "Error: C must be > 0\n"); MPI_Abort(MPI_COMM_WORLD, 1); }
        if (Cc < 0 || Cc >= C) { fprintf(stderr, "Error: Cc must be in [0, C)\n"); MPI_Abort(MPI_COMM_WORLD, 1); }
        if (H <= 0) { fprintf(stderr, "Error: H must be > 0\n"); MPI_Abort(MPI_COMM_WORLD, 1); }
        if (n < 1) { fprintf(stderr, "Error: n must be >= 1\n"); MPI_Abort(MPI_COMM_WORLD, 1); }
    }

    // Distribute work
    long base = n / size;
    long rem = n % size;
    long local_n = base + (rank < rem ? 1 : 0);

    unsigned int myseed = seed + (unsigned int)rank * 10007u;

    long local_r = 0, local_b = 0, local_t = 0;

    double prob_absorb = Cc / C;

    for (long i = 0; i < local_n; ++i) {
        double d = 0.0;
        double x = 0.0;
        bool alive = true;
        while (alive) {
            double u_dist = rand_uniform_r(&myseed);
            if (u_dist == 0.0) u_dist = 1.0e-10;
            double L = -(1.0 / C) * log(u_dist);
            x = x + L * cos(d);
            if (x < 0) {
                local_r++;
                alive = false;
            } else if (x >= H) {
                local_t++;
                alive = false;
            } else {
                double u_event = rand_uniform_r(&myseed);
                if (u_event < prob_absorb) {
                    local_b++;
                    alive = false;
                } else {
                    double u_dir = rand_uniform_r(&myseed);
                    d = u_dir * M_PI;
                }
            }
        }
    }

    // Reduce counts to rank 0
    long g_r = 0, g_b = 0, g_t = 0;
    MPI_Reduce(&local_r, &g_r, 1, MPI_LONG, MPI_SUM, 0, MPI_COMM_WORLD);
    MPI_Reduce(&local_b, &g_b, 1, MPI_LONG, MPI_SUM, 0, MPI_COMM_WORLD);
    MPI_Reduce(&local_t, &g_t, 1, MPI_LONG, MPI_SUM, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        printf("%.8f %.8f %.8f\n", (double)g_r / n, (double)g_b / n, (double)g_t / n);
    }

    MPI_Finalize();
    return EXIT_SUCCESS;
}
