import sys
import cv2
import os


def get_screen_size(default=(1920, 1080)):
    """Best-effort screen size lookup; falls back to `default` if unavailable."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        size = (root.winfo_screenwidth(), root.winfo_screenheight())
        root.destroy()
        return size
    except Exception:
        return default


def prompt_sample_name():
    """Prompt for sample name using console input."""
    print("Enter sample name (or press Enter to cancel):")
    return input().strip()


def prompt_continue():
    """Prompt to continue using console input."""
    while True:
        print("Label another crop? (y/n):")
        choice = input().strip().lower()
        if choice in ('y', 'n'):
            return choice == 'y'
        print("Please enter 'y' or 'n'.")


def save_coordinates(img_path, sample_name, x0, y0, auto_x, auto_y, box_w, box_h, roi_w, roi_h):
    """Save coordinates to a text file in the same directory as the image."""
    dir_path = os.path.dirname(img_path)
    output_path = os.path.join(dir_path, "coordinates.txt")
    
    with open(output_path, "a") as f:
        f.write(f"  {sample_name}:\n")
        f.write(f"    <<: *sample_crop_settings\n")
        f.write(f"    OffsetX: {x0}\n")
        f.write(f"    OffsetY: {y0}\n")
        f.write(f"    AutoOffsetX: {auto_x}\n")
        f.write(f"    AutoOffsetY: {auto_y}\n")
        f.write(f"    BoxWidth: {box_w}\n")
        f.write(f"    BoxHeight: {box_h}\n")
        f.write(f"    ROIWidth: {roi_w}\n")
        f.write(f"    ROIHeight: {roi_h}\n")
        f.write("\n")


def main():
    if len(sys.argv) not in (4, 6):
        print("Usage: python get_all_crop_coordinates.py <image_path> <box_width> <box_height> [roi_width roi_height]")
        sys.exit(1)

    # Parse command-line arguments
    img_path = sys.argv[1]
    box_w = int(sys.argv[2])
    box_h = int(sys.argv[3])

    if len(sys.argv) == 6:
        roi_w = int(sys.argv[4])
        roi_h = int(sys.argv[5])
        if roi_w <= 0 or roi_h <= 0:
            print("ROI width and height must be positive integers.")
            sys.exit(1)
    else:
        roi_w = box_w
        roi_h = box_h

    img = cv2.imread(img_path)
    if img is None:
        print(f"Could not load image: {img_path}")
        sys.exit(1)

    # Scale to screen size
    h, w = img.shape[:2]
    screen_w, screen_h = get_screen_size()
    margin = 0.9
    scale = min(1.0, (screen_w * margin) / w, (screen_h * margin) / h)
    disp_w, disp_h = int(w * scale), int(h * scale)
    disp_img = cv2.resize(img, (disp_w, disp_h), interpolation=cv2.INTER_AREA) if scale != 1.0 else img

    window = "Crop Selector (click to print top-left coord, q/Esc to quit)"
    cv2.namedWindow(window)

    state = {"x": w // 2, "y": h // 2}  # always stored in full-res coordinates

    def clamp_top_left(cx, cy):
        # Box is centered on the cursor; clamp so it stays inside the image.
        x0 = max(0, min(cx - box_w // 2, w - box_w))
        y0 = max(0, min(cy - box_h // 2, h - box_h))
        return x0, y0

    def on_mouse(event, x, y, flags, param):
        # Convert displayed-window coords back to full-resolution coords.
        state["x"], state["y"] = int(x / scale), int(y / scale)
        if event == cv2.EVENT_LBUTTONDOWN:
            x0, y0 = clamp_top_left(state["x"], state["y"])
            
            # Ensure OpenCV window is active
            cv2.setWindowProperty(window, cv2.WND_PROP_VISIBLE, 1)
            
            sample_name = prompt_sample_name()
            if not sample_name:
                return
            
            auto_x = int(x0 + (box_w - roi_w) / 2)
            auto_y = int(y0 + (box_h - roi_h) / 2)
            
            # Save to file
            save_coordinates(img_path, sample_name, x0, y0, auto_x, auto_y, box_w, box_h, roi_w, roi_h)
            
            # Print to console
            print(f"  {sample_name}:")
            print(f"    <<: *sample_crop_settings")
            print(f'    OffsetX: {x0}')
            print(f'    OffsetY: {y0}')
            print(f'    AutoOffsetX: {auto_x}')
            print(f'    AutoOffsetY: {auto_y}')
            
            # Ask if the user wants to continue
            if not prompt_continue():
                cv2.destroyAllWindows()
                sys.exit(0)

    cv2.setMouseCallback(window, on_mouse)

    while True:
        frame = disp_img.copy()
        x0, y0 = clamp_top_left(state["x"], state["y"])
        dx0, dy0 = int(x0 * scale), int(y0 * scale)
        dbw, dbh = max(1, int(box_w * scale)), max(1, int(box_h * scale))
        cv2.rectangle(frame, (dx0, dy0), (dx0 + dbw, dy0 + dbh), (0, 255, 0), 2)

        if roi_w is not None:
            roi_x = x0 + (box_w - roi_w) // 2
            roi_y = y0 + (box_h - roi_h) // 2
            droi_x = int(roi_x * scale)
            droi_y = int(roi_y * scale)
            droi_w = max(1, int(roi_w * scale))
            droi_h = max(1, int(roi_h * scale))
            cv2.rectangle(frame, (droi_x, droi_y), (droi_x + droi_w, droi_y + droi_h), (0, 128, 255), 1)

        label = f"top-left: ({x0}, {y0})  size: {box_w}x{box_h}  (view scale {scale:.2f})"
        if roi_w is not None:
            label += f"  ROI: {roi_w}x{roi_h}"
        cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.imshow(window, frame)

        key = cv2.waitKey(20) & 0xFF
        if key in (ord('q'), 27):  # q or Esc
            break
        if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()