import tkinter as tk
from tkinter import filedialog, messagebox
import random
import shutil
from pathlib import Path
from PIL import Image

def prepare_dataset(input_dir, output_dir, train_ratio=0.8, class_names=["vesicle"]):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    image_train = output_dir / "images/train"
    image_val = output_dir / "images/val"
    label_train = output_dir / "labels/train"
    label_val = output_dir / "labels/val"

    for d in [image_train, image_val, label_train, label_val]:
        d.mkdir(parents=True, exist_ok=True)

    all_tiffs = list(input_dir.glob("*.tiff"))
    random.shuffle(all_tiffs)
    split_idx = int(len(all_tiffs) * train_ratio)
    train_tiffs = all_tiffs[:split_idx]
    val_tiffs = all_tiffs[split_idx:]

    def convert_and_copy(tiff_path, dest_img_dir, dest_lbl_dir):
        base = tiff_path.stem
        jpg_path = dest_img_dir / f"{base}.jpg"
        txt_path = input_dir / f"{base}.txt"
        with Image.open(tiff_path) as im:
            im.convert("RGB").save(jpg_path, quality=95)
        if txt_path.exists():
            shutil.copy(txt_path, dest_lbl_dir / txt_path.name)

    for t in train_tiffs:
        convert_and_copy(t, image_train, label_train)
    for t in val_tiffs:
        convert_and_copy(t, image_val, label_val)

    yaml_path = output_dir / "data.yaml"
    with open(yaml_path, "w") as f:
        f.write(f"path: {output_dir.resolve()}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write(f"nc: {len(class_names)}\n")
        f.write(f"names: {class_names}\n")

    messagebox.showinfo("✅ Done", f"Dataset prepared at: {output_dir}")

def run_gui():
    def select_input():
        input_dir.set(filedialog.askdirectory())

    def select_output():
        output_dir.set(filedialog.askdirectory())

    def start():
        if not input_dir.get() or not output_dir.get():
            messagebox.showerror("Error", "Please select input and output directories.")
            return
        prepare_dataset(input_dir.get(), output_dir.get(), train_ratio.get())

    root = tk.Tk()
    root.title("YOLO Dataset Preparer")

    input_dir = tk.StringVar()
    output_dir = tk.StringVar()
    train_ratio = tk.DoubleVar(value=0.8)

    tk.Label(root, text="Input directory:").grid(row=0, column=0, sticky="w")
    tk.Entry(root, textvariable=input_dir, width=40).grid(row=0, column=1)
    tk.Button(root, text="Browse", command=select_input).grid(row=0, column=2)

    tk.Label(root, text="Output directory:").grid(row=1, column=0, sticky="w")
    tk.Entry(root, textvariable=output_dir, width=40).grid(row=1, column=1)
    tk.Button(root, text="Browse", command=select_output).grid(row=1, column=2)

    tk.Label(root, text="Train Ratio:").grid(row=2, column=0, sticky="w")
    tk.Scale(root, variable=train_ratio, from_=0.5, to=0.95, resolution=0.05, orient=tk.HORIZONTAL).grid(row=2, column=1, columnspan=2, sticky="we")

    tk.Button(root, text="Prepare Dataset", command=start).grid(row=3, column=0, columnspan=3, pady=10)

    root.mainloop()

if __name__ == "__main__":
    run_gui()
