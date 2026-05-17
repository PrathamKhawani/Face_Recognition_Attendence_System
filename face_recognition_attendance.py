# face_recognition_attendance.py

import cv2
import numpy as np
import face_recognition
import os
from datetime import datetime
import pandas as pd

# ----------------------------
# STEP 1: Load student images
# ----------------------------
path = "ImagesAttendance"  # folder with student images
images = []
studentNames = []
myList = os.listdir(path)

print("Loading student images...")

for file in myList:
    img = cv2.imread(f"{path}/{file}")
    images.append(img)
    studentNames.append(os.path.splitext(file)[0])  # filename without extension

print("Loaded:", studentNames)


# ----------------------------
# STEP 2: Encode faces
# ----------------------------
def findEncodings(imagesList):
    encodeList = []
    for img in imagesList:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # convert BGR to RGB
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)
    return encodeList


knownEncodings = findEncodings(images)
print("Encoding Complete ✅")


# ----------------------------
# STEP 3: Mark attendance
# ----------------------------
def markAttendance(name):
    file = "Attendance.csv"

    # Create file if it doesn’t exist
    if not os.path.exists(file):
        df = pd.DataFrame(columns=["Name", "Date", "Time"])
        df.to_csv(file, index=False)

    df = pd.read_csv(file)

    # Prevent duplicate entries (same student, same date)
    today = datetime.now().strftime("%Y-%m-%d")
    if not ((df["Name"] == name) & (df["Date"] == today)).any():
        now = datetime.now()
        timeStr = now.strftime("%H:%M:%S")
        dateStr = now.strftime("%Y-%m-%d")
        newRow = {"Name": name, "Date": dateStr, "Time": timeStr}
        df = pd.concat([df, pd.DataFrame([newRow])], ignore_index=True)
        df.to_csv(file, index=False)
        print(f"[+] Attendance marked for {name}")


# ----------------------------
# STEP 4: Webcam recognition
# ----------------------------
cap = cv2.VideoCapture(0)  # 0 = default camera

while True:
    success, img = cap.read()
    imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)  # reduce size for speed
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

    facesCurFrame = face_recognition.face_locations(imgS)
    encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)

    for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
        matches = face_recognition.compare_faces(knownEncodings, encodeFace)
        faceDis = face_recognition.face_distance(knownEncodings, encodeFace)
        matchIndex = np.argmin(faceDis)

        if matches[matchIndex]:
            name = studentNames[matchIndex].upper()
            y1, x2, y2, x1 = faceLoc
            y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4  # scale back up
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.rectangle(img, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
            cv2.putText(img, name, (x1+6, y2-6),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            markAttendance(name)

    cv2.imshow("Webcam", img)
    if cv2.waitKey(1) & 0xFF == ord("q"):  # press q to exit
        break

cap.release()
cv2.destroyAllWindows()
