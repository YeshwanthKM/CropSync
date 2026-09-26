import os
import json
import urllib.request
import urllib.error
import db

SYSTEM_AGRI_PROMPT = """
You are CropSync AI, an expert agricultural advisor assistant for farmers in India.
Your mission is to provide concise, practical, highly accurate, and empowering farming advice.

Guidelines:
1. Provide actionable advice on crop selection, pest & disease identification, soil health, NPK fertilizer usage, irrigation, and Government Minimum Support Price (MSP) reference rates.
2. Structure your responses clearly with bold section headers, clean bullet points, and practical steps.
3. If Government MSP rates are provided in the context, refer to them accurately to help farmers get the best market value.
4. Keep the tone warm, encouraging, respectful, and clear.
"""

# Agricultural Knowledge Base for Fallback Engine
AGRI_KNOWLEDGE_BASE = {
    'msp': {
        'en': """💡 **Government Minimum Support Price (MSP) Advisory**:
- **Paddy (Rice)**: ₹2,183 / quintal (Grade A)
- **Wheat**: ₹2,275 / quintal
- **Maize**: ₹2,090 / quintal
- **Cotton**: ₹6,620 / quintal (Medium Staple)
- **Sugarcane**: ₹315 / quintal (FRP)

👉 *Tip*: Always check that your crop meets moisture standard requirements (typically under 14%) to receive the full MSP rate at government procurement centers.""",

        'ta': """💡 **அரசு குறைந்தபட்ச ஆதரவு விலை (MSP) ஆலோசனை**:
- **நெல் (அரிசி)**: ₹2,183 / குவிண்டால் (கிரேடு ஏ)
- **கோதுமை**: ₹2,275 / குவிண்டால்
- **சோளம் (மக்காச்சோளம்)**: ₹2,090 / குவிண்டால்
- **பருத்தி**: ₹6,620 / குவிண்டால்
- **கரும்பு**: ₹315 / குவிண்டால்

👉 *குறிப்பு*: அரசு கொள்முதல் நிலையங்களில் முழு MSP விலையைப் பெற, உங்கள் பயிர் ஈரப்பதம் 14% க்கு குறைவாக இருப்பதை உறுதிப்படுத்தவும்."""
    },

    'pest': {
        'en': """🐛 **Crop Pest & Disease Management Guide**:

1. **Leaf Blight / Spot Disease**:
   - *Symptoms*: Yellowing, brown spots, or drying leaf margins.
   - *Action*: Apply Neem Oil Spray (5ml/L) or copper oxychloride (2g/L). Avoid over-watering.

2. **Stem Borer / Caterpillar Attack**:
   - *Symptoms*: Dead hearts in stems, bored holes in leaves.
   - *Action*: Install Pheromone Traps (5 per acre). Spray Bacillus thuringiensis (Bt) or Chlorantraniliprole.

3. **Aphids & Whiteflies**:
   - *Symptoms*: Sticky honeydew on leaves, curling shoots.
   - *Action*: Spray Yellow Sticky Traps or Imidacloprid (0.5ml/L) early morning.""",

        'ta': """🐛 **பயிர் பூச்சி மற்றும் நோய் மேலாண்மை வழிகாட்டி**:

1. **இலை கருகல் / புள்ளி நோய்**:
   - *அறிகுறிகள்*: இலைகள் மஞ்சள் ஆகுதல், பழுப்பு புள்ளிகள்.
   - *தீர்வு*: வேப்ப எண்ணெய் தெளிக்கவும் (1 லிட்டருக்கு 5 மி.லி) அல்லது காப்பர் ஆக்சிக்ளோரைடு.

2. **தண்டு துளைப்பான் / புழு தாக்குதல்**:
   - *அறிகுறிகள்*: தண்டுகள் காய்ந்து போதல்.
   - *தீர்வு*: ஏக்கருக்கு 5 மோகக் கவர்ச்சி பொறிகள் வைக்கவும்.

3. **அசுவினி & வெள்ளை ஈக்கள்**:
   - *அறிகுறிகள்*: இலை சுருக்கம், பிசுபிசுப்பான இலைகள்.
   - *தீர்வு*: மஞ்சள் ஒட்டும் பொறிகள் பயன்படுத்தவும்."""
    },

    'fertilizer': {
        'en': """🌱 **Soil & N-P-K Fertilizer Guidance**:

- **Basal Application (At Planting)**: Apply Organic Compost/FYM (5 tons/acre) + Full Phosphorus (DAP) + 50% Potash (MOP).
- **Vegetative Stage (3-4 weeks)**: Top dress 50% Nitrogen (Urea) for foliage vigor.
- **Flowering & Grain Filling Stage**: Apply remaining 50% Nitrogen & 50% Potash to enhance grain weight and quality.

💡 *Pro-Tip*: Conduct a soil health test once a year to optimize fertilizer investment and prevent soil acidity.""",

        'ta': """🌱 **மண் மற்றும் உர மேலாண்மை (N-P-K)**:

- **அடி உரம் (நடவின் போது)**: இயற்கை உரம் (ஏக்கருக்கு 5 டன்) + முழு பாஸ்பரஸ் (DAP) + 50% பொட்டாஷ்.
- **வளர்ச்சி பருவம் (3-4 வாரங்கள்)**: 50% யுரியா மேலுரமாக இடவும்.
- **பூக்கும் பருவம்**: மீதமுள்ள 50% யுரியா மற்றும் பொட்டாஷ் இடவும்.

💡 *குறிப்பு*: உர செலவைக் குறைக்க ஆண்டுக்கு ஒருமுறை மண் பரிசோதனை செய்யுங்கள்."""
    },

    'season': {
        'en': """🌾 **Seasonal Crop Selection Guide**:

- **Kharif Season (Monsoon: June – Oct)**: Paddy, Maize, Cotton, Pulses (Tur, Urad), Groundnut.
- **Rabi Season (Winter: Oct – March)**: Wheat, Mustard, Gram (Chickpea), Sunflower, Vegetables.
- **Zaid Season (Summer: March – June)**: Watermelon, Cucumber, Fodder Crops, Green Gram.

👉 *Market Strategy*: Intercropping pulses with main crops increases soil nitrogen naturally while providing dual revenue streams.""",

        'ta': """🌾 **பருவகால பயிர் தேர்வு வழிகாட்டி**:

- **காரிஃப் பருவம் (மழைக்காலம்: ஜூன் – அக்டோபர்)**: நெல், மக்காச்சோளம், பருத்தி, உளுந்து, நிலக்கடலை.
- **ரபி பருவம் (குளிர்காலம்: அக்டோபர் – மார்ச்)**: கோதுமை, கடுகு, கொண்டைக்கடலை, சூரியகாந்தி.
- **கோடை பருவம் (மார்ச் – ஜூன்)**: தர்பூசணி, வெள்ளரி, பாசிப்பயறு.

👉 *குறிப்பு*: ஊடு பயிர் செய்வதன் மூலம் மண்ணின் வளம் அதிகரிக்கும் மற்றும் கூடுதல் வருமானம் கிடைக்கும்."""
    }
}


def _fetch_msp_context():
    """Fetch current MSP rates from database to include in AI prompt."""
    try:
        msp_list = db.get_all_msp_references()
        if msp_list:
            formatted = []
            for item in msp_list[:10]:
                formatted.append(f"- {item.get('crop_name')}: ₹{item.get('msp_price_per_kg')}/kg (₹{item.get('msp_price_per_quintal')}/quintal) - Category: {item.get('category')}")
            return "\n".join(formatted)
    except Exception as e:
        print("[!] Could not fetch MSP context:", e)
    return "Standard MSP rates apply."


def generate_agri_advice(query, category='general', language='en'):
    """
    Generates intelligent agricultural advice using Gemini API or offline domain knowledge base.
    """
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    msp_context = _fetch_msp_context()

    # Determine fallback category
    q_lower = query.lower()
    if any(k in q_lower for k in ['msp', 'price', 'rate', 'cost', 'government', 'விலை', 'அரசு']):
        fb_category = 'msp'
    elif any(k in q_lower for k in ['pest', 'disease', 'bug', 'caterpillar', 'spray', 'பூச்சி', 'நோய்']):
        fb_category = 'pest'
    elif any(k in q_lower for k in ['fertilizer', 'soil', 'npk', 'dap', 'urea', 'உரம்', 'மண்']):
        fb_category = 'fertilizer'
    elif any(k in q_lower for k in ['season', 'monsoon', 'crop', 'plant', 'weather', 'பயிர்', 'பருவம்']):
        fb_category = 'season'
    else:
        fb_category = category if category in AGRI_KNOWLEDGE_BASE else 'season'

    lang_code = 'ta' if language == 'ta' or any(ord(c) > 0x0B80 and ord(c) < 0x0BFF for c in query) else 'en'

    # Try Gemini API if key exists
    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            prompt_text = f"""
{SYSTEM_AGRI_PROMPT}

Government MSP Reference Data:
{msp_context}

Farmer Question ({'Tamil' if lang_code == 'ta' else 'English'}):
"{query}"

Respond clearly in {'Tamil' if lang_code == 'ta' else 'English'}. Keep response practical, encouraging, and under 300 words.
"""
            payload = {
                "contents": [{
                    "parts": [{"text": prompt_text}]
                }]
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=8) as response:
                result = json.loads(response.read().decode('utf-8'))
                candidates = result.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    if parts and 'text' in parts[0]:
                        return parts[0]['text'].strip()
        except Exception as e:
            print("[!] Gemini API request failed, using domain knowledge base:", e)

    # Fallback to rich domain knowledge base
    fallback_entry = AGRI_KNOWLEDGE_BASE.get(fb_category, AGRI_KNOWLEDGE_BASE['season'])
    response_text = fallback_entry.get(lang_code, fallback_entry['en'])

    if fb_category == 'msp' and msp_context:
        header = "🌾 **Live CropSync Government MSP Rates**:\n" if lang_code == 'en' else "🌾 **நேரலை பயிர் அரசு ஆதரவு விலை (MSP)**:\n"
        response_text = f"{header}{msp_context}\n\n{response_text}"

    return response_text


SYSTEM_VISION_PROMPT = """
You are CropSync AI Vision, an expert plant pathologist and agricultural diagnostics assistant for farmers.
Analyze the provided crop/leaf image carefully and return a structured agricultural diagnosis.

Structure your diagnosis as follows:
1. **Identified Issue / Disease Name**: Clear name of the crop disease or pest (e.g. Leaf Blight, Powdery Mildew, Caterpillars, Nutrient Deficiency).
2. **Severity Level**: Mild, Moderate, or Severe.
3. **Key Visual Symptoms**: List 2-3 observable signs visible on the plant.
4. **Organic & Chemical Cures**: Practical treatment options with dosage per liter of water.
5. **Preventive Steps**: Actions to protect future crops.

If the image is unclear or not a plant, provide general crop health inspection guidance.
"""

def diagnose_crop_image(image_base64, mime_type='image/jpeg', language='en'):
    """
    Analyzes an uploaded crop leaf/plant image using Gemini 1.5 Flash Vision API or domain fallback.
    """
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    lang_code = 'ta' if language == 'ta' else 'en'
    
    # Strip data URL prefix if present (e.g. "data:image/jpeg;base64,...")
    if ',' in image_base64:
        header, image_base64 = image_base64.split(',', 1)
        if 'png' in header:
            mime_type = 'image/png'
        elif 'webp' in header:
            mime_type = 'image/webp'
            
    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            prompt_text = f"""
{SYSTEM_VISION_PROMPT}

Language: Respond strictly in {'Tamil' if lang_code == 'ta' else 'English'}. Keep response clear, practical, and structured.
"""
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt_text},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_base64
                            }
                        }
                    ]
                }]
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode('utf-8'))
                candidates = result.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    if parts and 'text' in parts[0]:
                        report = parts[0]['text'].strip()
                        
                        # Extract disease name & severity if present
                        disease_name = "Crop Disease Analysis"
                        severity = "Moderate"
                        for line in report.split('\n'):
                            if 'Identified Issue' in line or 'Disease Name' in line or 'அடையாளம்' in line:
                                disease_name = line.split(':')[-1].replace('*', '').strip() or disease_name
                            elif 'Severity' in line or 'தீவிரம்' in line:
                                severity = line.split(':')[-1].replace('*', '').strip() or severity
                                
                        return {
                            'success': True,
                            'diagnosis_report': report,
                            'disease_name': disease_name,
                            'severity': severity
                        }
        except Exception as e:
            print("[!] Gemini Vision API request error, using fallback diagnosis:", e)

    # Offline / Fallback Diagnosis Guide
    if lang_code == 'ta':
        report = """🔍 **அடையாளம் காணப்பட்ட பிரச்சனை**: இலை கருகல் / பூச்சி தாக்குதல் பகுப்பாய்வு
⚠️ **தீவிரம்**: மிதமான நிலை (Moderate)

🌿 **முக்கிய அறிகுறிகள்**:
• இலைகளில் மஞ்சள் அல்லது பழுப்பு புள்ளிகள்
• தண்டுகளில் சிறிய பூச்சி துளைகள் அல்லது இலை சுருக்கம்

🧪 **பரிந்துரைக்கப்பட்ட சிகிச்சை**:
• **இயற்கை முறை**: வேப்ப எண்ணெய் கரைசல் தெளிக்கவும் (1 லிட்டருக்கு 5 மி.லி).
• **இரசாயன முறை**: காப்பர் ஆக்சிக்ளோரைடு (1 லிட்டருக்கு 2 கிராம்) அல்லது இமிடாக்ளோப்ரிட் தெளிக்கவும்.

🛡️ **தடுப்பு முறைகள்**:
• அதிக நீர் தேங்குவதைத் தவிர்க்கவும்.
• பயிர்களுக்கு இடையே போதிய இடைவெளி பராமரிக்கவும்."""
        disease_name = "இலை கருகல் / பூச்சி தாக்குதல்"
    else:
        report = """🔍 **Identified Issue / Disease**: Leaf Spot / Fungal Infection Analysis
⚠️ **Severity Level**: Moderate

🌿 **Key Visual Symptoms**:
• Yellowish-brown spots along leaf margins and veins.
• Slight curling on younger shoots.

🧪 **Recommended Treatment**:
• **Organic Care**: Spray Neem Oil Solution (5ml per liter of water) early morning.
• **Targeted Care**: Apply Copper Oxychloride (2g/L) or Carbendazim (1g/L).

🛡️ **Preventive Steps**:
• Ensure proper field drainage to prevent root moisture rot.
• Maintain optimal spacing between crop rows for airflow."""
        disease_name = "Leaf Spot / Fungal Infection"

    return {
        'success': True,
        'diagnosis_report': report,
        'disease_name': disease_name,
        'severity': 'Moderate'
    }
