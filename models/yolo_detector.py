"""YOLO detection + segmentation helper.

Loads the detection and segmentation models, exposes preset colors,
and provides a ``draw_segmentation`` routine that mirrors the original
behavior from :class:`SmartNavNode` (including the 0.5 confidence filter
and segmentation info collection).
"""

import cv2
import numpy as np
from ultralytics import YOLO


# Preset segmentation class colors
PRESET_COLORS = [
    (255, 69, 0), (138, 43, 226), (220, 20, 60),      # Orange-red, blue-violet, deep red
    (255, 0, 0), (0, 255, 0), (0, 0, 255),           # Red, green, blue
    (255, 255, 0), (0, 255, 255), (255, 0, 255),     # Yellow, cyan, magenta
    (255, 165, 0), (128, 0, 128), (0, 128, 128),     # Orange, purple, teal
    (128, 128, 0), (192, 192, 192), (255, 20, 147),  # Olive, silver, deep pink
    (30, 144, 255), (255, 140, 0), (50, 205, 50),    # Blue, orange-red, lime green
    (255, 99, 71), (75, 0, 130), (255, 215, 0),      # Tomato red, indigo, gold
    (0, 191, 255), (255, 105, 180), (34, 139, 34),   # Deep sky blue, hot pink, forest green
]


def build_seg_colors(num_classes=80):
    """Return a mapping ``class_id -> BGR color`` for up to ``num_classes`` classes."""
    return {i: PRESET_COLORS[i % len(PRESET_COLORS)] for i in range(num_classes)}


class YoloDetector:
    """Bundles detection model, segmentation model, and drawing helpers."""

    def __init__(self, logger, detect_weights='yolov8l.pt',
                 seg_weights='yolo11l-seg.pt', fallback_seg_weights='yolov8n-seg.pt'):
        self.logger = logger
        self.model = YOLO(detect_weights)
        try:
            self.seg_model = YOLO(seg_weights)
            self.logger.info("✅ YOLOv11 segmentation model loaded successfully")
        except Exception as e:
            self.logger.warn(f"⚠️ YOLOv11 failed to load, using backup model: {e}")
            self.seg_model = YOLO(fallback_seg_weights)

        self.seg_colors = build_seg_colors(80)
        self.current_segmentation_results = []

    def detect(self, cv_image, conf=0.6):
        """Run object detection and return the first results object."""
        return self.model(cv_image, conf=conf)[0]

    def segment(self, cv_image, conf=0.5):
        """Run segmentation and return the first results object."""
        return self.seg_model(cv_image, conf=conf)[0]

    def draw_segmentation(self, image, results):
        """Draw semantic segmentation results - enhanced version"""
        if results.masks is None:
            return image

        overlay = image.copy()
        masks = results.masks.data.cpu().numpy()
        boxes = results.boxes.data.cpu().numpy()

        segmentation_info = []

        for mask, box in zip(masks, boxes):
            cls_id = int(box[5])
            confidence = float(box[4])

            if confidence < 0.5:
                continue

            mask_resized = cv2.resize(mask, (image.shape[1], image.shape[0]))
            mask_bool = mask_resized > 0.5

            color = self.seg_colors.get(cls_id, (255, 255, 255))

            overlay[mask_bool] = color

            y_coords, x_coords = np.where(mask_bool)
            if len(y_coords) > 0:
                center_y, center_x = int(np.mean(y_coords)), int(np.mean(x_coords))
                area = len(y_coords)

                class_name = self.seg_model.names[cls_id]
                label = f"{class_name}: {confidence:.2f}"

                (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(overlay,
                              (center_x - text_width // 2 - 5, center_y - text_height - 5),
                              (center_x + text_width // 2 + 5, center_y + 5),
                              (0, 0, 0), -1)

                cv2.putText(overlay, label, (center_x - text_width // 2, center_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                segmentation_info.append({
                    "class_name": class_name,
                    "confidence": confidence,
                    "center_x": center_x,
                    "center_y": center_y,
                    "area": area,
                    "color": color
                })

        self.current_segmentation_results = segmentation_info

        return cv2.addWeighted(image, 0.6, overlay, 0.4, 0)
