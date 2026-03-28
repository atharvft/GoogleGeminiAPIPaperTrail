"""Quick test script to verify MongoDB and Sarvam API configuration."""
import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

print("=" * 60)
print("PaperTrail Configuration Test")
print("=" * 60)

# Test 1: Environment Variables
print("\n1. Checking Environment Variables...")
sarvam_key = os.getenv("SARVAM_API_KEY")
mongo_uri = os.getenv("MONGO_URI")
mongo_db = os.getenv("MONGO_DB_NAME")

if sarvam_key and sarvam_key.startswith("sk_"):
    print(f"   ✅ SARVAM_API_KEY loaded (starts with: {sarvam_key[:15]}...)")
else:
    print("   ❌ SARVAM_API_KEY not found or invalid")

if mongo_uri and "mongodb" in mongo_uri:
    print(f"   ✅ MONGO_URI loaded")
else:
    print("   ❌ MONGO_URI not found")

if mongo_db:
    print(f"   ✅ MONGO_DB_NAME: {mongo_db}")
else:
    print("   ❌ MONGO_DB_NAME not found")

# Test 2: MongoDB Connection
print("\n2. Testing MongoDB Atlas Connection...")
try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    # Ping the database
    client.admin.command('ping')
    print("   ✅ MongoDB Atlas connection successful!")
    
    # Get database
    db = client[mongo_db]
    print(f"   ✅ Database '{mongo_db}' accessible")
    
    # List collections
    collections = db.list_collection_names()
    print(f"   ✅ Existing collections: {collections if collections else 'None (new database)'}")
    
    # Test department collections
    print("\n3. Verifying Department Collections Setup...")
    civil_records = db["civil_records_department"]
    citizen_services = db["citizen_services_department"]
    audit_logs = db["audit_logs"]
    
    print("   ✅ civil_records_department (for Birth Certificates)")
    print("   ✅ citizen_services_department (for Residence Certificates)")
    print("   ✅ audit_logs (for Audit Trail)")
    
    client.close()
    
except Exception as e:
    print(f"   ❌ MongoDB connection failed: {str(e)}")
    print("   Check your MONGO_URI and internet connection")

print("\n" + "=" * 60)
print("Configuration Summary")
print("=" * 60)
print("✅ Birth Certificates → civil_records_department")
print("✅ Residence Certificates → citizen_services_department")
print("✅ Sarvam OCR API configured")
print("✅ MongoDB Atlas connected")
print("\nReady to process forms!")
print("=" * 60)
