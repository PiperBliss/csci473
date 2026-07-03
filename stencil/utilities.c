#include "utilities.h"

void malloc2D(double*** a, int rows, int cols) {
    double **x = (double **)malloc(rows * sizeof(double*) + rows * cols * sizeof(double));
    if (x == NULL) {
        fprintf(stderr, "ERROR: Failed to allocate memory in malloc2D\n");
        exit(-1);
        }

    x[0] = (double *)(x + rows);

    for (int j = 1; j < rows; j++) {
        x[j] = x[j-1] + cols;
    }

    *a = x;

}

void read_data_2d(const char* filename, double*** data, int* rows, int* cols) {
    FILE* file = fopen(filename, "rb");
    if (file == NULL) {
        fprintf(stderr, "ERROR: Could not open file %s for reading.\n", filename);
        exit(-1);
    }

    // Read metadata: rows and cols [cite: 15]
    if (fread(rows, sizeof(int), 1, file) != 1) {
        fprintf(stderr, "ERROR: Could not read rows from %s\n", filename);
        exit(-1);
    }
    if (fread(cols, sizeof(int), 1, file) != 1) {
        fprintf(stderr, "ERROR: Could not read cols from %s\n", filename);
        exit(-1);
    }

    // Allocate memory for the 2D array
    malloc2D(data, *rows, *cols);

    // Read the data in a single block
    size_t data_size = (size_t)(*rows) * (*cols);
    if (fread((*data)[0], sizeof(double), data_size, file) != data_size) {
        fprintf(stderr, "ERROR: Could not read data block from %s\n", filename);
        exit(-1);
    }

    fclose(file);
}

void write_data_2d(const char* filename, double** data, int rows, int cols) {
    FILE* file = fopen(filename, "wb");
    if (file == NULL) {
        fprintf(stderr, "ERROR: Could not open file %s for writing.\n", filename);
        exit(-1);
    }

    // Write metadata: rows and cols [cite: 15]
    if (fwrite(&rows, sizeof(int), 1, file) != 1) {
        fprintf(stderr, "ERROR: Could not write rows to %s\n", filename);
        exit(-1);
    }
    if (fwrite(&cols, sizeof(int), 1, file) != 1) {
        fprintf(stderr, "ERROR: Could not write cols to %s\n", filename);
        exit(-1);
    }

    // Write the data in a single block
    size_t data_size = (size_t)rows * cols;
    if (fwrite(data[0], sizeof(double), data_size, file) != data_size) {
        fprintf(stderr, "ERROR: Could not write data block to %s\n", filename);
        exit(-1);
    }

    fclose(file);
}