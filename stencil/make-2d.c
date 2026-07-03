#include <stdio.h>
#include <stdlib.h>
#include "utilities.h"

int main(int argc, char* argv[]) {
    if (argc != 4) {
        // Usage based on [cite: 14]
        fprintf(stderr, "usage: ./make-2d <rows> <cols> <output_file>\n");
        return -1;
    }

    int rows = atoi(argv[1]);
    int cols = atoi(argv[2]);
    const char* filename = argv[3];

    if (rows <= 2 || cols <= 2) {
        fprintf(stderr, "ERROR: rows and cols must be greater than 2.\n");
        return -1;
    }

    double** plate;
    malloc2D(&plate, rows, cols);

    // Set initial conditions [cite: 3]
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            if (j == 0 || j == cols - 1) {
                plate[i][j] = 1.0; // Left and Right walls
            } else if (i == 0 || i == rows - 1) {
                plate[i][j] = 0.0; // Top and Bottom walls
            } else {
                plate[i][j] = 0.0; // Interior
            }
        }
    }

    // Write the data to the output file
    write_data_2d(filename, plate, rows, cols);
    printf("Generated %s with size %dx%d\n", filename, rows, cols);

    free(plate);

    return 0;
}