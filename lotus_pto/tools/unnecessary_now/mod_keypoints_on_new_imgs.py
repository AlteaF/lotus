# import json
# import re
# from pathlib import Path
# import napari
# import numpy as np
# from PIL import Image, ImageDraw


# def load_label_studio_data(json_path: Path):
#     with open(json_path, "r", encoding="utf-8") as f:
#         data = json.load(f)
#     return [data] if isinstance(data, dict) else data


# def interactive_annotator(
#     json_path: str,
#     target_img_dir: str,
#     output_img_dir: str,
#     output_json_path: str,
#     available_labels: list = None,
# ):
#     json_file = Path(json_path)
#     target_dir = Path(target_img_dir)
#     out_img_dir = Path(output_img_dir)
#     out_img_dir.mkdir(parents=True, exist_ok=True)

#     if available_labels is None:
#         available_labels = ["Barnacle", "Starfish", "New_Point"]

#     # Define color palette for labels
#     color_cycle = ["red", "yellow", "purple", "cyan", "green", "orange", "magenta"]
#     label_color_map = {
#         label: color_cycle[i % len(color_cycle)]
#         for i, label in enumerate(available_labels)
#     }

#     raw_data = load_label_studio_data(json_file)
#     updated_json_data = []

#     for item in raw_data:
#         raw_img_path = item.get("img", "")
#         if not raw_img_path:
#             continue

#         # Extract filename (removes Label Studio hash prefix)
#         raw_filename = Path(raw_img_path).name
#         clean_filename = re.sub(r"^[a-f0-9]+-", "", raw_filename)

#         target_image_path = target_dir / clean_filename
#         if not target_image_path.exists():
#             target_image_path = target_dir / raw_filename
#             if not target_image_path.exists():
#                 print(f"Skipping: '{clean_filename}' not found in '{target_dir}'")
#                 continue

#         # Load image details
#         with Image.open(target_image_path) as img:
#             img_w, img_h = img.size
#             img_np = np.array(img.convert("RGB"))

#         # Extract existing points & labels
#         points_coords = []  # Napari uses [y, x] pixel coordinates
#         point_labels = []

#         for key, annotations in item.items():
#             if not isinstance(annotations, list):
#                 continue
#             for ann in annotations:
#                 if isinstance(ann, dict) and "x" in ann and "y" in ann:
#                     px = (ann["x"] / 100.0) * img_w
#                     py = (ann["y"] / 100.0) * img_h
#                     points_coords.append([py, px])

#                     labels = ann.get("keypointlabels", [])
#                     label = labels[0] if labels else "New_Point"
#                     point_labels.append(label)

#         # Launch Napari Viewer
#         viewer = napari.Viewer(title=f"Annotating: {clean_filename}")
#         viewer.add_image(img_np, name="Base Image")

#         # Create Points Layer
#         pts_coords_arr = np.array(points_coords) if points_coords else np.empty((0, 2))
        
#         points_layer = viewer.add_points(
#             pts_coords_arr,
#             properties={"label": point_labels if point_labels else ["New_Point"]},
#             property_choices={"label": available_labels},
#             edge_color="label",
#             edge_color_cycle=color_cycle,
#             face_color="label",
#             face_color_cycle=color_cycle,
#             size=10,
#             name="Keypoints",
#         )

#         print(f"\n--- Editing {clean_filename} ---")
#         print("1. Select 'Keypoints' layer on left.")
#         print("2. Use 'Select points' (P) to DRAG existing points.")
#         print("3. Use 'Add points' (N) to CLICK new points.")
#         print("4. Change active label in layer controls panel on top-left.")
#         print("5. CLOSE the window when finished with this image to advance to next.")

#         napari.run()  # Blocks script execution until window is closed

#         # Extract modified points and labels after user closes window
#         final_coords = points_layer.data  # [y, x]
#         final_labels = points_layer.properties["label"]

#         # Build updated Label Studio JSON structure
#         updated_annotations = []
#         for (py, px), lbl in zip(final_coords, final_labels):
#             x_pct = float((px / img_w) * 100.0)
#             y_pct = float((py / img_h) * 100.0)

#             updated_annotations.append(
#                 {
#                     "x": round(x_pct, 4),
#                     "y": round(y_pct, 4),
#                     "width": 0.34,
#                     "keypointlabels": [str(lbl)],
#                 }
#             )

#         updated_item = dict(item)
#         updated_item["kp-1"] = updated_annotations
#         updated_json_data.append(updated_item)

#         # Save static output image with rendered points
#         with Image.open(target_image_path).convert("RGB") as img_out:
#             draw = ImageDraw.Draw(img_out)
#             radius = 4
#             for (py, px), lbl in zip(final_coords, final_labels):
#                 color = label_color_map.get(lbl, "purple")
#                 draw.ellipse(
#                     [(px - radius, py - radius), (px + radius, py + radius)],
#                     fill=color,
#                     outline="white",
#                 )

#             save_path = out_img_dir / f"annotated_{clean_filename}"
#             img_out.save(save_path)
#             print(f"Saved image output: {save_path}")

#     # Save final aggregated JSON
#     with open(output_json_path, "w", encoding="utf-8") as f:
#         json.dump(updated_json_data, f, indent=2)
#     print(f"\nSaved updated JSON: {output_json_path}")


# if __name__ == "__main__":
#     JSON_PATH = "/Users/alteafogh/Documents/AAU/Lotus/imgs/project-13-at-2026-09-16-11-39-eb7c23db.json"
#     TARGET_IMAGES_DIR = "/Users/alteafogh/Documents/AAU/Lotus/imgs/cropped-20260725-110133_rig1_default_demoAll"
#     OUTPUT_IMG_DIR = "/Users/alteafogh/Documents/AAU/Lotus/imgs/newly_annotated_20260725-110133_rig1_default_demoAll"
#     OUTPUT_JSON_PATH = "/Users/alteafogh/Documents/AAU/Lotus/imgs/newly_annotated_20260725-110133_rig1_default_demoAll_updated_annotations.json"

#     # Define all labels you want accessible in the dropdown
#     LABELS = ["Barnacle", "Starfish", "New_Point"]

#     interactive_annotator(
#         JSON_PATH, TARGET_IMAGES_DIR, OUTPUT_IMG_DIR, OUTPUT_JSON_PATH, LABELS
#     )

import json
import re
from pathlib import Path
import napari
import numpy as np
from PIL import Image, ImageDraw


def load_label_studio_data(json_path: Path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [data] if isinstance(data, dict) else data


def interactive_annotator(
    json_path: str,
    target_img_dir: str,
    output_img_dir: str,
    output_json_path: str,
    available_labels: list = None,
):
    json_file = Path(json_path)
    target_dir = Path(target_img_dir)
    out_img_dir = Path(output_img_dir)
    out_img_dir.mkdir(parents=True, exist_ok=True)

    if available_labels is None:
        available_labels = ["Barnacle", "Starfish", "New_Point"]

    color_cycle = ["red", "yellow", "purple", "cyan", "green", "orange", "magenta"]
    label_color_map = {
        label: color_cycle[i % len(color_cycle)]
        for i, label in enumerate(available_labels)
    }

    raw_data = load_label_studio_data(json_file)
    updated_json_data = []

    # Map existing files in target directory
    existing_files_in_target = {f.name: f for f in target_dir.glob("*") if f.is_file()}
    print(f"\n[DEBUG] Found {len(existing_files_in_target)} files in target directory.")

    for item in raw_data:
        # Extract image path from standard Label Studio 'data' key
        data_dict = item.get("data", {})
        
        # Try finding image key inside 'data' (or fallback to top-level)
        raw_img_path = (
            data_dict.get("img") 
            or data_dict.get("image") 
            or item.get("img") 
            or item.get("image", "")
        )

        if not raw_img_path:
            print(f"[DEBUG] Skipping Task ID {item.get('id')}: No image field found in 'data'.")
            continue

        raw_filename = Path(raw_img_path).name
        # Clean common Label Studio prefixes (e.g. 'fbd86c11-E_3.png' -> 'E_3.png')
        clean_filename = re.sub(r"^[a-f0-9]{8}-", "", raw_filename)
        clean_filename_generic = re.sub(r"^.*?-", "", raw_filename)

        # Match against actual files on disk
        target_image_path = None
        for candidate in [clean_filename, clean_filename_generic, raw_filename]:
            if candidate in existing_files_in_target:
                target_image_path = existing_files_in_target[candidate]
                break

        if not target_image_path:
            print(f"[MISSING] No matching file on disk for: '{raw_filename}'")
            continue

        print(f"\n[SUCCESS] Processing Task {item.get('id')} -> Image: {target_image_path.name}")

        # Open target image
        with Image.open(target_image_path) as img:
            img_w, img_h = img.size
            img_np = np.array(img.convert("RGB"))

        points_coords = []
        point_labels = []

        # Extract annotations from standard Label Studio structure
        annotations_list = item.get("annotations", [])
        if annotations_list:
            # Get results list from first annotation entry
            results = annotations_list[0].get("result", [])
            for res in results:
                if res.get("type") == "keypointlabels":
                    val = res.get("value", {})
                    if "x" in val and "y" in val:
                        # Convert percentage coordinates to pixel coordinates
                        px = (val["x"] / 100.0) * img_w
                        py = (val["y"] / 100.0) * img_h
                        points_coords.append([py, px])  # Napari uses [y, x]

                        labels = val.get("keypointlabels", [])
                        label = labels[0] if labels else "New_Point"
                        point_labels.append(label)

        # Launch Napari Viewer
        viewer = napari.Viewer(title=f"Annotating Task {item.get('id')}: {target_image_path.name}")
        viewer.add_image(img_np, name="Base Image")

        pts_coords_arr = np.array(points_coords) if points_coords else np.empty((0, 2))
        
        points_layer = viewer.add_points(
            pts_coords_arr,
            properties={"label": point_labels if point_labels else ["New_Point"]},
            property_choices={"label": available_labels},
            border_color="label",
            border_color_cycle=color_cycle,
            face_color="label",
            face_color_cycle=color_cycle,
            size=10,
            name="Keypoints",
        )

        print("--> Adjust points in Napari, then CLOSE the window to proceed.")
        napari.run()

        # Extract updated points from Napari layer
        final_coords = points_layer.data
        final_labels = points_layer.properties["label"]

        # Rebuild standard Label Studio result objects
        updated_results = []
        for idx, ((py, px), lbl) in enumerate(zip(final_coords, final_labels)):
            x_pct = float((px / img_w) * 100.0)
            y_pct = float((py / img_h) * 100.0)

            updated_results.append({
                "original_width": img_w,
                "original_height": img_h,
                "image_rotation": 0,
                "value": {
                    "x": round(x_pct, 4),
                    "y": round(y_pct, 4),
                    "width": 0.34,
                    "keypointlabels": [str(lbl)],
                },
                "id": f"pt_{idx}",
                "from_name": "kp-1",
                "to_name": "img-1",
                "type": "keypointlabels",
                "origin": "manual"
            })

        # Deep copy item structure and inject updated results
        updated_item = dict(item)
        if "annotations" in updated_item and len(updated_item["annotations"]) > 0:
            updated_item["annotations"][0]["result"] = updated_results
        else:
            updated_item["annotations"] = [{"result": updated_results}]
            
        updated_json_data.append(updated_item)

        # Save static image output
        with Image.open(target_image_path).convert("RGB") as img_out:
            draw = ImageDraw.Draw(img_out)
            radius = 4
            for (py, px), lbl in zip(final_coords, final_labels):
                color = label_color_map.get(lbl, "purple")
                draw.ellipse(
                    [(px - radius, py - radius), (px + radius, py + radius)],
                    fill=color,
                    outline="white",
                )

            save_path = out_img_dir / f"annotated_{target_image_path.name}"
            img_out.save(save_path)
            print(f"Saved static rendering: {save_path}")

    # Write output JSON
    if updated_json_data:
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(updated_json_data, f, indent=2)
        print(f"\n[DONE] Saved updated JSON to: {output_json_path}")



if __name__ == "__main__":
    # Use raw string syntax r"..." for Windows file paths
    JSON_PATH = "/Users/alteafogh/Documents/AAU/Lotus/imgs/project-13-at-2026-09-15-13-50-eb7c23db.json"
    TARGET_IMAGES_DIR = "/Users/alteafogh/Documents/AAU/Lotus/imgs/cropped-20260725-110133_rig1_default_demoAll"
    OUTPUT_IMG_DIR = "/Users/alteafogh/Documents/AAU/Lotus/imgs/newly_annotated_20260725-110133_rig1_default_demoAll"
    OUTPUT_JSON_PATH = "/Users/alteafogh/Documents/AAU/Lotus/imgs/newly_annotated_20260725-110133_rig1_default_demoAll_updated_annotations.json"

    LABELS = ["Barnacle", "Starfish", "New_Point"]

    interactive_annotator(
        JSON_PATH, TARGET_IMAGES_DIR, OUTPUT_IMG_DIR, OUTPUT_JSON_PATH, LABELS
    )