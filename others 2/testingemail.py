import smtplib
import time
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(level=logging.INFO)

def send_email_notification(student_name, course_title, student_email):
    """Send an email notification to a student when their attendance is marked."""
    sender_email = "thearnest7@gmail.com"
    sender_password = "eutzqmfzvrqqdxbi"  # <-- Replace with your actual app password

    subject = f"Attendance Marked for {course_title}"
    body = f"Dear {student_name},\n\nYour attendance has been successfully marked for the course: {course_title}.\n\nBest regards,\nAttendance System"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = student_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    for attempt in range(3):  # Retry up to 3 times
        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            logging.info(f"Attendance notification sent to {student_email} for {student_name} in {course_title}.")
            return True
        except smtplib.SMTPException as e:
            logging.error(f"Attempt {attempt + 1}: Failed to send email: {e}")
            if attempt < 2:  # Wait before retrying
                time.sleep(5)  # Wait 5 seconds before retrying
            else:
                print(f"An error occurred while sending the email notification: {e}")
                return False

if __name__ == "__main__":
    result = send_email_notification(
        student_name="Roman Reigns",
        course_title="Programming for Problem Solving",
        student_email="mrforensics100@gmail.com"
    )
    if result:
        print("Email sent successfully!")
    else:
        print("Failed to send email.")
