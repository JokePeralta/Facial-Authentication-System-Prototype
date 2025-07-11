from flask import Flask, render_template, request, jsonify, Response
import cv2
import face_recognition
import numpy as np
import json
import base64
from datetime import datetime
from database import FaceAuthDatabase
import threading
import time

app = Flask(__name__)

class WebFaceAuthSystem:
    def __init__(self):
        self.db = FaceAuthDatabase()
        self.known_encodings = []
        self.camera = None
        self.camera_active = False
        self.load_encodings()
    
    def load_encodings(self):
        """Load face encodings from database"""
        try:
            users = self.db.get_users_with_encodings()
            self.known_encodings = []

            for user in users:
                encoding_data = {
                    'name': user['username'],
                    'full_name': user['full_name'],
                    'email': user['email'],
                    'encoding': user['face_encoding'],
                    'user_id': user['id']
                }
                self.known_encodings.append(encoding_data)

            print(f"✅ Loaded {len(self.known_encodings)} users from database")

        except Exception as e:
            print(f"❌ Error loading encodings: {str(e)}")
    
    def authenticate_frame(self, frame):
        """Authenticate faces in a frame"""
        results = []
        
        # Find faces in the frame
        face_locations = face_recognition.face_locations(frame)
        face_encodings = face_recognition.face_encodings(frame, face_locations)
        
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            best_match_name = "Unknown"
            best_confidence = 0
            best_user_id = None
            
            for known_face in self.known_encodings:
                distance = face_recognition.face_distance([known_face['encoding']], face_encoding)[0]
                confidence = (1 - distance) * 100
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match_name = known_face['name']
                    best_user_id = known_face['user_id']
            
            results.append({
                'name': best_match_name,
                'confidence': best_confidence,
                'user_id': best_user_id,
                'bbox': [left, top, right, bottom],
                'authenticated': best_confidence > 60
            })
        
        return results

# Initialize the system
face_system = WebFaceAuthSystem()

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/register')
def register_page():
    """User registration page"""
    return render_template('register.html')

@app.route('/logs')
def logs_page():
    return render_template('logs.html')

@app.route('/authenticate')
def authenticate_page():
    """Authentication page"""
    return render_template('authenticate.html')

@app.route('/api/stats')
def get_stats():
    """Get system statistics"""
    try:
        stats = face_system.db.get_user_stats()
        users = face_system.db.get_all_users()
        
        return jsonify({
            'total_users': stats['total_users'] if stats else 0,
            'today_auths': stats['today_auths'] if stats else 0,
            'today_success': stats['today_success'] if stats else 0,
            'success_rate': stats['success_rate'] if stats else 0,
            'users': [{'username': u['username'], 'full_name': u['full_name'], 
                      'created_at': u['created_at']} for u in users]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
def get_logs():
    """Get authentication logs"""
    try:
        logs = face_system.db.get_auth_logs(20)
        return jsonify(logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/register', methods=['POST'])
def register_user():
    """Register a new user via API using 5 face samples"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'})
            
        username = data.get('username')
        full_name = data.get('full_name', '')
        email = data.get('email', '')
        images = data.get('images')

        # Basic validation
        if not username:
            return jsonify({'success': False, 'message': 'Username is required'})
            
        if not images or len(images) != 5:
            return jsonify({'success': False, 'message': '5 face images are required'})

        # Check if user already exists
        if face_system.db.get_user_by_username(username):
            return jsonify({'success': False, 'message': 'Username already exists'})

        encodings = []

        for i, image_data in enumerate(images):
            try:
                # Handle data URL format
                if ',' in image_data:
                    header, base64_data = image_data.split(',', 1)
                else:
                    base64_data = image_data
                    
                image_bytes = base64.b64decode(base64_data)

                # Convert to OpenCV image
                nparr = np.frombuffer(image_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is None:
                    return jsonify({'success': False, 'message': f'Invalid image format in image {i + 1}'})

                # Detect face encoding
                face_locations = face_recognition.face_locations(frame)
                face_encodings = face_recognition.face_encodings(frame, face_locations)

                if not face_encodings:
                    return jsonify({'success': False, 'message': f'No face detected in image {i + 1}'})

                encodings.append(face_encodings[0])

            except Exception as e:
                return jsonify({'success': False, 'message': f'Error processing image {i + 1}: {str(e)}'})

        # Average all 5 encodings into one
        average_encoding = np.mean(encodings, axis=0)

        # Save user
        user_id = face_system.db.add_user(username, average_encoding, full_name, email)

        if user_id:
            face_system.load_encodings()  # Reload encodings after registration
            face_system.db.log_authentication(user_id, username, "REGISTRATION", 100.0, "SUCCESS")
            return jsonify({'success': True, 'message': f'User {username} registered successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to register user'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})

@app.route('/api/check_face', methods=['POST'])
def check_face():
    """Check if a face is detected in the image"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'})
            
        image_data = data.get('image')

        if not image_data:
            return jsonify({'success': False, 'message': 'Image is required'})

        # Handle data URL format
        if ',' in image_data:
            image_data = image_data.split(',')[1]
            
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({'success': False, 'message': 'Invalid image format'})

        face_locations = face_recognition.face_locations(frame)
        if not face_locations:
            return jsonify({'success': False, 'message': 'No face detected'})
            
        return jsonify({'success': True, 'message': 'Face detected'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/authenticate', methods=['POST'])
def authenticate_user():
    """Authenticate user via API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'})
            
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'Image is required'})
        
        # Handle data URL format
        if ',' in image_data:
            image_data = image_data.split(',')[1]
            
        image_bytes = base64.b64decode(image_data)
        
        # Convert to opencv format
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'success': False, 'message': 'Invalid image format'})
        
        # Authenticate
        results = face_system.authenticate_frame(frame)
        
        if results:
            best_result = max(results, key=lambda x: x['confidence'])
            
            if best_result['authenticated']:
                # Log successful authentication
                face_system.db.log_authentication(
                    best_result['user_id'], 
                    best_result['name'], 
                    "WEB_AUTH", 
                    best_result['confidence'], 
                    "SUCCESS"
                )
                
                return jsonify({
                    'success': True,
                    'user': best_result['name'],
                    'confidence': round(best_result['confidence'], 2),
                    'message': f'Welcome {best_result["name"]}!'
                })
            else:
                # Log failed authentication
                face_system.db.log_authentication(
                    None, 
                    "Unknown", 
                    "WEB_AUTH", 
                    best_result['confidence'], 
                    "FAILED"
                )
                
                return jsonify({
                    'success': False,
                    'confidence': round(best_result['confidence'], 2),
                    'message': 'Authentication failed. Low confidence.'
                })
        else:
            return jsonify({'success': False, 'message': 'No face detected'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/delete_user', methods=['POST'])
def delete_user():
    """Delete a user from the system"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'})
            
        username = data.get('username')

        if not username:
            return jsonify({'success': False, 'message': 'Username is required'})

        user = face_system.db.get_user_by_username(username)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})

        success = face_system.db.delete_user(username)
        if success:
            face_system.load_encodings()  # Refresh encodings to remove this user's face
            return jsonify({'success': True, 'message': f'User {username} deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete user'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    
@app.route('/api/get_users', methods=['GET'])
def get_users():
    """Return list of active users with limited fields for frontend"""
    try:
        users = face_system.db.get_all_users()
        safe_users = [
            {
                'username': user['username'],
                'full_name': user['full_name'],
                'created_at': user['created_at']
            } for user in users
        ]
        return jsonify({'success': True, 'users': safe_users})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)