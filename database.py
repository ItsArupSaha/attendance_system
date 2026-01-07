"""
Firestore operations for teacher attendance system.
Handles all database interactions using Firestore (Cloud Firestore).
"""
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import pytz
from config import get_firebase_credentials_dict

# Bangladesh timezone (UTC+6)
BD_TIMEZONE = pytz.timezone('Asia/Dhaka')


# Initialize Firebase Admin SDK
_initialized = False


def initialize_firebase():
    """Initialize Firebase Admin SDK if not already initialized."""
    global _initialized
    if not _initialized:
        if not firebase_admin._apps:
            # Get credentials from environment variables
            cred_dict = get_firebase_credentials_dict()
            
            # Validate required fields
            missing = []
            if not cred_dict.get('project_id'):
                missing.append('FIREBASE_PROJECT_ID')
            if not cred_dict.get('private_key'):
                missing.append('FIREBASE_PRIVATE_KEY')
            if not cred_dict.get('client_email'):
                missing.append('FIREBASE_CLIENT_EMAIL')
            
            if missing:
                raise ValueError(
                    f"Missing required Firebase environment variables: {', '.join(missing)}. "
                    "Please set these in your .env file or environment."
                )
            
            # Create credentials from dictionary
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        _initialized = True


def get_db():
    """Get Firestore database instance."""
    initialize_firebase()
    return firestore.client()


def register_teacher(teacher_id, name, department, fingerprint_id):
    """
    Register a new teacher in Firestore.
    
    Args:
        teacher_id: Unique identifier for the teacher
        name: Teacher's name
        department: Teacher's department
        fingerprint_id: Fingerprint ID from AS608 module (matching done locally)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = get_db()
        teacher_ref = db.collection('teachers').document(teacher_id)
        
        teacher_data = {
            'name': name,
            'department': department,
            'fingerprint_id': fingerprint_id,
            'attendance': {}  # Will store date-keyed attendance records
        }
        
        teacher_ref.set(teacher_data)
        return True
    except Exception as e:
        print(f"Error registering teacher: {e}")
        return False


def get_teacher_by_fingerprint_id(fingerprint_id):
    """
    Find teacher by fingerprint_id using Firestore query.
    
    Args:
        fingerprint_id: Fingerprint ID to search for
    
    Returns:
        dict: Teacher data if found, None otherwise
    """
    try:
        db = get_db()
        teachers_ref = db.collection('teachers')
        
        # Query by fingerprint_id - efficient direct query
        query = teachers_ref.where('fingerprint_id', '==', fingerprint_id).limit(1)
        docs = query.stream()
        
        for doc in docs:
            teacher_data = doc.to_dict()
            return {
                'teacher_id': doc.id,
                **teacher_data
            }
        
        return None
    except Exception as e:
        print(f"Error finding teacher by fingerprint: {e}")
        return None


def get_teacher_by_id(teacher_id):
    """
    Get teacher data by teacher_id.
    
    Args:
        teacher_id: Teacher's unique identifier
    
    Returns:
        dict: Teacher data if found, None otherwise
    """
    try:
        db = get_db()
        teacher_ref = db.collection('teachers').document(teacher_id)
        doc = teacher_ref.get()
        
        if doc.exists:
            teacher_data = doc.to_dict()
            return {
                'teacher_id': doc.id,
                **teacher_data
            }
        return None
    except Exception as e:
        print(f"Error getting teacher: {e}")
        return None


def get_today_attendance(teacher_id, date_str):
    """
    Get attendance record for a specific date.
    
    Args:
        teacher_id: Teacher's unique identifier
        date_str: Date in YYYY-MM-DD format
    
    Returns:
        dict: Attendance record if exists, None otherwise
    """
    try:
        db = get_db()
        teacher_ref = db.collection('teachers').document(teacher_id)
        teacher_doc = teacher_ref.get()
        
        if not teacher_doc.exists:
            return None
        
        teacher_data = teacher_doc.to_dict()
        attendance = teacher_data.get('attendance', {})
        
        # Return attendance record for the specific date
        return attendance.get(date_str)
    except Exception as e:
        print(f"Error getting attendance: {e}")
        return None


def create_check_in(teacher_id, date_str, time_str):
    """
    Create a check-in record for a teacher on a specific date.
    
    Args:
        teacher_id: Teacher's unique identifier
        date_str: Date in YYYY-MM-DD format
        time_str: Time in HH:MM:SS format
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = get_db()
        teacher_ref = db.collection('teachers').document(teacher_id)
        
        # Get current attendance data
        teacher_doc = teacher_ref.get()
        if not teacher_doc.exists:
            return False
        
        teacher_data = teacher_doc.to_dict()
        attendance = teacher_data.get('attendance', {})
        
        # Update attendance for the specific date
        attendance[date_str] = {
            'check_in': time_str
        }
        
        # Update the document
        teacher_ref.update({
            'attendance': attendance
        })
        
        return True
    except Exception as e:
        print(f"Error creating check-in: {e}")
        return False


def create_check_out(teacher_id, date_str, time_str, working_hours):
    """
    Create a check-out record for a teacher on a specific date.
    
    Args:
        teacher_id: Teacher's unique identifier
        date_str: Date in YYYY-MM-DD format
        time_str: Time in HH:MM:SS format
        working_hours: Human-readable working hours string
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = get_db()
        teacher_ref = db.collection('teachers').document(teacher_id)
        
        # Get current attendance data
        teacher_doc = teacher_ref.get()
        if not teacher_doc.exists:
            return False
        
        teacher_data = teacher_doc.to_dict()
        attendance = teacher_data.get('attendance', {})
        
        # Update attendance for the specific date
        if date_str not in attendance:
            attendance[date_str] = {}
        
        attendance[date_str].update({
            'check_out': time_str,
            'working_hours': working_hours
        })
        
        # Update the document
        teacher_ref.update({
            'attendance': attendance
        })
        
        return True
    except Exception as e:
        print(f"Error creating check-out: {e}")
        return False


def get_all_teachers():
    """
    Get all registered teachers.
    
    Returns:
        dict: All teachers data (teacher_id as key)
    """
    try:
        db = get_db()
        teachers_ref = db.collection('teachers')
        docs = teachers_ref.stream()
        
        teachers = {}
        for doc in docs:
            teachers[doc.id] = doc.to_dict()
        
        return teachers
    except Exception as e:
        print(f"Error getting all teachers: {e}")
        return {}


# ============================================
# System Mode Management
# ============================================

def get_system_mode():
    """
    Get current system mode.
    
    Returns:
        str: Current mode ('register' or 'attendance'), defaults to 'attendance'
    """
    try:
        db = get_db()
        system_ref = db.collection('system').document('mode')
        doc = system_ref.get()
        
        if doc.exists:
            mode_data = doc.to_dict()
            return mode_data.get('mode', 'attendance')
        else:
            # Default to attendance mode if not set
            set_system_mode('attendance')
            return 'attendance'
    except Exception as e:
        print(f"Error getting system mode: {e}")
        return 'attendance'  # Default to attendance on error


def set_system_mode(mode):
    """
    Set system mode.
    
    Args:
        mode: 'register' or 'attendance'
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if mode not in ['register', 'attendance']:
            return False
        
        db = get_db()
        system_ref = db.collection('system').document('mode')
        system_ref.set({
            'mode': mode,
            'updated_at': datetime.now(BD_TIMEZONE).isoformat()
        })
        return True
    except Exception as e:
        print(f"Error setting system mode: {e}")
        return False


# ============================================
# Pending Registration Management
# ============================================

def save_pending_registration(name, department):
    """
    Save pending registration (name and department) waiting for fingerprint.
    
    Args:
        name: Teacher's name
        department: Teacher's department
    
    Returns:
        str: Pending registration ID, or None if failed
    """
    try:
        db = get_db()
        pending_ref = db.collection('pending_registrations')
        
        pending_data = {
            'name': name,
            'department': department,
            'created_at': datetime.now(BD_TIMEZONE).isoformat(),
            'status': 'pending'
        }
        
        doc_ref = pending_ref.add(pending_data)
        return doc_ref[1].id  # Return document ID
    except Exception as e:
        print(f"Error saving pending registration: {e}")
        return None


def get_pending_registration(pending_id):
    """
    Get pending registration by ID.
    
    Args:
        pending_id: Pending registration document ID
    
    Returns:
        dict: Pending registration data if found, None otherwise
    """
    try:
        db = get_db()
        pending_ref = db.collection('pending_registrations').document(pending_id)
        doc = pending_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            return {
                'pending_id': doc.id,
                **data
            }
        return None
    except Exception as e:
        print(f"Error getting pending registration: {e}")
        return None


def delete_pending_registration(pending_id):
    """
    Delete pending registration after successful completion.
    
    Args:
        pending_id: Pending registration document ID
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = get_db()
        pending_ref = db.collection('pending_registrations').document(pending_id)
        pending_ref.delete()
        return True
    except Exception as e:
        print(f"Error deleting pending registration: {e}")
        return False


def get_latest_pending_registration():
    """
    Get the most recent pending registration.
    Used when ESP32 sends fingerprint without pending_id.
    
    Returns:
        dict: Latest pending registration if found, None otherwise
    """
    try:
        db = get_db()
        pending_ref = db.collection('pending_registrations')
        query = pending_ref.where('status', '==', 'pending')
        docs = query.stream()
        
        # Get all pending and find the latest by created_at
        latest = None
        latest_time = None
        
        for doc in docs:
            data = doc.to_dict()
            created_at = data.get('created_at', '')
            if not latest or (created_at > latest_time if latest_time else True):
                latest = {
                    'pending_id': doc.id,
                    **data
                }
                latest_time = created_at
        
        return latest
    except Exception as e:
        print(f"Error getting latest pending registration: {e}")
        return None
