# HDI Voice AI Integration Guide

## 🎤 Complete Voice AI Setup

### API Endpoints for Voice Assistant

#### 1. **Voice-Optimized Search**
```
POST /api/v1/properties/voice-search
{
  "spoken_text": "find nine twenty four zoe street"
}
```

#### 2. **Natural Language AI Chat**
```
POST /api/v1/properties/ask
{
  "question": "What's the investment potential?",
  "context": { "property_address": "924 ZOE ST" }
}
```

#### 3. **Voice-Formatted Responses**
```
GET /api/v1/properties/voice-format/{account_number}
```

#### 4. **Location-Based Search**
```
GET /api/v1/properties/location?lat=29.7&lon=-95.4&limit=5
```

### 📚 Example Voice Commands & API Calls

#### Property Search Commands:
- **"Find property at 924 Zoe"**
  ```json
  POST /voice-search
  { "spoken_text": "Find property at 924 Zoe" }
  ```

- **"Show me homes on Main Street"**
  ```json
  POST /voice-search
  { "spoken_text": "Show me homes on Main Street" }
  ```

- **"Properties near me"** (with GPS)
  ```
  GET /location?lat={user_lat}&lon={user_lon}
  ```

#### Market Analysis Commands:
- **"What's the Houston market like?"**
  ```
  GET /market/trends?area=Houston
  ```

- **"Tell me about The Woodlands"**
  ```json
  POST /ask
  { "question": "Tell me about real estate in The Woodlands area" }
  ```

#### Investment Commands:
- **"Is this a good investment?"**
  ```json
  POST /ask
  {
    "question": "Is this a good investment property?",
    "context": { "property_data": {...} }
  }
  ```

### 🔧 Voice AI Implementation Code

```javascript
class HoustonVoiceAI {
  constructor() {
    this.apiBase = 'https://hdi-api-production.up.railway.app/api/v1';
    this.context = {};
  }

  async processVoiceCommand(spokenText) {
    // 1. Try voice search first
    const searchResult = await this.voiceSearch(spokenText);
    
    if (searchResult.count > 0) {
      // Found properties
      return this.formatPropertyResponse(searchResult.properties[0]);
    }
    
    // 2. Fall back to AI chat for complex questions
    const aiResponse = await this.askAI(spokenText);
    return aiResponse.answer;
  }

  async voiceSearch(spokenText) {
    const response = await fetch(`${this.apiBase}/properties/voice-search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ spoken_text: spokenText })
    });
    return response.json();
  }

  async askAI(question) {
    const response = await fetch(`${this.apiBase}/properties/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        question, 
        context: this.context,
        search_web: true 
      })
    });
    return response.json();
  }

  formatPropertyResponse(property) {
    return `I found a property at ${property.address}. 
            It's valued at $${property.marketValue.toLocaleString()} 
            with ${property.squareFeet} square feet. 
            Would you like more details?`;
  }
}
```

### 🎯 Voice Response Best Practices

1. **Number Formatting**
   - $450,000 → "four hundred fifty thousand dollars"
   - 2,500 sq ft → "twenty five hundred square feet"

2. **Address Speaking**
   - "924 ZOE ST" → "nine twenty four Zoe Street"
   - Spell out abbreviations: "ST" → "Street", "AVE" → "Avenue"

3. **Error Responses**
   ```javascript
   const voiceErrors = {
     no_results: "I couldn't find any properties matching that description. Could you be more specific?",
     api_error: "I'm having trouble accessing property data right now. Please try again.",
     unclear: "I didn't quite catch that. Could you repeat the address?"
   };
   ```

### 📊 Conversation Context Management

```javascript
// Maintain context across questions
let conversation = {
  currentProperty: null,
  searchHistory: [],
  lastQuestion: null
};

// Example conversation flow:
// User: "Find 924 Zoe Street"
conversation.currentProperty = searchResult.properties[0];

// User: "What about the taxes?" (context-aware follow-up)
const followUp = await askAI("What about the property taxes?", {
  property_data: conversation.currentProperty
});
```

### 🚀 Performance Tips

1. **Cache Common Searches**
   - Popular neighborhoods
   - Frequently asked properties
   - Market trend data (update daily)

2. **Preload Voice Responses**
   - Generate voice-friendly summaries in advance
   - Store formatted number pronunciations

3. **Batch Requests**
   - If showing multiple properties, use `/batch/analyze`
   - Prefetch nearby properties for "show me more" commands

### ✅ Testing Your Voice AI

```bash
# Test voice search
curl -X POST https://hdi-api-production.up.railway.app/api/v1/properties/voice-search \
  -H "Content-Type: application/json" \
  -d '{"spoken_text": "find property at nine twenty four zoe"}'

# Test AI chat
curl -X POST https://hdi-api-production.up.railway.app/api/v1/properties/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What areas in Houston are best for families?"}'

# Test voice formatting
curl https://hdi-api-production.up.railway.app/api/v1/properties/voice-format/0123456789
```

### 🎤 Common Voice Scenarios

1. **Property Lookup**
   - "Show me 1234 Main Street"
   - "Find properties on Westheimer"
   - "What's at nine hundred Zoe?"

2. **Market Questions**
   - "How's the market in Katy?"
   - "What areas are growing?"
   - "Best neighborhoods for investment?"

3. **Comparisons**
   - "Compare this to similar properties"
   - "What's the average price here?"
   - "How does this compare to last year?"

4. **Specific Details**
   - "When was it built?"
   - "How big is the lot?"
   - "What are the taxes?"
   - "Who owns it?"

### 🔒 API Keys & Security

Remember to:
- Use your Perplexity API key for AI features
- Implement rate limiting for voice requests
- Cache responses to reduce API calls
- Sanitize voice input before database queries

### Ready to Launch! 🚀

Your Voice AI now has:
- ✅ Smart address parsing
- ✅ Natural language understanding
- ✅ Real-time market data
- ✅ 1.7M property database access
- ✅ Conversational AI with Perplexity
- ✅ Voice-optimized responses

Test endpoint: https://hdi-api-production.up.railway.app/api/v1/properties/voice-search