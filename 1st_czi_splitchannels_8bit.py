import tkinter as tk
from tkinter import filedialog
from czifile import CziFile
import numpy as np
import cv2
from PIL import Image, ImageTk
import os
import xml.etree.ElementTree as ET
from pathlib import Path

class Settings:
    def __init__(self):
        self.low_percentile = 0.5
        self.high_percentile = 99.5
        self.brightness = 1.0
        self.selected_channel = None

def apply_percentile_contrast(img, low_p, high_p, brightness=1.0):
    low = np.percentile(img, low_p)
    high = np.percentile(img, high_p)
    img = np.clip((img - low) * 255.0 / (high - low + 1e-5), 0, 255)
    img = img * brightness
    return np.clip(img, 0, 255).astype(np.uint8)

def normalize_to_uint8(img):
    img = img.astype(np.float32)
    img = 255.0 * (img - img.min()) / (img.max() - 1e-5)
    return np.clip(img, 0, 255).astype(np.uint8)

def extract_and_save_channels(czi_path, settings):
    with CziFile(czi_path) as czi:
        metadata = czi.metadata()
        img = czi.asarray()
    img = np.squeeze(img)

    root_xml = ET.fromstring(metadata)
    channel_tags = root_xml.findall(".//Channel")

    seen = set()
    channel_meta = []
    for ch in channel_tags:
        name = ch.attrib.get("Name", "Unnamed")
        if name not in seen:
            seen.add(name)
            channel_meta.append(name)

    out_dir = os.path.splitext(czi_path)[0] + "_channels"
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.basename(czi_path).replace(".czi", "")

    if img.ndim < 3:
        img = np.expand_dims(img, axis=0)

    try:
        idx = channel_meta.index(settings.selected_channel)
        if idx >= img.shape[0]:
            print(f"Channel index {idx} out of bounds for shape {img.shape}")
            return out_dir

        raw = np.squeeze(img[idx])
        norm = normalize_to_uint8(raw)
        enh = apply_percentile_contrast(norm, settings.low_percentile, settings.high_percentile, settings.brightness)

        cv2.imwrite(os.path.join(out_dir, f"{base}_{settings.selected_channel}_raw.tiff"), raw)
        cv2.imwrite(os.path.join(out_dir, f"{base}_{settings.selected_channel}_enhanced.tiff"), enh)
    except ValueError:
        print(f"Selected channel '{settings.selected_channel}' not found in metadata.")

    return out_dir

def main():
    root = tk.Tk()
    root.title("Single Window Image Preview")

    file_paths = filedialog.askopenfilenames(filetypes=[("CZI files", "*.czi")], parent=root)
    if not file_paths:
        root.destroy()
        return

    root.focus_force()

    settings = Settings()
    index = [0]
    selected_channel = tk.StringVar()
    channel_names = []

    def load_channel_names(czi_path):
        with CziFile(czi_path) as czi:
            metadata = czi.metadata()
        root_xml = ET.fromstring(metadata)
        channel_tags = root_xml.findall(".//Channel")

        seen = set()
        channel_list = []
        for ch in channel_tags:
            name = ch.attrib.get("Name", "Unnamed")
            if name not in seen:
                seen.add(name)
                channel_list.append(name)
        return channel_list

    channel_names[:] = load_channel_names(file_paths[0])
    selected_channel.set(channel_names[0] if channel_names else "None")
    settings.selected_channel = selected_channel.get()

    image_label = tk.Label(root)
    image_label.grid(row=0, column=0, columnspan=6, pady=10)

    def update_preview():
        root.title(f"Viewing: {Path(file_paths[index[0]]).name}")
        czi_path = file_paths[index[0]]
        with CziFile(czi_path) as czi:
            metadata = czi.metadata()
            img = czi.asarray()
        img = np.squeeze(img)

        root_xml = ET.fromstring(metadata)
        channel_tags = root_xml.findall(".//Channel")
        seen = set()
        channel_meta = []
        for ch in channel_tags:
            name = ch.attrib.get("Name", "Unnamed")
            if name not in seen:
                seen.add(name)
                channel_meta.append(name)

        try:
            selected_name = selected_channel.get()
            settings.selected_channel = selected_name
            channel_idx = channel_meta.index(selected_name)
        except ValueError:
            channel_idx = None

        if channel_idx is not None and img.ndim == 3:
            raw_img = normalize_to_uint8(np.squeeze(img[channel_idx]))
        else:
            raw_img = np.ones((512, 512), dtype=np.uint8) * 50
            cv2.putText(raw_img, "Channel not found", (50, 256), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 255, 2)

        enhanced = apply_percentile_contrast(
            raw_img, settings.low_percentile, settings.high_percentile, settings.brightness
        )

        h, w = enhanced.shape
        scale = min(1376 / w, 1104 / h)
        im_pil = Image.fromarray(enhanced).resize((int(w * scale), int(h * scale)))
        imgtk = ImageTk.PhotoImage(image=im_pil)
        image_label.config(image=imgtk)
        image_label.image = imgtk

    def sync_from_sliders():
        settings.low_percentile = low_slider.get() / 10.0
        settings.high_percentile = high_slider.get() / 10.0
        settings.brightness = brightness_slider.get() / 10.0

        low_entry.delete(0, tk.END)
        low_entry.insert(0, f"{settings.low_percentile:.1f}")
        high_entry.delete(0, tk.END)
        high_entry.insert(0, f"{settings.high_percentile:.1f}")
        brightness_entry.delete(0, tk.END)
        brightness_entry.insert(0, f"{settings.brightness:.1f}")

        update_preview()

    def sync_from_entries(event=None):
        try:
            settings.low_percentile = float(low_entry.get())
            settings.high_percentile = float(high_entry.get())
            settings.brightness = float(brightness_entry.get())
            low_slider.set(int(settings.low_percentile * 10))
            high_slider.set(int(settings.high_percentile * 10))
            brightness_slider.set(int(settings.brightness * 10))
            update_preview()
            root.focus_set()
        except ValueError:
            pass

    def next_image(event=None):
        if index[0] < len(file_paths) - 1:
            index[0] += 1
            update_preview()

    def prev_image(event=None):
        if index[0] > 0:
            index[0] -= 1
            update_preview()

    def save_current(event=None):
        sync_from_entries()
        extract_and_save_channels(file_paths[index[0]], settings)
        print(f"Saved: {Path(file_paths[index[0]]).stem}")

    def apply_to_all(event=None):
        sync_from_entries()
        for filepath in file_paths:
            extract_and_save_channels(filepath, settings)
        print("All images processed with current settings.")

    def quit_preview(event=None):
        root.destroy()

    # Layout controls
    tk.Label(root, text="Low %:").grid(row=1, column=0)
    low_entry = tk.Entry(root, width=6)
    low_entry.insert(0, "0.5")
    low_entry.grid(row=1, column=1)
    low_slider = tk.Scale(root, from_=0, to=200, orient=tk.HORIZONTAL, length=300, command=lambda v: sync_from_sliders())
    low_slider.set(5)
    low_slider.grid(row=1, column=2, columnspan=3)

    tk.Label(root, text="High %:").grid(row=2, column=0)
    high_entry = tk.Entry(root, width=6)
    high_entry.insert(0, "99.5")
    high_entry.grid(row=2, column=1)
    high_slider = tk.Scale(root, from_=900, to=1000, orient=tk.HORIZONTAL, length=300, command=lambda v: sync_from_sliders())
    high_slider.set(995)
    high_slider.grid(row=2, column=2, columnspan=3)

    tk.Label(root, text="Brightness:").grid(row=3, column=0)
    brightness_entry = tk.Entry(root, width=6)
    brightness_entry.insert(0, "1.0")
    brightness_entry.grid(row=3, column=1)
    brightness_slider = tk.Scale(root, from_=0, to=50, orient=tk.HORIZONTAL, length=300, command=lambda v: sync_from_sliders())
    brightness_slider.set(10)
    brightness_slider.grid(row=3, column=2, columnspan=3)

    # Move channel dropdown to right side of sliders
    tk.Label(root, text="Channel:").grid(row=1, column=5, sticky="w")
    channel_dropdown = tk.OptionMenu(root, selected_channel, *channel_names, command=lambda name: [selected_channel.set(name), setattr(settings, "selected_channel", name), update_preview()])
    channel_dropdown.grid(row=2, column=5, rowspan=2, sticky="n")

    # Buttons
    tk.Button(root, text="Previous (A)", command=prev_image).grid(row=6, column=0)
    tk.Button(root, text="Save (S)", command=save_current).grid(row=6, column=1)
    tk.Button(root, text="Next (D)", command=next_image).grid(row=6, column=2)
    tk.Button(root, text="Apply to All (Z)", command=apply_to_all).grid(row=6, column=3)
    tk.Button(root, text="Quit (Q)", command=quit_preview).grid(row=6, column=4)

    # Entry & key bindings
    low_entry.bind("<Return>", sync_from_entries)
    high_entry.bind("<Return>", sync_from_entries)
    brightness_entry.bind("<Return>", sync_from_entries)
    root.bind("<a>", prev_image)
    root.bind("<s>", save_current)
    root.bind("<d>", next_image)
    root.bind("<z>", apply_to_all)
    root.bind("<q>", quit_preview)

    update_preview()
    root.mainloop()

if __name__ == "__main__":
    main()
