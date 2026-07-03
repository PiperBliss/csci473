#!/usr/bin/env python3

import sys
import struct
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import os

def main():
    """
    Creates a movie from a raw stack file.
    Usage: python ./make-movie.py <input .dat file> <output movie MP4 file> [cite: 13]
    """
    if len(sys.argv) != 3:
        print("Usage: python ./make-movie.py <input stack file> <output movie.mp4>")
        sys.exit(1)

    stack_file = sys.argv[1]
    out_file = sys.argv[2]

    try:
        # Keep the file open to read frames progressively
        f = open(stack_file, 'rb')

        # --- MODIFICATION ---
        # Read stack metadata: [int rows][int cols]
        # The num_frames is no longer in the header.
        header_bytes = f.read(8)
        if len(header_bytes) != 8:
            print(f"Error: Could not read metadata from {stack_file}")
            sys.exit(1)
            
        rows, cols = struct.unpack('ii', header_bytes)
        
        # Calculate num_frames based on file size
        f.seek(0, 2) # Go to end of file
        total_size = f.tell()
        data_size_bytes = total_size - 8 # Subtract 8-byte header
        
        frame_size_bytes = rows * cols * 8 # 8 bytes per double
        
        if data_size_bytes % frame_size_bytes != 0:
            print(f"Error: File size {total_size} is not consistent with {rows}x{cols} frames.")
            sys.exit(1)
            
        num_frames = data_size_bytes // frame_size_bytes
        
        # Reset file pointer to the start of the data (after the 8-byte header)
        f.seek(8)
        # --- End Modification ---

        print(f"Reading {num_frames} frames of {rows}x{cols} data from {stack_file}...")

        data_size = rows * cols # This is elements, not bytes

        # --- Set up the plot ---
        fig, ax = plt.subplots()
        # Initialize with the first frame
        frame0 = np.fromfile(f, dtype=np.float64, count=data_size).reshape((rows, cols))
        im = ax.imshow(frame0, cmap='coolwarm', vmin=0, vmax=1)
        
        # Add colorbar [cite: 41]
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label('Value')
        
        # Add frame text [cite: 41]
        frame_text = ax.text(0.02, 0.95, '', transform=ax.transAxes, color='white',
                             bbox=dict(facecolor='black', alpha=0.5))

        def init():
            """Init function for the animation."""
            # --- MODIFICATION ---
            # Reset file pointer to just after 8-byte metadata
            f.seek(8)
            # --- End Modification ---
            im.set_array(np.zeros((rows, cols)))
            frame_text.set_text('')
            return im, frame_text

        def update_frame(frame_num):
            """Update function for each frame."""
            data = np.fromfile(f, dtype=np.float64, count=data_size)
            
            if data.size == 0:
                # Handle case where file ends unexpectedly
                return im, frame_text

            data = data.reshape((rows, cols))
            im.set_array(data)
            frame_text.set_text(f'frame {frame_num}')
            return im, frame_text

        # --- Create and save the animation ---
        ani = animation.FuncAnimation(fig, update_frame, frames=num_frames,
                                      init_func=init, blit=True)

        print(f"Saving movie to {out_file}... (this may take a while)")
        ani.save(out_file, writer='ffmpeg', fps=30, dpi=150)
        
        print(f"Successfully saved movie to {out_file}")

    except FileNotFoundError:
        print(f"Error: File not found {stack_file}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'f' in locals() and not f.closed:
            f.close()

if __name__ == "__main__":
    main()
