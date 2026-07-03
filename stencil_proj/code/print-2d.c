#include <stdio.h>
#include <stdlib.h>
#include "utilities.h"

int main(int argc, char* argv[]) {
    if (argc != 2) {
        // Usage based on [cite: 14]
        fprintf(stderr, "usage: ./print-2d <input data file>\n");
        return -1;
    }

    const char* filename = argv[1];
    double** plate;
    int rows, cols;

    // Read the data file
    read_data_2d(filename, &plate, &rows, &cols);

    printf("./print-2d, %s,\nreading in file: %s\n", filename, filename);

    // Print in "appealing format" , like in [cite: 14]
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            printf("%.2f  ", plate[i][j]);
        }
        printf("\n");
    }

    free(plate);

    return 0;
}