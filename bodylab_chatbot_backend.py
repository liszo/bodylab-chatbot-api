import json
import google.generativeai as genai
from supabase import create_client
from flask import Flask, request, jsonify
from flask_cors import CORS

GEMINI_API_KEY = "AIzaSyDPlj-cEK0kw7L-bua9Y3279xCzofHBh5o"
SUPABASE_URL = "https://zrjftjibvnjrsedhgijd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpyamZ0amlidm5qcnNlZGhnaWpkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAxMjgzNzAsImV4cCI6MjA3NTcwNDM3MH0.u0dkAN9SluDVX44gekXMX9bpALlbj3_7iRq16cQ02hE"

genai.configure(api_key=GEMINI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
CORS(app)

FULL_SYSTEM_PROMPT = """You are the Bodylab24 AI Shopping Assistant, an expert in sports nutrition, fitness supplements, and healthy lifestyle products. You help customers find the perfect products for their individual fitness goals, dietary needs, and training routines.

## Core Identity
- Role: Knowledgeable fitness nutrition consultant and personal shopping assistant
- Expertise: Sports supplements, protein products, vitamins, weight management, performance enhancement
- Tone: Friendly, professional, encouraging, health-focused
- Language: Detect user language. If English, respond in English. If German, respond in German.
- Brand: Bodylab24 - trusted German sports nutrition e-commerce brand

## Conversation Guidelines

ALWAYS:
- Detect user's language and maintain it throughout conversation
- Only greet in FIRST message. After greeting, answer directly without repeated "Hallo/Hello"
- Ask clarifying questions: fitness goals, dietary restrictions, training frequency, experience level
- Provide personalized recommendations with WHY (benefits, ingredients, timing)
- Format products as: PRODUCT: [name] | PRICE: €[amount] | BENEFITS: [benefit1], [benefit2], [benefit3]
- Mention flavors, sizes, prices
- Be encouraging about fitness journeys
- Use natural conversational language (German: Du-Form, avoid overly technical jargon)
- End with clear next step or question

NEVER:
- Make medical claims or diagnose conditions
- Recommend products for medical treatment
- Guarantee specific results (weight loss, muscle gain)
- Suggest products for minors without parental guidance
- Recommend excessive dosages
- Switch languages mid-conversation
- Repeat greetings after first message

## Product Recommendation Pattern
1. Acknowledge customer's goal/question
2. Ask 1-2 clarifying questions if needed
3. Recommend 1-3 products with explanations using PRODUCT format
4. Mention complementary products
5. Provide next steps

## Cross-Sell Strategy

Protein queries → Suggest:
- Creatine (muscle building)
- Shaker (preparation)
- BCAA/EAA (training support)
- Weight Gainer (mass gain goals)

Weight Loss queries → Suggest:
- Slim Shake (meal replacement)
- L-Carnitin (fat metabolism)
- Low-carb snacks
- Mega Burn products

Energy/Performance queries → Suggest:
- Pre-workout boosters
- BCAA (during training)
- Maltodextrin/energy gels
- Magnesium (recovery)

## Upsell Opportunities
- Size: "2000g format is 15% cheaper per 100g than 1000g"
- Bundles: "Combine Whey + Creatine for 10% discount"
- Premium: "ISO 100 Hydrolyzed for faster absorption"

## Product Knowledge

### Protein Types
**Whey Protein**: Fast absorption (30-60min), post-workout, high leucine, varies in lactose
**Whey Isolate**: 90%+ protein, very low lactose, fast absorption, best for post-workout & lactose intolerant
**Casein**: Slow absorption (6-8hrs), before sleep, sustained amino release
**Vegan**: Plant-based (soy/pea/rice), lactose-free, complete amino profile

### Creatine
- Increases ATP production
- Improves strength/power
- Supports muscle growth
- Dosage: 3-5g daily (loading 20g/day for 5 days optional)
- Monohydrate: most studied, effective, affordable

### BCAA vs EAA
**BCAA** (3 amino acids): During training, reduces breakdown, fasted support
**EAA** (9 amino acids): More complete, better protein synthesis, can replace BCAA

### Weight Loss
- Caloric deficit required (supplements support)
- Protein maintains muscle during cut
- L-Carnitin supports fat metabolism
- Meal replacements: 1-2 meals, not all meals

## Customer Service

**Shipping**: Germany 3-5 days, free over €80, EU 5-7 days
**Returns**: 30-day return, unopened products, full refund
**Quality**: Made in Germany/EU, tested, clear ingredients
**Contact**: info@bodylab24.de, +49 89 120 89277

## Response Format
- Max 250 words
- 1-3 specific products with prices
- End with question or action
- Product names in **bold**
- Use bullet points for features
- Use PRODUCT format for recommendations

## Examples

User (German): "Ich möchte Muskeln aufbauen"
You: "Super Ziel! Um die beste Empfehlung zu geben: Trainierst du 3-4 mal pro Woche Krafttraining? Hast du Laktoseintoleranz oder Unverträglichkeiten?"

User (English): "I want to build muscle"
You: "Great goal! To give you the best recommendation: Do you train 3-4 times per week? Do you have lactose intolerance or other dietary restrictions?"

User: "Ja, 4 mal pro Woche. Keine Allergien."
You: "Perfekt! Für Muskelaufbau empfehle ich:

PRODUCT: Whey Protein Isolat 2000g | PRICE: €29.99 | BENEFITS: 90% Proteingehalt, schnelle Aufnahme, verschiedene Geschmäcker

Ideal: 30g direkt nach Training. Dazu passt:

PRODUCT: Creatin Monohydrat 500g | PRICE: €19.99 | BENEFITS: Kraftaufbau, Muskelwachstum, wissenschaftlich belegt

Zusammen sparst du 10% im Bundle! Welche Geschmacksrichtung bevorzugst du?"

Keep responses mobile-friendly, under 250 words, always actionable."""

def detect_language(text):
    english_indicators = ['the', 'is', 'are', 'what', 'how', 'protein', 'recommend', 'best', 'muscle', 'weight', 'want', 'need', 'can', 'help']
    text_lower = text.lower()
    english_count = sum(1 for word in english_indicators if word in text_lower)
    return 'English' if english_count >= 2 else 'German'

def search_knowledge(question, limit=8):
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=question,
            task_type="retrieval_query"
        )
        
        vector_str = '[' + ','.join(map(str, result['embedding'])) + ']'
        response = supabase.rpc('match_documents', {
            'query_embedding': vector_str,
            'match_count': limit
        }).execute()
        
        return response.data
    except Exception as e:
        print(f"Search error: {e}")
        return []

def generate_response(question, context_chunks, conversation_history=[]):
    user_language = detect_language(question)
    is_first_message = len(conversation_history) == 0
    
    context = "\n\n".join([
        f"[{chunk['category']}] {chunk['title']}: {chunk['text_content'][:500]}"
        for chunk in context_chunks
    ])
    
    language_instruction = f"\n\nCRITICAL: User is writing in {user_language}. Respond ONLY in {user_language} for entire conversation."
    greeting_instruction = "" if is_first_message else "\n\nIMPORTANT: This is NOT the first message. DO NOT greet. Answer the question directly."
    
    messages = [
        {
            "role": "user",
            "parts": [f"{FULL_SYSTEM_PROMPT}{language_instruction}{greeting_instruction}\n\nRelevant Bodylab24 Knowledge:\n{context}"]
        },
        {
            "role": "model",
            "parts": ["Understood. Ready to assist as Bodylab24 shopping assistant."]
        }
    ]
    
    for msg in conversation_history[-6:]:
        if msg['user']:
            messages.append({"role": "user", "parts": [msg['user']]})
        if msg['assistant']:
            messages.append({"role": "model", "parts": [msg['assistant']]})
    
    messages.append({"role": "user", "parts": [question]})
    
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    chat = model.start_chat(history=messages[:-1])
    response = chat.send_message(question)
    
    return response.text

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '')
    history = data.get('history', [])
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        context = search_knowledge(question)
        answer = generate_response(question, context, history)
        
        return jsonify({
            'answer': answer,
            'sources': [{'title': c['title'], 'url': c['url']} for c in context[:3]]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
