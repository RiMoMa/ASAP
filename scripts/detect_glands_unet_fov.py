#!/usr/bin/env python3
"""Run UNet-based gland detection on a field of view.

The script mirrors :mod:`detect_glands_fov.py` but uses a UNet model
implemented with ``segmentation_models_pytorch``.  A region of the slide
is extracted, downscaled by a factor of four and fed through the network.
The resulting mask is post-processed and converted to ASAP polygons.  The
annotations are appended to the given XML file so multiple runs can
accumulate glands from different fields of view.
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
import segmentation_models_pytorch as smp
from PIL import Image

from xml_utils import generate_xml_annotations, read_xml_annotations, simplify_polygon


def load_config(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def extract_patch(
    slide: openslide.OpenSlide,
    x: int,
    y: int,
    width: int,
    height: int,
    downscale: int = 1,
) -> Tuple[np.ndarray, float]:
    """Return an RGB numpy array and the downscale factor used."""
    region = slide.read_region((x, y), 0, (width, height)).convert("RGB")
    img = np.array(region)
    if downscale > 1:
        new_w = max(1, width // downscale)
        new_h = max(1, height // downscale)
        img = np.array(Image.fromarray(img).resize((new_w, new_h), Image.BILINEAR))
    return img, float(downscale)


def load_unet(path: str, encoder: str, device: str) -> torch.nn.Module:
    model = smp.Unet(
        encoder_name=encoder,
        decoder_use_batchnorm=True,
        in_channels=3,
        classes=1,
    ).to(device)
    state = torch.load(path, map_location=device)
    model.load_state_dict(state)
    model.eval()
    return model


def min_max_norm(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float32)
    arr_min = arr.min()
    arr_max = arr.max()
    if arr_max - arr_min == 0:
        return np.zeros_like(arr, dtype=np.float32)
    return (arr - arr_min) / (arr_max - arr_min)


def postprocess_mask(
    mask: np.ndarray,
    gland_threshold: float = 0.7,
    median_kernel_size: int = 5,
    morph_kernel_size: int = 5,
    min_size: int = 500,
) -> np.ndarray:
    import cv2
    from skimage.morphology import remove_small_objects

    binary_mask = (mask > gland_threshold).astype(np.uint8)
    binary_mask = cv2.medianBlur(binary_mask, median_kernel_size)
    kernel = np.ones((morph_kernel_size, morph_kernel_size), np.uint8)
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel)
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
    binary_mask = remove_small_objects(binary_mask.astype(bool), min_size=min_size).astype(np.uint8)
    binary_mask = cv2.GaussianBlur(binary_mask, (5, 5), 0)
    _, binary_mask = cv2.threshold(binary_mask, 0.5, 1, cv2.THRESH_BINARY)
    binary_mask = remove_small_objects(binary_mask.astype(bool), min_size=min_size).astype(np.uint8)
    return binary_mask


def predict_mask(model: torch.nn.Module, img: np.ndarray, device: str, cfg: Dict) -> np.ndarray:
    """Return a binary mask from UNet prediction."""
    img_norm = min_max_norm(img)
    with torch.no_grad():
        tensor = torch.from_numpy(img_norm.transpose(2, 0, 1)).unsqueeze(0).float().to(device)
        pred = torch.sigmoid(model(tensor)).cpu().numpy()[0, 0]
    mask = postprocess_mask(pred, min_size=cfg.get("postprocess_min_size", 500))
    binary_mask = (mask > 0).astype(int)
    return binary_mask


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


def masks_to_annotations(
    mask: np.ndarray,
    factor: float,
    offset: Tuple[int, int],
    simplify_tol: float,
) -> List[Dict]:
    annotations = []
    x0, y0 = offset
    contours = find_contours(mask, 0.5)
    for contour in contours:
        pts = [
            (x0 + int(pt[1] * factor), y0 + int(pt[0] * factor)) for pt in contour
        ]
        pts = simplify_polygon(pts, tolerance=simplify_tol)
        if len(pts) >= 3:
            annotations.append({"coords": pts, "class": "gland"})
    return annotations


def show_patch(image: np.ndarray, annotations: List[Dict], origin: Tuple[int, int], scale: float = 1.0) -> None:
    """Display a patch with annotation overlays using matplotlib."""
    import matplotlib.pyplot as plt

    ox, oy = origin
    plt.imshow(image)
    for ann in annotations:
        pts = np.array([((x - ox) / scale, (y - oy) / scale) for x, y in ann.get("coords", [])])
        if len(pts) > 0:
            plt.plot(pts[:, 0], pts[:, 1], "r")
    plt.axis("off")
    plt.show(block=False)
    plt.pause(0.001)


def annotations_in_region(annotations: List[Dict], region: Tuple[int, int, int, int]) -> List[Dict]:
    """Return annotations that intersect a given region."""
    x, y, w, h = region
    subset: List[Dict] = []
    for ann in annotations:
        for px, py in ann.get("coords", []):
            if x <= px < x + w and y <= py < y + h:
                subset.append(ann)
                break
    return subset


def run_detection(
    cfg: Dict,
    slide_path: str,
    coords: Tuple[int, int, int, int],
    out_path: str | None,
    show: bool = False,
    stdout: bool = False,
) -> None:
    x, y, w, h = coords
    slide = openslide.OpenSlide(slide_path)

    image, factor = extract_patch(slide, x, y, w, h, downscale=4)

    device = cfg.get("device", "cpu")
    model = load_unet(cfg["unet_checkpoint"], cfg.get("unet_encoder", "resnet18"), device)
    mask = predict_mask(model, image, device, cfg)
    ann_mask = create_binary_mask([
        {"segmentation": mask, "area": int(mask.sum())}
    ], cfg.get("min_area", 400), cfg.get("max_area", 5000), cfg.get("min_circularity", 0.8))
    new_annotations = masks_to_annotations(ann_mask, factor, (x, y), cfg.get("simplify_tolerance", 5.0))
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
    if show:
        relevant = annotations_in_region(all_annotations, (x, y, w, h))
        show_patch(image, relevant, (x, y), scale=factor)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="UNet gland detection on FOV")
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
    cfg = load_config(os.path.join(os.path.dirname(__file__), "config.json"))
    run_detection(
        cfg,
        args.slide,
        (args.x, args.y, args.width, args.height),
        args.out,
        show=args.show,
        stdout=args.stdout,
    )


if __name__ == "__main__":
    main()
