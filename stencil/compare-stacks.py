import sys
import struct
import numpy as np

def read_metadata(f):
    """Reads the [rows, cols, num_frames] header from a stack file."""
    try:
        metadata_bytes = f.read(12)
        if len(metadata_bytes) != 12:
            return None, None, None
        rows, cols, num_frames = struct.unpack('iii', metadata_bytes)
        return rows, cols, num_frames
    except Exception as e:
        print(f"Error reading metadata: {e}")
        return None, None, None

def read_frame(f, rows, cols):
    """Reads one frame of [rows * cols] doubles."""
    try:
        data_size = rows * cols
        frame_bytes = f.read(data_size * 8) # 8 bytes per double
        if len(frame_bytes) != data_size * 8:
            return None
        
        data = np.frombuffer(frame_bytes, dtype=np.float64).reshape((rows, cols))
        return data
    except Exception as e:
        print(f"Error reading frame data: {e}")
        return None

def main():
    if len(sys.argv) != 3:
        print("Usage: python ./compare-stacks.py <file1.dat> <file2.dat>")
        sys.exit(1)

    file1_path = sys.argv[1]
    file2_path = sys.argv[2]
    
    print(f"Comparing '{file1_path}' and '{file2_path}'...")

    try:
        with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
            # --- 1. Compare Metadata ---
            rows1, cols1, frames1 = read_metadata(f1)
            rows2, cols2, frames2 = read_metadata(f2)

            if not all((rows1, cols1, frames1, rows2, cols2, frames2)):
                print("Error: Could not read metadata from one or both files.")
                sys.exit(1)

            if (rows1, cols1, frames1) != (rows2, cols2, frames2):
                print("Files have different metadata (dimensions or frame count):")
                print(f"  {file1_path}: {rows1}x{cols1}, {frames1} frames")
                print(f"  {file2_path}: {rows2}x{cols2}, {frames2} frames")
                sys.exit(1)
            
            print(f"Files match metadata: {rows1}x{cols1} grid, {frames1} frames.")
            
            # --- 2. Compare Frame Data ---
            total_max_diff = 0.0
            for i in range(frames1):
                frame1 = read_frame(f1, rows1, cols1)
                frame2 = read_frame(f2, rows2, cols2)
                
                if frame1 is None or frame2 is None:
                    print(f"Error: Could not read frame {i}. Files may be corrupt.")
                    sys.exit(1)

                # Calculate difference
                abs_diff = np.abs(frame1 - frame2)
                max_diff = np.max(abs_diff)
                total_max_diff = max(total_max_diff, max_diff)

                if max_diff > 1e-9: # Use a small tolerance for floating point
                    print(f"  [Frame {i}] differs! Max numerical difference: {max_diff}")

            # --- 3. Final Report ---
            if total_max_diff < 1e-9:
                print("\nResult: Files are numerically identical.")
            else:
                print(f"\nResult: Files differ. The largest difference was {total_max_diff}.")

    except FileNotFoundError as e:
        print(f"Error: File not found: {e.filename}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()