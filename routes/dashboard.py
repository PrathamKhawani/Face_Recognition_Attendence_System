from flask import Blueprint, render_template, jsonify
from datetime import date
from database import db, User, AttendanceLog
import config

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    return render_template('dashboard.html',
                           min_checkout_h=config.MIN_CHECKOUT_HOURS,
                           office_lat=config.OFFICE_LAT,
                           office_lon=config.OFFICE_LON,
                           geofence_radius=config.GEOFENCE_RADIUS,
                           geofencing_enabled=config.GEOFENCING_ENABLED)



@dashboard_bp.route('/api/stats')
def stats():
    today        = date.today()
    total_users  = User.query.filter_by(is_active=True).count()
    present_ids  = (db.session.query(AttendanceLog.user_id)
                    .filter(AttendanceLog.date == today)
                    .filter(AttendanceLog.check_in != None)
                    .distinct().count())
    absent       = max(0, total_users - present_ids)
    rate         = round(present_ids / total_users * 100, 1) if total_users else 0

    # Recent activity (last 12 events)
    recent_logs = (AttendanceLog.query
                   .filter(AttendanceLog.date == today)
                   .order_by(db.func.coalesce(AttendanceLog.check_out, AttendanceLog.check_in).desc())
                   .limit(12).all())
    recent = []
    for log in recent_logs:
        recent.append({
            'name':       log.user.name,
            'department': log.user.department,
            'check_in':   log.check_in or '',
            'check_out':  log.check_out or '',
            'status':     log.status,
            'hours':      log.hours_worked,
        })

    # Hourly distribution for today
    hourly = [0] * 24
    logs_today = (AttendanceLog.query
                  .filter(AttendanceLog.date == today)
                  .filter(AttendanceLog.check_in != None).all())
    for log in logs_today:
        try:
            h = int(log.check_in.split(':')[0])
            hourly[h] += 1
        except Exception:
            pass

    return jsonify({
        'total_users':    total_users,
        'present_today':  present_ids,
        'absent_today':   absent,
        'attendance_rate': rate,
        'recent':         recent,
        'hourly':         hourly,
    })
