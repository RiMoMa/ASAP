#!/usr/bin/env python3
"""Run UNet-based gland detection on a field of view.

This script loads a patch from an SVS slide, runs a UNet segmentation
model and stores the resulting polygons in an ASAP XML file.  It shares
the same command line interface as ``detect_glands_fov.py``.
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
from shapely.geometry import Polygon
from shapely.validation import make_valid
from PIL import Image

from xml_utils import generate_xml_annotations, read_xml_annotations, simplify_polygon


def load_config(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def extract_patch(slide: openslide.OpenSlide, x: int, y: int, width: int, height: int) -> np.ndarray:
    region = slide.read_region((x, y), 0, (width, height)).convert("RGB")
    return np.array(region)


def load_unet(path: str, device: str) -> torch.nn.Module:
    model = torch.load(path, map_location=device)
    model.eval()
    return model


def predict_mask(model: torch.nn.Module, img: np.ndarray, device: str) -> np.ndarray:
    """Return a binary mask from UNet prediction."""
    with torch.no_grad():
        inp = torch.from_numpy(img.transpose(2, 0, 1)).unsqueeze(0).float() / 255.0
        inp = inp.to(device)
        out = model(inp)
        if isinstance(out, (list, tuple)):
            out = out[0]
        out = out.squeeze().cpu().numpy()
    mask = (out > 0.5).astype(np.uint8)
    return mask


def create_binary_mask(anns: List[Dict], min_area: int, max_area: int, min_circ: float) -> np.ndarray:
    if not anns:
        return np.zeros((1, 1), dtype=np.uint8)
    sorted_anns = sorted(anns, key=lambda x: x["area"], reverse=True)
    h, w = sorted_anns[0]["segmentation"].shape
    mask = np.zeros((h, w), dtype=np.uint8)
    from skimage.measure import perimeter
    for ann in sorted_anns:
        area = ann["area"]
        seg = ann["segmentation"]
        peri = perimeter(seg)
        circ = (4 * np.pi * area) / (peri ** 2) if peri > 0 else 0
        if min_area <= area <= max_area and circ >= min_circ:
            mask[seg] = 1
    return mask


def masks_to_annotations(mask: np.ndarray, offset: Tuple[int, int], simplify_tol: float) -> List[Dict]:
    annotations = []
    x0, y0 = offset
    contours = find_contours(mask, 0.5)
    for contour in contours:
        pts = [(x0 + pt[1], y0 + pt[0]) for pt in contour]
        pts = simplify_polygon(pts, tolerance=simplify_tol)
        if len(pts) >= 3:
            annotations.append({"coords": pts, "class": "gland"})
    return annotations


def run_detection(cfg: Dict, slide_path: str, coords: Tuple[int, int, int, int], out_path: str | None, stdout: bool = False) -> None:
    x, y, w, h = coords
    slide = openslide.OpenSlide(slide_path)
    image = extract_patch(slide, x, y, w, h)
    device = cfg.get("device", "cpu")
    model = load_unet(cfg["unet_checkpoint"], device)
    mask = predict_mask(model, image, device)
    ann_mask = create_binary_mask([
        {"segmentation": mask, "area": int(mask.sum())}
    ], cfg.get("min_area", 400), cfg.get("max_area", 5000), cfg.get("min_circularity", 0.8))
    new_annotations = masks_to_annotations(ann_mask, (x, y), cfg.get("simplify_tolerance", 5.0))
    all_annotations = new_annotations
    if out_path:
        existing = read_xml_annotations(out_path)
        all_annotations = existing + new_annotations
        generate_xml_annotations(all_annotations, out_path)
        if not stdout:
            print(f"Saved annotations to {out_path}")
    if stdout:
        import json
        print(json.dumps(new_annotations))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="UNet gland detection on FOV")
    p.add_argument("slide", help="Path to SVS slide")
    p.add_argument("--x", type=int, required=True, help="Top-left X coordinate")
    p.add_argument("--y", type=int, required=True, help="Top-left Y coordinate")
    p.add_argument("--width", type=int, required=True, help="Patch width")
    p.add_argument("--height", type=int, required=True, help="Patch height")
    p.add_argument("--out", help="Output XML path")
    p.add_argument("--stdout", action="store_true", help="Print annotations as JSON")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(os.path.join(os.path.dirname(__file__), "config.json"))
    run_detection(cfg, args.slide, (args.x, args.y, args.width, args.height), args.out, stdout=args.stdout)


if __name__ == "__main__":
    main()
