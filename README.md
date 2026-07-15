# Automated-Vesicle-Detection-and-Intensity-Analysis-Pipeline
A modular Python-based pipeline for automated detection, extraction, and quantitative analysis of fluorescently labeled vesicles (e.g. liposomes). The workflow supports both pretrained YOLO models and new model training using manually annotated data. The scripts allow users to run the entire pipeline or individual components as needed.

1. Channel Extraction

Raw microscope images acquired in .czi format are first processed using 1st_czi_splitchannels.py.
This script reads the image stack, identifies all fluorescence channels from the embedded metadata, and exports each channel as a TIFF. An optional percentile-based contrast enhancement and brightness scaling are available to improve visibility of vesicles. A graphical interface allows users to preview contrast settings in real time and batch-process multiple files. Both raw and enhanced images are saved for downstream annotation or automated detection.

2. Preparing Training Data for YOLO

When training a new vesicle-detection model, the images are organized using 2nd_prepare_yolo_dataset.py.
This tool:

Converts .tiff images to .jpg while preserving naming consistency.
Splits images into training and validation sets (default 80/20).
Copies YOLO-formatted annotations when present.
Generates a data.yaml file defining dataset structure and class names.

The output is a fully YOLO-compatible dataset suitable for training in Colab or any YOLO training environment.

3. YOLO-Based Vesicle Detection

Vesicle detection is performed in the accompanying notebook 3rd_vesicle_detection_yolo_colab_gpu.ipynb.
The notebook provides:

Training routines for YOLOv8/YOLOv11 models using the dataset from Step 2.
GPU-accelerated inference to generate bounding-box predictions on new images.
Output in standard YOLO.txt annotation format (normalized box coordinates).

Users may choose between training a custom detector or applying a pretrained model.

4. Cropping Detected Vesicles

Detected vesicles are cropped from the original images using 4th_extract_squares_yoloCoords.py.
For each YOLO bounding box, the script:

Converts normalized coordinates to pixel dimensions.
Extracts a square region centered on the detected vesicle (optionally expanding the crop via a user-defined margin).
Saves each cropped vesicle as an individual TIFF or JPEG.

This step produces standardized vesicle crops that can be directly analyzed in the final stage.

5. Quantitative Intensity Analysis

Vesicle properties are quantified using 5th_vesicle_linescan_analyzer_v13.py.
This graphical tool performs line-profile–based analysis on each cropped vesicle:

A horizontal, vertical, or diagonal intensity profile (with user-defined thickness) is extracted from the vesicle image.
Vesicle size is estimated from the profile length, and lumen intensity is computed from the central portion of the profile.
Optional background subtraction uses intensity from the outer regions of each profile.
Normalized profiles, raw profiles, and corresponding CSV files are saved for each vesicle.
A summary table, size and intensity histograms, scatterplots, and a PDF report are generated automatically.

This step provides quantitative metrics such as vesicle diameter, lumen brightness, and background intensity, enabling statistical comparisons across experimental groups.

Summary

Together, these five components constitute a complete image-analysis workflow:
(1) channel extraction, (2) dataset preparation, (3) YOLO-based vesicle detection, (4) vesicle cropping, and (5) quantitative intensity analysis.
The modular design allows users to substitute custom YOLO models, adjust contrast or detection parameters, or independently run only the analysis stage on pre-cropped vesicles.

## External Software Requirement: labelImg

Manual annotation of vesicles for YOLO training requires the external tool **labelImg**, which is **not included** in this repository.

labelImg is an open-source graphical annotation tool available at:
https://github.com/tzutalin/labelImg

Annotations generated with labelImg (YOLO format) are used as inputs to 2nd_prepare_yolo_dataset.py.

## Dependencies
numpy, opencv-python, pillow, czifile, tkinter, xml, pathlib, shutil, random, yaml, pandas, matplotlib, tqdm, fpdf





