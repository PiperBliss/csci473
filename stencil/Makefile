# Based on the provided example [cite: 896]
CC=gcc
CFLAGS=-g -Wall -Wstrict-prototypes -std=gnu99 -pthread 

# --- MODIFICATIONS ---
# Separate LFLAGS for standard math and pthreads
LFLAGS_STD=-lm
LFLAGS_PTH=-lm -lpthread

# Add new program to the list
PROGS=print-2d make-2d stencil-2d pth-stencil-2d
# --- END MODIFICATIONS ---

all: $(PROGS)

print-2d: utilities.o print-2d.o
	$(CC) $(LFLAGS_STD) -o print-2d utilities.o print-2d.o

make-2d: utilities.o make-2d.o
	$(CC) $(LFLAGS_STD) -o make-2d utilities.o make-2d.o

stencil-2d: utilities.o stencil-2d.o
	$(CC) $(LFLAGS_STD) -o stencil-2d utilities.o stencil-2d.o

# --- NEW RULE ---
# Rule for the new pthreads version
# Note: uses LFLAGS_PTH to link the pthread library
pth-stencil-2d: utilities.o pth-stencil-2d.o
	$(CC) $(LFLAGS_PTH) -o pth-stencil-2d utilities.o pth-stencil-2d.o
# --- END NEW RULE ---

# --- Object file rules ---

utilities.o: utilities.c utilities.h
	$(CC) $(CFLAGS) -c utilities.c

print-2d.o: print-2d.c utilities.h
	$(CC) $(CFLAGS) -c print-2d.c

make-2d.o: make-2d.c utilities.h
	$(CC) $(CFLAGS) -c make-2d.c

# stencil-2d.o also depends on timer.h [cite: 896]
stencil-2d.o: stencil-2d.c utilities.h timer.h
	$(CC) $(CFLAGS) -c stencil-2d.c

# --- NEW RULE ---
# Object file rule for the pthreads C file
pth-stencil-2d.o: pth-stencil-2d.c utilities.h timer.h
	$(CC) $(CFLAGS) -c pth-stencil-2d.c
# --- END NEW RULE ---

clean:
	rm -f *.o core* $(PROGS)