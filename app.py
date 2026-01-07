"""
Flask backend for Biometric Attendance System (Fingerprint-Only).
Handles teacher registration and attendance recording via fingerprint authentication.
Supports mode-based operation: REGISTER MODE and ATTENDANCE MODE.
"""
from flask import Flask, request, render_template, jsonify
from datetime import datetime, timedelta
import database
from config import COOLDOWN_MINUTES

app = Flask(__name__)

# In-memory storage for latest scanned fingerprint_id (waiting for registration)
# Structure: { "fingerprint_id": int, "timestamp": ISO8601 string }
_latest_fingerprint_id = None


def calculate_working_hours(check_in_time, check_out_time):
    """
    Calculate working hours between check-in and check-out times.
    
    Args:
        check_in_time: Check-in time string (HH:MM:SS)
        check_out_time: Check-out time string (HH:MM:SS)
    
    Returns:
        str: Human-readable working hours (e.g., "8 hours 30 minutes")
    """
    try:
        # Parse time strings
        check_in = datetime.strptime(check_in_time, "%H:%M:%S").time()
        check_out = datetime.strptime(check_out_time, "%H:%M:%S").time()
        
        # Create datetime objects for calculation
        check_in_dt = datetime.combine(datetime.today(), check_in)
        check_out_dt = datetime.combine(datetime.today(), check_out)
        
        # Handle case where check-out is next day
        if check_out_dt < check_in_dt:
            check_out_dt += timedelta(days=1)
        
        # Calculate difference
        diff = check_out_dt - check_in_dt
        total_seconds = int(diff.total_seconds())
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        return f"{hours} hours {minutes} minutes"
    except Exception as e:
        print(f"Error calculating working hours: {e}")
        return "0 hours 0 minutes"


def get_server_time():
    """Get current server time in ISO8601 format."""
    return datetime.now().isoformat()


def get_date_string():
    """Get current date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")


def get_time_string():
    """Get current time in HH:MM:SS format."""
    return datetime.now().strftime("%H:%M:%S")


@app.route('/')
def index():
    """Admin page with mode control and registration form."""
    current_mode = database.get_system_mode()
    return render_template('register.html', current_mode=current_mode)


@app.route('/mode', methods=['GET'])
def get_mode():
    """
    Get current system mode.
    ESP32 can query this to know which mode is active.
    """
    try:
        current_mode = database.get_system_mode()
        return jsonify({
            'status': 'success',
            'mode': current_mode,
            'server_time': get_server_time()
        }), 200
    except Exception as e:
        print(f"Error getting mode: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get system mode: {str(e)}',
            'server_time': get_server_time()
        }), 500


@app.route('/mode', methods=['POST'])
def set_mode():
    """
    Set system mode (admin only).
    Request: { "mode": "register" | "attendance" }
    """
    try:
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Request must be JSON',
                'server_time': get_server_time()
            }), 400
        
        data = request.get_json()
        mode = data.get('mode', '').lower()
        
        if mode not in ['register', 'attendance']:
            return jsonify({
                'status': 'error',
                'message': 'Mode must be "register" or "attendance"',
                'server_time': get_server_time()
            }), 400
        
        success = database.set_system_mode(mode)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'System mode set to {mode}',
                'mode': mode,
                'server_time': get_server_time()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to set system mode',
                'server_time': get_server_time()
            }), 500
    
    except Exception as e:
        print(f"Error setting mode: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to set mode: {str(e)}',
            'server_time': get_server_time()
        }), 500


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Register a new teacher - saves all three fields together.
    
    Request (JSON or form-data):
    {
        "name": "John Doe",
        "department": "CSE",
        "fingerprint_id": 7
    }
    
    In REGISTER MODE:
    - Accepts name, department, and fingerprint_id together
    - Validates all fields are present
    - Saves complete teacher record
    
    In ATTENDANCE MODE:
    - Returns error (registration disabled)
    """
    if request.method == 'GET':
        current_mode = database.get_system_mode()
        return render_template('register.html', current_mode=current_mode)
    
    try:
        # Check system mode
        current_mode = database.get_system_mode()
        
        if current_mode != 'register':
            return jsonify({
                'status': 'error',
                'message': f'System is in {current_mode} mode. Switch to register mode to register teachers.'
            }), 403
        
        # Get data (supports both JSON and form-data)
        if request.is_json:
            data = request.get_json()
            name = data.get('name', '').strip()
            department = data.get('department', '').strip()
            fingerprint_id = data.get('fingerprint_id')
        else:
            name = request.form.get('name', '').strip()
            department = request.form.get('department', '').strip()
            fingerprint_id_str = request.form.get('fingerprint_id', '').strip()
            fingerprint_id = int(fingerprint_id_str) if fingerprint_id_str else None
        
        # Validate all required fields
        if not name or not department or fingerprint_id is None:
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: name, department, fingerprint_id'
            }), 400
        
        # Validate fingerprint_id type
        try:
            fingerprint_id = int(fingerprint_id)
        except (ValueError, TypeError):
            return jsonify({
                'status': 'error',
                'message': 'Invalid fingerprint_id format (must be integer)'
            }), 400
        
        # Check if fingerprint_id already exists
        existing_teacher = database.get_teacher_by_fingerprint_id(fingerprint_id)
        if existing_teacher:
            return jsonify({
                'status': 'error',
                'message': f'Fingerprint ID {fingerprint_id} already registered'
            }), 400
        
        # Generate unique teacher_id
        teacher_id = f"teacher_{datetime.now().strftime('%Y%m%d%H%M%S')}_{fingerprint_id}"
        
        # Register teacher in database (all three fields together)
        success = database.register_teacher(
            teacher_id=teacher_id,
            name=name,
            department=department,
            fingerprint_id=fingerprint_id
        )
        
        if success:
            # Clear the latest fingerprint_id after successful registration
            global _latest_fingerprint_id
            _latest_fingerprint_id = None
            
            return jsonify({
                'status': 'success',
                'message': f'Teacher {name} registered successfully',
                'teacher_id': teacher_id
            }), 201
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to register teacher in database'
            }), 500
    
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Registration failed: {str(e)}'
        }), 500


@app.route('/register-fingerprint', methods=['POST'])
def register_fingerprint():
    """
    ESP32 sends scanned fingerprint_id (REGISTER MODE only).
    
    ESP32 sends:
    {
        "fingerprint_id": 7
    }
    
    Backend:
    - Validates system is in REGISTER MODE
    - Stores fingerprint_id in memory (latest_fingerprint_id)
    - Rejects duplicate fingerprint_id (already registered)
    - Returns success with fingerprint_id
    """
    try:
        server_time_iso = get_server_time()
        
        # Check system mode
        current_mode = database.get_system_mode()
        
        if current_mode != 'register':
            return jsonify({
                'status': 'error',
                'message': f'System is in {current_mode} mode',
                'server_time': server_time_iso
            }), 403
        
        # Validate request format
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Request must be JSON',
                'server_time': server_time_iso
            }), 400
        
        data = request.get_json()
        fingerprint_id = data.get('fingerprint_id')
        
        # Validate fingerprint_id
        if fingerprint_id is None:
            return jsonify({
                'status': 'error',
                'message': 'Missing fingerprint_id in request',
                'server_time': server_time_iso
            }), 400
        
        try:
            fingerprint_id = int(fingerprint_id)
        except (ValueError, TypeError):
            return jsonify({
                'status': 'error',
                'message': 'Invalid fingerprint_id format (must be integer)',
                'server_time': server_time_iso
            }), 400
        
        # Check if fingerprint_id already exists (already registered)
        existing_teacher = database.get_teacher_by_fingerprint_id(fingerprint_id)
        if existing_teacher:
            return jsonify({
                'status': 'error',
                'message': f'Fingerprint ID {fingerprint_id} already registered',
                'server_time': server_time_iso
            }), 400
        
        # Store fingerprint_id in memory (waiting for registration form submission)
        global _latest_fingerprint_id
        _latest_fingerprint_id = {
            'fingerprint_id': fingerprint_id,
            'timestamp': get_server_time()
        }
        
        return jsonify({
            'status': 'success',
            'message': 'Fingerprint ID received and stored',
            'fingerprint_id': fingerprint_id,
            'server_time': server_time_iso
        }), 200
    
    except Exception as e:
        print(f"Fingerprint registration error: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to store fingerprint: {str(e)}',
            'server_time': get_server_time()
        }), 500


@app.route('/register-fingerprint/latest', methods=['GET'])
def get_latest_fingerprint():
    """
    Frontend polls this endpoint to check if fingerprint_id is available.
    
    Returns:
    {
        "status": "waiting" | "ready",
        "fingerprint_id": 7  // Only present when status == "ready"
    }
    """
    try:
        global _latest_fingerprint_id
        
        if _latest_fingerprint_id is None:
            return jsonify({
                'status': 'waiting',
                'message': 'No fingerprint scanned yet'
            }), 200
        else:
            return jsonify({
                'status': 'ready',
                'fingerprint_id': _latest_fingerprint_id['fingerprint_id'],
                'timestamp': _latest_fingerprint_id['timestamp']
            }), 200
    
    except Exception as e:
        print(f"Error getting latest fingerprint: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get fingerprint status: {str(e)}'
        }), 500


@app.route('/register-fingerprint/clear', methods=['POST'])
def clear_latest_fingerprint():
    """
    Clear the stored fingerprint_id (optional endpoint).
    Can be called after successful registration or to reset.
    """
    try:
        global _latest_fingerprint_id
        _latest_fingerprint_id = None
        
        return jsonify({
            'status': 'success',
            'message': 'Fingerprint ID cleared'
        }), 200
    
    except Exception as e:
        print(f"Error clearing fingerprint: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to clear fingerprint: {str(e)}'
        }), 500


@app.route('/attendance', methods=['POST'])
def attendance():
    """
    Main attendance endpoint - Fingerprint-only authentication.
    
    ESP32 sends: { "fingerprint_id": int }
    Backend automatically decides: check-in or check-out
    
    Attendance Logic (UNCHANGED):
    1. First scan of day → check_in
    2. Second scan (≥15 min after check-in) → check_out
    3. Early checkout (<15 min) → reject with remaining_minutes
    4. Duplicate scan (already checked out) → reject
    
    All timestamps use server time (ESP32 time ignored).
    
    Mode Enforcement:
    - Only works in ATTENDANCE MODE
    - Returns error if in REGISTER MODE
    """
    try:
        # Get current server time and date (authoritative)
        current_time = get_time_string()
        current_date = get_date_string()
        server_time_iso = get_server_time()
        
        # Check system mode
        current_mode = database.get_system_mode()
        
        if current_mode != 'attendance':
            return jsonify({
                'status': 'error',
                'message': f'System is in {current_mode} mode',
                'server_time': server_time_iso
            }), 403
        
        # Validate request format
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Request must be JSON with fingerprint_id',
                'server_time': server_time_iso
            }), 400
        
        data = request.get_json()
        fingerprint_id = data.get('fingerprint_id')
        
        if fingerprint_id is None:
            return jsonify({
                'status': 'error',
                'message': 'Missing fingerprint_id in request',
                'server_time': server_time_iso
            }), 400
        
        # Validate fingerprint_id type
        try:
            fingerprint_id = int(fingerprint_id)
        except (ValueError, TypeError):
            return jsonify({
                'status': 'error',
                'message': 'Invalid fingerprint_id format (must be integer)',
                'server_time': server_time_iso
            }), 400
        
        # Find teacher by fingerprint_id
        teacher = database.get_teacher_by_fingerprint_id(fingerprint_id)
        
        if not teacher:
            return jsonify({
                'status': 'error',
                'action': 'not_found',
                'message': f'Fingerprint ID {fingerprint_id} not registered',
                'teacher': None,
                'server_time': server_time_iso
            }), 404
        
        # Teacher identified - proceed with attendance logic
        teacher_id = teacher['teacher_id']
        teacher_name = teacher.get('name')
        department = teacher.get('department')
        
        # Get today's attendance record
        today_attendance = database.get_today_attendance(teacher_id, current_date)
        
        # ============================================
        # ATTENDANCE DECISION LOGIC (UNCHANGED)
        # ============================================
        
        # Case 1: No record exists → create check_in
        if not today_attendance:
            success = database.create_check_in(teacher_id, current_date, current_time)
            if success:
                return jsonify({
                    'status': 'success',
                    'action': 'check_in',
                    'message': 'Checked in successfully',
                    'teacher': {
                        'name': teacher_name,
                        'department': department
                    },
                    'check_in': current_time,
                    'server_time': server_time_iso
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'action': 'error',
                    'message': 'Failed to record check-in',
                    'teacher': {
                        'name': teacher_name,
                        'department': department
                    },
                    'server_time': server_time_iso
                }), 500
        
        # Case 2: check_in exists, check_out does NOT exist
        check_in = today_attendance.get('check_in')
        check_out = today_attendance.get('check_out')
        
        if check_in and not check_out:
            # Attempt check-out, but enforce 15-minute cooldown
            
            try:
                # Parse check-in time
                check_in_time = datetime.strptime(check_in, "%H:%M:%S").time()
                current_time_obj = datetime.strptime(current_time, "%H:%M:%S").time()
                
                # Create datetime objects for comparison
                check_in_dt = datetime.combine(datetime.today(), check_in_time)
                current_dt = datetime.combine(datetime.today(), current_time_obj)
                
                # Handle case where current time is next day (midnight crossover)
                if current_dt < check_in_dt:
                    current_dt += timedelta(days=1)
                
                # Calculate time difference in minutes
                time_diff = current_dt - check_in_dt
                minutes_passed = int(time_diff.total_seconds() / 60)
                
                # Enforce cooldown: reject if < 15 minutes
                if minutes_passed < COOLDOWN_MINUTES:
                    remaining_minutes = COOLDOWN_MINUTES - minutes_passed
                    return jsonify({
                        'status': 'error',
                        'action': 'cooldown',
                        'message': f'Please try again after {remaining_minutes} minute(s)',
                        'remaining_minutes': remaining_minutes,
                        'teacher': {
                            'name': teacher_name,
                            'department': department,
                            'check_in': check_in
                        },
                        'server_time': server_time_iso
                    }), 400
                
                # Valid check-out (≥15 minutes passed)
                working_hours = calculate_working_hours(check_in, current_time)
                success = database.create_check_out(
                    teacher_id, current_date, current_time, working_hours
                )
                
                if success:
                    return jsonify({
                        'status': 'success',
                        'action': 'check_out',
                        'message': 'Checked out successfully',
                        'teacher': {
                            'name': teacher_name,
                            'department': department
                        },
                        'check_in': check_in,
                        'check_out': current_time,
                        'working_hours': working_hours,
                        'server_time': server_time_iso
                    }), 200
                else:
                    return jsonify({
                        'status': 'error',
                        'action': 'error',
                        'message': 'Failed to record check-out',
                        'teacher': {
                            'name': teacher_name,
                            'department': department
                        },
                        'server_time': server_time_iso
                    }), 500
            
            except Exception as e:
                print(f"Error processing check-out: {e}")
                return jsonify({
                    'status': 'error',
                    'message': 'Error processing check-out time',
                    'server_time': server_time_iso
                }), 500
        
        # Case 3: Both check_in and check_out exist → reject (duplicate scan)
        elif check_in and check_out:
            return jsonify({
                'status': 'error',
                'action': 'completed',
                'message': 'Attendance already completed for today',
                'teacher': {
                    'name': teacher_name,
                    'department': department
                },
                'server_time': server_time_iso
            }), 400
        
        # Case 4: Unexpected state (should not happen)
        else:
            return jsonify({
                'status': 'error',
                'action': 'error',
                'message': 'Invalid attendance state',
                'teacher': {
                    'name': teacher_name,
                    'department': department
                },
                'server_time': server_time_iso
            }), 500
    
    except Exception as e:
        print(f"Attendance error: {e}")
        return jsonify({
            'status': 'error',
            'action': 'error',
            'message': f'Attendance processing failed: {str(e)}',
            'server_time': get_server_time()
        }), 500


@app.route('/teachers', methods=['GET'])
def get_teachers():
    """
    Get all teachers and their attendance records.
    Used by frontend to display attendance table.
    """
    try:
        teachers = database.get_all_teachers()
        # Flatten attendance into records for easier UI rendering
        records = []
        for teacher_id, data in teachers.items():
            name = data.get('name')
            department = data.get('department')
            attendance = data.get('attendance', {}) or {}
            if not attendance:
                records.append({
                    'teacher_id': teacher_id,
                    'name': name,
                    'department': department,
                    'date': None,
                    'check_in': None,
                    'check_out': None,
                    'working_hours': None
                })
            else:
                for date_str, rec in attendance.items():
                    records.append({
                        'teacher_id': teacher_id,
                        'name': name,
                        'department': department,
                        'date': date_str,
                        'check_in': rec.get('check_in'),
                        'check_out': rec.get('check_out'),
                        'working_hours': rec.get('working_hours')
                    })

        return jsonify({
            'status': 'success',
            'records': records,
            'server_time': get_server_time()
        }), 200
    except Exception as e:
        print(f"Error getting teachers: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get teachers: {str(e)}',
            'server_time': get_server_time()
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'server_time': get_server_time()
    }), 200


if __name__ == '__main__':
    from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
