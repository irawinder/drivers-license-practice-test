#!/usr/bin/env python3
"""
Image Annotation Tool Server

Usage:
    /tmp/pdfenv/bin/python image_annotator.py

Then open http://localhost:8765 in your browser.
Draw rectangles around question images and tag them with question numbers.
"""

import http.server
import json
import os
import re
import sys
from urllib.parse import urlparse

PORT = 8765
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXTRACTED_DIR = os.path.join(BASE_DIR, "extracted")
IMAGES_DIR = os.path.join(EXTRACTED_DIR, "images")
Q_IMAGES_DIR = os.path.join(EXTRACTED_DIR, "question_images")
ANNOTATIONS_FILE = os.path.join(EXTRACTED_DIR, "image_annotations.json")

# Reference material images expected on pages 2-3
# Each: (tag, description)
REF_IMAGES_PAGE2 = [
    ("ref_traffic_lights", "Traffic light signals (green, yellow, red, arrows)"),
    ("ref_hand_signals", "Police officer / traffic warden hand signals"),
    ("ref_sign_road_blocked", "Road Blocked sign"),
    ("ref_sign_no_overtaking", "No-Overtaking sign"),
    ("ref_sign_motor_vehicles_only", "Motor Vehicles Only sign"),
    ("ref_sign_pedestrians_only", "Pedestrians Only sign"),
    ("ref_sign_designated_direction", "Proceed Only in Designated Direction(s) sign"),
    ("ref_sign_road_under_repair", "Road Under Repair warning sign"),
    ("ref_marking_no_entry_zone", "No Entry Zone pavement marking"),
    ("ref_marking_no_stopping_zone", "No Stopping Zone pavement marking"),
    ("ref_sign_no_crossing_halfway", "No Crossing Over Halfway Line sign"),
    ("ref_priority_lane_bus", "Priority Lane for Route Buses sign"),
    ("ref_parking_stopping_markings", "Parking/stopping zone pavement markings"),
    ("ref_vehicle_classification_table", "Vehicle Type Classification Table"),
]

REF_IMAGES_PAGE3 = [
    ("ref_speed_limits_table", "Speed limits table (expressways)"),
    ("ref_carrying_restrictions", "Cargo/passenger restrictions diagram"),
]

# Page 35 has the "Anticipating Danger" guide
REF_IMAGES_PAGE35 = [
    ("ref_danger_anticipation_guide", "Anticipating Danger explanation diagram"),
]

# Page mappings: (pdf_page_0indexed, exam_type, exam_num, q_start, q_end)
PAGES = [
    (3,  "lp", 1, 1, 25), (4,  "lp", 1, 26, 50),
    (5,  "lp", 2, 1, 25), (6,  "lp", 2, 26, 50),
    (7,  "lp", 3, 1, 25), (8,  "lp", 3, 26, 50),
    (9,  "lp", 4, 1, 25), (10, "lp", 4, 26, 50),
    (11, "lp", 5, 1, 25), (12, "lp", 5, 26, 50),
    (13, "dl", 1, 1, 45), (14, "dl", 1, 46, 90),
    (15, "dl", 1, 91, 95),
    (16, "dl", 2, 1, 45), (17, "dl", 2, 46, 90),
    (18, "dl", 2, 91, 95),
    (19, "dl", 3, 1, 45), (20, "dl", 3, 46, 90),
    (21, "dl", 3, 91, 95),
    (22, "dl", 4, 1, 45), (23, "dl", 4, 46, 90),
    (24, "dl", 4, 91, 95),
    (25, "dl", 5, 1, 45), (26, "dl", 5, 46, 90),
    (27, "dl", 5, 91, 95),
    (28, "dl", 6, 1, 45), (29, "dl", 6, 46, 90),
    (30, "dl", 6, 91, 95),
]


def get_pages_data():
    page_files = sorted(f for f in os.listdir(IMAGES_DIR) if f.endswith('.png'))

    page_exam_map = {}
    for pdf_page, et, en, qs, qe in PAGES:
        key = f"page_{pdf_page:02d}"
        page_exam_map.setdefault(key, []).append({
            "exam_type": et, "exam_num": en, "q_start": qs, "q_end": qe
        })

    exam_data = {}
    for f in os.listdir(EXTRACTED_DIR):
        if f.endswith('.json') and 'exam' in f:
            with open(os.path.join(EXTRACTED_DIR, f)) as fh:
                exam_data[f] = json.load(fh)

    pages = []
    for pf in page_files:
        parts = pf.split('_')
        page_prefix = parts[0] + '_' + parts[1]
        page_info = {"filename": pf, "image_questions": [], "label": pf.replace('.png', '')}

        if page_prefix in page_exam_map:
            for entry in page_exam_map[page_prefix]:
                et, en = entry["exam_type"], entry["exam_num"]
                qs, qe = entry["q_start"], entry["q_end"]
                json_key = f"learners_permit_exam_{en}.json" if et == "lp" else f"drivers_license_exam_{en}.json"

                if json_key in exam_data:
                    data = exam_data[json_key]
                    for q in data.get("questions", []):
                        if qs <= q["number"] <= qe:
                            tag = f"{et}{en}_q{q['number']:02d}"
                            has_img = bool(q.get("has_image"))
                            page_info["image_questions"].append({
                                "tag": tag, "number": q["number"],
                                "text": (q["text"][:100] + "...") if len(q["text"]) > 100 else q["text"],
                                "desc": q.get("image_description") or "",
                                "has_image": has_img,
                            })
                    if qs >= 91:
                        for dq in data.get("danger_questions", []):
                            if qs <= dq["number"] <= qe:
                                tag = f"{et}{en}_q{dq['number']:02d}"
                                text = dq.get("scenario", dq.get("text", "Danger question"))
                                page_info["image_questions"].append({
                                    "tag": tag, "number": dq["number"],
                                    "text": (text[:100] + "...") if len(text) > 100 else text,
                                    "desc": "Danger anticipation photo",
                                    "has_image": True,
                                })
        # Add reference material images for pages 1, 2 (key points) and 34 (danger info)
        if 'page_01' in pf and 'key_points' in pf:
            for tag, desc in REF_IMAGES_PAGE2:
                page_info["image_questions"].append({
                    "tag": tag, "number": 0, "text": desc, "desc": desc,
                    "has_image": True,
                })
        elif 'page_02' in pf and 'key_points' in pf:
            for tag, desc in REF_IMAGES_PAGE3:
                page_info["image_questions"].append({
                    "tag": tag, "number": 0, "text": desc, "desc": desc,
                    "has_image": True,
                })
        elif 'page_34' in pf or 'anticipating_danger_info' in pf:
            for tag, desc in REF_IMAGES_PAGE35:
                page_info["image_questions"].append({
                    "tag": tag, "number": 0, "text": desc, "desc": desc,
                    "has_image": True,
                })

        pages.append(page_info)
    return pages


def load_annotations():
    if os.path.exists(ANNOTATIONS_FILE):
        with open(ANNOTATIONS_FILE) as f:
            return json.load(f)
    return {}


def save_annotations(data):
    with open(ANNOTATIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# Map ref_ tags to where they belong in reference_material.json
# Section-level: tag -> section title substring
# Point-level: tag -> (section title substring, point text substring)
REF_TAG_PLACEMENT = {
    "ref_hand_signals": ("HAND SIGNALS", None),
    "ref_sign_road_blocked": ("OBSERVING TRAFFIC SIGNS", "Road Blocked"),
    "ref_sign_no_overtaking": ("OBSERVING TRAFFIC SIGNS", "No-Overtaking"),
    "ref_sign_motor_vehicles_only": ("OBSERVING TRAFFIC SIGNS", "Motor Vehicles Only"),
    "ref_sign_pedestrians_only": ("OBSERVING TRAFFIC SIGNS", "Pedestrians Only"),
    "ref_sign_designated_direction": ("OBSERVING TRAFFIC SIGNS", "Proceed Only in Designated"),
    "ref_sign_road_under_repair": ("OBSERVING TRAFFIC SIGNS", "Road Under Repair"),
    "ref_marking_no_entry_zone": ("OBSERVING TRAFFIC SIGNS", "No Entry Zone"),
    "ref_marking_no_stopping_zone": ("OBSERVING TRAFFIC SIGNS", "No Stopping Zone"),
    "ref_sign_no_crossing_halfway": ("OBSERVING TRAFFIC SIGNS", "No Crossing Over"),
    "ref_vehicle_classification_table": ("VEHICLE TYPE CLASSIFICATION TABLE", None),
    "ref_towing_vehicle_expressways": ("WHERE TOWING VEHICLES", "On national expressways"),
    "ref_towing_vehicles_exclusive_lanes": ("WHERE TOWING VEHICLES", "exclusive lanes for automobiles"),
    "ref_towing_vehicles_large_capacity": ("WHERE TOWING VEHICLES", "large cargos"),
    "ref_shifting_lanes": ("WHAT TO DO WHEN SHIFTING LANES", None),
    "ref_turning_at_intersection": ("WHAT TO DO WHEN PROCEEDING THROUGH INTERSECTIONS", None),
    "ref_danger_anticipation_guide": (None, None),  # Special: goes in anticipating_danger_guide
}


def _place_ref_images_inline(ref_data, ref_tags):
    """Place ref image paths inline in reference_material.json structure."""
    placed = 0
    for tag, filepath in ref_tags.items():
        placement = REF_TAG_PLACEMENT.get(tag)
        if not placement:
            continue

        section_match, point_match = placement

        # Special case: danger anticipation guide
        if section_match is None:
            if "anticipating_danger_guide" in ref_data:
                ref_data["anticipating_danger_guide"]["image_file"] = filepath
                placed += 1
            continue

        # Find matching section
        for section in ref_data.get("key_points_to_remember", {}).get("sections", []):
            if section_match not in section.get("title", ""):
                continue

            if point_match is None:
                # Section-level image
                section["image_file"] = filepath
                placed += 1
            else:
                # Point-level image
                points = section.get("points", [])
                for i, p in enumerate(points):
                    text = p["text"] if isinstance(p, dict) else p
                    if point_match in text:
                        if isinstance(p, str):
                            points[i] = {"text": p, "image_file": filepath}
                        else:
                            p["image_file"] = filepath
                        placed += 1
                        break
            break
    return placed


def process_annotations(annotations):
    from PIL import Image
    os.makedirs(Q_IMAGES_DIR, exist_ok=True)
    for f in os.listdir(Q_IMAGES_DIR):
        os.remove(os.path.join(Q_IMAGES_DIR, f))

    result = {"cropped": 0, "updated": 0, "no_image_marked": 0, "errors": []}
    tag_to_file = {}
    no_image_tags = set()

    for page_filename, anns in annotations.items():
        img_path = os.path.join(IMAGES_DIR, page_filename)
        img = None

        for ann in anns:
            tag = ann["tag"]
            # Handle "no image" markers (no rectangle to crop)
            if ann.get("no_image"):
                no_image_tags.add(tag)
                continue

            if not os.path.exists(img_path):
                result["errors"].append(f"Missing: {page_filename}")
                continue
            if img is None:
                img = Image.open(img_path)

            cropped = img.crop((ann["x1"], ann["y1"], ann["x2"], ann["y2"]))
            fname = f"{tag}.png"
            cropped.save(os.path.join(Q_IMAGES_DIR, fname))
            tag_to_file[tag] = f"question_images/{fname}"
            result["cropped"] += 1

    for f in os.listdir(EXTRACTED_DIR):
        if not f.endswith('.json') or 'exam' not in f:
            continue
        fp = os.path.join(EXTRACTED_DIR, f)
        with open(fp) as fh:
            data = json.load(fh)

        m = re.match(r'(learners_permit|drivers_license)_exam_(\d+)\.json', f)
        if not m:
            continue
        et = "lp" if m.group(1) == "learners_permit" else "dl"
        en = int(m.group(2))
        modified = False

        for q in data.get("questions", []):
            tag = f"{et}{en}_q{q['number']:02d}"
            if tag in no_image_tags:
                q["has_image"] = False
                q["image_file"] = None
                result["no_image_marked"] += 1
                modified = True
            elif tag in tag_to_file:
                q["has_image"] = True
                q["image_file"] = tag_to_file[tag]
                result["updated"] += 1
                modified = True
            else:
                q["image_file"] = None
        for dq in data.get("danger_questions", []):
            tag = f"{et}{en}_q{dq['number']:02d}"
            if tag in no_image_tags:
                dq["has_image"] = False
                dq["image_file"] = None
                result["no_image_marked"] += 1
                modified = True
            elif tag in tag_to_file:
                dq["has_image"] = True
                dq["image_file"] = tag_to_file[tag]
                result["updated"] += 1
                modified = True

        if modified:
            with open(fp, 'w') as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)

    # Update reference_material.json with ref_ tags placed inline
    ref_tags = {k: v for k, v in tag_to_file.items() if k.startswith("ref_")}
    if ref_tags:
        ref_fp = os.path.join(EXTRACTED_DIR, "reference_material.json")
        if os.path.exists(ref_fp):
            with open(ref_fp) as fh:
                ref_data = json.load(fh)
            # Remove flat images dict if present
            ref_data.pop("images", None)
            # Place images inline in sections and points
            placed = _place_ref_images_inline(ref_data, ref_tags)
            with open(ref_fp, 'w') as fh:
                json.dump(ref_data, fh, indent=2, ensure_ascii=False)
            result["updated"] += placed

    return result


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ('/', '/index.html'):
            self._serve_file(os.path.join(BASE_DIR, 'image_annotator.html'), 'text/html')
        elif path == '/api/pages':
            self._send_json(get_pages_data())
        elif path == '/api/annotations':
            self._send_json(load_annotations())
        elif path.startswith('/images/'):
            fp = os.path.join(IMAGES_DIR, path[8:])
            if os.path.exists(fp):
                self._serve_file(fp, 'image/png')
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        data = json.loads(body) if body else {}
        path = urlparse(self.path).path
        if path == '/api/save':
            save_annotations(data)
            self._send_json({"status": "ok"})
        elif path == '/api/process':
            result = process_annotations(data)
            self._send_json(result)
        else:
            self.send_error(404)

    def _serve_file(self, fp, ct):
        try:
            with open(fp, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404)

    def _send_json(self, data):
        content = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, fmt, *args):
        if '/images/' in str(args[0]):
            return
        super().log_message(fmt, *args)


if __name__ == '__main__':
    print(f"\n  Image Annotation Tool")
    print(f"  Open http://localhost:{PORT} in your browser")
    print(f"  Press Ctrl+C to stop\n")
    server = http.server.HTTPServer(('localhost', PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()
