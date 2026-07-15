import os
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, Label, Entry, Button, StringVar, OptionMenu, filedialog, messagebox, BooleanVar, Checkbutton, ttk
from fpdf import FPDF
from tqdm import tqdm
import re  # for filename sanitization

def normalize_profile(profile):
    return (profile - profile.min()) / (profile.max() - profile.min()) if np.ptp(profile) else profile

def compute_membrane_metrics(profile):
    profile = np.asarray(profile, dtype=float)
    size = len(profile)

    if size == 0:
        return np.nan, np.nan, np.nan, np.nan

    n_top = max(1, int(np.ceil(0.05 * size)))
    top_values = np.sort(profile)[-n_top:]
    membrane_mean_top5 = np.mean(top_values)

    mid = size // 2
    left_half = profile[:mid] if mid > 0 else profile
    right_half = profile[mid:] if size - mid > 0 else profile

    membrane_peak_left = np.max(left_half) if len(left_half) else np.nan
    membrane_peak_right = np.max(right_half) if len(right_half) else np.nan
    mean_of_two_highest_peaks = np.nanmean([membrane_peak_left, membrane_peak_right])

    return membrane_mean_top5, membrane_peak_left, membrane_peak_right, mean_of_two_highest_peaks

def get_line_profile(img, direction, thickness=1):
    h, w = img.shape
    half_thick = thickness // 2

    if direction == 'Horizontal':
        center = h // 2
        rows = img[max(center - half_thick, 0):min(center + half_thick + 1, h), :]
        return np.mean(rows, axis=0)

    elif direction == 'Vertical':
        center = w // 2
        cols = img[:, max(center - half_thick, 0):min(center + half_thick + 1, w)]
        return np.mean(cols, axis=1)

    elif direction == 'Diagonal':
        diagonals = []
        for offset in range(-half_thick, half_thick + 1):
            if offset >= 0:
                diag = np.diagonal(img, offset=offset)
            else:
                diag = np.diagonal(np.fliplr(img), offset=-offset)[::-1]
            diagonals.append(diag)
        min_len = min(len(d) for d in diagonals)
        diagonals = [d[:min_len] for d in diagonals]
        return np.mean(diagonals, axis=0)

    else:
        raise ValueError("Invalid direction")

class UserInputGUI:
    def __init__(self, root):
        self.root = root
        root.title("Vesicle Analysis Setup")

        Label(root, text="Input Folder:").grid(row=0, column=0, sticky='e')
        self.input_dir = StringVar()
        Entry(root, textvariable=self.input_dir, width=40).grid(row=0, column=1)
        Button(root, text="Browse", command=self.browse_input).grid(row=0, column=2)

        Label(root, text="Output Folder:").grid(row=1, column=0, sticky='e')
        self.output_dir = StringVar()
        Entry(root, textvariable=self.output_dir, width=40).grid(row=1, column=1)
        Button(root, text="Browse", command=self.browse_output).grid(row=1, column=2)

        Label(root, text="Min Vesicle Size:").grid(row=2, column=0, sticky='e')
        self.min_size = StringVar(value='0')
        Entry(root, textvariable=self.min_size).grid(row=2, column=1)

        Label(root, text="Max Vesicle Size:").grid(row=3, column=0, sticky='e')
        self.max_size = StringVar(value='0')
        Entry(root, textvariable=self.max_size).grid(row=3, column=1)

        Label(root, text="Line Direction:").grid(row=4, column=0, sticky='e')
        self.direction = StringVar(value='Diagonal')
        OptionMenu(root, self.direction, 'Diagonal', 'Horizontal', 'Vertical').grid(row=4, column=1)

        Label(root, text="Line Thickness (pixels):").grid(row=5, column=0, sticky='e')
        self.line_thickness = StringVar(value='1')
        Entry(root, textvariable=self.line_thickness).grid(row=5, column=1)

        Label(root, text="Image Quality:").grid(row=6, column=0, sticky='e')
        self.quality = StringVar(value='High (300 dpi)')
        OptionMenu(root, self.quality, 'Low (100 dpi)', 'Medium (150 dpi)', 'High (300 dpi)').grid(row=6, column=1)

        self.show_plots = BooleanVar(value=True)
        Checkbutton(root, text="Generate Plots", variable=self.show_plots).grid(row=7, column=1)

        self.subtract_background = BooleanVar(value=True)
        Checkbutton(root, text="Subtract Background", variable=self.subtract_background).grid(row=8, column=1)

        Label(root, text="Pixel Size (nm):").grid(row=9, column=0, sticky='e')
        self.pixel_size = StringVar()
        Entry(root, textvariable=self.pixel_size).grid(row=9, column=1)

        self.progress = ttk.Progressbar(root, length=300, mode='determinate')
        self.progress.grid(row=11, column=0, columnspan=3, pady=10)

        Button(root, text="Start", command=self.root.quit).grid(row=10, column=1)

    def browse_input(self):
        self.input_dir.set(filedialog.askdirectory())

    def browse_output(self):
        self.output_dir.set(filedialog.askdirectory())

root = Tk()
gui = UserInputGUI(root)
root.mainloop()

input_dir = gui.input_dir.get()
output_dir = gui.output_dir.get()
min_size = int(gui.min_size.get())
max_size = int(gui.max_size.get())
line_direction = gui.direction.get()
line_thickness = int(gui.line_thickness.get())
show_plots = gui.show_plots.get()
subtract_background = gui.subtract_background.get()
lumen_fraction = 0.30 # central 30% of the line will be used for lumen intensity average. Change to 0.5, 0.4, etc.
pixel_size_nm = gui.pixel_size.get()
pixel_size_nm = float(pixel_size_nm) if pixel_size_nm.strip() else None

quality_map = {
    'Low (100 dpi)': 100,
    'Medium (150 dpi)': 150,
    'High (300 dpi)': 300
}
dpi_setting = quality_map[gui.quality.get()]

raw_dir = os.path.join(output_dir, "raw")
norm_dir = os.path.join(output_dir, "normalized")
os.makedirs(raw_dir, exist_ok=True)
os.makedirs(norm_dir, exist_ok=True)

vesicle_sizes = []
lumen_intensities = []
outside_intensities = []
membrane_mean_top5_values = []
mean_of_two_highest_peaks_values = []
summary_data = []

image_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))]

gui.progress['maximum'] = len(image_files)
for idx, filename in enumerate(image_files):
    gui.progress['value'] = idx + 1
    gui.root.update_idletasks()
    img = cv2.imread(os.path.join(input_dir, filename), cv2.IMREAD_GRAYSCALE)
    if img is None:
        continue

    profile_for_size = get_line_profile(img, 'Horizontal', thickness=line_thickness)
    size_fraction = 0.8 # assuming 20% margin was added while cropping vesicles
    estimated_size_px = int(size_fraction * len(profile_for_size))
    estimated_size = estimated_size_px * pixel_size_nm if pixel_size_nm else estimated_size_px
    if (min_size > 0 and estimated_size_px < min_size) or (max_size > 0 and estimated_size_px > max_size):
        continue

    profile_raw = get_line_profile(img, line_direction, thickness=line_thickness)
    size = len(profile_raw)

    outside_region = np.concatenate([profile_raw[:size // 8], profile_raw[7 * size // 8:]])
    outside_intensity = np.mean(outside_region)

    if subtract_background:
        profile_corrected = profile_raw - outside_intensity
        #profile_corrected = np.clip(profile_corrected, a_min=0, a_max=None)
    else:
        profile_corrected = profile_raw.copy()

    profile_norm = normalize_profile(profile_corrected)
    margin = (1 - lumen_fraction) / 2
    start = int(margin * len(profile_corrected))
    end = int((1 - margin) * len(profile_corrected))
    lumen_region = profile_corrected[start:end]
    lumen_intensity = np.mean(lumen_region)

    membrane_mean_top5, membrane_peak_left, membrane_peak_right, mean_of_two_highest_peaks = compute_membrane_metrics(profile_corrected)

    vesicle_sizes.append(estimated_size)
    lumen_intensities.append(lumen_intensity)
    outside_intensities.append(outside_intensity)
    membrane_mean_top5_values.append(membrane_mean_top5)
    mean_of_two_highest_peaks_values.append(mean_of_two_highest_peaks)
    summary_data.append({
        "Filename": filename,
        "Size": estimated_size,
        "Lumen_Intensity": lumen_intensity,
        "Outside_Intensity": outside_intensity,
        "Membrane_Mean_of_Top_5%": membrane_mean_top5,
        "Membrane_Peak_Left": membrane_peak_left,
        "Membrane_Peak_Right": membrane_peak_right,
        "Mean_of_Two_Highest_Peaks": mean_of_two_highest_peaks
    })

    if show_plots:
        base_name = os.path.splitext(filename)[0]
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", base_name)

        label = f'{"Background-Subtracted " if subtract_background else ""}Intensity (thickness={line_thickness})'
        plt.figure(figsize=(8, 6), dpi=dpi_setting)
        plt.plot(profile_corrected, label=label)
        plt.title(f'{label} - {filename}')
        plt.xlabel(f'Distance ({"nm" if pixel_size_nm else "pixels"})')
        plt.ylabel('Intensity')
        plt.legend()
        plt.tight_layout()
        raw_png_path = os.path.join(raw_dir, f"{safe_name}_raw.png")
        raw_csv_path = os.path.join(raw_dir, f"{safe_name}_raw.csv")
        plt.savefig(raw_png_path)
        plt.close()
        distances = np.linspace(0, size * pixel_size_nm if pixel_size_nm else size, size)
        distance_label = f"Distance ({'nm' if pixel_size_nm else 'pixels'})"
        pd.DataFrame({distance_label: distances, "Intensity": profile_corrected}).to_csv(raw_csv_path, index=False)

        plt.figure(figsize=(8, 6), dpi=dpi_setting)
        plt.plot(distances, profile_norm, label='Normalized Intensity')
        plt.title(f'Normalized Intensity - {filename}')
        plt.xlabel(f'Distance ({"nm" if pixel_size_nm else "pixels"})')
        plt.ylabel('Normalized Intensity')
        plt.legend()
        plt.tight_layout()
        norm_png_path = os.path.join(norm_dir, f"{safe_name}_norm.png")
        norm_csv_path = os.path.join(norm_dir, f"{safe_name}_norm.csv")
        plt.savefig(norm_png_path)
        plt.close()
        pd.DataFrame({distance_label: distances, "Normalized Intensity": profile_norm}).to_csv(norm_csv_path, index=False)

df = pd.DataFrame(summary_data)
df.rename(columns={"Size": f"Size ({'nm' if pixel_size_nm else 'pixels'})"}, inplace=True)
df.to_csv(os.path.join(output_dir, "vesicle_summary.csv"), index=False)

pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.cell(200, 10, txt="Vesicle Analysis Report", ln=True, align='C')

def add_scatter_plot_to_pdf(x, y, x_label, y_label, title, filename):
    plt.figure(figsize=(8, 6), dpi=dpi_setting)
    plt.scatter(x, y)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    output_path = os.path.join(output_dir, filename)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    pdf.image(output_path, w=180)

def add_histogram_to_pdf(values, x_label, title, filename):
    plt.figure(figsize=(8, 6), dpi=dpi_setting)
    plt.hist(values, bins=20, edgecolor='black')
    plt.xlabel(x_label)
    plt.ylabel('Count')
    plt.title(title)
    output_path = os.path.join(output_dir, filename)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    pdf.image(output_path, w=180)

size_label = f'Vesicle Size ({"nm" if pixel_size_nm else "pixels"})'

add_scatter_plot_to_pdf(
    vesicle_sizes, lumen_intensities,
    size_label, 'Lumen Intensity',
    'Vesicle Size vs. Lumen Intensity',
    'scatter_plot_lumen.png'
)

add_scatter_plot_to_pdf(
    vesicle_sizes, membrane_mean_top5_values,
    size_label, 'Membrane Mean of Top 5%',
    'Vesicle Size vs. Membrane Mean of Top 5%',
    'scatter_plot_membrane_top5.png'
)

add_scatter_plot_to_pdf(
    vesicle_sizes, mean_of_two_highest_peaks_values,
    size_label, 'Mean of Two Highest Peaks',
    'Vesicle Size vs. Mean of Two Highest Peaks',
    'scatter_plot_membrane_two_peaks.png'
)

add_histogram_to_pdf(
    vesicle_sizes,
    size_label,
    'Histogram of Vesicle Sizes',
    'size_hist.png'
)

add_histogram_to_pdf(
    lumen_intensities,
    'Lumen Intensity',
    'Histogram of Lumen Intensities',
    'lumen_hist.png'
)

add_histogram_to_pdf(
    membrane_mean_top5_values,
    'Membrane Mean of Top 5%',
    'Histogram of Membrane Mean of Top 5%',
    'membrane_top5_hist.png'
)

add_histogram_to_pdf(
    mean_of_two_highest_peaks_values,
    'Mean of Two Highest Peaks',
    'Histogram of Mean of Two Highest Peaks',
    'membrane_two_peaks_hist.png'
)

pdf.add_page()
desc = df.describe().round(2)
pdf.set_font("Arial", size=10)
pdf.cell(0, 10, "Summary Statistics", ln=True)
for col in desc.columns:
    pdf.cell(0, 10, f"{col}: {desc[col].to_dict()}", ln=True)

pdf.ln(10)
pdf.set_font("Arial", style='B', size=10)
pdf.cell(0, 10, "Notes on Analysis", ln=True)
pdf.set_font("Arial", size=10)
pdf.multi_cell(0, 10,
    f"Vesicle size is estimated as {round(size_fraction*100)}% of the horizontal line profile length, assuming a {round((1 - size_fraction)*100)}% margin added during vesicle cropping.\n"
    f"Lumen intensity is computed as the average pixel value across the central {round(lumen_fraction * 100)}% of the selected profile direction.\n"
    "If 'Subtract Background' is enabled, this intensity is background-subtracted, with background estimated from the outer 12.5% at both ends of the line.\n"
    "Additional membrane metrics are computed from the same profile: the mean of the brightest 5% of profile values (Membrane_Mean_of_Top_5%), the maximum value in the left half (Membrane_Peak_Left), the maximum value in the right half (Membrane_Peak_Right), and the mean of those two half-profile peaks (Mean_of_Two_Highest_Peaks).\n"
    "The PDF report additionally includes vesicle size vs. membrane intensity scatter plots for Membrane_Mean_of_Top_5% and Mean_of_Two_Highest_Peaks, as well as histograms of these membrane metrics.\n"
    "All profile distances are expressed in nanometers if pixel size was provided, otherwise in pixels.\n"
    "Intensity values are unitless and derived from grayscale pixel values.\n"
    "Quartiles (25%, 50%, 75%) refer to the distribution of average lumen intensities across vesicles, not within individual profiles. For example, the 75% value means that 75% of vesicles had a lumen intensity below this number.\n"
    f"Line profiles were averaged across a thickness of {line_thickness} pixel(s) perpendicular to the scan direction."
)

pdf_path = os.path.join(output_dir, "vesicle_report.pdf")
pdf.output(pdf_path)

messagebox.showinfo("Done", f"Analysis complete!\nReport saved to {pdf_path}")
