import os
import re
from pathlib import Path
from PIL import Image


def parse_coordinates_txt(coords_path):
    """Parses custom formatted text file containing sample crop parameters."""
    samples = {}
    current_sample = None

    # Matches sample headers, e.g., "  sample_01:"
    sample_header_re = re.compile(r"^\s*([a-zA-Z0-9_\-]+):\s*$")
    # Matches key-value pairs, e.g., "    OffsetX: 100"
    key_val_re = re.compile(r"^\s*([a-zA-Z0-9_\-]+):\s*([0-9\.]+)\s*$")

    with open(coords_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str or line_str.startswith("<<:"):
                continue

            header_match = sample_header_re.match(line)
            if header_match:
                current_sample = header_match.group(1)
                samples[current_sample] = {}
                continue

            kv_match = key_val_re.match(line)
            if kv_match and current_sample:
                key, val = kv_match.group(1), kv_match.group(2)
                samples[current_sample][key] = (
                    float(val) if "." in val else int(val)
                )

    return samples


def process_image_crops(image_path_str: str, coords_path_str: str, file_name):
    image_path = Path(image_path_str)
    coords_path = Path(coords_path_str)

    # 1. File Existence Checks
    if not image_path.is_file():
        print(f"Error: Image file not found at '{image_path}'")
        return

    if not coords_path.is_file():
        print(f"Error: Coordinates text file not found at '{coords_path}'")
        return

    # 2. Output Directory Creation
    output_dir = image_path.parent / f"cropped_{file_name}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 3. Load Base Image
    try:
        base_img = Image.open(image_path)
        img_w, img_h = base_img.size
    except Exception as e:
        print(f"Error loading image: {e}")
        return

    # 4. Parse Text File
    try:
        entries = parse_coordinates_txt(coords_path)
    except Exception as e:
        print(f"Error reading coordinates file: {e}")
        return

    if not entries:
        print("Warning: No valid sample entries found in text file.")
        return

    # 5. Crop and Save Loop
    required_keys = ["OffsetX", "OffsetY", "BoxWidth", "BoxHeight"]

    for sample_name, settings in entries.items():
        missing_keys = [k for k in required_keys if k not in settings]
        if missing_keys:
            print(
                f"Skipping '{sample_name}': Missing parameters {missing_keys}"
            )
            continue

        try:
            x0 = int(settings["OffsetX"])
            y0 = int(settings["OffsetY"])
            box_w = int(settings["BoxWidth"])
            box_h = int(settings["BoxHeight"])
        except ValueError:
            print(
                f"Skipping '{sample_name}': Non-numeric crop values detected."
            )
            continue

        x1 = x0 + box_w
        y1 = y0 + box_h

        # Bounds Checking
        if x0 < 0 or y0 < 0 or x1 > img_w or y1 > img_h or box_w <= 0 or box_h <= 0:
            print(
                f"Skipping '{sample_name}': Bounding box [{x0}, {y0}, {x1}, {y1}] "
                f"exceeds image dimensions ({img_w}x{img_h})."
            )
            continue

        # Execute Crop & Export
        try:
            cropped_img = base_img.crop((x0, y0, x1, y1))
            output_file = output_dir / f"{sample_name}.png"
            cropped_img.save(output_file, format="PNG")
            print(f"Successfully generated: {output_file.name}")
        except Exception as e:
            print(f"Skipping '{sample_name}': Save error ({e}).")


if __name__ == "__main__":
    # Replace these with your actual target paths
    path= "/Users/alteafogh/Documents/AAU/Lotus/imgs/images/"
    file_name = "20260720-064736_rig1_default_lightsOff.png"
    
    IMAGE_FILE = f"../../imgs/images/{file_name}"
    COORDS_FILE = f"../../imgs/coordinates.txt"

    process_image_crops(IMAGE_FILE, COORDS_FILE, file_name)