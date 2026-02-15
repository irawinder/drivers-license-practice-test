#!/usr/bin/env python3
"""Build docs/ site data from extracted exam JSONs and images."""

import json
import os
import shutil

EXTRACTED = "extracted"
DOCS = "docs"
DATA_DIR = os.path.join(DOCS, "data")
IMG_DIR = os.path.join(DOCS, "images")
SRC_IMG_DIR = os.path.join(EXTRACTED, "question_images")


def rewrite_image_path(path):
    """Rewrite 'question_images/X' to 'images/X'."""
    if path and path.startswith("question_images/"):
        return "images/" + path[len("question_images/"):]
    return path


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_questions():
    questions = []

    # Learner's Permit exams 1-5
    for i in range(1, 6):
        data = load_json(os.path.join(EXTRACTED, f"learners_permit_exam_{i}.json"))
        source = f"lp{i}"
        for q in data["questions"]:
            questions.append({
                "id": f"{source}_q{q['number']:02d}",
                "source": source,
                "type": "standard",
                "text": q["text"],
                "has_image": q["has_image"],
                "image_file": rewrite_image_path(q["image_file"]),
                "correct_answer": q["correct_answer"],
                "explanation": q["explanation"],
            })

    # Driver's License exams 1-6
    for i in range(1, 7):
        data = load_json(os.path.join(EXTRACTED, f"drivers_license_exam_{i}.json"))
        source = f"dl{i}"
        # Standard true/false questions
        for q in data["questions"]:
            questions.append({
                "id": f"{source}_q{q['number']:02d}",
                "source": source,
                "type": "standard",
                "text": q["text"],
                "has_image": q["has_image"],
                "image_file": rewrite_image_path(q["image_file"]),
                "correct_answer": q["correct_answer"],
                "explanation": q["explanation"],
            })
        # Danger anticipation questions -> flatten sub-questions
        for dq in data.get("danger_questions", []):
            for sq in dq["sub_questions"]:
                questions.append({
                    "id": f"{source}_q{dq['number']:02d}_{sq['number']}",
                    "source": source,
                    "type": "danger",
                    "scenario": dq["scenario"],
                    "text": sq["text"],
                    "has_image": dq.get("has_image", False),
                    "image_file": rewrite_image_path(dq.get("image_file")),
                    "correct_answer": sq["correct_answer"],
                    "explanation": sq["explanation"],
                })

    return questions


def build_reference():
    ref = load_json(os.path.join(EXTRACTED, "reference_material.json"))
    # Rewrite image paths in reference material
    for section in ref["key_points_to_remember"]["sections"]:
        if "image_file" in section and section["image_file"]:
            section["image_file"] = rewrite_image_path(section["image_file"])
        if "points" in section:
            new_points = []
            for point in section["points"]:
                if isinstance(point, dict):
                    if point.get("image_file"):
                        point["image_file"] = rewrite_image_path(point["image_file"])
                    new_points.append(point)
                else:
                    new_points.append(point)
            section["points"] = new_points
    # Rewrite anticipating_danger_guide image path
    if "anticipating_danger_guide" in ref:
        guide = ref["anticipating_danger_guide"]
        if guide.get("image_file"):
            guide["image_file"] = rewrite_image_path(guide["image_file"])
    return ref


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)

    # Build and write questions.json
    questions = build_questions()
    with open(os.path.join(DATA_DIR, "questions.json"), "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(questions)} questions to {DATA_DIR}/questions.json")

    # Build and write reference.json
    ref = build_reference()
    with open(os.path.join(DATA_DIR, "reference.json"), "w", encoding="utf-8") as f:
        json.dump(ref, f, ensure_ascii=False, indent=2)
    print(f"Wrote reference material to {DATA_DIR}/reference.json")

    # Copy images
    count = 0
    if os.path.isdir(SRC_IMG_DIR):
        for fname in os.listdir(SRC_IMG_DIR):
            if fname.endswith(".png"):
                shutil.copy2(os.path.join(SRC_IMG_DIR, fname), os.path.join(IMG_DIR, fname))
                count += 1
    print(f"Copied {count} images to {IMG_DIR}/")


if __name__ == "__main__":
    main()
