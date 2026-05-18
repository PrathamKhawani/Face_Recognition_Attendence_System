import os
from datetime import timedelta
from flask import Flask, session, redirect, url_for, request
from database import db
from face_engine import engine
from extensions import limiter, csrf
import config

from routes.dashboard  import dashboard_bp
from routes.attendance import attendance_bp
from routes.users      import users_bp
from routes.camera     import camera_bp
from routes.import_users import import_bp
from routes.analytics  import analytics_bp
from routes.auth       import auth_bp


def create_app():
    app = Flask(__name__)

    os.makedirs(config.INSTANCE_DIR, exist_ok=True)
    os.makedirs(config.IMAGES_DIR,   exist_ok=True)

    app.config['SQLALCHEMY_DATABASE_URI']        = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH']             = config.MAX_CONTENT_LENGTH
    app.secret_key                               = 'faceid-enterprise-s3cr3t-2026'
    app.permanent_session_lifetime               = timedelta(hours=12)
    
    # Required for Hugging Face Spaces (iframe embedding cross-origin cookies)
    app.config['SESSION_COOKIE_SAMESITE']        = 'None'
    app.config['SESSION_COOKIE_SECURE']          = True

    db.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        db.create_all()
        _migrate_csv(app)
        from database import User
        users = User.query.filter_by(is_active=True).all()
        n = engine.load_faces(users)
        print(f"[FaceEngine] {n} face(s) loaded.")

    # ── Register Blueprints ────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(import_bp)
    app.register_blueprint(analytics_bp)

    # ── Global auth guard ──────────────────────────────────────────
    PUBLIC_ROUTES = {'auth.login', 'auth.logout', 'static'}

    @app.before_request
    def require_login():
        if request.endpoint in PUBLIC_ROUTES:
            return
        if not session.get('logged_in'):
            return redirect(url_for('auth.login', next=request.path))
        
        # Protect Admin routes
        admin_patterns = ['dashboard.', 'users.', 'attendance.attendance', 'import_users.', 'analytics.']
        if any(request.endpoint.startswith(p) for p in admin_patterns):
            if not session.get('admin_logged_in'):
                return redirect(url_for('auth.employee_dashboard'))

    @app.after_request
    def add_security_headers(response):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Dynamically authorize Hugging Face Space domain in production while keeping airtight local security
        is_cloud = os.environ.get("PORT") is not None
        if is_cloud:
            # Modern browsers use frame-ancestors over X-Frame-Options
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; media-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'self' https://*.huggingface.co https://huggingface.co;"
        else:
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; media-src 'self' blob:; object-src 'none'; base-uri 'self';"
            
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # ── Monthly Automated Email Report ──────────────────────────────
    def _report_daemon():
        from datetime import datetime, date, timedelta
        import time, smtplib, io
        from email.message import EmailMessage
        import openpyxl

        last_sent_month = None
        while True:
            now = datetime.now()
            # 1st of every month at 09:00 AM
            if now.day == 1 and now.hour == 9 and last_sent_month != now.month:
                if config.SMTP_EMAIL and config.SMTP_PASSWORD:
                    try:
                        with app.app_context():
                            print("[AutoReport] Generating monthly Excel report...")
                            # 1. Generate Report for the previous month
                            first_day_of_current_month = now.date().replace(day=1)
                            last_day_of_prev_month = first_day_of_current_month - timedelta(days=1)
                            first_day_of_prev_month = last_day_of_prev_month.replace(day=1)
                            
                            logs = AttendanceLog.query.filter(
                                AttendanceLog.date >= first_day_of_prev_month,
                                AttendanceLog.date <= last_day_of_prev_month
                            ).all()
                            
                            wb = openpyxl.Workbook()
                            ws = wb.active
                            ws.title = "Monthly Report"
                            ws.append(['Date', 'Employee ID', 'Name', 'Check-In', 'Check-Out', 'Status'])
                            for log in logs:
                                ws.append([str(log.date), log.user.employee_id, log.user.name, 
                                           log.check_in or '', log.check_out or '', log.status])
                            
                            output = io.BytesIO()
                            wb.save(output)
                            output.seek(0)
                            
                            # 2. Send Email
                            msg = EmailMessage()
                            msg['Subject'] = f"Monthly Attendance Report - {first_day_of_prev_month.strftime('%B %Y')}"
                            msg['From'] = config.SMTP_EMAIL
                            msg['To'] = config.SMTP_EMAIL # Sending to self/admin for demo
                            msg.set_content(f"Attached is the automated monthly attendance report for {first_day_of_prev_month.strftime('%B %Y')}.")
                            msg.add_attachment(output.read(), maintype='application', subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=f"Monthly_Report_{first_day_of_prev_month.strftime('%Y_%m')}.xlsx")
                            
                            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                                smtp.login(config.SMTP_EMAIL, config.SMTP_PASSWORD)
                                smtp.send_message(msg)
                            
                            print("[AutoReport] Monthly report sent successfully!")
                            last_sent_month = now.month

                    except Exception as e:
                        print(f"[AutoReport] Failed to send email: {e}")
            time.sleep(60) # Check every minute

    import threading
    t1 = threading.Thread(target=_report_daemon, daemon=True)
    t1.start()

    def _backup_daemon():
        from cloud_backup import perform_backup
        import time
        last_run_date = None
        while True:
            now = datetime.now()
            # Run at 02:00 AM every day
            if now.hour == 2 and now.minute == 0 and last_run_date != now.date():
                try:
                    perform_backup()
                    last_run_date = now.date()
                except Exception as e:
                    print(f"[BackupDaemon] Error: {e}")
            time.sleep(30)

    t2 = threading.Thread(target=_backup_daemon, daemon=True)
    t2.start()

    return app


def _migrate_csv(app):
    csv_path = os.path.join(config.BASE_DIR, 'Attendance.csv')
    if not os.path.exists(csv_path):
        return
    flag = os.path.join(config.INSTANCE_DIR, '.csv_migrated')
    if os.path.exists(flag):
        return

    import csv
    from datetime import date
    from database import User, AttendanceLog

    print("[Migration] Importing legacy Attendance.csv …")
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        count  = 0
        for row in reader:
            try:
                name = row.get('Name', '').strip().title()
                d    = date.fromisoformat(row.get('Date', ''))
                t    = row.get('Time', '').strip()
            except Exception:
                continue
            user = User.query.filter(
                db.func.lower(User.name) == name.lower()).first()
            if not user:
                import uuid
                user = User(name=name,
                            employee_id=f"CSV-{str(uuid.uuid4())[:6].upper()}")
                db.session.add(user)
                db.session.flush()
            if not AttendanceLog.query.filter_by(user_id=user.id, date=d).first():
                db.session.add(AttendanceLog(
                    user_id=user.id, date=d, check_in=t, status='Present'))
                count += 1
    db.session.commit()
    open(flag, 'w').close()
    print(f"[Migration] Done — {count} records imported.")


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # Only use adhoc SSL context locally if PORT is not set by a cloud host
    use_ssl = os.environ.get("PORT") is None
    ssl_ctx = 'adhoc' if use_ssl else None
    
    print(f"Starting server on port {port} (SSL: {use_ssl})")
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True, ssl_context=ssl_ctx)

