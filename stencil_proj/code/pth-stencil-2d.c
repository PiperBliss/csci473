#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h> // For getopt
#include <pthread.h>
#include "utilities.h"
#include "timer.h"

// --- Globals (for thread access) ---
int rows, cols, num_iters, num_threads;
double **plate_A, **plate_B, **temp_swap;
FILE* f_stack = NULL;

// Barriers for synchronization
pthread_barrier_t barrier1;
pthread_barrier_t barrier2;

// --- Thread Argument Struct ---
typedef struct {
    int tid;
    int start_row; // First computational row (inclusive)
    int end_row;   // Last computational row (exclusive)
} ThreadArgs;

/**
 * @brief Prints the required usage string for the program. 
 */
void print_usage(void) {
    fprintf(stderr, "Usage: ./pth-stencil-2d -n <iters> -I <in.raw> -o <out.raw> [-s <stack.raw>] -t <threads>\n");
}

/**
 * @brief The worker function each thread will execute.
 */
void* worker_function(void* arg) {
    ThreadArgs* my_args = (ThreadArgs*) arg;
    int tid = my_args->tid;
    int my_start = my_args->start_row;
    int my_end = my_args->end_row;

    for (int iter = 0; iter < num_iters; iter++) {
        
        // --- 1. Compute assigned rows ---
        // Iterate over assigned interior points 
        for (int i = my_start; i < my_end; i++) {
            for (int j = 1; j < cols - 1; j++) {
                // 9-point stencil operation [cite: 834]
                plate_B[i][j] = (plate_A[i-1][j-1] + plate_A[i-1][j] + plate_A[i-1][j+1] + \
                                 plate_A[i][j+1]   + plate_A[i+1][j+1] + plate_A[i+1][j] + \
                                 plate_A[i+1][j-1] + plate_A[i][j-1]   + plate_A[i][j]) / 9.0;
            }
        }

        // --- 2. Copy boundaries (Thread 0 only) ---
        // Boundaries (walls) do not change and are copied from A to B
        if (tid == 0) {
            for (int i = 0; i < rows; i++) {
                plate_B[i][0] = plate_A[i][0];
                plate_B[i][cols-1] = plate_A[i][cols-1];
            }
            for (int j = 0; j < cols; j++) {
                plate_B[0][j] = plate_A[0][j];
                plate_B[rows-1][j] = plate_A[rows-1][j];
            }
        }

        // --- 3. Barrier 1 ---
        // Wait for all threads to finish computation and boundary copy
        pthread_barrier_wait(&barrier1);

        // --- 4. Swap buffers and Write to stack (Thread 0 only) ---
        if (tid == 0) {
            // Swap buffers (B becomes A for next iteration)
            temp_swap = plate_A;
            plate_A = plate_B;
            plate_B = temp_swap;

            // Write the newly computed frame (now in plate_A) to stack
            if (f_stack) {
                fwrite(plate_A[0], sizeof(double), (size_t)rows * cols, f_stack);
            }
        }

        // --- 5. Barrier 2 ---
        // Wait for Thread 0 to finish swap/IO before starting next iteration
        pthread_barrier_wait(&barrier2);
    }

    return NULL;
}

// --- Main Function ---
int main(int argc, char* argv[]) {
    int opt;
    char *in_file = NULL, *out_file = NULL, *stack_file_opt = NULL;

    // --- 1. Parse Command-Line Arguments [cite: 10-16] ---
    while ((opt = getopt(argc, argv, "n:I:o:s:t:h")) != -1) {
        switch (opt) {
            case 'n':
                num_iters = atoi(optarg);
                break;
            case 'I':
                in_file = optarg;
                break;
            case 'o':
                out_file = optarg;
                break;
            case 's':
                stack_file_opt = optarg;
                break;
            case 't':
                num_threads = atoi(optarg);
                break;
            case 'h':
                print_usage();
                return 0;
            default:
                print_usage();
                return -1;
        }
    }

    // --- 2. Validate Arguments ---
    if (num_iters <= 0 || in_file == NULL || out_file == NULL || num_threads <= 0) {
        fprintf(stderr, "ERROR: Missing or invalid required arguments.\n");
        print_usage();
        return -1;
    }

    // --- 3. Read Initial Data ---
    read_data_2d(in_file, &plate_A, &rows, &cols);
    malloc2D(&plate_B, rows, cols); // Allocate swap buffer

    // --- 4. Open Stack File (if specified) ---
    if (stack_file_opt) {
        f_stack = fopen(stack_file_opt, "wb");
        if (f_stack == NULL) {
            fprintf(stderr, "ERROR: Could not open stack file %s\n", stack_file_opt);
            return -1;
        }
        // Write stack metadata: [int rows][int cols]
        fwrite(&rows, sizeof(int), 1, f_stack);
        fwrite(&cols, sizeof(int), 1, f_stack);
        // Write initial state (frame 0)
        fwrite(plate_A[0], sizeof(double), (size_t)rows * cols, f_stack);
    }

    printf("Running parallel stencil (%d threads) for %d iterations on %dx%d grid...\n",
           num_threads, num_iters, rows, cols);

    // --- 5. Initialize Barriers and Thread Data ---
    pthread_barrier_init(&barrier1, NULL, num_threads);
    pthread_barrier_init(&barrier2, NULL, num_threads);

    pthread_t* threads = (pthread_t*)malloc(num_threads * sizeof(pthread_t));
    ThreadArgs* args = (ThreadArgs*)malloc(num_threads * sizeof(ThreadArgs));

    // Calculate row decomposition 
    int total_comp_rows = rows - 2; // Only interior rows are computed
    int base_rows = total_comp_rows / num_threads;
    int remainder = total_comp_rows % num_threads;
    int current_start_row = 1;

    for (int i = 0; i < num_threads; i++) {
        args[i].tid = i;
        args[i].start_row = current_start_row;
        int num_my_rows = base_rows + (i < remainder ? 1 : 0);
        args[i].end_row = current_start_row + num_my_rows;
        current_start_row = args[i].end_row;
    }

    // --- 6. Start Timer and Run Threads ---
    double start, finish, elapsed;
    GET_TIME(start);

    for (int i = 0; i < num_threads; i++) {
        pthread_create(&threads[i], NULL, worker_function, &args[i]);
    }

    // --- 7. Wait for Threads to Complete ---
    for (int i = 0; i < num_threads; i++) {
        pthread_join(threads[i], NULL);
    }

    GET_TIME(finish);
    elapsed = finish - start;
    printf("Stencil operation took %e seconds\n", elapsed);

    // --- 8. Clean Up and Write Final Output ---
    if (f_stack) {
        fclose(f_stack);
        printf("Wrote all %d frames to %s\n", num_iters + 1, stack_file_opt);
    }

    // Write final state (which is in plate_A)
    write_data_2d(out_file, plate_A, rows, cols);
    printf("Wrote final state to %s\n", out_file);

    // Free all resources
    free(plate_A);
    free(plate_B);
    free(threads);
    free(args);
    pthread_barrier_destroy(&barrier1);
    pthread_barrier_destroy(&barrier2);

    return 0;
}