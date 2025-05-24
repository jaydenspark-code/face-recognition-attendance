import cv2
import os
import pickle

# Define paths
FACE_DIR = "ImageAttendance"
FACE_DB_FILE = "faces.pkl"

def register_specific_faces():
    # List of expected faces
    expected_faces = ["Elon Musk", "Bill Gates", "Jack Ma"]
    
    # Check if the directory exists
    if not os.path.exists(FACE_DIR):
        print(f"Error: Directory {FACE_DIR} does not exist!")
        return
    
    # Initialize faces dictionary
    faces = {}
    
    # First, try to load existing database
    if os.path.exists(FACE_DB_FILE):
        try:
            with open(FACE_DB_FILE, 'rb') as f:
                faces = pickle.load(f)
            print(f"Loaded existing database with {len(faces)} faces")
        except:
            print("Could not load existing database, creating new one")
    
    # Check for each expected face
    for name in expected_faces:
        # Check different possible filenames
        possible_filenames = [
            f"{name}.jpg",
            f"{name}.jpeg", 
            f"{name}.png",
            f"{name.lower()}.jpg",
            f"{name.lower()}.jpeg",
            f"{name.lower()}.png",
            f"{name.replace(' ', '_')}.jpg",
            f"{name.replace(' ', '_')}.jpeg",
            f"{name.replace(' ', '_')}.png",
            f"{name.lower().replace(' ', '_')}.jpg",
            f"{name.lower().replace(' ', '_')}.jpeg",
            f"{name.lower().replace(' ', '_')}.png"
        ]
        
        found = False
        for filename in possible_filenames:
            path = os.path.join(FACE_DIR, filename)
            if os.path.exists(path):
                print(f"Found {name} at {path}")
                
                # Try to read the image
                image = cv2.imread(path)
                if image is None:
                    print(f"Warning: Could not read image {path}")
                    continue
                
                # Store in our faces dictionary
                person_id = name.lower().replace(" ", "_")
                faces[person_id] = {"name": name, "path": path}
                print(f"Added {name} to database")
                found = True
                break
        
        if not found:
            print(f"Warning: Could not find image for {name}")
    
    # Save the updated database
    with open(FACE_DB_FILE, 'wb') as f:
        pickle.dump(faces, f)
    
    print(f"Database updated with {len(faces)} faces")
    
    # Show the list of registered faces
    print("\nRegistered faces:")
    for person_id, data in faces.items():
        print(f"- {data['name']} (path: {data['path']})")

if __name__ == "__main__":
    register_specific_faces()