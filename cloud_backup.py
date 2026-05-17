import os
import shutil
import zipfile
import time
from datetime import datetime
import config

def perform_backup():
    """
    Zips the database and images, and prepares for cloud upload.
    """
    backup_dir = os.path.join(config.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_name = f"backup_{timestamp}.zip"
    zip_path = os.path.join(backup_dir, zip_name)
    
    db_path = os.path.join(config.INSTANCE_DIR, 'attendance.db')
    images_dir = config.IMAGES_DIR
    
    print(f"[Backup] Starting backup to {zip_name}...")
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.exists(db_path):
                zipf.write(db_path, 'attendance.db')
            
            for root, dirs, files in os.walk(images_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(images_dir))
                    zipf.write(file_path, arcname)
        
        print(f"[Backup] Local zip created: {zip_path}")
        
        # ── Cloud Upload Placeholders ──────────────────────────────────
        # upload_to_google_drive(zip_path)
        # upload_to_aws_s3(zip_path)
        
        # Cleanup old backups (keep last 7 days)
        _cleanup_old_backups(backup_dir)
        
    except Exception as e:
        print(f"[Backup] Error: {e}")

def _cleanup_old_backups(directory, days=7):
    now = time.time()
    for f in os.listdir(directory):
        f_path = os.path.join(directory, f)
        if os.stat(f_path).st_mtime < now - (days * 86400):
            if os.path.isfile(f_path):
                os.remove(f_path)
                print(f"[Backup] Removed old backup: {f}")

def upload_to_google_drive(file_path):
    # TODO: Implement Pydrive or Google API upload
    # Requires credentials.json
    print("[Backup] Placeholder: Uploading to Google Drive...")
    pass

def upload_to_aws_s3(file_path):
    # TODO: Implement boto3 upload
    # Requires AWS_ACCESS_KEY and AWS_SECRET_KEY
    print("[Backup] Placeholder: Uploading to AWS S3...")
    pass

if __name__ == "__main__":
    perform_backup()
