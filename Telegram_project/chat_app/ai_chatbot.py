import os
from django.conf import settings
from openai import OpenAI


class AIChatBot:
    """AI ChatBot using OpenAI API"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client = None
        self.conversation_history = {}
        self.max_history = 10
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
    
    def get_response(self, user_message, username="User"):
        """Get AI response for user message"""
        if not self.client:
            return "AI chatbot is not configured. Please set your OpenAI API key in the .env file."
        
        session_key = username
        
        if session_key not in self.conversation_history:
            self.conversation_history[session_key] = []
        
        self.conversation_history[session_key].append({
            "role": "user",
            "content": user_message
        })
        
        system_message = {
            "role": "system",
            "content": """You are a helpful, friendly AI assistant in a chat application. 
You should be conversational, helpful, and informative. Keep your responses concise but 
meaningful. Be friendly and supportive. You can help with various tasks like answering 
questions, providing explanations, brainstorming ideas, writing assistance, and more."""
        }
        
        messages = [system_message] + self.conversation_history[session_key][-self.max_history:]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            self.conversation_history[session_key].append({
                "role": "assistant",
                "content": ai_response
            })
            
            if len(self.conversation_history[session_key]) > self.max_history * 2 + 1:
                self.conversation_history[session_key] = self.conversation_history[session_key][-self.max_history * 2:]
            
            return ai_response
            
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."
    
    def clear_history(self, username):
        """Clear conversation history for a user"""
        if username in self.conversation_history:
            del self.conversation_history[username]
        return True
    
    def get_suggestions(self, user_message):
        """Get suggested responses based on user input"""
        suggestions = []
        
        greeting_words = ['hello', 'hi', 'hey', 'howdy', 'greetings']
        help_words = ['help', 'how', 'what', 'why', 'when', 'where', 'can you']
        
        msg_lower = user_message.lower()
        
        if any(word in msg_lower for word in greeting_words):
            suggestions = [
                "How are you?",
                "What can you help me with?",
                "Tell me about yourself",
            ]
        elif any(word in msg_lower for word in help_words):
            suggestions = [
                "Explain in more detail",
                "Give me an example",
                "What are the alternatives?",
            ]
        else:
            suggestions = [
                "Can you elaborate?",
                "That's interesting!",
                "Thank you for explaining",
            ]
        
        return suggestions
