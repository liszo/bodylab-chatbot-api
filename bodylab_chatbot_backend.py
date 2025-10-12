import os
import json
import google.generativeai as genai
from supabase import create_client
from flask import Flask, request, jsonify
from flask_cors import CORS

# Environment variables for Vercel
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyDPlj-cEK0kw7L-bua9Y3279xCzofHBh5o')
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://zrjftjibvnjrsedhgijd.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpyamZ0amlidm5qcnNlZGhnaWpkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAxMjgzNzAsImV4cCI6MjA3NTcwNDM3MH0.u0dkAN9SluDVX44gekXMX9bpALlbj3_7iRq16cQ02hE')

# Initialize
genai.configure(api_key=GEMINI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
CORS(app)

SYSTEM_PROMPT = """You are the Bodylab24 AI Shopping Assistant, an expert in sports nutrition and fitness supplements.

Core Identity:
- Friendly German fitness nutrition consultant
- Expertise: Protein, creatine, BCAA, weight management, performance
- Tone: Friendly, professional, encouraging
- Language: German primary, English if customer uses English

Guidelines:
- Ask clarifying questions (goals, training frequency, restrictions)
- Recommend 1-3 products with prices and explanations
- Suggest complementary products
- Use natural conversational German (Du-Form)
- Never make medical claims
- Adapt complexity to customer's experience level
- Keep responses under 300 words
- Format product names in **bold**

Always end with clear next step or question."""

def search_knowledge(question, limit=8):
    """Search vector database for relevant context"""
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
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Search error: {e}")
        return []

def generate_response(question, context_chunks, conversation_history=[]):
    """Generate response using Gemini with context"""
    
    # Build context from retrieved chunks
    context = "\n\n".join([
        f"[{chunk['category']}] {chunk['title']}: {chunk['text_content'][:500]}"
        for chunk in context_chunks
    ])
    
    # Build conversation for Gemini
    messages = []
    
    # Add conversation history
    for msg in conversation_history[-6:]:  # Last 3 exchanges
        messages.append({"role": "user", "parts": [msg['user']]})
        messages.append({"role": "model", "parts": [msg['assistant']]})
    
    # Add current question with context
    prompt = f"""{SYSTEM_PROMPT}

Relevant Bodylab24 Knowledge:
{context}

Customer Question: {question}

Generate helpful response using the knowledge above."""
    
    messages.append({"role": "user", "parts": [prompt]})
    
    # Generate response
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    if len(messages) == 1:
        response = model.generate_content(messages[0]['parts'][0])
    else:
        chat = model.start_chat(history=messages[:-1])
        response = chat.send_message(messages[-1]['parts'][0])
    
    return response.text

@app.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint"""
    data = request.json
    question = data.get('question', '')
    history = data.get('history', [])
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        # Search knowledge base
        context = search_knowledge(question)
        
        # Generate response
        answer = generate_response(question, context, history)
        
        return jsonify({
            'answer': answer,
            'sources': [{'title': c['title'], 'url': c['url']} for c in context[:3]]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'Bodylab AI Chatbot'})

@app.route('/', methods=['GET'])
def home():
    """Root endpoint"""
    return jsonify({
        'service': 'Bodylab24 AI Chatbot API',
        'endpoints': {
            '/chat': 'POST - Main chat endpoint',
            '/health': 'GET - Health check'
        }
    })

# For Vercel serverless
app = app