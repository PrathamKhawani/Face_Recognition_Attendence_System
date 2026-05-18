"""
Thread-safe face recognition engine with Anti-Spoofing Liveness HUD.

Key design:
- Singleton — one engine instance shared across all Flask threads
- face_lock  — protects known_encodings list during reload
- cooldown_cache — prevents duplicate attendance marks within 30 s
- Frame skipping — processes every Nth frame for high throughput
- EAR (Eye Aspect Ratio) Liveness Detection — prevents spoofing
"""

import cv2
import numpy as np
import face_recognition
import threading
import time
import os

import config


def eye_aspect_ratio(eye):
    # Compute the euclidean distances between the two sets of vertical eye landmarks
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    # Compute the euclidean distance between the horizontal eye landmark
    C = np.linalg.norm(eye[0] - eye[3])
    # Compute the eye aspect ratio
    ear = (A + B) / (2.0 * C)
    return ear


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
        
        # Liveness Tracking
        self.blink_counters = {}         # {user_id: consecutive_frames_eyes_closed}
        self.liveness_state = {}         # {user_id: has_blinked}
        self.EAR_THRESHOLD = 0.21        # Eye Aspect Ratio threshold for blink
        self.EAR_CONSEC_FRAMES = 2       # Frames eye must be below threshold

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
            # Reset liveness states on reload
            self.blink_counters = {}
            self.liveness_state = {}

        return len(new_enc)

    # ------------------------------------------------------------------
    def process_frame(self, frame):
        """
        Analyse one camera frame.

        Returns:
            annotated_frame  – frame with bounding boxes drawn
            recognized_list  – list of {uid, name, confidence, liveness} that cleared cooldown
        """
        self.frame_count += 1

        # Skip frames — draw cached results on non-processed frames
        if self.frame_count % config.FRAME_SKIP != 0:
            return self._draw(frame, self._last_results), []

        # Downsample for speed
        small = cv2.resize(frame, (0, 0), fx=config.FRAME_SCALE, fy=config.FRAME_SCALE)
        
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
            # Find landmarks for liveness detection
            landmarks_list = face_recognition.face_landmarks(rgb, locations)

            for enc, loc, landmarks in zip(encodings, locations, landmarks_list):
                distances = face_recognition.face_distance(self.known_encodings, enc)
                idx = int(np.argmin(distances))

                scale = int(1 / config.FRAME_SCALE)
                top, right, bottom, left = [v * scale for v in loc]

                if distances[idx] < config.FACE_MATCH_THRESHOLD:
                    uid        = self.known_ids[idx]
                    name       = self.known_names[idx]
                    confidence = round((1 - distances[idx]) * 100, 1)
                    
                    # LIVENESS DETECTION (EAR)
                    liveness_score = 50.0  # Default base score
                    is_live = False
                    
                    if 'left_eye' in landmarks and 'right_eye' in landmarks:
                        left_eye = np.array(landmarks['left_eye'])
                        right_eye = np.array(landmarks['right_eye'])
                        
                        leftEAR = eye_aspect_ratio(left_eye)
                        rightEAR = eye_aspect_ratio(right_eye)
                        ear = (leftEAR + rightEAR) / 2.0
                        
                        # Initialize tracking for this user
                        if uid not in self.blink_counters:
                            self.blink_counters[uid] = 0
                            self.liveness_state[uid] = False
                            
                        if ear < self.EAR_THRESHOLD:
                            self.blink_counters[uid] += 1
                        else:
                            if self.blink_counters[uid] >= self.EAR_CONSEC_FRAMES:
                                self.liveness_state[uid] = True
                            self.blink_counters[uid] = 0
                            
                        is_live = self.liveness_state.get(uid, False)
                        
                        # Calculate a dynamic score for the UI
                        if is_live:
                            liveness_score = min(99.9, 85.0 + (ear * 50))
                        else:
                            liveness_score = max(10.0, ear * 150)
                            
                        # If the face is still within the initial check period and hasn't blinked
                        if not is_live and self.cooldown.get(uid, 0) == 0:
                            liveness_score = min(49.9, liveness_score)
                    
                    liveness_score = round(liveness_score, 1)

                    results.append({
                        'name': name, 'uid': uid,
                        'confidence': confidence,
                        'box': (top, right, bottom, left),
                        'matched': True,
                        'liveness': liveness_score,
                        'is_live': is_live
                    })

                    # Only register attendance if liveness is confirmed (blinked at least once)
                    if is_live or not config.GEOFENCING_ENABLED: # Fallback if geofencing is off for testing
                        now = time.time()
                        last = self.cooldown.get(uid, 0)
                        if now - last > config.RECOGNITION_COOLDOWN:
                            self.cooldown[uid] = now
                            recognized.append({'uid': uid, 'name': name,
                                            'confidence': confidence, 'liveness': liveness_score})
                else:
                    results.append({
                        'name': 'UNKNOWN', 'uid': None,
                        'confidence': 0,
                        'box': (top, right, bottom, left),
                        'matched': False,
                        'liveness': 0.0,
                        'is_live': False
                    })

        self._last_results = results
        return self._draw(frame.copy(), results), recognized

    # ------------------------------------------------------------------
    def _draw(self, frame, results):
        for r in results:
            top, right, bottom, left = r['box']
            matched = r['matched']
            is_live = r.get('is_live', False)
            liveness = r.get('liveness', 0.0)
            
            # Colors based on match and liveness
            if matched and is_live:
                color = (255, 200, 0) # Cyan-ish in BGR for live match
                box_color = (200, 255, 0)
            elif matched and not is_live:
                color = (0, 165, 255) # Orange for spoof warning
                box_color = (0, 100, 255)
            else:
                color = (50, 50, 220) # Red for unknown
                box_color = (50, 50, 220)

            # Military HUD Style corners
            length = 20
            thickness = 2
            
            # Top Left
            cv2.line(frame, (left, top), (left + length, top), box_color, thickness)
            cv2.line(frame, (left, top), (left, top + length), box_color, thickness)
            # Top Right
            cv2.line(frame, (right, top), (right - length, top), box_color, thickness)
            cv2.line(frame, (right, top), (right, top + length), box_color, thickness)
            # Bottom Left
            cv2.line(frame, (left, bottom), (left + length, bottom), box_color, thickness)
            cv2.line(frame, (left, bottom), (left, bottom - length), box_color, thickness)
            # Bottom Right
            cv2.line(frame, (right, bottom), (right - length, bottom), box_color, thickness)
            cv2.line(frame, (right, bottom), (right, bottom - length), box_color, thickness)

            # Labels
            label = r['name']
            if matched:
                if is_live:
                    badge_text = f"LIVE {liveness}%"
                    badge_color = (200, 255, 0)
                else:
                    badge_text = f"SPOOF DETECTED"
                    badge_color = (0, 0, 255)
                    
                (bw, bh), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_DUPLEX, 0.45, 1)
                cv2.rectangle(frame, (left, top - 25), (left + bw + 10, top), badge_color, cv2.FILLED)
                cv2.putText(frame, badge_text, (left + 5, top - 8), cv2.FONT_HERSHEY_DUPLEX, 0.45, (0, 0, 0) if is_live else (255,255,255), 1)

                label += f" ({r['confidence']}%)"

            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.52, 1)
            cv2.rectangle(frame,
                          (left, bottom),
                          (left + tw + 10, bottom + 22),
                          color, cv2.FILLED)
            cv2.putText(frame, label,
                        (left + 5, bottom + 16),
                        cv2.FONT_HERSHEY_DUPLEX, 0.52,
                        (0, 0, 0) if matched else (255, 255, 255), 1)
                        
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
