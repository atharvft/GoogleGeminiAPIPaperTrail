# PaperTrail Backend - Quick Start Guide

## ⚡ 60-Second Setup

```bash
# 1. Navigate to project
cd papertrail_backend

# 2. Run setup script
./setup.sh

# 3. Add your API key
echo "SARVAM_API_KEY=your_key_here" >> .env

# 4. Start MongoDB
docker run -d -p 27017:27017 --name papertrail-mongo mongo

# 5. Activate environment and run
source venv/bin/activate
uvicorn main:app --reload
```

🎉 **Done!** API running at http://localhost:8000

## 📚 Essential URLs

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Quick Test

```bash
# Test health
curl http://localhost:8000/health

# Upload a form (replace with your image)
curl -X POST http://localhost:8000/api/upload-form \
  -F "file=@your_form.jpg"

# Get statistics
curl http://localhost:8000/api/stats
```

## 📁 Project Files

```
papertrail_backend/
├── main.py                 # FastAPI app entry point
├── config.py              # Configuration
├── database.py            # MongoDB operations
├── preprocessing.py       # OpenCV processing
├── sarvam_ocr.py         # OCR integration
├── template_classifier.py # Form detection
├── field_extractor.py    # Field extraction
├── models.py             # Pydantic models
├── routes/
│   ├── upload_routes.py     # Upload endpoint
│   ├── verification_routes.py # Verification
│   └── records_routes.py    # Records & search
├── requirements.txt      # Dependencies
├── .env.example         # Config template
└── README.md           # Full documentation
```

## 🔑 Key Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/upload-form` | Upload & process form |
| POST | `/api/verify-form` | Submit corrections |
| GET | `/api/forms` | List all forms |
| GET | `/api/stats` | Get statistics |
| GET | `/health` | Health check |

## 🎯 Supported Templates

1. **Birth Certificate** → civil_records_department
2. **Residence Certificate** → citizen_services_department

## ⚙️ Environment Variables

```env
SARVAM_API_KEY=your_sarvam_api_key
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=papertrail_db
UPLOAD_FOLDER=uploads/
```

## �� Troubleshooting

**MongoDB not connecting?**
```bash
docker ps  # Check if MongoDB is running
docker start papertrail-mongo
```

**Missing dependencies?**
```bash
pip install -r requirements.txt
```

**Can't find .env?**
```bash
cp .env.example .env
# Edit .env and add your API key
```

## 📖 Full Documentation

- **README.md** - Complete setup guide
- **TESTING.md** - Testing procedures
- **PROJECT_SUMMARY.md** - Project overview

## 🚀 Next Steps

1. ✅ Test with sample images
2. ✅ Review extracted data
3. ✅ Test verification flow
4. ✅ Check MongoDB collections
5. ✅ Deploy to production

---

**Need Help?** Check README.md or TESTING.md
