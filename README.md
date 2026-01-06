# Fingerprint Attendance System - Backend

A production-ready Flask-based backend for a university teacher attendance system using IoT hardware (ESP32, AS608 fingerprint module) and cloud infrastructure.

## Features

- **Fingerprint-Only Authentication**: Fingerprint matching done locally on AS608 hardware
- **Backend-Controlled Logic**: All attendance decisions made server-side
- **Firebase Integration**: Persistent storage using Firestore (Cloud Firestore)
- **Smart Attendance Logic**: Automatic check-in/check-out with 15-minute cooldown
- **OLED-Friendly Responses**: Short, readable JSON messages for hardware display
- **Production-Ready**: Pure Python dependencies, no native compilation required

## Architecture

- **Hardware (Edge)**: ESP32, AS608 fingerprint module, SSD1306 OLED
- **Backend (Cloud)**: Flask server with Firestore (Cloud Firestore)
- **Authentication**: Fingerprint ID mapping (matching done on AS608 hardware)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: All dependencies are pure Python - no CMake, Visual Studio, or native compilation needed!

### 2. Configure Environment

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```
   Or on Windows:
   ```powershell
   copy .env.example .env
   ```

2. Open `.env` and replace the placeholders with your actual Firebase credentials (see step 3 below for where to get them).

   The `.env.example` file contains all the required fields with clear placeholders and instructions.

### 3. Firebase Setup

**Why Service Account Keys?** This backend uses **Firebase Admin SDK** (not Client SDK). Admin SDK requires a private service account key to bypass Security Rules and perform server-side operations.

1. Create a Firebase project at https://console.firebase.google.com
2. Enable Firestore Database:
   - Go to **Firestore Database** in Firebase Console
   - Click **Create Database**
   - Choose **Production mode** (or Test mode for development)
   - Select a location for your database
3. Go to Project Settings → Service Accounts
4. Click "Generate New Private Key" to download the service account JSON file
5. Open the downloaded JSON file and copy these fields to your `.env` file:
   - `project_id` → `FIREBASE_PROJECT_ID`
   - `private_key_id` → `FIREBASE_PRIVATE_KEY_ID`
   - `private_key` → `FIREBASE_PRIVATE_KEY` 
     - **Important**: The private key in JSON is multi-line, but in `.env` it must be on ONE line
     - Copy the entire `private_key` value from JSON (it already has `\n` characters)
     - Keep all `\n` characters exactly as they appear in JSON
     - Wrap the entire value in double quotes: `"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"`
   - `client_email` → `FIREBASE_CLIENT_EMAIL`
   - `client_id` → `FIREBASE_CLIENT_ID`
   - `auth_uri` → `FIREBASE_AUTH_URI`
   - `token_uri` → `FIREBASE_TOKEN_URI`
   - `auth_provider_x509_cert_url` → `FIREBASE_AUTH_PROVIDER_X509_CERT_URL`
   - `client_x509_cert_url` → `FIREBASE_CLIENT_X509_CERT_URL`
6. **Note**: Firestore doesn't require a database URL - it uses the `project_id` from your service account credentials automatically

**⚠️ CRITICAL SECURITY WARNING**: 
- **NEVER commit** your `.env` file or Firebase JSON files to GitHub
- If exposed, attackers can access and delete your entire database
- Your `.gitignore` is already configured to protect these files
- Never commit credentials to version control

### 4. Run the Server

```bash
python app.py
```

The server will start on `http://localhost:8000` (or configured port).

## API Endpoints

### `GET /`
Home page with teacher registration form.

### `POST /register`
Register a new teacher.

**Form Data:**
- `name` (required): Teacher's name
- `department` (required): Department name
- `fingerprint_id` (required): Fingerprint ID from AS608 module

**Response:**
```json
{
  "status": "success",
  "message": "Teacher registered successfully",
  "teacher_id": "teacher_20240101120000_123"
}
```

### `POST /attendance`
Record attendance (check-in or check-out).

**Request (JSON):**
```json
{
  "fingerprint_id": 123
}
```

**Response (Success - Check-in):**
```json
{
  "status": "success",
  "message": "Check-in recorded for John Doe",
  "server_time": "2024-01-01T12:00:00"
}
```

**Response (Success - Check-out):**
```json
{
  "status": "success",
  "message": "Check-out recorded for John Doe. Worked: 8 hours 30 minutes",
  "server_time": "2024-01-01T20:30:00"
}
```

**Response (Error - Cooldown):**
```json
{
  "status": "error",
  "message": "Check-out too early. Wait 12 more minute(s)",
  "remaining_minutes": 12,
  "server_time": "2024-01-01T12:05:00"
}
```

**Response (Error - Not Registered):**
```json
{
  "status": "error",
  "message": "Fingerprint ID 123 not registered",
  "server_time": "2024-01-01T12:00:00"
}
```

### `GET /health`
Health check endpoint.

## Attendance Logic

The backend automatically decides check-in or check-out based on the current state:

1. **First scan of the day**: Creates `check_in` record
2. **Second scan (≥15 minutes after check-in)**: Creates `check_out` record with working hours
3. **Second scan (<15 minutes after check-in)**: Rejected with remaining cooldown time
4. **Third scan**: Rejected (attendance already completed)

**Important Rules:**
- All timestamps use **server time** (ESP32 time is ignored)
- Maximum **2 valid events per day** per teacher
- **15-minute cooldown** enforced between check-in and check-out
- Date format: `YYYY-MM-DD`
- Time format: `HH:MM:SS`

## Data Model

### Firestore Structure

```
Collection: teachers
  Document: teacher_id
    Fields:
      name: string
      department: string
      fingerprint_id: number
      attendance: {
        YYYY-MM-DD: {
          check_in: HH:MM:SS
          check_out: HH:MM:SS
          working_hours: "X hours Y minutes"
        }
      }
```

## How It Works

1. **Enrollment**: Admin registers teacher with name, department, and fingerprint_id (assigned by AS608 during hardware enrollment)

2. **Authentication**: 
   - ESP32 captures fingerprint on AS608 module
   - AS608 performs local matching and returns fingerprint_id
   - ESP32 sends `{ "fingerprint_id": int }` to backend

3. **Attendance Recording**:
   - Backend maps fingerprint_id → teacher
   - Backend checks today's attendance record
   - Backend automatically decides: check-in or check-out
   - Backend enforces 15-minute cooldown
   - Backend calculates working hours at check-out

## Testing

### Quick Setup Check

First, verify your configuration:

```bash
python check_setup.py
```

This will check:
- ✅ `.env` file exists
- ✅ All required environment variables are set
- ✅ Firebase connection works

### Run Full Test Suite

**Option 1: Automatic (Recommended)**
```bash
python run_tests.py
```
This automatically starts the server, runs all tests, and stops the server.

**Option 2: Manual**
```bash
# Terminal 1: Start server
python app.py

# Terminal 2: Run tests
python test_backend.py
```

**Test Coverage**:
- Health check endpoint
- Registration validation
- Attendance flow (check-in, cooldown, check-out)
- Error handling
- Response format compliance
- Server time authority

## Deployment

This backend is production-ready and can be deployed to any Python hosting platform.

**✅ No JSON files needed!** Your code already uses environment variables, which is the secure production standard.

### Quick Deployment Steps:

1. **Set environment variables** on your hosting platform (Heroku, Railway, Render, etc.)
2. **Never upload JSON files** - use environment variables instead
3. **Deploy your code** - credentials are set via platform dashboard

### Detailed Guide:

See `PRODUCTION_DEPLOYMENT.md` for:
- Step-by-step deployment instructions for each platform
- How to securely store credentials in production
- Security best practices
- Troubleshooting guide

**No special build tools required** - just `pip install -r requirements.txt`!

## Requirements Compliance

✅ Fingerprint-only authentication (face recognition removed)  
✅ Backend-controlled logic (ESP32 never decides attendance)  
✅ Server time authority (all timestamps from backend)  
✅ 15-minute cooldown enforcement  
✅ Working hours calculation  
✅ OLED-friendly error messages  
✅ Pure Python dependencies (no native compilation)  
✅ Production-deployable  

## License

Academic project / Thesis work.
