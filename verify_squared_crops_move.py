# Sometimes vesicles are detected at the image edges resulting in non-squared crops. This script allows for identification and removal of such vesicles, with some user-defined tolerance.
# If you enter 5% tolerance, then the image is accepted as "square enough" if the width and height differ by no more than 5% of the larger dimension.


import os
import shutil
from PIL import Image

def find_almost_square_images(directory, tolerance_percent=1.0, extensions=(".png", ".tif", ".tiff", ".jpg")):
    non_square_images = []

    for filename in os.listdir(directory):
        if filename.lower().endswith(extensions):
            filepath = os.path.join(directory, filename)
            try:
                with Image.open(filepath) as img:
                    width, height = img.size
                    difference = abs(width - height)
                    max_dim = max(width, height)
                    deviation_percent = (difference / max_dim) * 100
                    if deviation_percent > tolerance_percent:
                        non_square_images.append((filepath, width, height, deviation_percent))
            except Exception as e:
                print(f"Error reading {filename}: {e}")
    
    return non_square_images

def main():
    directory = input("Enter the directory to scan: ").strip()
    
    if not os.path.isdir(directory):
        print("Invalid directory.")
        return

    try:
        tolerance_percent = float(input("Enter tolerance in % (e.g., 1.0): ").strip())
    except ValueError:
        print("Invalid percentage.")
        return

    non_square_images = find_almost_square_images(directory, tolerance_percent)

    if non_square_images:
        print(f"\nFound non-square images (tolerance ±{tolerance_percent}%):\n")
        for filepath, width, height, dev in non_square_images:
            print(f"- {os.path.basename(filepath)}: {width}x{height} ({dev:.2f}% deviation)")

        print(f"\nTotal: {len(non_square_images)} file(s) exceed the ±{tolerance_percent}% tolerance.")

        confirm = input("\nMove these files to a 'nonsquared' folder? (y/n): ").strip().lower()
        if confirm != "y":
            print("No files moved.")
            return

        nonsquared_dir = os.path.join(directory, "nonsquared")
        os.makedirs(nonsquared_dir, exist_ok=True)

        log_path = os.path.join(nonsquared_dir, "moved_files_log.txt")
        with open(log_path, "w") as log_file:
            for filepath, _, _, _ in non_square_images:
                try:
                    filename = os.path.basename(filepath)
                    destination = os.path.join(nonsquared_dir, filename)
                    shutil.move(filepath, destination)
                    print(f"Moved: {filename} -> {destination}")
                    log_file.write(f"{filename}\n")
                except Exception as e:
                    print(f"Could not move {filepath}: {e}")
        
        print(f"\nLog written to: {log_path}")
    else:
        print(f"All images are within ±{tolerance_percent}% square tolerance.")

if __name__ == "__main__":
    main()
