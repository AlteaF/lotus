import json
import os
import re
from pathlib import Path
from PIL import Image, ImageDraw


def draw_label_studio_annotations(
    json_path: str, target_img_dir: str, output_dir: str
):
    json_file = Path(json_path)
    target_dir = Path(target_img_dir)
    out_dir = Path(output_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Wrap single object in list if JSON isn't an array of records
    if isinstance(data, dict):
        data = [data]

    # Color map for different labels
    label_colors = {
        "Barnacle": "red",
        "Starfish": "yellow",
        "default": "cyan",
    }

    for item in data:
        raw_img_path = item.get("img", "")
        if not raw_img_path:
            continue

        # Extract filename (removes Label Studio hash prefix e.g., 'fbd86c11-E_3.png' -> 'E_3.png')
        raw_filename = Path(raw_img_path).name
        clean_filename = re.sub(r"^[a-f0-9]+-", "", raw_filename)

        # Locate image in target directory
        target_image_path = target_dir / clean_filename
        if not target_image_path.exists():
            # Fallback check for raw filename
            target_image_path = target_dir / raw_filename
            if not target_image_path.exists():
                print(
                    f"Skipping: '{clean_filename}' not found in '{target_dir}'"
                )
                continue

        # Open target image
        with Image.open(target_image_path).convert("RGB") as img:
            draw = ImageDraw.Draw(img)
            img_w, img_h = img.size

            # Iterate over annotation keys (e.g., 'kp-1', 'kp-2', etc.)
            for key, annotations in item.items():
                if not isinstance(annotations, list):
                    continue

                for ann in annotations:
                    if not isinstance(ann, dict) or "x" not in ann:
                        continue

                    # Convert 0-100% coordinates to absolute pixels
                    px = (ann["x"] / 100.0) * img_w
                    py = (ann["y"] / 100.0) * img_h

                    # Determine label color
                    labels = ann.get("keypointlabels", [])
                    label = labels[0] if labels else "default"
                    color = label_colors.get(label, label_colors["default"])

                    # Draw point marker (radius = 5px)
                    radius = 3
                    draw.ellipse(
                        [
                            (px - radius, py - radius),
                            (px + radius, py + radius),
                        ],
                        fill=color,
                        outline="white",
                    )

            # Save annotated image
            save_path = out_dir / f"annotated_{clean_filename}"
            img.save(save_path)
            print(f"Saved: {save_path}")


if __name__ == "__main__":
    JSON_PATH = "/Users/alteafogh/Documents/AAU/Lotus/imgs/project-13-at-2026-09-15-13-57-eb7c23db.json"
    TARGET_IMAGES_DIR = "/Users/alteafogh/Documents/AAU/Lotus/imgs/cropped-20260725-110133_rig1_default_demoAll"
    OUTPUT_DIR = "/Users/alteafogh/Documents/AAU/Lotus/imgs/newly_annotated_20260725-110133_rig1_default_demoAll"

    draw_label_studio_annotations(JSON_PATH, TARGET_IMAGES_DIR, OUTPUT_DIR)