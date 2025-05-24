import smtplib
import ssl
from email.mime.text import MIMEText

smtp_port = 587
smtp_server = "smtp.gmail.com"

email_from = "thearnest7@gmail.com"
email_to = "mrforensics100@gmail.com"
pswd = "utzqmfzvrqqdxbi"  # Use your Gmail app password

subject = "Test Email"
body = "Dear god, please help!!"

# Create a MIMEText object
msg = MIMEText(body)
msg["Subject"] = subject
msg["From"] = email_from
msg["To"] = email_to

simple_email_context = ssl.create_default_context()

TIE_server = None
try:
    print("Connecting to email server...")
    TIE_server = smtplib.SMTP(smtp_server, smtp_port)
    TIE_server.starttls(context=simple_email_context)
    TIE_server.login(email_from, pswd)
    print("Connected to email server :-")

    print(f"Sending email to {email_to}...")
    TIE_server.sendmail(email_from, email_to, msg.as_string())
    print(f"Email successfully sent to - {email_to}")

except Exception as e:
    print(e)

finally:
    if TIE_server:
        TIE_server.quit()
        print("Connection to email server closed.")