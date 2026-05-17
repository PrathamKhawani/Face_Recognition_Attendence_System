"""
Camera Blueprint — MJPEG streaming with entry/exit gate modes.

Entry mode  → marks Check-In  (status: Present / Late)
Exit  mode  → marks Check-Out (calculates hours_worked)
"""

import cv2
import threading
from datetime import datetime, date, timedelta

from flask import Blueprint, Response, request, jsonify, current_app

import config
from database import db, User, AttendanceLog
from face_engine import engine

camera_bp = Blueprint('camera', __name__)

import base64
import numpy as np
from extensions import csrf

# ── Camera handles (one per hardware index) ───────────────────────────
_cams  = {}
_cam_lock = threading.Lock()
_read_locks = {}

def _get_cap_and_lock(mode: str):
    idx = config.ENTRY_CAMERA_INDEX if mode == 'entry' else config.EXIT_CAMERA_INDEX
    with _cam_lock:
        if idx not in _cams or not _cams[idx].isOpened():
            # Use CAP_DSHOW for faster/more reliable access on Windows
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            _cams[idx] = cap
            _read_locks[idx] = threading.Lock()
        return _cams[idx], _read_locks[idx]


# ── Attendance marking ─────────────────────────────────────────────────
def _mark(uid: int, mode: str, app):
    with app.app_context():
        today = date.today()
        log   = AttendanceLog.query.filter_by(user_id=uid, date=today).first()
        user  = db.session.get(User, uid)
        if not user:
            return

        now_str = datetime.now().strftime('%H:%M:%S')

        if mode == 'entry':
            if log:
                return  # already checked in today
            shift_start = datetime.strptime(
                user.shift_start or config.DEFAULT_SHIFT_START, '%H:%M')
            grace = (shift_start + timedelta(
                minutes=config.LATE_GRACE_MINUTES)).strftime('%H:%M:%S')
            status = 'Late' if now_str > grace else 'Present'
            db.session.add(AttendanceLog(
                user_id=uid, date=today,
                check_in=now_str, status=status))
            db.session.commit()

        elif mode == 'exit':
            if not log or not log.check_in:
                return  # never checked in
            if log.check_out:
                return  # already checked out

            # ── Washroom protection ───────────────────────────────────
            ci_dt  = datetime.strptime(log.check_in, '%H:%M:%S')
            now_dt = datetime.strptime(now_str, '%H:%M:%S')
            hours_since_in = (now_dt - ci_dt).total_seconds() / 3600
            if hours_since_in < config.MIN_CHECKOUT_HOURS:
                # Recognised at exit but too early — skip checkout silently
                return

            log.check_out    = now_str
            log.hours_worked = round(hours_since_in, 2)

            shift_end = datetime.strptime(
                user.shift_end or config.DEFAULT_SHIFT_END, '%H:%M')
            if now_dt < shift_end:
                if log.status == 'Present':
                    log.status = 'Early Departure'
            db.session.commit()



# ── MJPEG generator ───────────────────────────────────────────────────
def _gen(mode: str, app):
    cap, read_lock = _get_cap_and_lock(mode)
    while True:
        with read_lock:
            ok, frame = cap.read()
        if not ok:
            break

        annotated, recognized = engine.process_frame(frame)

        # Fire-and-forget DB writes in a daemon thread
        for r in recognized:
            t = threading.Thread(target=_mark,
                                 args=(r['uid'], mode, app),
                                 daemon=True)
            t.start()

        ok2, buf = cv2.imencode('.jpg', annotated,
                                [cv2.IMWRITE_JPEG_QUALITY, 82])
        if ok2:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n'
                   + buf.tobytes() + b'\r\n')


# ── Routes ────────────────────────────────────────────────────────────
@camera_bp.route('/video_feed')
def video_feed():
    mode = request.args.get('mode', 'entry')
    app  = current_app._get_current_object()
    return Response(_gen(mode, app),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@camera_bp.route('/process_frame_client', methods=['POST'])
@csrf.exempt
def process_frame_client():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'error': 'No image provided'}), 400
        
    mode = data.get('mode', 'entry')
    img_data = data['image']
    
    if ',' in img_data:
        img_data = img_data.split(',')[1]
        
    try:
        # Decode base64 to opencv frame
        nparr = np.frombuffer(base64.b64decode(img_data), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({'error': 'Invalid image'}), 400
            
        annotated, recognized = engine.process_frame(frame)
        
        # Mark attendance for recognized users
        app = current_app._get_current_object()
        for r in recognized:
            t = threading.Thread(target=_mark,
                                 args=(r['uid'], mode, app),
                                 daemon=True)
            t.start()
            
        # Re-encode back to base64
        ok, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            return jsonify({'error': 'Encoding error'}), 500
            
        b64_str = base64.b64encode(buf).decode('utf-8')
        return jsonify({
            'status': 'ok',
            'image': f"data:image/jpeg;base64,{b64_str}",
            'recognized': recognized
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@camera_bp.route('/reload_faces', methods=['GET', 'POST'])
def reload_faces():
    users = User.query.filter_by(is_active=True).all()
    n     = engine.load_faces(users)
    return jsonify({'status': 'ok', 'faces_loaded': n})

