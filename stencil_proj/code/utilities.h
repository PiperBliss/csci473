#ifndef UTILITIES_H
#define UTILITIES_H

#include <stdio.h>
#include <stdlib.h>

// Function prototype to malloc the space for the 2D array
void malloc2D(double*** a, int jmax, int imax);

// Function prototypes to read and write 2D data
void read_data_2d(const char* filename, double*** data, int* rows, int* cols);
void write_data_2d(const char* filename, double** data, int rows, int cols);

#endif