import argparse
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw

LABEL_COLORS = {
    "Barnacle": "red",
    "Starfish": "yellow",
    "default": "cyan",
}


def draw_labelme_single_image(
    json_path: Path, target_image_path: Path, output_dir: Path
):
    """Draws Labelme annotations onto a single target image."""
    if not json_path.is_file():
        print(f"Error: JSON file not found at '{json_path}'")
        return

    if not target_image_path.is_file():
        print(f"Error: Image file not found at '{target_image_path}'")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON '{json_path.name}': {e}")
        return

    # Open image
    try:
        with Image.open(target_image_path).convert("RGB") as img:
            draw = ImageDraw.Draw(img)

            # Labelme shapes array contains all annotations
            shapes = data.get("shapes", [])

            for shape in shapes:
                label = shape.get("label", "default")
                color = LABEL_COLORS.get(label, LABEL_COLORS["default"])
                points = shape.get("points", [])

                for pt in points:
                    if len(pt) < 2:
                        continue

                    # Labelme coordinates are already absolute pixel values [x, y]
                    px, py = pt[0], pt[1]

                    # Draw point marker
                    radius = 3
                    draw.ellipse(
                        [(px - radius, py - radius), (px + radius, py + radius)],
                        fill=color,
                        outline="white",
                    )

            save_path = output_dir / f"annotated_{target_image_path.name}"
            img.save(save_path)
            print(f"Saved: {save_path}")

    except Exception as e:
        print(f"Error processing image '{target_image_path.name}': {e}")


def draw_labelme_annotations(
    json_input_path: str, target_img_input: str, output_dir: str
):
    """Handles both single-file and folder-by-folder execution modes."""
    json_path = Path(json_input_path)
    target_path = Path(target_img_input)
    out_dir = Path(output_dir)

    # ---------------------------------------------------------
    # Mode 1: Folder-by-folder
    # ---------------------------------------------------------
    if json_path.is_dir() and target_path.is_dir():
        print("Running in FOLDER-BY-FOLDER mode...")
        # Match images to their corresponding json files (e.g., A_0.png <-> A_0.json)
        valid_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
        image_files = [
            f for f in target_path.iterdir() if f.suffix.lower() in valid_extensions
        ]

        if not image_files:
            print(f"No valid image files found in '{target_path}'")
            return

        for img_file in image_files:
            # Look for matching json (e.g. A_0.json for A_0.png)
            matching_json = json_path / f"{img_file.stem}.json"
            if matching_json.is_file():
                draw_labelme_single_image(matching_json, img_file, out_dir)
            else:
                print(f"Skipping '{img_file.name}': No matching JSON file found.")

    # ---------------------------------------------------------
    # Mode 2: Single image & file
    # ---------------------------------------------------------
    elif json_path.is_file() and target_path.is_file():
        print("Running in SINGLE-FILE mode...")
        draw_labelme_single_image(json_path, target_path, out_dir)

    # ---------------------------------------------------------
    # Mode 3: Labelme project JSON pointing to a target image/folder
    # ---------------------------------------------------------
    elif json_path.is_file() and target_path.is_dir():
        print("Running in SINGLE JSON to IMAGE FOLDER mode...")
        # Labelme json filename usually matches image filename (e.g. A_0.json -> A_0.png)
        img_name = json_path.stem
        matched_image = None
        for ext in [".png", ".jpg", ".jpeg"]:
            candidate = target_path / f"{img_name}{ext}"
            if candidate.is_file():
                matched_image = candidate
                break

        if matched_image:
            draw_labelme_single_image(json_path, matched_image, out_dir)
        else:
            print(f"Could not find matching image for '{json_path.name}' in '{target_path}'")

    else:
        print("Error: Invalid inputs. Both arguments must be paths to files or directories.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Overlay Labelme JSON annotations on images (Supports file-by-file or folder-by-folder)."
    )
    parser.add_argument(
        "-j",
        "--json",
        required=True,
        help="Path to a Labelme JSON file OR directory containing JSON files.",
    )
    parser.add_argument(
        "-i",
        "--image",
        required=True,
        help="Path to a single image file OR directory containing images.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Path to destination directory for annotated output images.",
    )

    args = parser.parse_args()

    draw_labelme_annotations(args.json, args.image, args.output)










## this is the old version for label studio, single image and single file 

# import json
# import os
# import re
# from pathlib import Path
# from PIL import Image, ImageDraw


# def draw_label_studio_annotations(
#     json_path: str, target_img_dir: str, output_dir: str
# ):
#     json_file = Path(json_path)
#     target_dir = Path(target_img_dir)
#     out_dir = Path(output_dir)

#     out_dir.mkdir(parents=True, exist_ok=True)

#     with open(json_file, "r", encoding="utf-8") as f:
#         data = json.load(f)

#     # Wrap single object in list if JSON isn't an array of records
#     if isinstance(data, dict):
#         data = [data]

#     # Color map for different labels
#     label_colors = {
#         "Barnacle": "red",
#         "Starfish": "yellow",
#         "default": "cyan",
#     }

#     for item in data:
#         raw_img_path = item.get("img", "")
#         if not raw_img_path:
#             continue

#         # Extract filename (removes Label Studio hash prefix e.g., 'fbd86c11-E_3.png' -> 'E_3.png')
#         raw_filename = Path(raw_img_path).name
#         clean_filename = re.sub(r"^[a-f0-9]+-", "", raw_filename)

#         # Locate image in target directory
#         target_image_path = target_dir / clean_filename
#         if not target_image_path.exists():
#             # Fallback check for raw filename
#             target_image_path = target_dir / raw_filename
#             if not target_image_path.exists():
#                 print(
#                     f"Skipping: '{clean_filename}' not found in '{target_dir}'"
#                 )
#                 continue

#         # Open target image
#         with Image.open(target_image_path).convert("RGB") as img:
#             draw = ImageDraw.Draw(img)
#             img_w, img_h = img.size

#             # Iterate over annotation keys (e.g., 'kp-1', 'kp-2', etc.)
#             for key, annotations in item.items():
#                 if not isinstance(annotations, list):
#                     continue

#                 for ann in annotations:
#                     if not isinstance(ann, dict) or "x" not in ann:
#                         continue

#                     # Convert 0-100% coordinates to absolute pixels
#                     px = (ann["x"] / 100.0) * img_w
#                     py = (ann["y"] / 100.0) * img_h

#                     # Determine label color
#                     labels = ann.get("keypointlabels", [])
#                     label = labels[0] if labels else "default"
#                     color = label_colors.get(label, label_colors["default"])

#                     # Draw point marker (radius = 5px)
#                     radius = 3
#                     draw.ellipse(
#                         [
#                             (px - radius, py - radius),
#                             (px + radius, py + radius),
#                         ],
#                         fill=color,
#                         outline="white",
#                     )

#             # Save annotated image
#             save_path = out_dir / f"annotated_{clean_filename}"
#             img.save(save_path)
#             print(f"Saved: {save_path}")


# if __name__ == "__main__":
#     JSON_PATH = "/Users/alteafogh/Documents/AAU/Lotus/imgs/project-13-at-2026-09-15-13-57-eb7c23db.json"
#     TARGET_IMAGES_DIR = "/Users/alteafogh/Documents/AAU/Lotus/imgs/cropped-20260725-110133_rig1_default_demoAll"
#     OUTPUT_DIR = "/Users/alteafogh/Documents/AAU/Lotus/imgs/newly_annotated_20260725-110133_rig1_default_demoAll"

#     draw_label_studio_annotations(JSON_PATH, TARGET_IMAGES_DIR, OUTPUT_DIR)