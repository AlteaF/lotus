#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# ---- SHARED PARAMS (same for every tile) ----

DATA_DIR="/Volumes/vap-data/Datasets/LOTUS/images"
OUT_DIR="$HOME"
START="2026-07-22"
END="2026-07-27"
RIG="rig1"
CAMERA="20pAutoExp"
LIGHTING="lightsOff"
TIME_PERIOD_START="07:00"
TIME_PERIOD_END="07:45"
FPS=1
CROP_W=800
CROP_H=800
# ---- 4x4 GRID OF crop-x,crop-y PAIRS ---- Fill these in with your real 16 top-left corners. Order below is row-major: row0 (crop01-04), row1 (crop05-08), etc.
CROPS=(
 "163,46,800,800,A_0"
 "998,68,800,800,B_0"
 "1814,65,800,800,C_0"
 "2701,40,800,800,D_0"
 "172,1012,800,800,B_1"
 "1015,1001,800,800,C_1"
 "1820,1026,800,800,D_1"
 "2657,944,800,800,E_1"
 "158,1828,800,800,E_2"
 "996,1795,800,800,A_2"
 "1817,1781,800,800,B_2"
 "2647,1776,800,800,C_2"
 "150,2734,800,800,D_3"
 "1822,2666,800,800,E_3"
 "2660,2726,800,800,A_3"
)

for entry in "${CROPS[@]}"; do
 IFS=',' read -r CROP_X CROP_Y CROP_W CROP_H LABEL <<< "$entry"
 OUT_FILE="${OUT_DIR}/${LABEL}_${START//-/}_${END//-/}_${CAMERA}_${LIGHTING}.mp4"
 echo "=== ${LABEL}: x=${CROP_X} y=${CROP_Y} w=${CROP_W} h=${CROP_H} -> ${OUT_FILE} ==="
 PYTHONPATH="$SCRIPT_DIR" python3 "${SCRIPT_DIR}/timelapse_generator.py" "$DATA_DIR" "$OUT_FILE" "$START" "$END" --rig "$RIG" --fps "$FPS" --camera "$CAMERA" --lighting "$LIGHTING" --time_period "$TIME_PERIOD_START" "$TIME_PERIOD_END" --crop "$CROP_X" "$CROP_Y" "$CROP_W" "$CROP_H" --overlay "${LABEL} [${CAMERA}] [${LIGHTING}]"
done
