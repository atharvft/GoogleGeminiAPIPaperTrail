# PaperTrail - Clerk Workflow Guide

## 📸 For Government Office Clerks

This guide explains how clerks will use PaperTrail to digitize handwritten government forms.

---

## 🎯 What This System Does

- ✅ Automatically reads handwritten forms
- ✅ Extracts all field data (names, dates, addresses, etc.)
- ✅ Detects which type of form it is
- ✅ Saves data to the correct department
- ✅ Flags uncertain fields for you to verify
- ✅ Creates complete audit trail

---

## 📋 Supported Forms

### 1. Birth Certificate (West Bengal)
- Government of West Bengal
- Department of Health & Family Welfare
- Example: Rafikul Islam's birth certificate

### 2. Residence Certificate (Maharashtra)
- Government of Maharashtra State
- Application for Residence Certificate
- 6 numbered fields + signature section

---

## 🔄 Step-by-Step Workflow

### Step 1: Take Photo of Handwritten Form

**Tips for best results:**
- 📸 Good lighting (natural light preferred)
- 📐 Flat form (remove any folds)
- 🎯 Straight angle (not tilted)
- 🔍 Clear focus (no blur)
- 📏 All text visible (no cutoff edges)

**Accepted formats:** JPG, PNG, JPEG

---

### Step 2: Upload to System

**Via Web Interface:**
1. Open PaperTrail web app
2. Click "Upload Form"
3. Select photo from your device
4. Click "Process"

**Via API (for developers):**
```bash
curl -X POST http://localhost:8000/api/upload-form \
  -F "file=@form_photo.jpg"
```

---

### Step 3: System Auto-Processing

**What happens automatically:**

1. ✅ Image enhancement (OpenCV)
   - Removes shadows
   - Improves contrast
   - Cleans noise

2. ✅ Text extraction (Sarvam OCR)
   - Reads handwriting
   - Handles Bengali text
   - Provides confidence scores

3. ✅ Form detection
   - Identifies: Birth or Residence Certificate
   - Routes to correct department

4. ✅ Field extraction
   - Pulls out all data fields
   - Scores each field's confidence
   - Flags uncertain fields

⏱️ **Processing time:** 5-10 seconds

---

### Step 4: Review Extracted Data

**You will see:**

✅ **Green checkmarks** = High confidence (≥75%) - Likely correct
⚠️ **Yellow flags** = Low confidence (<75%) - Needs verification

**Example Birth Certificate:**
```
✅ Name: Rafikul Islam (Confidence: 92%)
✅ Sex: Male (Confidence: 88%)
⚠️ Registration No: 92B (Confidence: 62%) ← VERIFY THIS
✅ Date of Birth: 22-10-1993 (Confidence: 85%)
```

---

### Step 5: Verify & Correct

**For flagged fields:**

1. Compare extracted text with original form
2. If incorrect: Type the correct value
3. If correct: Click "Confirm"

**Example corrections:**
- Extracted: `92B` → Correct to: `928`
- Extracted: `Satti Begam` → Correct to: `Sathi Begam`

---

### Step 6: Submit

Click **"Submit"** button

**What happens:**
- ✅ Original extraction saved
- ✅ Your corrections saved separately
- ✅ Routed to correct department collection
- ✅ Audit log created
- ✅ Form marked as "Verified"

---

## 📊 Field Details by Form Type

### Birth Certificate Fields (12 total)

| # | Field | Example |
|---|-------|---------|
| 1 | Name | Rafikul Islam |
| 2 | Sex | Male |
| 3 | Date of Birth | 22-10-1993 |
| 4 | Place of Birth | Paikpara |
| 5 | Mother's Name | Sathi Begam |
| 6 | Father's Name | Samsul Haque |
| 7 | Address at Birth | Vill - Chakbarbaria po |
| 8 | Permanent Address | Noapara, ps-Duttapukur |
| 9 | Registration Number | 928 |
| 10 | Date of Registration | 17-08-2002 |
| 11 | Remarks | Name Correction |
| 12 | Date of Issue | 18/07/22 |

### Residence Certificate Fields (8 total)

| # | Field | Example |
|---|-------|---------|
| 1 | Full Name | Rajesh Kumar Sharma |
| 2 | Father/Husband Name | Mohan Sharma |
| 3 | Residential Address | 123 MG Road, Pune 411001 |
| 4 | Mobile Number | 9876543210 |
| 5 | Purpose of Certificate | Educational |
| 6 | Duration of Residence | 10 years |
| 7 | Date | 28-03-2024 |
| 8 | Place | Pune |

---

## 🔍 Common OCR Challenges

Be extra careful with these:

### Numbers that look like letters:
- `0` vs `O` (zero vs letter O)
- `1` vs `I` (one vs letter I)
- `5` vs `S` (five vs letter S)
- `8` vs `B` (eight vs letter B)

### Handwriting variations:
- Cursive writing may merge letters
- Similar-looking letters: `a/o`, `c/e`, `u/v`
- Unclear dates: verify day/month/year order

### Multi-line fields:
- Addresses often span 2-3 lines
- Check all lines are captured
- Look for missing street/city/pin code

---

## ✅ Quality Checklist

Before submitting, verify:

- [ ] All flagged fields reviewed
- [ ] Names spelled correctly
- [ ] Dates in correct format (DD-MM-YYYY)
- [ ] Registration numbers complete
- [ ] Addresses include all details
- [ ] Mobile numbers have 10 digits
- [ ] Form type correctly identified

---

## 📈 Confidence Scoring

**How it works:**

| Score | Meaning | Your Action |
|-------|---------|-------------|
| 90-100% | Excellent | Just verify quickly |
| 75-89% | Good | Double-check |
| 50-74% | Uncertain | Carefully verify |
| Below 50% | Poor | Re-check original form |

**System automatically flags anything below 75%**

---

## 🚨 Error Handling

### If upload fails:
1. Check file format (JPG/PNG only)
2. Check file size (max 10MB)
3. Ensure form is government template
4. Try re-taking photo with better lighting

### If wrong form type detected:
1. Check if correct government form
2. Photo should show form header clearly
3. Contact IT support if persistent

### If too many fields have low confidence:
1. Retake photo with better lighting
2. Ensure form is flat (no folds)
3. Use higher resolution camera
4. Manually enter data if necessary

---

## 💾 Where Data Goes

### Birth Certificates
- **Department**: Civil Records Department
- **Database Collection**: `civil_records_department`
- **Status**: Pending → Verified

### Residence Certificates
- **Department**: Citizen Services Department
- **Database Collection**: `citizen_services_department`
- **Status**: Pending → Verified

### Audit Trail
- Every action logged in `audit_logs`
- Includes: timestamp, clerk ID, actions
- Cannot be deleted (permanent record)

---

## 📊 Clerk Dashboard Features

**Available views:**

1. **Pending Verification** - Forms needing review
2. **Recently Processed** - Last 50 forms
3. **My Statistics** - Your daily/monthly counts
4. **Search** - Find forms by name, number, date

**Quick Actions:**

- View form image
- See confidence scores
- Compare extracted vs corrected
- Export to PDF
- Print certificate

---

## ⏱️ Expected Time Savings

**Traditional manual entry:**
- Birth Certificate: ~5 minutes
- Residence Certificate: ~3 minutes

**With PaperTrail:**
- Upload: 10 seconds
- Auto-processing: 5 seconds
- Verification: 30-60 seconds
- **Total: ~1 minute** ⚡

**70-80% faster than manual entry!**

---

## 🎓 Training Tips

### For new clerks:

1. **Start with clear forms** - Practice with neat handwriting first
2. **Compare results** - Match extracted text with original
3. **Learn patterns** - Notice which fields often need correction
4. **Use examples** - Refer to sample forms in system
5. **Ask questions** - Contact supervisor for unclear cases

### Common mistakes to avoid:

❌ Skipping verification of flagged fields  
❌ Not checking date formats  
❌ Ignoring low confidence warnings  
❌ Submitting without final review  
❌ Using poor quality photos  

---

## 📞 Support

**Technical Issues:**
- IT Helpdesk: [contact info]
- Email: support@papertrail.gov.in

**Process Questions:**
- Department Supervisor
- User Manual: README.md

**System Status:**
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

---

## 🎯 Success Metrics

**Your department tracks:**

- ✅ Forms processed per day
- ✅ Verification accuracy rate
- ✅ Average processing time
- ✅ Low-confidence field rate
- ✅ Correction frequency

**Department goals:**

- 95% accuracy on first extraction
- <2 minutes average processing
- 100% of flagged fields verified
- Zero unverified forms in system

---

## 🔐 Security & Privacy

**Important reminders:**

- 🔒 Never share login credentials
- 📸 Delete form photos from phone after upload
- 🚫 Don't photograph sensitive personal data
- ✅ Log out after each session
- 📋 Follow data protection guidelines

---

**Last Updated:** March 28, 2024  
**Version:** 1.0  
**For:** Government Office Clerks
