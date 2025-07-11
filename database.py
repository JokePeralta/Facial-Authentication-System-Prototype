import sqlite3
import json
import pickle
from datetime import datetime
import os

class FaceAuthDatabase:
    def __init__(self, db_path="face_auth.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                full_name TEXT,
                email TEXT,
                face_encoding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Authentication logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                auth_type TEXT,
                confidence REAL,
                status TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
    
    def add_user(self, username, face_encoding, full_name=None, email=None):
        """Add a new user to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert face encoding to binary for storage
            encoding_blob = pickle.dumps(face_encoding)
            
            cursor.execute('''
                INSERT INTO users (username, full_name, email, face_encoding)
                VALUES (?, ?, ?, ?)
            ''', (username, full_name, email, encoding_blob))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ User '{username}' added successfully (ID: {user_id})")
            return user_id
            
        except sqlite3.IntegrityError:
            print(f"❌ User '{username}' already exists")
            return None
        except Exception as e:
            print(f"❌ Error adding user: {str(e)}")
            return None
    
    def get_all_users(self):
        """Get all users from the database (without face encodings)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, username, full_name, email, created_at, is_active
                FROM users WHERE is_active = 1
            ''')

            users = []
            for row in cursor.fetchall():
                user = {
                    'id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'email': row[3],
                    'created_at': row[4],
                    'is_active': row[5]
                }
                users.append(user)

            conn.close()
            return users

        except Exception as e:
            print(f"❌ Error retrieving users: {str(e)}")
            return []
    
    def get_users_with_encodings(self):
        """Get all users with their face encodings (for authentication)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, username, full_name, email, face_encoding, created_at, is_active
                FROM users WHERE is_active = 1
            ''')

            users = []
            for row in cursor.fetchall():
                user = {
                    'id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'email': row[3],
                    'face_encoding': pickle.loads(row[4]),  # Deserialize face encoding
                    'created_at': row[5],
                    'is_active': row[6]
                }
                users.append(user)

            conn.close()
            return users

        except Exception as e:
            print(f"❌ Error retrieving users with encodings: {str(e)}")
            return []
    
    def get_user_by_username(self, username):
        """Get a specific user by username"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, full_name, email, created_at, is_active
                FROM users WHERE username = ? AND is_active = 1
            ''', (username,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'email': row[3],
                    'created_at': row[4],
                    'is_active': row[5]
                }
            return None
            
        except Exception as e:
            print(f"❌ Error retrieving user: {str(e)}")
            return None
    
    def log_authentication(self, user_id, username, auth_type, confidence, status):
        """Log authentication attempt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO auth_logs (user_id, username, auth_type, confidence, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, auth_type, confidence, status))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Error logging authentication: {str(e)}")
    
    def get_auth_logs(self, limit=50):
        """Get recent authentication logs"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, username, auth_type, confidence, status, timestamp
                FROM auth_logs
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            logs = []
            for row in cursor.fetchall():
                log = {
                    'user_id': row[0],
                    'username': row[1],
                    'auth_type': row[2],
                    'confidence': row[3],
                    'status': row[4],
                    'timestamp': row[5]
                }
                logs.append(log)
            
            conn.close()
            return logs
            
        except Exception as e:
            print(f"❌ Error retrieving logs: {str(e)}")
            return []
    
    def delete_user(self, username):
        """Soft delete a user (mark as inactive)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET is_active = 0 WHERE username = ?
            ''', (username,))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                print(f"✅ User '{username}' deleted successfully")
                return True
            else:
                conn.close()
                print(f"❌ User '{username}' not found")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting user: {str(e)}")
            return False
    
    def get_user_stats(self):
        """Get database statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total users
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
            total_users = cursor.fetchone()[0]
            
            # Total authentication attempts today
            cursor.execute('''
                SELECT COUNT(*) FROM auth_logs 
                WHERE DATE(timestamp) = DATE('now')
            ''')
            today_auths = cursor.fetchone()[0]
            
            # Successful authentications today
            cursor.execute('''
                SELECT COUNT(*) FROM auth_logs 
                WHERE DATE(timestamp) = DATE('now') AND status = 'SUCCESS'
            ''')
            today_success = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_users': total_users,
                'today_auths': today_auths,
                'today_success': today_success,
                'success_rate': (today_success/today_auths*100) if today_auths > 0 else 0
            }
            
        except Exception as e:
            print(f"❌ Error getting stats: {str(e)}")
            return None

# Test the database
if __name__ == "__main__":
    db = FaceAuthDatabase()
    stats = db.get_user_stats()
    print(f"📊 Database Stats: {stats}")