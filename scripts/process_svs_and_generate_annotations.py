#!/usr/bin/env python3
"""Segment SVS slides and generate ASAP annotations.

This script provides a thin wrapper around the `segment-anything` model to
produce annotations in the XML format used by ASAP.  Configuration is read from
``config.json`` located in the same directory as the script.  A minimal
configuration looks like::

    {
        "input_path": "./slides",          # directory containing SVS files
        "output_path": "./annotations",    # where XML files are written
        "sam_checkpoint": "sam_vit_h.pth",  # path to a SAM checkpoint
        "model_type": "vit_h",             # model type as used by SAM
        "device": "cuda:0",                # or "cpu"
        "downsample": 32                    # optional downsample factor
    }

The script loops over all ``.svs`` files in ``input_path`` and creates matching
``.xml`` files in ``output_path``.
"""
from __future__ import annotations

import json
import os
from typing import List, Tuple, Dict

import numpy as np
from PIL import Image
import openslide
from tqdm import tqdm
from skimage.measure import find_contours

import torch
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator

import sys
sys.path.append(os.path.dirname(__file__))
from xml_utils import generate_xml_annotations  # type: ignore


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def load_config(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def slide_to_image(slide: openslide.OpenSlide, downsample: int) -> Tuple[np.ndarray, float]:
    """Read a whole-slide image at a given downsample factor."""
    level = slide.get_best_level_for_downsample(downsample)
    factor = slide.level_downsamples[level]
    dim = slide.level_dimensions[level]
    img = slide.read_region((0, 0), level, dim).convert("RGB")
    return np.array(img), factor


def masks_to_annotations(masks: List[Dict], factor: float) -> List[Dict]:
    """Convert SAM masks to polygon annotations."""
    annotations = []
    for m in masks:
        segmentation = m.get("segmentation")
        if segmentation is None:
            continue
        contours = find_contours(segmentation, 0.5)
        for contour in contours:
            coords = [(x * factor, y * factor) for y, x in contour]
            annotations.append({"coords": coords, "class": "region"})
    return annotations


# ---------------------------------------------------------------------------
# Main processing routine
# ---------------------------------------------------------------------------

def process_slide(path: str, cfg: Dict, output_dir: str) -> None:
    slide = openslide.OpenSlide(path)
    image, factor = slide_to_image(slide, cfg.get("downsample", 32))

    sam = sam_model_registry[cfg.get("model_type", "vit_h")](
        checkpoint=cfg["sam_checkpoint"],
    )
    sam.to(cfg.get("device", "cuda:0"))
    mask_generator = SamAutomaticMaskGenerator(sam)

    with torch.no_grad():
        masks = mask_generator.generate(image)

    annotations = masks_to_annotations(masks, factor)

    name = os.path.splitext(os.path.basename(path))[0]
    os.makedirs(output_dir, exist_ok=True)
    xml_path = os.path.join(output_dir, f"{name}.xml")
    generate_xml_annotations(annotations, xml_path)
    print(f"Saved annotations to {xml_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
    cfg = load_config(cfg_path)
    input_dir = cfg.get("input_path", ".")
    output_dir = cfg.get("output_path", "./annotations")

    svs_files = [p for p in os.listdir(input_dir) if p.lower().endswith(".svs")]
    if not svs_files:
        print(f"No SVS files found in {input_dir}")
        return

    for svs_file in tqdm(svs_files, desc="Processing slides"):
        slide_path = os.path.join(input_dir, svs_file)
        process_slide(slide_path, cfg, output_dir)


if __name__ == "__main__":
    main()
