---
title: Face Recognition Attendance System
emoji: 👤
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 👤 Face Recognition Attendance System (Enterprise Grade)

An advanced, highly secure, and performance-optimized **Face Recognition Attendance System** built with **Flask**, **OpenCV**, and **Dlib** (`face_recognition`). This system is designed for enterprise environments, featuring real-time detection, GPS geofencing, automated reporting, and comprehensive admin/employee dashboards.

---

## 🌟 Key Features

### 1. 🔍 High-Accuracy Face Recognition
*   **Dlib-backed Engine**: Leverages deep learning facial recognition models with a default match threshold of `0.45` for maximum precision.
*   **CLAHE Enhancement**: Integrates Contrast Limited Adaptive Histogram Equalization (CLAHE) to boost recognition accuracy in uneven or poor lighting environments.
*   **Performance Optimization**:
    *   **Frame Downsampling**: Processes video at `0.25x` scale for high FPS.
    *   **Frame Skipping**: Analyzes every Nth frame to reduce CPU utilization.
    *   **Recognition Cooldown**: Prevents repetitive scans of the same face within a customized cooldown window.

### 2. 🗺️ GPS Geofencing (Mobile Protection)
*   Limits check-ins/check-outs to physical office boundaries using precise geographical coordinates.
*   Configurable geofence radius (default `200 meters`) around specified office Latitude and Longitude.

### 3. 💼 Enterprise Attendance & Shift Rules
*   **Grace Periods**: Automated tracking of "Late" arrivals based on a configurable start shift time and grace period.
*   **Washroom & Checkout Protection**: Enforces minimum hours (e.g., `4.0 hours`) checked-in before a valid check-out to avoid accidental triggers.
*   **Multi-Camera Support**: Dual-index support for dedicated entry and exit cameras.

### 4. 📊 Robust Dashboards & Analytics
*   **Admin Console**: Complete visualization of attendance rates, late stats, active employees, and history logs.
*   **Employee Self-Service**: Dedicated dashboards for individuals to view their check-in histories and profiles.
*   **CSV Import/Export**: Easy bulk employee enrollment via CSV files and attendance report generation.

### 5. 🔒 Modern Cybersecurity & Hardening
*   **Scrypt Hashing**: Secure administration login utilizing high-computation cryptographic hashing.
*   **Rate Limiting**: Integrated `Flask-Limiter` to prevent brute force attacks on authentication endpoints.
*   **CSRF Protection**: Comprehensive global cross-site request forgery protection with `Flask-WTF`.

### 6. 📧 Automated Weekly Reporting
*   Automated scheduler triggers comprehensive weekly attendance reports every Friday at 5:00 PM and emails them directly to the administration team using secure SMTP.

---

## 🛠️ Technology Stack

*   **Backend**: Flask (Python)
*   **Database**: SQLite (managed with Flask-SQLAlchemy)
*   **Face Recognition**: `face_recognition` (Dlib), OpenCV (`opencv-python`), Numpy, Pandas
*   **Security & Forms**: Werkzeug (`scrypt`), Flask-WTF, Flask-Limiter, Cryptography
*   **UI/Frontend**: Modern HTML5, CSS3, Vanilla JS, Responsive Design

---

## 🚀 Getting Started

### Prerequisites
*   **Python**: Version 3.8 to 3.11 is recommended.
*   **C++ Build Tools**: Required on Windows to compile the underlying `dlib` library. Install **Visual Studio Build Tools** with the "Desktop development with C++" workload.

### 📋 Local Setup

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/PrathamKhawani/Face_Recognition_Attendence_System.git
    cd Face_Recognition_Attendence_System
    ```

2.  **Create a Virtual Environment**:
    ```bash
    python -m venv .venv
    # Activate on Windows:
    .venv\Scripts\activate
    # Activate on macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment**:
    Edit parameters inside `config.py` to match your organization:
    *   **GPS Coordinates**: Change `OFFICE_LAT` and `OFFICE_LON`.
    *   **Shift Timings**: Adjust `DEFAULT_SHIFT_START` and `DEFAULT_SHIFT_END`.
    *   **Email Reports**: Populate `SMTP_EMAIL` and `SMTP_PASSWORD` to enable email automation.

5.  **Initialize & Run the Application**:
    ```bash
    flask run
    # Or run the script directly:
    python app.py
    ```
    Access the system locally at `http://127.0.0.1:5000`.

---

## 📂 Project Directory Structure

```text
├── ImagesAttendance/      # Registered employee reference photos
├── routes/                # Blueprint routes for auth, analytics, users, camera, etc.
│   ├── analytics.py       # Statistics, charting, and CSV exports
│   ├── attendance.py      # Core check-in / check-out endpoints
│   ├── auth.py            # Hashed admin authentication & limiters
│   ├── camera.py          # Real-time video streaming pipeline
│   ├── dashboard.py       # Admin and user dashboards controllers
│   ├── import_users.py    # Bulk employee CSV importer
│   └── users.py           # Employee profile management
├── static/                # Static assets (CSS styles, JS dashboards, charts)
├── templates/             # HTML Templates (Base layout, login, logs, etc.)
├── app.py                 # Core application startup entry point
├── config.py              # Centralized variables, thresholds, and security parameters
├── database.py            # SQLAlchemy Model structures and DB interface
├── extensions.py          # Shared Flask extensions (DB, CSRF, Limiter)
├── face_engine.py         # OpenCV video capture and Dlib face recognition processing
├── requirements.txt       # Project python packages list
└── .gitignore             # Git ignored folders (.venv, local DB, temp cache)
```

---

## 🛡️ License

This project is open-source and licensed under the [MIT License](LICENSE).
