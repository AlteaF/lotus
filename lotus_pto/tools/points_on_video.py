import argparse
import json
import os
import sys
import cv2


def parse_labelme_json(json_path, target_label="Barnacle"):
    """
    Parses a Labelme JSON file and extracts (x, y) integer coordinates
    for points matching target_label.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Annotation file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    points = []
    for shape in data.get("shapes", []):
        # Filter for points matching the label
        label = shape.get("label", "")
        shape_type = shape.get("shape_type", "point")

        if label == target_label and shape_type == "point":
            for pt in shape.get("points", []):
                # pt is [x, y], convert float coordinates to integer pixel positions
                x = int(round(pt[0]))
                y = int(round(pt[1]))
                points.append((x, y))

    return points


def overlay_annotations_on_video(
    video_path, json_path, output_path, target_label="Barnacle", radius=3
):
    """
    Reads input video, overlays static annotation points, and writes to output_path.
    """
    # 1. Parse annotation points from JSON
    points = parse_labelme_json(json_path, target_label=target_label)
    print(f"Loaded {len(points)} '{target_label}' points from {json_path}")

    # 2. Open input video stream
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open input video: {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps == 0 or total_frames == 0:
        fps = 30.0  # Fallback FPS if metadata is missing

    print(
        f"Video Specs: {width}x{height} @ {fps:.2f} FPS | Total Frames: {total_frames}"
    )

    # 3. Setup output video writer (mp4v codec for .mp4 containers)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Color in BGR for OpenCV: Red is (0, 0, 255) -> hex #FF0000
    color_bgr = (0, 0, 255)

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Draw each annotated point statically onto the frame
        for x, y in points:
            # -1 thickness fills the circle
            cv2.circle(frame, (x, y), radius, color_bgr, thickness=-1)

        out.write(frame)
        frame_count += 1

        if frame_count % 100 == 0 or frame_count == total_frames:
            print(f"Processed frame {frame_count}/{total_frames}")

    # Release video resources
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Annotated video successfully saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Overlay Labelme point annotations statically on a video."
    )
    parser.add_argument(
        "--video", required=True, help="Path to input video (.mp4)"
    )
    parser.add_argument(
        "--json", required=True, help="Path to Labelme JSON annotation file"
    )
    parser.add_argument(
        "--output", required=True, help="Path for output video file"
    )
    parser.add_argument(
        "--label",
        default="Barnacle",
        help="Label to draw (default: 'Barnacle')",
    )
    parser.add_argument(
        "--radius",
        type=int,
        default=3,
        help="Radius of drawn point in pixels (default: 3)",
    )

    args = parser.parse_args()

    overlay_annotations_on_video(
        video_path=args.video,
        json_path=args.json,
        output_path=args.output,
        target_label=args.label,
        radius=args.radius,
    )


if __name__ == "__main__":
    main()


