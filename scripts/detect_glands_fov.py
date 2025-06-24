#!/usr/bin/env python3
"""Run gland detection on a user-specified field of view.

This utility loads a portion of an SVS slide, runs the Segment Anything
Model (SAM) to segment glands and outputs an ASAP compatible XML file.
It reuses the configuration parameters from ``config.json``.

Example:

    python detect_glands_fov.py slide.svs --x 1000 --y 2000 --width 512 \
        --height 512 --out results.xml
    # or to print annotations as JSON
    python detect_glands_fov.py slide.svs --x 0 --y 0 --width 512 --height 512 --stdout
"""
from __future__ import annotations

import argparse
import json
import os
from typing import List, Dict, Tuple

import numpy as np
import openslide
from skimage.measure import find_contours

import torch
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator

from xml_utils import generate_xml_annotations, read_xml_annotations


def load_config(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def extract_patch(slide: openslide.OpenSlide, x: int, y: int, width: int, height: int, level: int = 0) -> np.ndarray:
    region = slide.read_region((x, y), level, (width, height)).convert("RGB")
    return np.array(region)


def masks_to_annotations(masks: List[Dict], factor: float, offset: Tuple[int, int]) -> List[Dict]:
    annotations = []
    ox, oy = offset
    for m in masks:
        segmentation = m.get("segmentation")
        if segmentation is None:
            continue
        contours = find_contours(segmentation, 0.5)
        for contour in contours:
            coords = [(ox + x * factor, oy + y * factor) for y, x in contour]
            annotations.append({"coords": coords, "class": "gland"})
    return annotations


def show_patch(image: np.ndarray, annotations: List[Dict], origin: Tuple[int, int]) -> None:
    """Display a patch with annotation overlays using matplotlib."""
    import matplotlib.pyplot as plt

    ox, oy = origin
    plt.imshow(image)
    for ann in annotations:
        pts = np.array([(x - ox, y - oy) for x, y in ann.get("coords", [])])
        if len(pts) > 0:
            plt.plot(pts[:, 0], pts[:, 1], "r")
    plt.axis("off")
    plt.show(block=False)
    plt.pause(0.001)


def annotations_in_region(annotations: List[Dict], region: Tuple[int, int, int, int]) -> List[Dict]:
    """Return annotations that intersect a given region."""
    x, y, w, h = region
    subset = []
    for ann in annotations:
        for px, py in ann.get("coords", []):
            if x <= px < x + w and y <= py < y + h:
                subset.append(ann)
                break
    return subset


def run_fov_detection(
    cfg: Dict,
    slide_path: str,
    coords: Tuple[int, int, int, int],
    out_path: str | None,
    show: bool = False,
    stdout: bool = False,
) -> None:
    slide = openslide.OpenSlide(slide_path)
    x, y, w, h = coords

    image = extract_patch(slide, x, y, w, h, level=0)
    factor = 1.0

    sam = sam_model_registry[cfg.get("model_type", "vit_h")](
        checkpoint=cfg["sam_checkpoint"],
    )
    sam.to(cfg.get("device", "cuda:0"))
    mask_generator = SamAutomaticMaskGenerator(sam)

    with torch.no_grad():
        masks = mask_generator.generate(image)

    new_annotations = masks_to_annotations(masks, factor, (x, y))
    all_annotations = new_annotations
    if out_path:
        existing = read_xml_annotations(out_path)
        all_annotations = existing + new_annotations
        generate_xml_annotations(all_annotations, out_path)
        print(f"Saved annotations to {out_path}")

    if stdout:
        import json
        print(json.dumps(new_annotations))

    if show:
        relevant = annotations_in_region(all_annotations, (x, y, w, h))
        show_patch(image, relevant, (x, y))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gland detection on a field of view")
    p.add_argument("slide", help="Path to SVS slide")
    p.add_argument("--x", type=int, required=True, help="Top-left X coordinate")
    p.add_argument("--y", type=int, required=True, help="Top-left Y coordinate")
    p.add_argument("--width", type=int, required=True, help="Patch width")
    p.add_argument("--height", type=int, required=True, help="Patch height")
    p.add_argument("--out", help="Output XML path")
    p.add_argument("--show", action="store_true", help="Display patch with overlays")
    p.add_argument("--stdout", action="store_true", help="Print annotations as JSON")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
    cfg = load_config(cfg_path)
    run_fov_detection(
        cfg,
        args.slide,
        (args.x, args.y, args.width, args.height),
        args.out,
        show=args.show,
        stdout=args.stdout,
    )


if __name__ == "__main__":
    main()
