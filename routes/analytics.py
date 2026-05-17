"""
Employee detail + deep analytics route.
GET /users/<id>/detail  →  Full analytics page per employee
GET /api/users/<id>/analytics  →  JSON analytics data
"""

from collections import defaultdict
from datetime import date, timedelta, datetime

from flask import Blueprint, render_template, jsonify, request
from database import db, User, AttendanceLog

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/users/<int:uid>/detail')
def employee_detail(uid):
    user = db.session.get(User, uid)
    if not user:
        return "Employee not found", 404
    return render_template('employee_detail.html', user=user)


@analytics_bp.route('/api/users/<int:uid>/analytics')
def employee_analytics(uid):
    user = db.session.get(User, uid)
    if not user:
        return jsonify({'error': 'Not found'}), 404

    today     = date.today()
    month_start = today.replace(day=1)
    year_start  = today.replace(month=1, day=1)

    all_logs = (AttendanceLog.query
                .filter_by(user_id=uid)
                .order_by(AttendanceLog.date).all())

    # ── Summary counts ─────────────────────────────────────────────
    total_days   = len(all_logs)
    present_days = sum(1 for l in all_logs if l.check_in)
    late_days    = sum(1 for l in all_logs if l.status == 'Late')
    early_exits  = sum(1 for l in all_logs if l.status == 'Early Departure')
    total_hours  = sum(l.hours_worked for l in all_logs if l.hours_worked)
    avg_hours    = round(total_hours / present_days, 2) if present_days else 0

    # Average check-in time
    checkin_times = []
    for l in all_logs:
        if l.check_in:
            try:
                t = datetime.strptime(l.check_in, '%H:%M:%S')
                checkin_times.append(t.hour * 60 + t.minute)
            except Exception:
                pass
    avg_checkin_min = int(sum(checkin_times) / len(checkin_times)) if checkin_times else None
    avg_checkin_str = (f"{avg_checkin_min // 60:02d}:{avg_checkin_min % 60:02d}"
                       if avg_checkin_min is not None else '—')

    # Attendance rate this month
    month_logs = [l for l in all_logs if l.date >= month_start]
    work_days_this_month = _count_workdays(month_start, today)
    month_rate = round(len(month_logs) / work_days_this_month * 100, 1) if work_days_this_month else 0

    # ── Consecutive streak ─────────────────────────────────────────
    streak = 0
    check_day = today
    log_dates = {l.date for l in all_logs if l.check_in}
    while check_day in log_dates:
        streak    += 1
        check_day -= timedelta(days=1)

    # ── Last 30 days heatmap ──────────────────────────────────────
    heatmap = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        log = next((l for l in all_logs if l.date == d), None)
        heatmap.append({
            'date':   d.isoformat(),
            'status': log.status if log and log.check_in else ('Weekend' if d.weekday() >= 5 else 'Absent'),
            'hours':  log.hours_worked if log else None,
        })

    # ── Monthly trend (last 6 months) ─────────────────────────────
    monthly = []
    for m in range(5, -1, -1):
        ref    = (today.replace(day=1) - timedelta(days=m * 28)).replace(day=1)
        end_m  = (ref.replace(month=ref.month % 12 + 1, day=1) - timedelta(days=1)) if ref.month < 12 \
                 else ref.replace(month=12, day=31)
        cnt    = sum(1 for l in all_logs if ref <= l.date <= min(end_m, today) and l.check_in)
        wdays  = _count_workdays(ref, min(end_m, today))
        monthly.append({
            'label': ref.strftime('%b %Y'),
            'count': cnt,
            'rate':  round(cnt / wdays * 100, 1) if wdays else 0,
        })

    # ── Recent logs (last 20) ──────────────────────────────────────
    recent = [l.to_dict() for l in reversed(all_logs[-20:])]

    return jsonify({
        'user': user.to_dict(),
        'summary': {
            'total_days':    total_days,
            'present_days':  present_days,
            'late_days':     late_days,
            'early_exits':   early_exits,
            'total_hours':   round(total_hours, 1),
            'avg_hours':     avg_hours,
            'avg_checkin':   avg_checkin_str,
            'month_rate':    month_rate,
            'streak':        streak,
        },
        'heatmap':  heatmap,
        'monthly':  monthly,
        'recent':   recent,
    })


def _count_workdays(start: date, end: date) -> int:
    """Count Mon–Fri days between start and end inclusive."""
    count = 0
    d = start
    while d <= end:
        if d.weekday() < 5:
            count += 1
        d += timedelta(days=1)
    return count
