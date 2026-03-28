# PaperTrail Backend

**Handwritten Government Form Digitisation System**

A production-ready FastAPI backend that processes handwritten or scanned government forms using OCR, computer vision, and intelligent field extraction.

## 🎯 Features

- **Multi-Template Support**: Birth Certificate and Residence Certificate forms
- **Advanced OCR**: Sarvam AI OCR integration for accurate text extraction
- **Image Preprocessing**: OpenCV-based image enhancement for better OCR results
- **Intelligent Classification**: Automatic form template detection
- **Field Extraction**: Structured data extraction with confidence scoring
- **Department Routing**: Automatic routing to correct department collections
- **Human Verification**: Support for manual correction of low-confidence fields
- **Audit Logging**: Complete traceability of all operations
- **RESTful API**: Clean, well-documented API endpoints

## 📋 Supported Templates

### Template 1: Birth Certificate Application
**Department**: Civil Records Department

**Extracted Fields**:
- Name
- Sex/Gender
- Date of Birth
- Place of Birth
- Mother's Name
- Father's Name
- Address at Birth
- Permanent Address
- Registration Number
- Date of Registration
- Date of Issue

### Template 2: Residence Certificate Application
**Department**: Citizen Services Department

**Extracted Fields**:
- Full Name
- Father/Husband Name
- Residential Address
- Mobile Number
- Purpose of Certificate
- Duration of Residence
- Date
- Place

## 🏗️ Project Structure

```
papertrail_backend/
├── main.py                      # FastAPI application entry point
├── config.py                    # Configuration management
├── database.py                  # MongoDB operations
├── preprocessing.py             # OpenCV image preprocessing
├── sarvam_ocr.py               # Sarvam OCR API integration
├── template_classifier.py       # Form template classification
├── field_extractor.py          # Structured field extraction
├── models.py                    # Pydantic request/response models
├── routes/
│   ├── __init__.py
│   ├── upload_routes.py        # Form upload endpoint
│   ├── verification_routes.py  # Verification endpoints
│   └── records_routes.py       # Records query endpoints
├── uploads/                     # Uploaded images storage
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
└── README.md                   # This file
```

## 🚀 Installation

### Prerequisites

- Python 3.8+
- MongoDB 4.4+
- Sarvam AI API Key

### Step 1: Clone Repository

```bash
cd papertrail_backend
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
SARVAM_API_KEY=your_actual_api_key
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=papertrail_db
UPLOAD_FOLDER=uploads/
```

### Step 5: Start MongoDB

```bash
# Using Docker (recommended)
docker run -d -p 27017:27017 --name papertrail-mongo mongo:latest

# Or start local MongoDB service
sudo systemctl start mongod  # Linux
brew services start mongodb-community  # macOS
```

### Step 6: Run Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Server will start at: `http://localhost:8000`

## 📡 API Endpoints

### Upload Form

```http
POST /api/upload-form
Content-Type: multipart/form-data

Body: file (image)
```

**Response**:
```json
{
  "success": true,
  "message": "Form processed successfully",
  "form_id": "507f1f77bcf86cd799439011",
  "form_type": "birth_certificate",
  "department": "civil_records_department",
  "extracted_data": {
    "name": "Rafikul Islam",
    "sex": "Male",
    "date_of_birth": "22-10-1993",
    ...
  },
  "confidence_scores": {
    "name": 0.92,
    "sex": 0.88,
    ...
  },
  "verification_flags": {
    "name": false,
    "registration_number": true
  }
}
```

### Verify Form

```http
POST /api/verify-form
Content-Type: application/json

{
  "form_id": "507f1f77bcf86cd799439011",
  "department": "civil_records_department",
  "corrected_data": {
    "registration_number": "238"
  }
}
```

### Get All Forms

```http
GET /api/forms?limit=100&skip=0&status=pending_verification
```

### Get Department Forms

```http
GET /api/departments/civil_records_department/forms
```

### Search Forms

```http
GET /api/search?query=Rafikul&field=name
```

### Get Statistics

```http
GET /api/stats
```

### Health Check

```http
GET /health
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SARVAM_API_KEY` | Sarvam OCR API key | Required |
| `MONGO_URI` | MongoDB connection URI | `mongodb://localhost:27017/` |
| `MONGO_DB_NAME` | Database name | `papertrail_db` |
| `UPLOAD_FOLDER` | Upload directory path | `uploads/` |

### MongoDB Collections

- **civil_records_department**: Birth certificate forms
- **citizen_services_department**: Residence certificate forms
- **audit_logs**: System audit trail

## 🧪 Testing

### Test with cURL

```bash
# Upload form
curl -X POST http://localhost:8000/api/upload-form \
  -F "file=@/path/to/birth_certificate.jpg"

# Health check
curl http://localhost:8000/health
```

### Interactive API Documentation

Visit `http://localhost:8000/docs` for Swagger UI

Visit `http://localhost:8000/redoc` for ReDoc

## 🔐 Security Best Practices

1. **Never commit `.env` file** - Contains sensitive credentials
2. **Use environment-specific configs** - Different keys for dev/prod
3. **Validate all inputs** - FastAPI Pydantic models handle this
4. **Set CORS properly** - Update `allow_origins` in production
5. **Use HTTPS** - Always in production
6. **Rotate API keys** - Regular key rotation policy

## 📊 Database Schema

### Birth Certificate Document

```javascript
{
  _id: ObjectId,
  department: "civil_records_department",
  form_type: "birth_certificate",
  image_path: "uploads/form_001.jpg",
  extracted_data: {
    name: String,
    sex: String,
    date_of_birth: String,
    place_of_birth: String,
    mother_name: String,
    father_name: String,
    address_at_birth: String,
    permanent_address: String,
    registration_number: String,
    date_of_registration: String,
    date_of_issue: String
  },
  confidence_scores: { field_name: Float },
  corrected_data: { field_name: String },
  status: "pending_verification" | "verified",
  created_at: ISODate,
  updated_at: ISODate
}
```

## 🎨 Image Preprocessing Pipeline

The OpenCV preprocessing pipeline includes:

1. **Grayscale Conversion**: Reduces complexity
2. **Contrast Enhancement**: CLAHE algorithm
3. **Noise Removal**: Gaussian blur
4. **Adaptive Thresholding**: Handles varying lighting
5. **Morphological Operations**: Enhances text clarity

## 🤖 OCR Processing Flow

1. Image upload and validation
2. OpenCV preprocessing
3. Sarvam OCR API call
4. Template classification
5. Field extraction with regex patterns
6. Confidence scoring
7. Department routing
8. MongoDB storage
9. Audit logging

## 🐛 Troubleshooting

### Common Issues

**Issue**: MongoDB connection failed
```bash
# Check if MongoDB is running
sudo systemctl status mongod

# Check connection
mongo --eval "db.runCommand({ ping: 1 })"
```

**Issue**: OCR API fails
- Verify `SARVAM_API_KEY` in `.env`
- Check API quota and rate limits
- Ensure image format is supported

**Issue**: Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📈 Performance Tips

1. **Use connection pooling** - Already implemented in `database.py`
2. **Cache OCR results** - Add Redis for frequent queries
3. **Optimize images** - Resize large images before processing
4. **Use async operations** - FastAPI handles this automatically
5. **Index MongoDB fields** - Add indexes for frequently queried fields

## 🔄 Future Enhancements

- [ ] Support for additional form templates
- [ ] Multi-language OCR support
- [ ] Batch processing endpoint
- [ ] Real-time websocket updates
- [ ] Advanced analytics dashboard
- [ ] ML-based field extraction
- [ ] Automated quality scoring

## 📝 License

MIT License - See LICENSE file for details

## 👥 Support

For issues and questions:
- Create an issue on GitHub
- Contact: support@papertrail.com

## 🙏 Acknowledgments

- **Sarvam AI** for OCR services
- **FastAPI** for the excellent framework
- **OpenCV** for image processing capabilities
- **MongoDB** for flexible data storage

---

**Built with ❤️ for digital governance**
