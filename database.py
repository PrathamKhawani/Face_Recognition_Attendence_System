from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    department  = db.Column(db.String(100), default='')
    role        = db.Column(db.String(100), default='')
    email       = db.Column(db.String(150), default='')
    phone       = db.Column(db.String(30),  default='')
    shift_start = db.Column(db.String(10),  default='09:00')
    shift_end   = db.Column(db.String(10),  default='18:00')
    join_date   = db.Column(db.Date, default=date.today)
    image_path    = db.Column(db.String(500), default='')
    password_hash = db.Column(db.String(255), nullable=True) # for personal dashboard
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    logs = db.relationship('AttendanceLog', backref='user', lazy=True,
                           cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':          self.id,
            'name':        self.name,
            'employee_id': self.employee_id,
            'department':  self.department,
            'role':        self.role,
            'email':       self.email,
            'phone':       self.phone,
            'shift_start': self.shift_start,
            'shift_end':   self.shift_end,
            'join_date':   self.join_date.isoformat() if self.join_date else '',
            'is_active':   self.is_active,
            'created_at':  self.created_at.isoformat() if self.created_at else '',
            'has_image':   bool(self.image_path),
        }


class AttendanceLog(db.Model):
    __tablename__ = 'attendance_logs'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date         = db.Column(db.Date,    nullable=False, default=date.today)
    check_in     = db.Column(db.String(8),  nullable=True)   # HH:MM:SS
    check_out    = db.Column(db.String(8),  nullable=True)
    hours_worked = db.Column(db.Float,   nullable=True)
    status       = db.Column(db.String(30), default='Present')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':           self.id,
            'user_id':      self.user_id,
            'name':         self.user.name if self.user else '',
            'employee_id':  self.user.employee_id if self.user else '',
            'department':   self.user.department if self.user else '',
            'date':         self.date.isoformat() if self.date else '',
            'check_in':     self.check_in or '',
            'check_out':    self.check_out or '',
            'hours_worked': self.hours_worked,
            'status':       self.status,
        }
