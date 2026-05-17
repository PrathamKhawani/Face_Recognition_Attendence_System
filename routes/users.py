import os
import uuid
import base64
from datetime import date

from flask import (Blueprint, render_template, request,
                   jsonify, redirect, url_for, current_app, session)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

import config
from database import db, User, AttendanceLog
from face_engine import engine

users_bp = Blueprint('users', __name__)

def _allowed(filename):
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS)

@users_bp.route('/users')
def users():
    return render_template('users.html')

@users_bp.route('/users/add', methods=['GET', 'POST'])
def add_user():
    if request.method == 'GET':
        return render_template('add_user.html')

    # ── POST: create user ──────────────────────────────────────────
    name        = request.form.get('name', '').strip()
    employee_id = request.form.get('employee_id', '').strip()
    department  = request.form.get('department', '').strip()
    role        = request.form.get('role', '').strip()
    email       = request.form.get('email', '').strip()
    phone       = request.form.get('phone', '').strip()
    shift_start = request.form.get('shift_start', config.DEFAULT_SHIFT_START)
    shift_end   = request.form.get('shift_end',   config.DEFAULT_SHIFT_END)
    join_date_s = request.form.get('join_date',   '')

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    # Auto-generate employee ID if blank
    if not employee_id:
        prefix = department[:3].upper() if department else 'EMP'
        employee_id = f"{prefix}-{str(uuid.uuid4())[:6].upper()}"

    # Check uniqueness
    if User.query.filter_by(employee_id=employee_id).first():
        return jsonify({'error': f'Employee ID {employee_id} already exists'}), 409

    # Parse join date
    try:
        join_date = date.fromisoformat(join_date_s) if join_date_s else date.today()
    except ValueError:
        join_date = date.today()

    # Save face image
    image_path = ''
    webcam_data = request.form.get('webcam_data')
    file = request.files.get('photo')
    
    os.makedirs(config.IMAGES_DIR, exist_ok=True)
    if webcam_data:
        header, encoded = webcam_data.split(",", 1)
        safe_name = secure_filename(f"{employee_id}_webcam.jpg")
        dest = os.path.join(config.IMAGES_DIR, safe_name)
        with open(dest, "wb") as fh:
            fh.write(base64.b64decode(encoded))
        image_path = dest
    elif file and _allowed(file.filename):
        safe_name = secure_filename(f"{employee_id}_{file.filename}")
        dest = os.path.join(config.IMAGES_DIR, safe_name)
        file.save(dest)
        image_path = dest

    user = User(
        name=name, employee_id=employee_id,
        department=department, role=role,
        email=email, phone=phone,
        shift_start=shift_start, shift_end=shift_end,
        join_date=join_date, image_path=image_path,
    )
    db.session.add(user)
    db.session.commit()

    # Hot-reload face engine
    active_users = User.query.filter_by(is_active=True).all()
    engine.load_faces(active_users)

    return jsonify({'status': 'ok', 'id': user.id,
                    'employee_id': user.employee_id})


# ── API ───────────────────────────────────────────────────────────────
@users_bp.route('/api/users')
def api_users():
    dept   = request.args.get('dept',   '')
    search = request.args.get('q',      '').strip().lower()
    page   = int(request.args.get('page', 1))
    per    = int(request.args.get('per',  20))

    q = User.query.filter_by(is_active=True)
    if dept:
        q = q.filter(User.department == dept)
    if search:
        q = q.filter(User.name.ilike(f'%{search}%'))

    total = q.count()
    users = q.order_by(User.name).offset((page - 1) * per).limit(per).all()

    today = date.today()
    result = []
    for u in users:
        log = (AttendanceLog.query
               .filter_by(user_id=u.id, date=today).first())
        d = u.to_dict()
        d['today_status']   = log.status    if log else 'Absent'
        d['today_checkin']  = log.check_in  if log else ''
        d['today_checkout'] = log.check_out if log else ''
        d['today_hours']    = log.hours_worked if log else None
        result.append(d)

    depts = [r[0] for r in db.session.query(User.department)
             .filter(User.is_active == True)
             .distinct().order_by(User.department).all() if r[0]]

    return jsonify({'users': result, 'total': total,
                    'page': page, 'departments': depts})


@users_bp.route('/api/users/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    user = db.session.get(User, uid)
    if not user:
        return jsonify({'error': 'Not found'}), 404
    user.is_active = False
    db.session.commit()
    # Reload engine without deleted user
    active_users = User.query.filter_by(is_active=True).all()
    engine.load_faces(active_users)
    return jsonify({'status': 'ok'})


@users_bp.route('/set_password', methods=['POST'])
def set_password():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    password = request.form.get('password')
    if not password:
        return redirect(url_for('auth.employee_dashboard'))
    
    user = db.session.get(User, session['user_id'])
    if user:
        user.password_hash = generate_password_hash(password)
        db.session.commit()
        session.pop('needs_password', None)
    
    return redirect(url_for('auth.employee_dashboard'))


@users_bp.route('/api/users/<int:uid>/attendance')
def user_attendance(uid):
    user = db.session.get(User, uid)
    if not user:
        return jsonify({'error': 'Not found'}), 404
    logs = (AttendanceLog.query
            .filter_by(user_id=uid)
            .order_by(AttendanceLog.date.desc()).all())
    return jsonify({'user': user.to_dict(),
                    'logs': [l.to_dict() for l in logs]})
