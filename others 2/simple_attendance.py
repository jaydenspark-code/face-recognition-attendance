import streamlit as st
import cv2
import numpy as np
import pandas as pd
import os
import datetime
import time
from face_recognition_opencv import detect_face, preprocess_face, extract_features, capture_face
from data_handler import load_data, save_data, record_attendance, get_attendance_report
from auth import check_password

# Define a function to find user by face features
def find_user_by_face_features(face_features, threshold=0.8):
    """
    Find a user by comparing face features.
    
    Args:
        face_features (numpy.ndarray): The face features to match
        threshold (float): Similarity threshold (0-1, higher is more strict)
        
    Returns:
        tuple: (user_id of matched user or None, confidence score)
    """
    from face_recognition_opencv import compare_faces
    
    if not st.session_state.user_data:
        return None, 0
    
    # Prepare a list of known face features and corresponding user IDs
    known_features = []
    user_ids = []
    
    for user_id, user_info in st.session_state.user_data.items():
        if 'face_data' in user_info and 'features' in user_info['face_data']:
            known_features.append(user_info['face_data']['features'])
            user_ids.append(user_id)
    
    if not known_features:
        return None, 0
    
    # Compare the face against known faces
    match_index, similarity = compare_faces(known_features, face_features, threshold)
    
    if match_index >= 0:
        # Return the user ID and confidence score
        return user_ids[match_index], similarity * 100
    
    return None, similarity * 100

# Set page config
st.set_page_config(
    page_title="Face ID Attendance System",
    page_icon="👤",
    layout="wide"
)

# Initialize session state variables if they don't exist
if 'user_data' not in st.session_state:
    st.session_state.user_data = load_data('users.pkl')

if 'attendance_data' not in st.session_state:
    st.session_state.attendance_data = load_data('attendance.pkl')

if 'admin_view' not in st.session_state:
    st.session_state.admin_view = False

# Main title
st.title("Face ID Attendance System")

# Sidebar for navigation
menu = st.sidebar.selectbox("Menu", ["Home", "Register", "Mark Attendance", "View Attendance", "Admin Panel"])

if menu == "Home":
    st.write("## Welcome to the Face ID Attendance System")
    st.write("This system allows you to:")
    st.write("1. Register your face for attendance tracking")
    st.write("2. Mark your attendance using facial recognition")
    st.write("3. View attendance records")
    
    st.write("### How it works")
    st.write("1. Register your face and details in the 'Register' section")
    st.write("2. Use 'Mark Attendance' to record your attendance")
    st.write("3. Administrators can view and manage attendance in the 'Admin Panel'")

elif menu == "Register":
    st.header("Register New User")
    
    # Form for user registration
    with st.form("registration_form"):
        name = st.text_input("Full Name")
        user_id = st.text_input("User ID (e.g., employee number, student ID)")
        department = st.text_input("Department/Class")
        
        # Use columns for the capture button and status
        col1, col2 = st.columns([1, 2])
        submit_button = col1.form_submit_button("Capture Face")
        
        if submit_button and name and user_id:
            # Initialize camera
            st.session_state.capture_image = True
            col2.write("Please look at the camera...")
    
    if st.session_state.get('capture_image', False):
        # Camera feed for face capture
        face_data = capture_face()
        
        if face_data is not None:
            # Add the new user to our data
            if user_id not in st.session_state.user_data:
                st.session_state.user_data[user_id] = {
                    'name': name,
                    'user_id': user_id,
                    'department': department,
                    'face_data': face_data,
                    'registration_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                save_data('users.pkl', st.session_state.user_data)
                st.success(f"Registration successful for {name}!")
            else:
                st.error("User ID already exists. Please use a different ID.")
            
            # Reset capture state
            st.session_state.capture_image = False
            st.rerun()
        else:
            st.error("No face detected or multiple faces detected. Please try again with a single clear face in view.")
            # Reset capture state
            st.session_state.capture_image = False

elif menu == "Mark Attendance":
    st.header("Mark Attendance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Start Attendance Capture"):
            st.session_state.attendance_capture = True
    
    with col2:
        if st.button("Stop Capture"):
            st.session_state.attendance_capture = False
    
    if st.session_state.get('attendance_capture', False):
        # Create a placeholder for the camera feed
        camera_placeholder = st.empty()
        status_placeholder = st.empty()
        
        # Initialize webcam
        cap = cv2.VideoCapture(0)
        
        try:
            # Set a timeout (30 seconds)
            timeout = time.time() + 30
            recognition_cooldown = 0
            
            while time.time() < timeout and st.session_state.get('attendance_capture', False):
                ret, frame = cap.read()
                if not ret:
                    status_placeholder.error("Failed to capture image from camera")
                    break
                
                # Convert to RGB for processing
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Display the frame with detected faces
                faces, face_locations = detect_face(rgb_frame)
                camera_placeholder.image(faces, channels="RGB", use_column_width=True)
                
                # Only process recognition every second to avoid overwhelming the system
                if time.time() > recognition_cooldown:
                    if len(face_locations) > 0:
                        # Process the face and try to recognize it
                        face_image = preprocess_face(rgb_frame, face_locations[0])
                        face_features = extract_features(face_image)
                        
                        # Try to match the face
                        user_id, confidence = find_user_by_face_features(face_features)
                        
                        if user_id:
                            user_info = st.session_state.user_data[user_id]
                            status_placeholder.success(f"Attendance marked for {user_info['name']} ({user_id}) - Confidence: {confidence:.2f}%")
                            
                            # Record attendance
                            record_attendance(user_id, user_info['name'], user_info['department'])
                            
                            # Short pause after successful recognition
                            time.sleep(2)
                        else:
                            status_placeholder.warning("Face not recognized. Please register first.")
                    else:
                        status_placeholder.info("No face detected")
                    
                    # Set cooldown for next recognition attempt
                    recognition_cooldown = time.time() + 1
                
                # Small pause to reduce CPU usage
                time.sleep(0.1)
                
            # If we timed out
            if time.time() >= timeout:
                status_placeholder.warning("Attendance capture session timed out. Press 'Start Attendance Capture' to begin a new session.")
                st.session_state.attendance_capture = False
        
        finally:
            # Always release the camera
            cap.release()

    # Add a backup method using ID and password
    st.write("### Or use ID and password")
    
    with st.form("manual_attendance_form"):
        user_id = st.text_input("User ID")
        password = st.text_input("Password (if set during registration)", type="password")
        
        submit_button = st.form_submit_button("Mark Attendance Manually")
        
        if submit_button and user_id:
            if user_id in st.session_state.user_data:
                user_info = st.session_state.user_data[user_id]
                # If the user has a password set, verify it
                if 'password' in user_info:
                    if password == user_info['password']:
                        record_attendance(user_id, user_info['name'], user_info['department'])
                        st.success(f"Attendance marked for {user_info['name']}")
                    else:
                        st.error("Incorrect password")
                else:
                    # If no password is set, allow attendance without verification
                    record_attendance(user_id, user_info['name'], user_info['department'])
                    st.success(f"Attendance marked for {user_info['name']}")
            else:
                st.error("User ID not found. Please register first.")

elif menu == "View Attendance":
    st.header("View Attendance Records")
    
    # Date filter
    date_filter = st.date_input("Select Date", datetime.date.today())
    
    # User filter
    users = [user_info['name'] for user_id, user_info in st.session_state.user_data.items()]
    users.insert(0, "All Users")
    selected_user = st.selectbox("Select User", users)
    
    # Get filtered attendance data
    selected_date_str = date_filter.strftime("%Y-%m-%d")
    
    attendance_df = get_attendance_report(selected_date_str, selected_user if selected_user != "All Users" else None)
    
    if not attendance_df.empty:
        st.write(f"### Attendance for {selected_date_str}")
        st.dataframe(attendance_df)
        
        # Download option
        csv = attendance_df.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f"attendance_{selected_date_str}.csv",
            mime="text/csv"
        )
    else:
        st.info(f"No attendance records found for {selected_date_str}")

elif menu == "Admin Panel":
    st.header("Admin Panel")
    
    # Simple authentication
    if not st.session_state.get('admin_authenticated', False):
        authenticated = check_password()
        if authenticated:
            st.session_state.admin_authenticated = True
            st.rerun()
    else:
        # Admin functions
        admin_action = st.selectbox("Admin Actions", [
            "View All Users", 
            "Remove User", 
            "Attendance Overview",
            "Export All Data"
        ])
        
        if admin_action == "View All Users":
            st.subheader("Registered Users")
            
            if not st.session_state.user_data:
                st.info("No users registered yet.")
            else:
                # Create a dataframe of user information
                user_rows = []
                for user_id, user_info in st.session_state.user_data.items():
                    user_info_copy = user_info.copy()
                    # Remove face data for display
                    user_info_copy.pop('face_data', None)
                    user_rows.append(user_info_copy)
                
                user_df = pd.DataFrame(user_rows)
                st.dataframe(user_df)
        
        elif admin_action == "Remove User":
            st.subheader("Remove User")
            
            if not st.session_state.user_data:
                st.info("No users registered yet.")
            else:
                # Create a list of users to select from
                user_options = [f"{info['name']} ({uid})" for uid, info in st.session_state.user_data.items()]
                user_options.insert(0, "Select a user to remove")
                
                selected_user = st.selectbox("Select User", user_options)
                
                if selected_user != "Select a user to remove":
                    # Extract user ID from the selection
                    user_id = selected_user.split('(')[-1].strip(')')
                    
                    if st.button(f"Confirm removal of {st.session_state.user_data[user_id]['name']}"):
                        # Remove the user
                        del st.session_state.user_data[user_id]
                        save_data('users.pkl', st.session_state.user_data)
                        st.success(f"User {user_id} has been removed")
                        st.rerun()
        
        elif admin_action == "Attendance Overview":
            st.subheader("Attendance Overview")
            
            # Date range selection
            col1, col2 = st.columns(2)
            start_date = col1.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=7))
            end_date = col2.date_input("End Date", datetime.date.today())
            
            # Calculate date range
            date_range = (end_date - start_date).days + 1
            
            # Get all attendance records
            all_attendance = []
            for record in st.session_state.attendance_data:
                record_date = datetime.datetime.strptime(record['timestamp'].split()[0], "%Y-%m-%d").date()
                if start_date <= record_date <= end_date:
                    all_attendance.append(record)
            
            # Create a summary
            if all_attendance:
                attendance_df = pd.DataFrame(all_attendance)
                
                # Summary by day
                st.write("### Daily Attendance Count")
                daily_counts = attendance_df['timestamp'].str.split(' ', expand=True)[0].value_counts().sort_index()
                st.bar_chart(daily_counts)
                
                # Summary by user
                st.write("### Attendance by User")
                user_counts = attendance_df['name'].value_counts()
                st.bar_chart(user_counts)
                
                # Summary by department
                st.write("### Attendance by Department")
                dept_counts = attendance_df['department'].value_counts()
                st.bar_chart(dept_counts)
                
                # Raw data
                st.write("### Raw Attendance Data")
                st.dataframe(attendance_df)
            else:
                st.info(f"No attendance records found between {start_date} and {end_date}")
        
        elif admin_action == "Export All Data":
            st.subheader("Export All Data")
            
            # Create dataframes
            if st.session_state.user_data:
                user_rows = []
                for user_id, user_info in st.session_state.user_data.items():
                    user_info_copy = user_info.copy()
                    # Remove face data for CSV export
                    user_info_copy.pop('face_data', None)
                    user_rows.append(user_info_copy)
                
                user_df = pd.DataFrame(user_rows)
                
                # Download users
                user_csv = user_df.to_csv(index=False)
                st.download_button(
                    label="Download User Data",
                    data=user_csv,
                    file_name="users_data.csv",
                    mime="text/csv"
                )
            else:
                st.info("No user data available for export.")
            
            # Attendance data
            if st.session_state.attendance_data:
                attendance_df = pd.DataFrame(st.session_state.attendance_data)
                attendance_csv = attendance_df.to_csv(index=False)
                
                st.download_button(
                    label="Download Attendance Data",
                    data=attendance_csv,
                    file_name="attendance_data.csv",
                    mime="text/csv"
                )
            else:
                st.info("No attendance data available for export.")
        
        # Logout button
        if st.button("Logout from Admin Panel"):
            st.session_state.admin_authenticated = False
            st.rerun()