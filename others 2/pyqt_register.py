import sys
import cv2
import os
import pickle
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QWidget, QLineEdit, QComboBox, QMessageBox
)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPixmap

FACE_DIR = "ImageAttendance"
FACE_DB_FILE = "faces.pkl"
ATTENDANCE_FILE = "attendance.xlsx"
os.makedirs(FACE_DIR, exist_ok=True)

def load_faces_db():
    if os.path.exists(FACE_DB_FILE):
        with open(FACE_DB_FILE, 'rb') as f:
            return pickle.load(f)
    return {}

def save_faces_db(db):
    with open(FACE_DB_FILE, 'wb') as f:
        pickle.dump(db, f)

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unified Attendance & Registration")
        self.image_label = QLabel()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter Name or ID")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter Email (for registration)")
        self.register_button = QPushButton("Register User")
        self.attendance_button = QPushButton("Mark Attendance")
        self.status_label = QLabel()
        self.course_box = QComboBox()
        self.course_box.addItems([
            "Office Productivity Software Tools",
            "Foreign Language (French) I",
            "Programming for Problem Solving",
            "Intro. to Cyber Security and Digital Forensics",
            "Communication Skills in English I",
            "Linear Algebra",
            "African Studies"
        ])
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("Registration"))
        self.layout.addWidget(self.name_input)
        self.layout.addWidget(self.email_input)
        self.layout.addWidget(self.register_button)
        self.layout.addWidget(QLabel("Attendance"))
        self.layout.addWidget(self.course_box)
        self.layout.addWidget(self.attendance_button)
        self.layout.addWidget(self.image_label)
        self.layout.addWidget(self.status_label)
        self.setLayout(self.layout)

        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self.capture_frame)
        self.capturing = False
        self.frame_count = 0

        self.register_button.clicked.connect(self.start_registration)
        self.attendance_button.clicked.connect(self.mark_attendance)

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.image_label.setPixmap(QPixmap.fromImage(qt_img))
            self.current_frame = frame

    def start_registration(self):
        self.person_id = self.name_input.text().strip().lower().replace(" ", "_")
        self.email = self.email_input.text().strip()
        if not self.person_id or not self.email:
            self.status_label.setText("Please enter name and email.")
            return
        self.status_label.setText("Capturing frames for registration...")
        self.frame_count = 0
        self.capturing = True
        self.capture_timer.start(1000)  # Capture every 1 second

    def capture_frame(self):
        if self.capturing and hasattr(self, 'current_frame'):
            filename = os.path.join(FACE_DIR, f"{self.person_id}_{self.frame_count}.jpg")
            cv2.imwrite(filename, self.current_frame)
            self.frame_count += 1
            if self.frame_count >= 7:  # Capture 7 frames
                self.capturing = False
                self.capture_timer.stop()
                # Save to DB
                faces_db = load_faces_db()
                face_paths = [
                    os.path.join(FACE_DIR, f"{self.person_id}_{i}.jpg") for i in range(7)
                ]
                faces_db[self.person_id] = {
                    "name": self.name_input.text().strip(),
                    "email": self.email,
                    "paths": face_paths
                }
                save_faces_db(faces_db)
                self.status_label.setText("Registration complete!")

    def mark_attendance(self):
        # Simple matching: compare current frame to all registered images (add DeepFace for real use)
        faces_db = load_faces_db()
        if not hasattr(self, 'current_frame'):
            self.status_label.setText("No camera frame available.")
            return
        # For demo: just check if any images exist for the entered name
        person_id = self.name_input.text().strip().lower().replace(" ", "_")
        if person_id in faces_db:
            # In production, use DeepFace to compare self.current_frame to faces_db[person_id]['paths']
            self.status_label.setText(f"Attendance marked for {faces_db[person_id]['name']} in {self.course_box.currentText()}.")
            # Optionally, save to Excel or CSV
            # ...
        else:
            self.status_label.setText("User not registered.")

    def closeEvent(self, event):
        self.cap.release()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainApp()
    win.show()
    sys.exit(app.exec_())