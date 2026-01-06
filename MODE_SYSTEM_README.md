# Mode-Based Biometric Attendance System

## Overview

The backend now supports **mode-based operation** with two distinct modes:
- **REGISTER MODE**: For enrolling new teachers
- **ATTENDANCE MODE**: For recording daily attendance

Only one mode can be active at a time, controlled by the admin through the web interface.

---

## System Architecture

### Mode Management
- Mode is stored in Firestore: `system/mode` document
- Default mode: `attendance` (if not set)
- Mode is queryable by ESP32 via `GET /mode`

### Registration Flow (Two-Step Process)

#### Step 1: Admin Submits Name & Department
- Admin fills form on web page (only name and department)
- Backend saves as **pending registration** in Firestore
- Returns success message: "Please scan fingerprint on device"

#### Step 2: ESP32 Sends Fingerprint
- ESP32 enrolls fingerprint on AS608 module
- ESP32 sends to `POST /register-fingerprint`:
  ```json
  {
    "fingerprint_id": 5,
    "name": "John Doe",      // Optional: helps match pending registration
    "department": "CSE"      // Optional: helps match pending registration
  }
  ```
- Backend matches fingerprint with latest pending registration
- Completes registration and deletes pending record

---

## API Endpoints

### Mode Control

#### `GET /mode`
Get current system mode.

**Response:**
```json
{
  "status": "success",
  "mode": "register" | "attendance",
  "server_time": "2024-01-15T10:30:00"
}
```

#### `POST /mode`
Set system mode (admin only).

**Request:**
```json
{
  "mode": "register" | "attendance"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "System mode set to register",
  "mode": "register",
  "server_time": "2024-01-15T10:30:00"
}
```

---

### Registration

#### `GET /register` or `GET /`
Admin page with mode controls and registration form.

#### `POST /register`
Register teacher (Step 1: name and department only).

**Mode Requirement:** Must be in `register` mode.

**Request (form-data):**
- `name`: Teacher's name
- `department`: Teacher's department

**Response:**
```json
{
  "status": "success",
  "message": "Teacher John Doe added. Please scan fingerprint on device.",
  "pending_id": "abc123..."
}
```

**Error (wrong mode):**
```json
{
  "status": "error",
  "message": "System is in attendance mode. Switch to register mode to register teachers."
}
```

#### `POST /register-fingerprint`
Complete registration (Step 2: ESP32 sends fingerprint).

**Mode Requirement:** Must be in `register` mode.

**Request (JSON):**
```json
{
  "fingerprint_id": 5,
  "name": "John Doe",      // Optional
  "department": "CSE"       // Optional
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Teacher John Doe registered successfully",
  "teacher_id": "teacher_20240115103000_5",
  "server_time": "2024-01-15T10:30:00"
}
```

**Error (duplicate fingerprint):**
```json
{
  "status": "error",
  "message": "Fingerprint ID 5 already registered",
  "server_time": "2024-01-15T10:30:00"
}
```

**Error (no pending registration):**
```json
{
  "status": "error",
  "message": "No pending registration found. Please register teacher first.",
  "server_time": "2024-01-15T10:30:00"
}
```

---

### Attendance

#### `POST /attendance`
Record check-in/check-out (unchanged logic).

**Mode Requirement:** Must be in `attendance` mode.

**Request (JSON):**
```json
{
  "fingerprint_id": 5
}
```

**Response (check-in):**
```json
{
  "status": "success",
  "message": "Check-in recorded for John Doe",
  "server_time": "2024-01-15T10:30:00"
}
```

**Response (check-out):**
```json
{
  "status": "success",
  "message": "Check-out recorded for John Doe. Worked: 8 hours 30 minutes",
  "server_time": "2024-01-15T18:30:00"
}
```

**Error (wrong mode):**
```json
{
  "status": "error",
  "message": "System is in register mode",
  "server_time": "2024-01-15T10:30:00"
}
```

---

## Mode Enforcement Rules

### REGISTER MODE
- ✅ `POST /register` - Works
- ✅ `POST /register-fingerprint` - Works
- ❌ `POST /attendance` - Returns 403 error

### ATTENDANCE MODE
- ❌ `POST /register` - Returns 403 error
- ❌ `POST /register-fingerprint` - Returns 403 error
- ✅ `POST /attendance` - Works

---

## Firestore Schema

### System Mode
```
system/
  mode/
    mode: "register" | "attendance"
    updated_at: ISO8601 timestamp
```

### Pending Registrations
```
pending_registrations/
  {pending_id}/
    name: string
    department: string
    status: "pending"
    created_at: ISO8601 timestamp
```

### Teachers (unchanged)
```
teachers/
  {teacher_id}/
    name: string
    department: string
    fingerprint_id: number
    attendance: {
      "YYYY-MM-DD": {
        check_in: "HH:MM:SS",
        check_out: "HH:MM:SS",
        working_hours: "X hours Y minutes"
      }
    }
```

---

## Admin Interface Features

1. **Mode Control Buttons**
   - "Register Mode" button
   - "Attendance Mode" button
   - Only one active at a time
   - Visual indicator of current mode

2. **Registration Form**
   - Only shows name and department fields
   - Fingerprint ID field removed
   - Form disabled when not in register mode
   - Instructions displayed for workflow

3. **Real-time Mode Display**
   - Shows current mode status
   - Updates automatically after mode change

---

## ESP32 Integration

### Query Current Mode
```cpp
// ESP32 code example
HTTPClient http;
http.begin("http://your-backend.com/mode");
int httpCode = http.GET();

if (httpCode == 200) {
  DynamicJsonDocument doc(1024);
  deserializeJson(doc, http.getString());
  String mode = doc["mode"]; // "register" or "attendance"
  
  if (mode == "register") {
    // Handle registration flow
  } else {
    // Handle attendance flow
  }
}
```

### Registration Flow (ESP32)
1. Check mode: `GET /mode`
2. If `register` mode:
   - Wait for admin to submit name/dept
   - Enroll fingerprint on AS608
   - Send to `POST /register-fingerprint`:
     ```json
     {
       "fingerprint_id": enrolled_id,
       "name": "John Doe",      // Optional
       "department": "CSE"       // Optional
     }
     ```

### Attendance Flow (ESP32)
1. Check mode: `GET /mode`
2. If `attendance` mode:
   - Scan fingerprint on AS608
   - Send to `POST /attendance`:
     ```json
     {
       "fingerprint_id": scanned_id
     }
     ```

---

## Key Benefits

1. **Separation of Concerns**: Registration and attendance are clearly separated
2. **Security**: Registration endpoints disabled during attendance mode
3. **Workflow Control**: Admin has full control over system behavior
4. **ESP32 Flexibility**: Hardware can query mode and adapt behavior
5. **Backward Compatible**: Attendance logic unchanged, existing ESP32 code works

---

## Testing

1. **Test Mode Switching**
   - Switch to register mode
   - Verify registration form is enabled
   - Switch to attendance mode
   - Verify registration form is disabled

2. **Test Registration Flow**
   - Set to register mode
   - Submit name and department
   - Simulate ESP32 sending fingerprint_id
   - Verify teacher is registered

3. **Test Mode Enforcement**
   - Try `/attendance` in register mode → should fail
   - Try `/register` in attendance mode → should fail

4. **Test Attendance Flow**
   - Set to attendance mode
   - Send fingerprint_id to `/attendance`
   - Verify check-in/check-out logic works

---

## Notes

- **Attendance logic is UNCHANGED**: All existing rules (15-min cooldown, max 2 events/day, etc.) remain intact
- **Server time authority**: All timestamps still use server time
- **OLED-friendly responses**: All JSON responses remain concise for small displays
- **Firebase schema**: Backward compatible, only adds new collections for mode and pending registrations
