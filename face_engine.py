"""
Thread-safe face recognition engine.

Key design:
- Singleton — one engine instance shared across all Flask threads
- face_lock  — protects known_encodings list during reload
- cooldown_cache — prevents duplicate attendance marks within 30 s
- Frame skipping — processes every Nth frame for high throughput
"""

import cv2
import numpy as np
import face_recognition
import threading
import time
import os

import config


class FaceEngine:
    _instance = None
    _init_lock = threading.Lock()

    def __new__(cls):
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._ready = False
        return cls._instance

    def __init__(self):
        if self._ready:
            return
        self._ready = True

        self.known_encodings: list = []
        self.known_names:     list = []
        self.known_ids:       list = []

        self.face_lock     = threading.Lock()
        self.cooldown      = {}          # {user_id: last_seen_timestamp}
        self.frame_count   = 0
        self._last_results = []          # cached boxes for skipped frames

    # ------------------------------------------------------------------
    def load_faces(self, users) -> int:
        """
        Encode face images for all active users.
        Replaces existing encodings atomically.
        """
        new_enc, new_names, new_ids = [], [], []

        for user in users:
            if not user.image_path or not os.path.exists(user.image_path):
                continue
            img = cv2.imread(user.image_path)
            if img is None:
                continue
            
            # Apply CLAHE for better consistency
            if config.ACCURACY_ENHANCEMENT:
                img = self._preprocess(img)

            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Use jitters for higher accuracy during training/loading
            encs = face_recognition.face_encodings(
                rgb, 
                num_jitters=config.ENCODING_JITTERS if config.ACCURACY_ENHANCEMENT else 1
            )
            
            if encs:
                new_enc.append(encs[0])
                new_names.append(user.name)
                new_ids.append(user.id)

        with self.face_lock:
            self.known_encodings = new_enc
            self.known_names     = new_names
            self.known_ids       = new_ids

        return len(new_enc)

    # ------------------------------------------------------------------
    def process_frame(self, frame):
        """
        Analyse one camera frame.

        Returns:
            annotated_frame  – frame with bounding boxes drawn
            recognized_list  – list of {uid, name, confidence} that cleared cooldown
        """
        self.frame_count += 1

        # Skip frames — draw cached results on non-processed frames
        if self.frame_count % config.FRAME_SKIP != 0:
            return self._draw(frame, self._last_results), []

        # Downsample for speed
        small = cv2.resize(frame, (0, 0),
                           fx=config.FRAME_SCALE, fy=config.FRAME_SCALE)
        
        # Preprocess for better accuracy (CLAHE)
        if config.ACCURACY_ENHANCEMENT:
            small = self._preprocess(small)

        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        locations = face_recognition.face_locations(rgb, model=config.DETECTION_MODEL)

        results    = []
        recognized = []

        with self.face_lock:
            if not self.known_encodings or not locations:
                self._last_results = []
                return frame, []

            encodings = face_recognition.face_encodings(rgb, locations)

            for enc, loc in zip(encodings, locations):
                distances = face_recognition.face_distance(self.known_encodings, enc)
                idx = int(np.argmin(distances))

                scale = int(1 / config.FRAME_SCALE)
                top, right, bottom, left = [v * scale for v in loc]

                if distances[idx] < config.FACE_MATCH_THRESHOLD:
                    uid        = self.known_ids[idx]
                    name       = self.known_names[idx]
                    confidence = round((1 - distances[idx]) * 100, 1)

                    results.append({
                        'name': name, 'uid': uid,
                        'confidence': confidence,
                        'box': (top, right, bottom, left),
                        'matched': True,
                    })

                    now = time.time()
                    last = self.cooldown.get(uid, 0)
                    if now - last > config.RECOGNITION_COOLDOWN:
                        self.cooldown[uid] = now
                        recognized.append({'uid': uid, 'name': name,
                                           'confidence': confidence})
                else:
                    results.append({
                        'name': 'UNKNOWN', 'uid': None,
                        'confidence': 0,
                        'box': (top, right, bottom, left),
                        'matched': False,
                    })

        self._last_results = results
        return self._draw(frame.copy(), results), recognized

    # ------------------------------------------------------------------
    def _draw(self, frame, results):
        for r in results:
            top, right, bottom, left = r['box']
            color = (0, 220, 120) if r['matched'] else (50, 50, 220)

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            label = r['name']
            if r['matched']:
                label += f"  {r['confidence']}%"

            (tw, th), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_DUPLEX, 0.52, 1)
            cv2.rectangle(frame,
                          (left, bottom),
                          (left + tw + 10, bottom + 22),
                          color, cv2.FILLED)
            cv2.putText(frame, label,
                        (left + 5, bottom + 16),
                        cv2.FONT_HERSHEY_DUPLEX, 0.52,
                        (255, 255, 255), 1)
        return frame

    def _preprocess(self, img):
        """Enhance image contrast using CLAHE for better face detection/recognition."""
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)


# Module-level singleton
engine = FaceEngine()
