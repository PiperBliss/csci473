# Based on the provided example 
CC=gcc
CFLAGS=-g -Wall -Wstrict-prototypes -std=gnu99
LFLAGS=-lm
PROGS=print-2d make-2d stencil-2d

all: $(PROGS)

print-2d: utilities.o print-2d.o
	$(CC) $(LFLAGS) -o print-2d utilities.o print-2d.o

make-2d: utilities.o make-2d.o
	$(CC) $(LFLAGS) -o make-2d utilities.o make-2d.o

stencil-2d: utilities.o stencil-2d.o
	$(CC) $(LFLAGS) -o stencil-2d utilities.o stencil-2d.o

utilities.o: utilities.c utilities.h
	$(CC) $(CFLAGS) -c utilities.c

print-2d.o: print-2d.c utilities.h
	$(CC) $(CFLAGS) -c print-2d.c

make-2d.o: make-2d.c utilities.h
	$(CC) $(CFLAGS) -c make-2d.c

stencil-2d.o: stencil-2d.c utilities.h timer.h
	$(CC) $(CFLAGS) -c stencil-2d.c

clean:
	rm -f *.o core* $(PROGS)