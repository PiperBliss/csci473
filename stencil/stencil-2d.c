#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "utilities.h"
#include "timer.h"

int main(int argc, char* argv[]) {
    if (argc != 5) {
        // Usage based on [cite: 24]
        fprintf(stderr, "usage: ./stencil-2d <num iterations> <input file> <output file> <all-iterations>\n");
        return -1;
    }

    int num_iters = atoi(argv[1]);
    const char* in_file = argv[2];
    const char* out_file = argv[3];
    const char* stack_file = argv[4];

    double **plate_A, **plate_B, **temp_swap;
    int rows, cols;
    double start, finish, elapsed;

    // Read initial data
    read_data_2d(in_file, &plate_A, &rows, &cols);

    // Allocate second buffer for computation
    malloc2D(&plate_B, rows, cols);

    // Open the all-iterations stack file for writing
    FILE* f_stack = fopen(stack_file, "wb");
    if (f_stack == NULL) {
        fprintf(stderr, "ERROR: Could not open stack file %s\n", stack_file);
        return -1;
    }

    // --- MODIFICATION ---
    // Write stack metadata: [int rows][int cols]
    // We are no longer writing num_frames to match the 'jones' file format.
    fwrite(&rows, sizeof(int), 1, f_stack);
    fwrite(&cols, sizeof(int), 1, f_stack);
    // --- End Modification ---

    // Write initial state (frame 0) to stack
    fwrite(plate_A[0], sizeof(double), (size_t)rows * cols, f_stack);

    printf("Running stencil for %d iterations on %dx%d grid...\n", num_iters, rows, cols);
    
    // Start timer before the loop [cite: 53-77]
    GET_TIME(start);

    for (int iter = 0; iter < num_iters; iter++) {
        // --- Apply 8-point stencil ---
        // Iterate over interior points only (1 to rows-2, 1 to cols-2)
        for (int i = 1; i < rows - 1; i++) {
            for (int j = 1; j < cols - 1; j++) {
                // Original 9-point average (includes the center point)
                plate_B[i][j] = (plate_A[i-1][j-1] + plate_A[i-1][j] + plate_A[i-1][j+1] + \
                plate_A[i][j+1]   + plate_A[i+1][j+1] + plate_A[i+1][j] + \
                plate_A[i+1][j-1] + plate_A[i][j-1]   + plate_A[i][j]) / 9.0;
            }
        }

        // --- Copy boundaries ---
        // Boundaries (walls) do not change
        for (int i = 0; i < rows; i++) {
            plate_B[i][0] = plate_A[i][0];
            plate_B[i][cols-1] = plate_A[i][cols-1];
        }
        for (int j = 0; j < cols; j++) {
            plate_B[0][j] = plate_A[0][j];
            plate_B[rows-1][j] = plate_A[rows-1][j];
        }

        // --- Swap buffers ---
        // plate_B becomes plate_A for the next iteration
        temp_swap = plate_A;
        plate_A = plate_B;
        plate_B = temp_swap;

        // Write the newly computed frame (which is now in plate_A) to the stack
        fwrite(plate_A[0], sizeof(double), (size_t)rows * cols, f_stack);
    }

    // Stop timer
    GET_TIME(finish);
    elapsed = finish - start;
    printf("Stencil operation took %e seconds\n", elapsed);

    fclose(f_stack);

    // Write the final state (which is in plate_A after the last swap)
    write_data_2d(out_file, plate_A, rows, cols);
    printf("Wrote final state to %s\n", out_file);
    // Print the number of frames that *were* written
    printf("Wrote all %d frames to %s\n", num_iters + 1, stack_file);

    // Clean up
    free(plate_A);
    free(plate_B);

    return 0;
}
