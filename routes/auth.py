"""
Login authentication — session-based, protects all dashboard routes.
Supports both Admin and Employee logins.
"""

from functools import wraps
from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash, jsonify)
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import limiter
from database import User, db
import config

auth_bp = Blueprint('auth', __name__)


# ── Decorators ──────────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated


# ── Routes ─────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if session.get('logged_in'):
        if session.get('admin_logged_in'):
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.employee_dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip() # Can be admin name or employee_id
        password = request.form.get('password', '')

        # 1. Check Admin
        if username == config.ADMIN_USERNAME and check_password_hash(config.ADMIN_PASSWORD_HASH, password):
            session.permanent = True
            session['logged_in']       = True
            session['admin_logged_in'] = True
            session['user_id']         = 0
            session['username']        = username
            return redirect(url_for('dashboard.index'))

        # 2. Check Employee
        user = User.query.filter_by(employee_id=username, is_active=True).first()
        if user:
            # For new users without password, allow them to set one on first login or use a default
            # Here we assume a password exists or we can add logic for 'first-time setup'
            if user.password_hash and check_password_hash(user.password_hash, password):
                session.permanent = True
                session['logged_in']       = True
                session['admin_logged_in'] = False
                session['user_id']         = user.id
                session['username']        = user.name
                session['employee_id']     = user.employee_id
                return redirect(url_for('auth.employee_dashboard'))
            elif not user.password_hash:
                # First time login logic: if password matches employee_id (default), let them in and ask to change
                if password == user.employee_id:
                    session['logged_in']   = True
                    session['user_id']     = user.id
                    session['username']    = user.name
                    session['needs_password'] = True
                    return redirect(url_for('auth.employee_dashboard'))
        
        error = 'Invalid credentials. Please try again.'

    return render_template('login.html', error=error)


@auth_bp.route('/dashboard/me')
@login_required
def employee_dashboard():
    if session.get('admin_logged_in'):
        return redirect(url_for('dashboard.index'))
    
    user = db.session.get(User, session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
        
    return render_template('employee_dashboard.html', user=user)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
