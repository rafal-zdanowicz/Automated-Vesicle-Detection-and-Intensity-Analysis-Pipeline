import os
import cv2
import numpy as np
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

def clamp(val, minval=0.0, maxval=1.0):
    return max(min(val, maxval), minval)

def extract_squares(input_dir, output_dir, margin=0.0):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    label_files = list(input_dir.glob("*.txt"))
    for label_path in label_files:
        # Check for matching .tiff or .jpg image
        image_path = None
        for ext in [".tiff", ".jpg"]:
            candidate = input_dir / label_path.with_suffix(ext).name
            if candidate.exists():
                image_path = candidate
                break

        if image_path is None:
            print(f"No image found for {label_path}. Skipping.")
            continue

        img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"Failed to read {image_path}. Skipping.")
            continue

        img_h, img_w = img.shape[:2]

        with open(label_path, "r") as f:
            lines = f.readlines()

        for idx, line in enumerate(lines):
            parts = line.strip().split()
            if len(parts) != 5:
                continue

            _, x_center, y_center, width, height = map(float, parts)

            x_center = clamp(x_center)
            y_center = clamp(y_center)
            width = clamp(width)
            height = clamp(height)

            x_center_pix = x_center * img_w
            y_center_pix = y_center * img_h
            width_pix = width * img_w
            height_pix = height * img_h

            side = max(width_pix, height_pix)
            side = side * (1 + margin)

            x1 = int(x_center_pix - side / 2)
            y1 = int(y_center_pix - side / 2)
            x2 = int(x_center_pix + side / 2)
            y2 = int(y_center_pix + side / 2)

            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(img_w, x2)
            y2 = min(img_h, y2)

            if x2 <= x1 or y2 <= y1:
                print(f"Invalid crop for {label_path} box {idx}. Skipping.")
                continue

            crop = img[y1:y2, x1:x2]
            # Use same extension as input image
            save_path = output_dir / f"{image_path.stem}_crop{int(x_center * 1000):03d}{image_path.suffix}"
            cv2.imwrite(str(save_path), crop)

def run_gui():
    def browse_input():
        path = filedialog.askdirectory()
        if path:
            input_entry.delete(0, tk.END)
            input_entry.insert(0, path)

    def browse_output():
        path = filedialog.askdirectory()
        if path:
            output_entry.delete(0, tk.END)
            output_entry.insert(0, path)

    def start_extraction():
        input_dir = input_entry.get()
        output_dir = output_entry.get()
        try:
            margin = float(margin_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Margin must be a number.")
            return

        if not input_dir or not output_dir:
            messagebox.showerror("Error", "Please select both input and output directories.")
            return

        extract_squares(input_dir, output_dir, margin)
        messagebox.showinfo("Done", "Extraction completed!")

    root = tk.Tk()
    root.title("Smart YOLO Crop Extractor")

    ttk.Label(root, text="Input Directory:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
    input_entry = ttk.Entry(root, width=50)
    input_entry.grid(row=0, column=1, padx=5, pady=5)
    ttk.Button(root, text="Browse", command=browse_input).grid(row=0, column=2, padx=5, pady=5)

    ttk.Label(root, text="Output Directory:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
    output_entry = ttk.Entry(root, width=50)
    output_entry.grid(row=1, column=1, padx=5, pady=5)
    ttk.Button(root, text="Browse", command=browse_output).grid(row=1, column=2, padx=5, pady=5)

    ttk.Label(root, text="Margin (fraction):").grid(row=2, column=0, padx=5, pady=5, sticky='e')
    margin_entry = ttk.Entry(root, width=10)
    margin_entry.insert(0, "0.0")
    margin_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')

    ttk.Button(root, text="Start Extraction", command=start_extraction).grid(row=3, column=1, padx=5, pady=20)

    root.mainloop()

if __name__ == "__main__":
    run_gui()
