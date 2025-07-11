import face_recognition
import cv2
import numpy as np
import pickle
import os
from datetime import datetime
import json

class FaceAuthSystem:
    def __init__(self, data_dir="face_data"):
        self.data_dir = data_dir
        self.encodings_file = os.path.join(data_dir, "face_encodings.pkl")
        self.users_file = os.path.join(data_dir, "users.json")
        
        # Create directory if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Load existing data
        self.load_data()
    
    def load_data(self):
        """Load existing face encodings and user data"""
        try:
            with open(self.encodings_file, 'rb') as f:
                self.known_encodings = pickle.load(f)
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        except FileNotFoundError:
            self.known_encodings = []
            self.users = {}
    
    def save_data(self):
        """Save face encodings and user data"""
        with open(self.encodings_file, 'wb') as f:
            pickle.dump(self.known_encodings, f)
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def register_user(self, username):
        """Register a new user with face samples"""
        if username in self.users:
            print(f"❌ User '{username}' already exists!")
            return False
        
        print(f"📸 Registering user: {username}")
        print("🎯 Instructions:")
        print("- Look directly at the camera")
        print("- Ensure good lighting")
        print("- Press SPACE to capture each sample")
        print("- Press ESC to cancel")
        print("- We'll capture 5 samples for better accuracy")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Could not open camera")
            return False
        
        samples = []
        sample_count = 0
        target_samples = 5
        
        while sample_count < target_samples:
            ret, frame = cap.read()
            if not ret:
                print("❌ Could not read frame")
                break
            
            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Draw instructions on frame
            cv2.putText(frame, f"Sample {sample_count + 1}/{target_samples}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, "Press SPACE to capture", 
                       (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, "Press ESC to cancel", 
                       (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Detect faces and draw rectangles
            face_locations = face_recognition.face_locations(frame)
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            
            cv2.imshow('Face Registration', frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC key
                print("❌ Registration cancelled")
                cap.release()
                cv2.destroyAllWindows()
                return False
            
            elif key == 32:  # SPACE key
                if len(face_locations) == 1:
                    print(f"📸 Capturing sample {sample_count + 1}...")
                    
                    # Get face encoding
                    face_encoding = face_recognition.face_encodings(frame)
                    if face_encoding:
                        samples.append(face_encoding[0])
                        sample_count += 1
                        print(f"✅ Sample {sample_count} captured successfully!")
                        
                        # Brief pause for user feedback
                        cv2.putText(frame, "CAPTURED!", (10, 130), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        cv2.imshow('Face Registration', frame)
                        cv2.waitKey(500)  # Show "CAPTURED!" for 500ms
                    else:
                        print("❌ Could not get face encoding, try again")
                
                elif len(face_locations) == 0:
                    print("❌ No face detected, please position yourself in the camera")
                else:
                    print("❌ Multiple faces detected, please ensure only one person is in frame")
        
        cap.release()
        cv2.destroyAllWindows()
        
        if len(samples) == target_samples:
            # Average the encodings for better accuracy
            avg_encoding = np.mean(samples, axis=0)
            
            # Save user data
            self.users[username] = {
                'created_at': datetime.now().isoformat(),
                'login_count': 0,
                'last_login': None
            }
            
            self.known_encodings.append({
                'username': username,
                'encoding': avg_encoding.tolist()
            })
            
            self.save_data()
            print(f"✅ User '{username}' registered successfully!")
            return True
        else:
            print(f"❌ Registration failed. Only captured {len(samples)} samples.")
            return False
    
    def authenticate_user(self):
        """Authenticate user through face recognition"""
        print("🔐 Face Authentication")
        print("Look at the camera for authentication...")
        print("Press ESC to cancel")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Could not open camera")
            return False
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Could not read frame")
                break
            
            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Draw instructions
            cv2.putText(frame, "Look at camera for authentication", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, "Press ESC to cancel", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Find faces in frame
            face_locations = face_recognition.face_locations(frame)
            face_encodings = face_recognition.face_encodings(frame, face_locations)
            
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Compare with known faces - simplified approach
                best_match_name = "Unknown"
                best_confidence = 0
                
                for known_face in self.known_encodings:
                    known_encoding = np.array(known_face['encoding'])
                    distance = face_recognition.face_distance([known_encoding], face_encoding)[0]
                    confidence = (1 - distance) * 100
                    
                    print(f"🔍 Debug: {known_face['username']} - Distance: {distance:.3f}, Confidence: {confidence:.1f}%")
                    
                    # Keep track of best match
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match_name = known_face['username']
                
                # Set final values
                name = best_match_name if best_confidence > 40 else "Unknown"  # Very lenient threshold
                confidence = best_confidence
                
                # Draw rectangle and name
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                cv2.putText(frame, f"{name} ({confidence:.1f}%)", 
                           (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                
                # Auto-authenticate if confidence is above 60%
                if confidence > 60:
                    print(f"✅ Authentication successful!")
                    print(f"👤 User: {name}")
                    print(f"🎯 Confidence: {confidence:.1f}%")
                    
                    # Update login info
                    self.users[name]['login_count'] += 1
                    self.users[name]['last_login'] = datetime.now().isoformat()
                    self.save_data()
                    
                    cap.release()
                    cv2.destroyAllWindows()
                    return True
            
            cv2.imshow('Face Authentication', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC key
                break
        
        cap.release()
        cv2.destroyAllWindows()
        print("❌ Authentication cancelled or failed")
        return False
    
    def list_users(self):
        """List all registered users"""
        if not self.users:
            print("📝 No users registered yet")
            return
        
        print("\n👥 Registered Users:")
        print("-" * 50)
        for username, info in self.users.items():
            created = datetime.fromisoformat(info['created_at']).strftime("%Y-%m-%d %H:%M")
            last_login = "Never"
            if info['last_login']:
                last_login = datetime.fromisoformat(info['last_login']).strftime("%Y-%m-%d %H:%M")
            
            print(f"👤 {username}")
            print(f"   📅 Created: {created}")
            print(f"   🔐 Last login: {last_login}")
            print(f"   📊 Login count: {info['login_count']}")
            print()
    
    def delete_user(self, username):
        """Delete a user"""
        if username not in self.users:
            print(f"❌ User '{username}' not found")
            return False
        
        # Remove from users
        del self.users[username]
        
        # Remove from encodings
        self.known_encodings = [enc for enc in self.known_encodings if enc['username'] != username]
        
        self.save_data()
        print(f"✅ User '{username}' deleted successfully")
        return True

def main():
    """Main menu for face authentication system"""
    auth_system = FaceAuthSystem()
    
    while True:
        print("\n" + "="*50)
        print("🔐 FACE AUTHENTICATION SYSTEM")
        print("="*50)
        print("1. 📝 Register new user")
        print("2. 🔐 Authenticate user")
        print("3. 👥 List all users")
        print("4. 🗑️  Delete user")
        print("5. 🚪 Exit")
        print("="*50)
        
        try:
            choice = input("Enter your choice (1-5): ").strip()
            
            if choice == '1':
                username = input("Enter username: ").strip()
                if username:
                    auth_system.register_user(username)
                else:
                    print("❌ Username cannot be empty")
            
            elif choice == '2':
                auth_system.authenticate_user()
            
            elif choice == '3':
                auth_system.list_users()
            
            elif choice == '4':
                username = input("Enter username to delete: ").strip()
                if username:
                    auth_system.delete_user(username)
                else:
                    print("❌ Username cannot be empty")
            
            elif choice == '5':
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice, please try again")
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()