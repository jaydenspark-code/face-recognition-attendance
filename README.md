Face Recognition Attendance System
A robust, multi-user face recognition attendance system built with Streamlit, OpenCV, DeepFace, and Excel for easy management and reporting.
Features
Multi-frame registration: Users register with multiple face images for higher accuracy.
Flexible anti-spoofing: System can be strict (live faces only) or flexible (accepts images).
Attendance marking: Users mark attendance by face verification.
Admin portal: Manage lecturers, course reps, students, and regenerate all embeddings.
Excel logs: Attendance and confirmation logs are saved in Excel files.
Email notifications: Sends attendance confirmation emails to students.
Daily summary: View daily attendance and absences by course.
User-friendly UI: Built with Streamlit for easy use.


Requirements
Python 3.7+
Install dependencies: (pip install streamlit opencv-python deepface openpyxl numpy dlib)

Usage
1. Run the App (streamlit run AttendanceProject.py)

2. Main Menu Options
Register New Face:
Register a new user by capturing 5–6 face images from different angles.

Take Attendance:
Mark your attendance by verifying your face.

View Attendance Records:
See all attendance logs in a table.

List Registered Faces:
View all registered users and their face images.

Verify Attendance:
For course reps and lecturers to verify and confirm attendance.

Daily Summary:
View daily attendance and absences per course.

Manual Attendance:
(If enabled) Mark attendance manually.

Admin Portal:
Manage users, courses, and system settings.

3. Admin Portal Features
Add/Remove Lecturer
Add/Remove Course Representative
Update Students Credentials:
Update student info and face images (multi-frame, just like registration).
Update Lecturer Emails
Manage Confirmation Logs:
View and remove attendance confirmation logs.
Regenerate All Face Embeddings:
Recompute embeddings for all users (for system upgrades or settings changes).

Data Files
faces.pkl: Stores registered users and their face embeddings.
attendance.xlsx: Stores attendance logs.
confirmation_logs.xlsx: Stores attendance verification logs.
users.pkl: Stores lecturer and course rep info.
ImageAttendance/: Folder for all face images.

Tips
For best accuracy, register with clear, well-lit images from multiple angles.
If using images (not live faces), set anti_spoofing=False in DeepFace calls.
For production, set anti_spoofing=True for maximum security.
Admin password is set in the script (ADMIN_PASSWORD). Change it for security.