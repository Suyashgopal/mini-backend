# Validation Troubleshooting Guide

## ✅ Backend Status: WORKING

The Groq validation endpoint is **working perfectly**. Tests show:
- Response time: ~2.7 seconds
- Status: 200 OK
- All fields extracted correctly

## 🔍 Issue Location: Frontend

The "Running Validation... Checking against encrypted hash system" message is coming from your **frontend code**, not the backend.

## Backend Endpoints

### 1. OCR Extraction
**Endpoint:** `POST /api/ocr/image`
- Extracts text from image
- Returns pharmaceutical fields (pattern-based)
- Response time: 2-5 seconds

### 2. Groq Validation
**Endpoint:** `POST /api/validation/validate-text`
- Validates extracted text with AI
- Returns detailed pharmaceutical analysis
- Response time: 2-4 seconds

## Testing

### Test Backend Directly

```bash
# Test validation endpoint
python test_validation_endpoint.py
```

### Test Frontend Integration

Open `test_validation_frontend.html` in your browser:
1. Open the file in Chrome/Firefox
2. Click "Validate Label"
3. See results in 2-3 seconds

## Common Frontend Issues

### Issue 1: Wrong Endpoint URL

**Problem:** Frontend calling wrong URL

**Fix:**
```javascript
// ❌ Wrong
fetch('http://localhost:5000/api/verify/...')

// ✅ Correct
fetch('http://localhost:5000/api/validation/validate-text')
```

### Issue 2: Missing Request Body

**Problem:** Not sending the text field

**Fix:**
```javascript
// ❌ Wrong
fetch(url, {
  method: 'POST',
  body: JSON.stringify({ content: text })  // Wrong field name
})

// ✅ Correct
fetch(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: text })  // Correct field name
})
```

### Issue 3: Not Handling Response

**Problem:** Frontend not processing the response

**Fix:**
```javascript
const response = await fetch(url, options);

// ❌ Wrong - not checking status
const data = await response.json();

// ✅ Correct - check status first
if (!response.ok) {
  throw new Error(`HTTP ${response.status}`);
}
const data = await response.json();
```

### Issue 4: Timeout Too Short

**Problem:** Frontend timeout shorter than API response time

**Fix:**
```javascript
// ❌ Wrong - 1 second timeout
const controller = new AbortController();
setTimeout(() => controller.abort(), 1000);

// ✅ Correct - 30 second timeout
const controller = new AbortController();
setTimeout(() => controller.abort(), 30000);

fetch(url, { signal: controller.signal })
```

### Issue 5: CORS Error

**Problem:** Browser blocking the request

**Check Console:** Look for CORS errors in browser console (F12)

**Fix:** Backend already has CORS enabled, but check your .env:
```env
CORS_ORIGINS=*  # Allow all origins (development)
```

## Correct Frontend Implementation

```javascript
async function validatePharmaceuticalLabel(extractedText) {
  try {
    // Show loading state
    setLoading(true);
    setError(null);
    
    // Call validation endpoint
    const response = await fetch('http://localhost:5000/api/validation/validate-text', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text: extractedText  // ← Must be 'text', not 'content' or other field
      })
    });
    
    // Check response status
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }
    
    // Parse response
    const data = await response.json();
    
    // Update UI with results
    setDrugName(data.drug_name);
    setBatchNumber(data.batch_number);
    setExpiryDate(data.expiry_date);
    setRiskLevel(data.risk_level);
    setConfidence(data.confidence_score);
    
    setLoading(false);
    
  } catch (error) {
    console.error('Validation error:', error);
    setError(error.message);
    setLoading(false);
  }
}
```

## Debug Checklist

- [ ] Backend server is running (`python src/app.py`)
- [ ] Server shows "All blueprints registered" in logs
- [ ] Can access http://localhost:5000/health
- [ ] GROQ_API_KEY is set in .env
- [ ] Frontend is calling correct endpoint URL
- [ ] Request body has `text` field (not `content` or other)
- [ ] Content-Type header is set to `application/json`
- [ ] Frontend timeout is at least 30 seconds
- [ ] Browser console shows no CORS errors
- [ ] Response status is checked before parsing JSON

## Quick Test

Run this in your browser console (F12):

```javascript
fetch('http://localhost:5000/api/validation/validate-text', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: 'Drug Name: ASPIRIN 500mg\nBatch: ABC123\nExp: 12/2025'
  })
})
.then(r => r.json())
.then(data => console.log('✓ Validation works!', data))
.catch(err => console.error('✗ Error:', err));
```

If this works in the console but not in your app, the issue is in your frontend code.

## Need More Help?

1. Open browser console (F12)
2. Look for error messages
3. Check the Network tab to see the actual request/response
4. Share the error message or network request details
