#!/usr/bin/env python3

import sys
import struct
import numpy as np
import matplotlib.pyplot as plt

def main():
    """
    Reads a single-frame binary data file and saves a PNG.
    Usage: python ./display_image.py <inputfile>
    """
    if len(sys.argv) != 2:
        print("Usage: python ./display_image.py <input data file>")
        sys.exit(1)

    in_file = sys.argv[1]
    # Default output filename [cite: 34]
    out_file = in_file.rsplit('.', 1)[0] + '.png'

    try:
        with open(in_file, 'rb') as f:
            # Read metadata: 2 ints (rows, cols) [cite: 15]
            rows, cols = struct.unpack('ii', f.read(8))
            
            # Read data: rows * cols doubles
            data = np.fromfile(f, dtype=np.float64, count=rows*cols)
            
            if data.size != rows * cols:
                print(f"Error: File {in_file} is incomplete.")
                sys.exit(1)

            data = data.reshape((rows, cols))

        # Plotting
        plt.figure(figsize=(8, 8))
        # Use coolwarm colormap (blue to red), vmin/vmax to fix range
        plt.imshow(data, cmap='coolwarm', vmin=0, vmax=1)
        plt.colorbar(label='Value')
        plt.title(f'Visualization of {in_file} ({rows}x{cols})')
        plt.savefig(out_file)
        
        print(f"Read {rows}x{cols} data from {in_file}.")
        print(f"Saved image to {out_file}")

    except FileNotFoundError:
        print(f"Error: File not found {in_file}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()