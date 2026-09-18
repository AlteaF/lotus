import json
import re
from label_studio_sdk import Client

# 1. Configuration
LABEL_STUDIO_URL = "http://localhost:8080"  # Update with your URL
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6ODA5Njc2MDY1NiwiaWF0IjoxNzg5NTYwNjU2LCJqdGkiOiI2MWIwZDUwZDRlMDc0MzE5YmFhNjU5MDEzZTY5OThhMyIsInVzZXJfaWQiOiIxIn0.j9FHluNuLUV3qGenh2uULGddxbxXax3RSdZ3gwpC1ZE"       # Find in Account & Settings -> API Key
NEW_PROJECT_ID = 15                         # Your new project ID

EXPORTED_JSON_FILE = "/Users/alteafogh/Documents/AAU/Lotus/imgs/project-13-at-2026-09-16-11-39-eb7c23db.json"

# 2. Connect to Label Studio
ls = Client(url=LABEL_STUDIO_URL, api_key=API_KEY)
project = ls.get_project(NEW_PROJECT_ID)

# 3. Get all existing tasks (the newly uploaded images) in the project
existing_tasks = project.get_tasks()

# Create a mapping of clean filename -> task ID
# Example: "A_0.png" -> 1052
filename_to_task_id = {}
for task in existing_tasks:
    raw_img = task["data"]["img"]
    # Extract clean filename from the newly uploaded image path
    clean_name = re.sub(r"^/data/upload/\d+/[a-f0-9]+-", "", raw_img)
    filename_to_task_id[clean_name] = task["id"]

# 4. Load original exported JSON
with open(EXPORTED_JSON_FILE, "r") as f:
    old_tasks = json.load(f)

# 5. Post annotations directly as predictions onto the matched tasks
success_count = 0

for old_task in old_tasks:
    # Extract clean filename from the old JSON task
    old_raw_path = old_task["data"]["img"]
    clean_old_name = re.sub(r"^/data/upload/\d+/[a-f0-9]+-", "", old_raw_path)

    # Check if this filename exists in the new project
    if clean_old_name in filename_to_task_id:
        target_task_id = filename_to_task_id[clean_old_name]
        
        # Extract results array from the old completed annotations
        if "annotations" in old_task and len(old_task["annotations"]) > 0:
            annotation_results = old_task["annotations"][0]["result"]

            # Create a prediction payload attached to the target task
            project.create_prediction(
                task_id=target_task_id,
                result=annotation_results,
                score=1.0
            )
            success_count += 1
            print(f"Successfully linked annotations for: {clean_old_name}")
    else:
        print(f"Warning: Could not find matching image in new project for: {clean_old_name}")

print(f"\nDone! Attached keypoints to {success_count} images.")