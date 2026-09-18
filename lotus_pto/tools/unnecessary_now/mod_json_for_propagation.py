import json
import re

input_file = "/Users/alteafogh/Documents/AAU/Lotus/imgs/project-13-at-2026-09-16-11-39-eb7c23db.json"
output_file = "/Users/alteafogh/Documents/AAU/Lotus/imgs/pre_annotations_to_import.json"

with open(input_file, "r") as f:
    tasks = json.load(f)

for task in tasks:
    # 1. Convert annotations to predictions
    if "annotations" in task:
        task["predictions"] = task.pop("annotations")
    
    # 2. Clean the file_upload field if present
    if "file_upload" in task and task["file_upload"]:
        # Removes the hash prefix (e.g., "0b0b59b7-A_2.png" -> "A_2.png")
        task["file_upload"] = re.sub(r'^[a-f0-9]+-', '', task["file_upload"])

    # 3. Clean the data.img path
    if "data" in task and "img" in task["data"]:
        raw_path = task["data"]["img"]
        # Removes "/data/upload/13/20e17a7a-A_2.png" -> "A_2.png"
        clean_filename = re.sub(r'^/data/upload/\d+/[a-f0-9]+-', '', raw_path)
        task["data"]["img"] = clean_filename

with open(output_file, "w") as f:
    json.dump(tasks, f, indent=2)