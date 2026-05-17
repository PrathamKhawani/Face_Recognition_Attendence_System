import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, 'ImagesAttendance')
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
DB_PATH = os.path.join(INSTANCE_DIR, 'attendance.db')
SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_PATH}'

# Face recognition
FACE_MATCH_THRESHOLD = 0.45   # lower = stricter (0.4–0.6)
FRAME_SCALE = 0.25            # downsample ratio for speed
FRAME_SKIP = 3                # process every Nth frame
RECOGNITION_COOLDOWN = 30     # seconds before same face re-triggers
MIN_CHECKOUT_HOURS   = 4.0    # min hours checked-in before checkout is valid (washroom protection)

# Performance & Accuracy
ACCURACY_ENHANCEMENT = True   # uses CLAHE and higher jitters
ENCODING_JITTERS     = 10     # higher = more accurate but slower loading
DETECTION_MODEL      = 'hog'  # 'hog' (fast CPU) or 'cnn' (slow CPU, fast GPU)

# GPS Geofencing (Mobile Protection)
GEOFENCING_ENABLED   = True
OFFICE_LAT           = 19.0760   # Example: Mumbai
OFFICE_LON           = 72.8777
GEOFENCE_RADIUS      = 200      # Meters

# Shift defaults (HH:MM 24h)
DEFAULT_SHIFT_START = "09:00"
DEFAULT_SHIFT_END   = "18:00"
LATE_GRACE_MINUTES  = 15      # minutes after shift_start before "Late"

# Upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

# Admin login (change these!)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD_HASH = 'scrypt:32768:8:1$cZ6FCDbHx8yzxcey$d38f91211ebe82fc64c0fd8b349e8fea5d9df6589c569c75a61f8f36400efd61d5fc4484abc8ed62c401400a4e60529bc4b72d6da1c6df57fe33e6319e1de994'

# Camera indices (change if using USB cameras)
ENTRY_CAMERA_INDEX = 0
EXIT_CAMERA_INDEX  = 0   # set to 1 when second camera is connected

# ── Reporting ───────────────────────────────────────────────────────────
# Set these to enable automated weekly Friday 5:00 PM email reports
SMTP_EMAIL    = ''  # e.g., 'your.company@gmail.com'
SMTP_PASSWORD = ''  # Google App Password if using Gmail
