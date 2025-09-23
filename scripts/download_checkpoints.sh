#!/usr/bin/env bashset -euo pipefail

# Carpeta destino
mkdir -p scripts

echo ">> Descargando checkpoints en ./scripts/ ..."

# SAM (ViT-H)
SAM_URL="https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"
SAM_OUT="scripts/sam_vit_h.pth"

echo "-> SAM ViT-H"
curl -L -o "$SAM_OUT" "$SAM_URL"

# U-Net (ajusta con tu enlace real)
UNET_URL="https://github.com/twpkevin06222/Gland-Segmentation/blob/main/weights/best_weight.pth"
UNET_OUT="scripts/best_weight.pth"

echo "-> U-Net"
curl -L -o "$UNET_OUT" "$UNET_URL"

echo ">> Checkpoints descargados:"
ls -lh scripts/*.pth
