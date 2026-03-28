# PaperTrail Backend Testing Guide

## Quick Test Checklist

### 1. Installation Test

```bash
# Run setup script
./setup.sh

# Or manual installation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration Test

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add:
# SARVAM_API_KEY=your_actual_key
# MONGO_URI=mongodb://localhost:27017/
```

### 3. MongoDB Test

```bash
# Start MongoDB with Docker
docker run -d -p 27017:27017 --name papertrail-mongo mongo:latest

# Or use local MongoDB
sudo systemctl start mongod  # Linux
brew services start mongodb-community  # macOS

# Test connection
mongo --eval "db.runCommand({ ping: 1 })"
```

### 4. Server Start Test

```bash
# Activate virtual environment
source venv/bin/activate

# Start server
uvicorn main:app --reload

# Expected output:
# ✓ Configuration validated
# ✓ Database connection established
# ✓ Upload folder ready
# ✅ Server ready to accept requests
```

### 5. Health Check Test

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-...",
  "database_connected": true,
  "upload_folder_exists": true
}
```

### 6. API Documentation Test

Visit in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Manual API Testing

### Test 1: Upload Birth Certificate

```bash
# Prepare a test image (birth_cert.jpg)
curl -X POST http://localhost:8000/api/upload-form \
  -F "file=@birth_cert.jpg" \
  | jq

# Expected response:
{
  "success": true,
  "form_type": "birth_certificate",
  "department": "civil_records_department",
  "extracted_data": { ... },
  "confidence_scores": { ... }
}
```

### Test 2: Upload Residence Certificate

```bash
curl -X POST http://localhost:8000/api/upload-form \
  -F "file=@residence_cert.jpg" \
  | jq
```

### Test 3: Get All Forms

```bash
curl http://localhost:8000/api/forms | jq
```

### Test 4: Get Statistics

```bash
curl http://localhost:8000/api/stats | jq
```

### Test 5: Verify Form

```bash
curl -X POST http://localhost:8000/api/verify-form \
  -H "Content-Type: application/json" \
  -d '{
    "form_id": "YOUR_FORM_ID_HERE",
    "department": "civil_records_department",
    "corrected_data": {
      "name": "Corrected Name",
      "registration_number": "123"
    }
  }' | jq
```

### Test 6: Search Forms

```bash
curl "http://localhost:8000/api/search?query=Rafikul&limit=10" | jq
```

## Python Testing Script

Save as `test_api.py`:

```python
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    response = requests.get(f"{BASE_URL}/health")
    print("Health Check:", response.json())
    assert response.status_code == 200

def test_upload_form(image_path):
    with open(image_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{BASE_URL}/api/upload-form", files=files)
    print("Upload Response:", json.dumps(response.json(), indent=2))
    return response.json()

def test_get_forms():
    response = requests.get(f"{BASE_URL}/api/forms")
    print("Forms:", json.dumps(response.json(), indent=2))

def test_stats():
    response = requests.get(f"{BASE_URL}/api/stats")
    print("Statistics:", json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_health()
    # test_upload_form("path/to/test/image.jpg")
    test_get_forms()
    test_stats()
```

Run with:
```bash
python test_api.py
```

## MongoDB Verification

```bash
# Connect to MongoDB
mongo

# Use database
use papertrail_db

# Check collections
show collections

# Query birth certificates
db.civil_records_department.find().pretty()

# Query residence certificates
db.citizen_services_department.find().pretty()

# Check audit logs
db.audit_logs.find().pretty()
```

## Common Issues & Solutions

### Issue: ImportError for OpenCV

```bash
pip install opencv-python-headless
```

### Issue: MongoDB connection refused

```bash
# Check if MongoDB is running
sudo systemctl status mongod

# Start MongoDB
docker run -d -p 27017:27017 mongo
```

### Issue: SARVAM_API_KEY not found

```bash
# Make sure .env file exists and has the key
cat .env | grep SARVAM_API_KEY
```

### Issue: Permission denied on uploads/

```bash
chmod 755 uploads/
```

## Performance Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils  # Ubuntu
brew install httpd  # macOS

# Test concurrent uploads
ab -n 100 -c 10 -p image.jpg -T "multipart/form-data" \
  http://localhost:8000/api/upload-form
```

## Load Testing with Locust

Create `locustfile.py`:

```python
from locust import HttpUser, task, between

class PaperTrailUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def health_check(self):
        self.client.get("/health")
    
    @task(3)
    def get_forms(self):
        self.client.get("/api/forms?limit=10")
    
    @task
    def get_stats(self):
        self.client.get("/api/stats")
```

Run:
```bash
pip install locust
locust -f locustfile.py
```

## Success Criteria

- ✅ All dependencies install without errors
- ✅ Server starts successfully
- ✅ Health check returns "healthy"
- ✅ Can upload birth certificate image
- ✅ Can upload residence certificate image
- ✅ Form classification works correctly
- ✅ Fields are extracted with confidence scores
- ✅ Data saved to correct MongoDB collection
- ✅ Can retrieve forms from database
- ✅ Can verify/correct form data
- ✅ Audit logs created for all actions
- ✅ API documentation accessible

## Next Steps After Testing

1. Add your actual Sarvam API key
2. Test with real form images
3. Tune regex patterns in field_extractor.py if needed
4. Adjust confidence thresholds in config.py
5. Set up production MongoDB instance
6. Configure proper CORS origins
7. Add authentication/authorization
8. Set up monitoring and logging
