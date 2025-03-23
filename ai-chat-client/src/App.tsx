import React, { useState, useEffect } from 'react';
import axios from 'axios';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import utc from 'dayjs/plugin/utc';
import ReactMarkdown from 'react-markdown';
import './App.css';

// Initialize the dayjs plugins
dayjs.extend(relativeTime);
dayjs.extend(utc);

const API_URL = 'http://127.0.0.1:8000/chat';

interface Message {
  message: string;
  sender: 'user' | 'ai';
  created_at: string;
  message_id: string;
  conversation_id: string;
  suggestions?: string[];
}

const App: React.FC = () => {
  const [chatHistory, setChatHistory] = useState<Message[]>([]);
  const [currentMessage, setCurrentMessage] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Create a shared function for initializing/resetting chat
  const initializeConversation = async (errorMessage: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post(API_URL, {
        message: '',
        conversation_id: '',
      });

      const aiMessage: Message = {
        message: response.data.message,
        sender: 'ai',
        created_at: response.data.created_at,
        message_id: response.data.message_id,
        conversation_id: response.data.conversation_id,
        suggestions: response.data.suggestions || [],
      };

      // Only add the message if it's not empty
      setConversationId(response.data.conversation_id);
      if (aiMessage.message.trim() !== '') {
        setChatHistory([aiMessage]);
      } else {
        setChatHistory([]);
      }
    } catch (err) {
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    initializeConversation('Failed to initialize chat. Please refresh the page.');
  }, []);

  useEffect(() => {
    if (!conversationId) return;

    // Scroll to the bottom of the chat history when a new message is added
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  }, [chatHistory, conversationId]);

  const handleSendMessage = async () => {
    if (currentMessage.trim() === '') return;

    // Create new message
    const userMessage: Message = {
      message: currentMessage,
      sender: 'user',
      created_at: new Date().toISOString(),
      message_id: new Date().getTime().toString(),
      conversation_id: conversationId || '',
    };

    // Update chat history with user message
    setChatHistory((prev) => [...prev, userMessage]);
    setCurrentMessage('');
    setLoading(true);
    setError(null);

    try {
      // Send message to AI
      const response = await axios.post(API_URL, {
        message: currentMessage,
        conversation_id: conversationId || '',
      });

      const aiMessage: Message = {
        message: response.data.message,
        sender: 'ai',
        created_at: response.data.created_at,
        message_id: response.data.message_id,
        conversation_id: response.data.conversation_id,
        suggestions: response.data.suggestions || [],
      };

      setConversationId(response.data.conversation_id);
      setChatHistory((prev) => [...prev, aiMessage]);
    } catch (err) {
      setError('Failed to send message. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleNewConversation = async () => {
    setChatHistory([]);
    setConversationId(null);
    await initializeConversation('Failed to start new conversation. Please try again.');
  };

  const handleSuggestionClick = (suggestion: string) => {
    setCurrentMessage(suggestion);
    handleSendSuggestion(suggestion);
  };

  const handleSendSuggestion = async (suggestion: string) => {
    if (suggestion.trim() === '') return;

    // Create new message
    const userMessage: Message = {
      message: suggestion,
      sender: 'user',
      created_at: new Date().toISOString(),
      message_id: new Date().getTime().toString(),
      conversation_id: conversationId || '',
    };

    // Update chat history with user message
    setChatHistory((prev) => [...prev, userMessage]);
    setLoading(true);
    setError(null);

    try {
      // Send message to AI
      const response = await axios.post(API_URL, {
        message: suggestion,
        conversation_id: conversationId || '',
      });

      const aiMessage: Message = {
        message: response.data.message,
        sender: 'ai',
        created_at: response.data.created_at,
        message_id: response.data.message_id,
        conversation_id: response.data.conversation_id,
        suggestions: response.data.suggestions || [],
      };

      setConversationId(response.data.conversation_id);
      setChatHistory((prev) => [...prev, aiMessage]);
    } catch (err) {
      setError('Failed to send message. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const renderMessage = (message: Message) => {
    // Skip rendering empty messages
    if (message.message.trim() === '') return null;
    
    // Convert UTC timestamp to local time properly
    const timestamp = dayjs.utc(message.created_at).local().format('hh:mm A');
    return (
      <div key={message.message_id} className={`message ${message.sender}`}>
        <div className="message-content">
          <ReactMarkdown>{message.message}</ReactMarkdown>
        </div>
        <small>{message.sender === 'ai' ? `AI - ${timestamp}` : `You - ${timestamp}`}</small>
      </div>
    );
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <button onClick={() => handleNewConversation()} className="new-conversation-btn">New Conversation</button>
        {error && <div className="error-message">{error}</div>}
      </div>
      
      <div id="chat-container" className="messages">
        {chatHistory.map(renderMessage)}
      </div>

      <div className="input-container">
        {loading && (
          <div className="loading-indicator">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div className="message-input">
          <input
            type="text"
            value={currentMessage}
            onChange={(e) => setCurrentMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type your message..."
            disabled={loading}
          />
          <button onClick={handleSendMessage} disabled={loading}>
            Send
          </button>
        </div>
        {chatHistory.length > 0 && 
          chatHistory[chatHistory.length - 1].suggestions && 
          chatHistory[chatHistory.length - 1].suggestions!.length > 0 && (
            <div className="suggestions">
              {chatHistory[chatHistory.length - 1].suggestions!.map((suggestion, index) => (
                <button 
                  className="suggestion-btn"
                  key={index} 
                  onClick={() => handleSuggestionClick(suggestion)}
                  disabled={loading}
                >
                  {suggestion}
                </button>
              ))}
            </div>
        )}
      </div>
    </div>
  );
};

export default App;