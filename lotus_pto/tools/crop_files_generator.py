"""
GUI for the image crop generator tool.

A Tkinter GUI wrapper that uses `utils_f.parsing` to filter captured images by
rig / camera / lighting / date range / daily time windows, parses a `coordinates.txt`
file, crops each filtered image into a subfolder named `cropped_<imgname>`, and
optionally copies matching JSON annotation files into the crop directories.
"""

import json
import logging
import os
import re
import shutil
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from PIL import Image

# Ensure project root and script directory are importable
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_SCRIPT_DIR))
sys.path.insert(0, _SCRIPT_DIR)

from utils_f import parsing


class _LogHandler(logging.Handler):
    """Route logging records to a GUI callback (safe across threads)."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        try:
            self.callback(f"[{record.levelname}] {record.getMessage()}")
        except Exception:
            pass


# ----------------------------------------------------------------------
# Core Parsing & Cropping Logic
# ----------------------------------------------------------------------
def parse_coordinates_txt(coords_path):
    """Parses custom formatted text file containing sample crop parameters."""
    samples = {}
    current_sample = None

    sample_header_re = re.compile(r"^\s*([a-zA-Z0-9_\-]+):\s*$")
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


def process_image_crops(image_path_str, output_parent_dir, entries, annotations_dir=None, logger=None):
    """Crops a single image based on parsed coordinates and optionally copies annotations."""
    image_path = Path(image_path_str)

    if not image_path.is_file():
        if logger:
            logger.error(f"Image file not found: '{image_path}'")
        return

    # Folder naming requirement: cropped_{imgname}
    img_stem = image_path.stem
    output_dir = Path(output_parent_dir) / f"cropped_{img_stem}"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        base_img = Image.open(image_path)
        img_w, img_h = base_img.size
    except Exception as e:
        if logger:
            logger.error(f"Error loading image '{image_path.name}': {e}")
        return

    required_keys = ["OffsetX", "OffsetY", "BoxWidth", "BoxHeight"]

    for sample_name, settings in entries.items():
        missing_keys = [k for k in required_keys if k not in settings]
        if missing_keys:
            if logger:
                logger.warning(f"[{img_stem}] Skipping '{sample_name}': Missing keys {missing_keys}")
            continue

        try:
            x0 = int(settings["OffsetX"])
            y0 = int(settings["OffsetY"])
            box_w = int(settings["BoxWidth"])
            box_h = int(settings["BoxHeight"])
        except ValueError:
            if logger:
                logger.warning(f"[{img_stem}] Skipping '{sample_name}': Non-numeric crop values.")
            continue

        x1 = x0 + box_w
        y1 = y0 + box_h

        if x0 < 0 or y0 < 0 or x1 > img_w or y1 > img_h or box_w <= 0 or box_h <= 0:
            if logger:
                logger.warning(f"[{img_stem}] Skipping '{sample_name}': Out of bounds [{x0},{y0},{x1},{y1}] vs image size ({img_w}x{img_h}).")
            continue

        try:
            cropped_img = base_img.crop((x0, y0, x1, y1))
            output_file = output_dir / f"{sample_name}.png"
            cropped_img.save(output_file, format="PNG")
        except Exception as e:
            if logger:
                logger.error(f"[{img_stem}] Error saving crop '{sample_name}': {e}")
            continue

        # Optional Annotation Copying
        if annotations_dir:
            ann_file = Path(annotations_dir) / f"{sample_name}.json"
            if ann_file.is_file():
                dest_ann = output_dir / f"{sample_name}.json"
                try:
                    shutil.copy2(ann_file, dest_ann)
                except Exception as e:
                    if logger:
                        logger.error(f"Failed copying annotation for '{sample_name}': {e}")
            elif logger:
                logger.debug(f"Annotation file not found: {ann_file}")


# ----------------------------------------------------------------------
# Main Application Class
# ----------------------------------------------------------------------
class ImageCropperGuiApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Image Crop Generator")
        self.root.geometry("760x900")
        self.root.resizable(False, False)

        self.time_periods = []
        self._records_cache = None
        self._cache_input_dir = None
        self._filtered_records = []

        self._build_scrollable_layout()
        self._set_defaults()

    def _build_scrollable_layout(self):
        canvas = tk.Canvas(self.root, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        main_frame = ttk.Frame(canvas, padding="15")
        main_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=main_frame, anchor="nw")

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-event.delta / 120), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._build_io_section(main_frame)
        self._build_date_section(main_frame)
        self._build_filter_section(main_frame)
        self._build_time_period_section(main_frame)
        self._build_settings_section(main_frame)
        self._build_run_section(main_frame)
        self._build_log_section(main_frame)

    def _build_io_section(self, parent):
        frame = ttk.LabelFrame(parent, text=" Directories & Files ", padding="10")
        frame.pack(fill=tk.X, pady=5)

        # Input Images Directory
        ttk.Label(frame, text="Input Images Folder:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.input_ent = ttk.Entry(frame)
        self.input_ent.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=5)
        ttk.Button(frame, text="Browse...", command=self.browse_input, width=10).grid(row=0, column=2, pady=2)

        # Coordinates File
        ttk.Label(frame, text="Coordinates File:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.coords_ent = ttk.Entry(frame)
        self.coords_ent.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=5)
        ttk.Button(frame, text="Browse...", command=self.browse_coords, width=10).grid(row=1, column=2, pady=2)

        # Output Directory
        ttk.Label(frame, text="Output Folder:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.output_ent = ttk.Entry(frame)
        self.output_ent.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=5)
        ttk.Button(frame, text="Browse...", command=self.browse_output, width=10).grid(row=2, column=2, pady=2)

        # Optional Annotations Directory
        ttk.Label(frame, text="Annotations Folder (Opt):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.annotations_ent = ttk.Entry(frame)
        self.annotations_ent.grid(row=3, column=1, sticky=tk.EW, pady=2, padx=5)
        ttk.Button(frame, text="Browse...", command=self.browse_annotations, width=10).grid(row=3, column=2, pady=2)

        frame.columnconfigure(1, weight=1)

    def _build_date_section(self, parent):
        frame = ttk.LabelFrame(parent, text=" Date Range ", padding="10")
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Start (YYYY-MM-DD):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.start_ent = ttk.Entry(frame, width=14)
        self.start_ent.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Label(frame, text="End (YYYY-MM-DD):").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.end_ent = ttk.Entry(frame, width=14)
        self.end_ent.grid(row=0, column=3, sticky=tk.W, pady=2, padx=5)

    def _build_filter_section(self, parent):
        frame = ttk.LabelFrame(parent, text=" Filters ", padding="10")
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Rig:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.rig_cmb = ttk.Combobox(frame, state="readonly")
        self.rig_cmb.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=5)
        frame.columnconfigure(1, weight=1)
        ttk.Button(frame, text="Scan Options", command=self.scan_options, width=12).grid(
            row=0, column=2, sticky=tk.EW, pady=2)

        lists = ttk.Frame(frame)
        lists.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=(6, 0))

        cam_frame = ttk.LabelFrame(lists, text=" Camera Configs (multi-select) ", padding="5")
        cam_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.camera_lb = tk.Listbox(cam_frame, height=4, selectmode=tk.EXTENDED, exportselection=False)
        cam_scroll = ttk.Scrollbar(cam_frame, orient="vertical", command=self.camera_lb.yview)
        self.camera_lb.configure(yscrollcommand=cam_scroll.set)
        self.camera_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cam_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        light_frame = ttk.LabelFrame(lists, text=" Lighting Configs (multi-select) ", padding="5")
        light_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        self.lighting_lb = tk.Listbox(light_frame, height=4, selectmode=tk.EXTENDED, exportselection=False)
        light_scroll = ttk.Scrollbar(light_frame, orient="vertical", command=self.lighting_lb.yview)
        self.lighting_lb.configure(yscrollcommand=light_scroll.set)
        self.lighting_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        light_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_time_period_section(self, parent):
        frame = ttk.LabelFrame(parent, text=" Time Periods (daily time windows) ", padding="10")
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Start (HH:MM):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.tp_start_ent = ttk.Entry(frame, width=8)
        self.tp_start_ent.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Label(frame, text="End (HH:MM):").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.tp_end_ent = ttk.Entry(frame, width=8)
        self.tp_end_ent.grid(row=0, column=3, sticky=tk.W, pady=2, padx=5)

        ttk.Button(frame, text="+ Add", command=self.add_time_period, width=8).grid(
            row=0, column=4, padx=(5, 0), pady=2)

        self.time_period_list = tk.Listbox(frame, height=3, exportselection=False)
        self.time_period_list.grid(row=1, column=0, columnspan=4, sticky=tk.EW, pady=(6, 0))
        ttk.Button(frame, text="Remove Selected", command=self.remove_time_period).grid(
            row=1, column=4, padx=(5, 0), sticky=tk.N)

    def _build_settings_section(self, parent):
        frame = ttk.LabelFrame(parent, text=" Options & Presets ", padding="10")
        frame.pack(fill=tk.X, pady=5)

        self.verbose_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Verbose Logging", variable=self.verbose_var).pack(anchor=tk.W, pady=(0, 5))

        btn_box = ttk.Frame(frame)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text="Export JSON Config", command=self.export_settings).pack(
            side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
        ttk.Button(btn_box, text="Import JSON Config", command=self.import_settings).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0), ipady=2)

    def _build_run_section(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=10)

        self.preview_btn = ttk.Button(frame, text="Preview Match Count", command=self.preview_threaded)
        self.preview_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), ipady=4)

        self.generate_btn = ttk.Button(frame, text="GENERATE CROPS", command=self.generate_threaded)
        self.generate_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        self.progress = ttk.Progressbar(parent, maximum=100, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(8, 4))
        self.status_lbl = ttk.Label(parent, text="Ready")
        self.status_lbl.pack(fill=tk.X)

    def _build_log_section(self, parent):
        frame = ttk.LabelFrame(parent, text=" Logs ", padding="5")
        frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.log_text = tk.Text(frame, height=8, state="disabled", wrap="word", background="#f0f0f0")
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _set_defaults(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.start_ent.insert(0, today)
        self.end_ent.insert(0, today)
        self.rig_cmb["values"] = ["All"]
        self.rig_cmb.current(0)

    # ----------------------------------------------------------------------
    # Browsing Handlers
    # ----------------------------------------------------------------------
    def browse_input(self):
        selected = filedialog.askdirectory(title="Select Input Image Folder")
        if selected:
            self.input_ent.delete(0, tk.END)
            self.input_ent.insert(0, selected)

    def browse_coords(self):
        selected = filedialog.askopenfilename(
            title="Select Coordinates File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if selected:
            self.coords_ent.delete(0, tk.END)
            self.coords_ent.insert(0, selected)

    def browse_output(self):
        selected = filedialog.askdirectory(title="Select Output Folder")
        if selected:
            self.output_ent.delete(0, tk.END)
            self.output_ent.insert(0, selected)

    def browse_annotations(self):
        selected = filedialog.askdirectory(title="Select Annotations Folder (Optional)")
        if selected:
            self.annotations_ent.delete(0, tk.END)
            self.annotations_ent.insert(0, selected)

    # ----------------------------------------------------------------------
    # Settings Export / Import
    # ----------------------------------------------------------------------
    def export_settings(self):
        path = filedialog.asksaveasfilename(
            title="Export settings", defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._collect_settings(), f, indent=2)
            self.log(f"Settings exported to {path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not save settings:\n{e}")

    def import_settings(self):
        path = filedialog.askopenfilename(
            title="Import settings", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Settings file must contain a JSON object.")
            self._apply_settings(data)
            self.log(f"Settings imported from {path}")
        except Exception as e:
            messagebox.showerror("Import Error", f"Could not read/apply settings:\n{e}")

    def _collect_settings(self):
        return {
            "input": self.input_ent.get().strip(),
            "coords": self.coords_ent.get().strip(),
            "output": self.output_ent.get().strip(),
            "annotations": self.annotations_ent.get().strip(),
            "start_date": self.start_ent.get().strip(),
            "end_date": self.end_ent.get().strip(),
            "rig": self.rig_cmb.get(),
            "rigs": list(self.rig_cmb["values"])[1:],
            "camera_configs": self._selected(self.camera_lb),
            "camera_options": list(self.camera_lb.get(0, tk.END)),
            "lighting_configs": self._selected(self.lighting_lb),
            "lighting_options": list(self.lighting_lb.get(0, tk.END)),
            "time_periods": [list(t) for t in self.time_periods],
            "verbose": self.verbose_var.get(),
        }

    def _apply_settings(self, data):
        def _set(entry, value):
            entry.delete(0, tk.END)
            entry.insert(0, str(value))

        _set(self.input_ent, data.get("input", ""))
        _set(self.coords_ent, data.get("coords", ""))
        _set(self.output_ent, data.get("output", ""))
        _set(self.annotations_ent, data.get("annotations", ""))
        _set(self.start_ent, data.get("start_date", datetime.now().strftime("%Y-%m-%d")))
        _set(self.end_ent, data.get("end_date", datetime.now().strftime("%Y-%m-%d")))

        rigs = data.get("rigs") or []
        self.rig_cmb["values"] = ["All"] + [r for r in rigs if r != "All"]
        rig = data.get("rig", "All")
        if rig not in self.rig_cmb["values"]:
            rig = "All"
        self.rig_cmb.current(self.rig_cmb["values"].index(rig))

        self._populate_and_select(self.camera_lb, data.get("camera_options") or [], data.get("camera_configs") or [])
        self._populate_and_select(self.lighting_lb, data.get("lighting_options") or [], data.get("lighting_configs") or [])

        self.time_periods.clear()
        self.time_period_list.delete(0, tk.END)
        for period in data.get("time_periods") or []:
            try:
                datetime.strptime(period[0], "%H:%M")
                datetime.strptime(period[1], "%H:%M")
            except (ValueError, IndexError, TypeError):
                continue
            self.time_periods.append((period[0], period[1]))
            self.time_period_list.insert(tk.END, f"{period[0]} - {period[1]}")

        self.verbose_var.set(bool(data.get("verbose", False)))

    def _populate_and_select(self, listbox, options, selected):
        listbox.delete(0, tk.END)
        selected = set(selected)
        for i, opt in enumerate(options):
            listbox.insert(tk.END, opt)
            if opt in selected:
                listbox.selection_set(i)

    # ----------------------------------------------------------------------
    # Scan / Filter Handlers
    # ----------------------------------------------------------------------
    def scan_options(self):
        if not self.input_ent.get().strip():
            messagebox.showerror("Error", "Select an input folder first.")
            return
        self._set_busy(True)
        threading.Thread(target=self._scan_options_safe, daemon=True).start()

    def _scan_options_safe(self):
        try:
            input_dir = self.input_ent.get().strip()
            self.log(f"Scanning '{input_dir}' for available filter options...")
            records = self._load_records()
            rigs = sorted({r.camera_rig for r in records})
            cams = sorted({r.camera_config for r in records if r.camera_config is not None})
            lights = sorted({r.lighting_config for r in records if r.lighting_config is not None})
            self.root.after(0, lambda: self._populate_filter_options(rigs, cams, lights, len(records)))
        except Exception as e:
            self.root.after(0, lambda err=e: messagebox.showerror("Scan Error", str(err)))
        finally:
            self.root.after(0, self._set_busy, False)

    def _populate_filter_options(self, rigs, cams, lights, total):
        self.rig_cmb["values"] = ["All"] + rigs
        self.rig_cmb.current(0)
        self.camera_lb.delete(0, tk.END)
        for cam in cams:
            self.camera_lb.insert(tk.END, cam)
        self.lighting_lb.delete(0, tk.END)
        for light in lights:
            self.lighting_lb.insert(tk.END, light)
        self.log(f"Found {total} timestamped image(s): {len(rigs)} rig(s), {len(cams)} camera config(s), {len(lights)} lighting config(s).")

    # ----------------------------------------------------------------------
    # Time Period Handlers
    # ----------------------------------------------------------------------
    def add_time_period(self):
        start = self.tp_start_ent.get().strip()
        end = self.tp_end_ent.get().strip()
        if not start or not end:
            messagebox.showerror("Error", "Fill in both a start and end hour.")
            return
        try:
            datetime.strptime(start, "%H:%M")
            datetime.strptime(end, "%H:%M")
        except ValueError:
            messagebox.showerror("Error", "Time periods must use HH:MM format (e.g. 00:00).")
            return
        self.time_periods.append((start, end))
        self.time_period_list.insert(tk.END, f"{start} - {end}")
        self.tp_start_ent.delete(0, tk.END)
        self.tp_end_ent.delete(0, tk.END)

    def remove_time_period(self):
        sel = self.time_period_list.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.time_periods[idx]
        self.time_period_list.delete(idx)

    # ----------------------------------------------------------------------
    # Parse & Filter Pipeline
    # ----------------------------------------------------------------------
    def _selected(self, listbox):
        return [listbox.get(i) for i in listbox.curselection()]

    def _load_records(self, logger=None):
        input_dir = self.input_ent.get().strip()
        if not input_dir:
            raise ValueError("Input folder is required.")
        if self._records_cache is None or self._cache_input_dir != input_dir:
            self._records_cache = parsing.parse_images(input_dir, logger=logger)
            self._cache_input_dir = input_dir
        return self._records_cache

    def _parse_and_filter(self, logger=None):
        input_dir = self.input_ent.get().strip()
        if not input_dir:
            raise ValueError("Input folder is required.")

        start = self.start_ent.get().strip()
        end = self.end_ent.get().strip()
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Dates must use YYYY-MM-DD format.")

        records = sorted(self._load_records(logger=logger), key=lambda r: r.timestamp)
        if not records:
            raise ValueError(f"No timestamped images were found in '{input_dir}'.")

        rig = self.rig_cmb.get()
        rig = None if rig in ("", "All") else rig

        camera_configs = self._selected(self.camera_lb) or None
        lighting_configs = self._selected(self.lighting_lb) or None

        time_ranges = None
        if self.time_periods:
            time_ranges = [(datetime.strptime(t[0], "%H:%M").time(),
                            datetime.strptime(t[1], "%H:%M").time())
                           for t in self.time_periods]

        self._filtered_records = parsing.filter_records(
            records,
            camera_rig=rig,
            camera_configs=camera_configs,
            lighting_configs=lighting_configs,
            date_range=(start_date, end_date),
            time_ranges=time_ranges,
            logger=logger,
        )
        self._filtered_records.sort(key=lambda r: r.timestamp)
        return self._filtered_records

    def _build_logger(self):
        logger = logging.getLogger("image_cropper_gui")
        logger.handlers.clear()
        handler = _LogHandler(self.log)
        handler.setLevel(logging.DEBUG if self.verbose_var.get() else logging.INFO)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG if self.verbose_var.get() else logging.INFO)
        logger.propagate = False
        return logger

    # ----------------------------------------------------------------------
    # Preview & Generation
    # ----------------------------------------------------------------------
    def preview_threaded(self):
        threading.Thread(target=self._preview_safe, daemon=True).start()

    def _preview_safe(self):
        try:
            records = self._parse_and_filter(logger=self._build_logger())
            count = len(records)
            self.log(f"Preview: {count} image(s) match the current filters.")
            self.root.after(0, lambda c=count: messagebox.showinfo(
                "Preview", f"{c} image(s) match the current filters."))
        except Exception as e:
            self.root.after(0, lambda err=e: messagebox.showerror("Preview Error", str(err)))

    def generate_threaded(self):
        coords_path = self.coords_ent.get().strip()
        output_dir = self.output_ent.get().strip()

        if not coords_path or not os.path.isfile(coords_path):
            messagebox.showerror("Error", "Valid coordinates file is required.")
            return
        if not output_dir:
            messagebox.showerror("Error", "Output folder is required.")
            return

        self._set_busy(True)
        threading.Thread(target=self._generate_safe, daemon=True).start()

    def _generate_safe(self):
        try:
            logger = self._build_logger()
            records = self._parse_and_filter(logger=logger)
            if not records:
                raise ValueError("No images match the current filters.")

            coords_path = self.coords_ent.get().strip()
            output_dir = self.output_ent.get().strip()
            ann_dir = self.annotations_ent.get().strip() or None

            if ann_dir and not os.path.isdir(ann_dir):
                logger.warning(f"Specified annotations folder '{ann_dir}' does not exist. Skipping annotations.")
                ann_dir = None

            entries = parse_coordinates_txt(coords_path)
            if not entries:
                raise ValueError("No valid sample entries found in coordinates file.")

            total = len(records)
            self.log(f"Starting processing of {total} image(s) with {len(entries)} crop region(s) each...")

            for idx, rec in enumerate(records, start=1):
                image_path = getattr(rec, "path", None) or getattr(rec, "filepath", None)
                if not image_path:
                    continue

                process_image_crops(
                    image_path_str=image_path,
                    output_parent_dir=output_dir,
                    entries=entries,
                    annotations_dir=ann_dir,
                    logger=logger
                )

                pct = (idx / total) * 100
                self.root.after(0, lambda p=pct, i=idx, t=total: self._set_progress(p, f"Processing image {i}/{t}"))

            self.log("Batch cropping completed successfully.")
            self.root.after(0, lambda: messagebox.showinfo("Success", "Cropping completed successfully!"))
        except Exception as e:
            self.root.after(0, lambda err=e: messagebox.showerror("Crop Error", str(err)))
        finally:
            self.root.after(0, self._on_generate_done)

    # ----------------------------------------------------------------------
    # UI Progress & Logging
    # ----------------------------------------------------------------------
    def _set_progress(self, pct, text):
        self.progress["value"] = pct
        self.status_lbl.config(text=text)

    def _on_generate_done(self):
        self._set_busy(False)
        self.progress["value"] = 0
        self.status_lbl.config(text="Ready")

    def _set_busy(self, busy):
        state = "disabled" if busy else "normal"
        for widget in (self.generate_btn, self.preview_btn):
            widget.config(state=state)

    def log(self, message):
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.root.after(0, _append)


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCropperGuiApp(root)
    root.mainloop()