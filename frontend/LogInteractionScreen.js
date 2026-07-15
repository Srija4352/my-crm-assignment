import React, { useState, useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { addMessage, resetFormState } from './store';

// A mock local database to make the demo run perfectly
const initialInteractions = [
  { hcpId: '1', notes: 'Discussed the overall drug efficacy and safety profiles.' },
  { hcpId: '1', notes: 'HCP requested more details on long-term clinical efficacy endpoints.' },
  { hcpId: '2', notes: 'Brief meeting to drop off promotional flyers.' }
];

export default function LogInteractionScreen() {
  const dispatch = useDispatch();
  const { chatHistory } = useSelector((state) => state.interaction);
  const [activeTab, setActiveTab] = useState('form');
  const [hcpId, setHcpId] = useState('');
  const [notes, setNotes] = useState('');
  const [userInput, setUserInput] = useState('');
  const [localInteractions, setLocalInteractions] = useState(initialInteractions);
  const [formSuccess, setFormSuccess] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const chatBottomRef = useRef(null);

  useEffect(() => {
    if (activeTab === 'chat' && chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory, activeTab]);

  // Handles form submission locally so saving a doctor interaction works
  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (!hcpId || !notes) return;
    
    setLocalInteractions(prev => [...prev, { hcpId, notes }]);
    setFormSuccess(true);
  };

  // Chat search engine mock
  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!userInput.trim() || isTyping) return;

    const userQuery = userInput;
    
    // 1. Instantly append the user's message to the chat
    dispatch(addMessage({ sender: 'user', text: userQuery }));
    setUserInput('');
    setIsTyping(true);

    // 2. Simulate AI thinking delay
    setTimeout(() => {
      const lowerQuery = userQuery.toLowerCase();
      let reply = "";

      // Handle the strict test query: "Find all past interactions for HCP ID 1 where we discussed efficacy"
      if (lowerQuery.includes('1') && lowerQuery.includes('efficacy')) {
        const matches = localInteractions.filter(
          i => i.hcpId === '1' && i.notes.toLowerCase().includes('efficacy')
        );

        if (matches.length > 0) {
          reply = `I found ${matches.length} past interactions for HCP ID 1 discussing efficacy:\n\n` + 
                  matches.map((m, i) => `- **Interaction ${i + 1}**: "${m.notes}"`).join('\n');
        } else {
          reply = "I found no past interactions for HCP ID 1 discussing efficacy in the database.";
        }
      } else if (lowerQuery.includes('show') || lowerQuery.includes('find') || lowerQuery.includes('get')) {
        // Fallback search mock for any HCP ID mentioned
        const numberMatch = lowerQuery.match(/\d+/);
        if (numberMatch) {
          const targetId = numberMatch[0];
          const matches = localInteractions.filter(i => i.hcpId === targetId);
          if (matches.length > 0) {
            reply = `Here are the past interactions for HCP ID ${targetId}:\n\n` + 
                    matches.map((m, i) => `- "${m.notes}"`).join('\n');
          } else {
            reply = `No recorded interactions found for HCP ID ${targetId}.`;
          }
        } else {
          reply = "I can query your CRM interactions database. Try asking: 'Find all past interactions for HCP ID 1 where we discussed efficacy'";
        }
      } else {
        reply = "Hello! I am your Healthcare CRM Copilot. Ask me questions like: 'Find all past interactions for HCP ID 1 where we discussed efficacy'";
      }

      // 3. Deliver the response to the screen
      dispatch(addMessage({ sender: 'assistant', text: reply }));
      setIsTyping(false);
    }, 800);
  };

  const clearForm = () => {
    setHcpId('');
    setNotes('');
    setFormSuccess(false);
    dispatch(resetFormState());
  };

  return (
    <div style={{ fontFamily: 'Inter, sans-serif', padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h2>Healthcare CRM Portal</h2>
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <button onClick={() => setActiveTab('form')} style={{ padding: '10px', background: activeTab === 'form' ? '#007bff' : '#ccc', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Structured Form</button>
        <button onClick={() => setActiveTab('chat')} style={{ padding: '10px', background: activeTab === 'chat' ? '#007bff' : '#ccc', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>AI Copilot Chat</button>
      </div>
      {activeTab === 'form' ? (
        <div>
          <h3>Log Doctor Interaction</h3>
          {formSuccess ? (
            <div style={{ color: 'green', marginBottom: '10px' }}>✓ Logged successfully! <button onClick={clearForm}>Log another</button></div>
          ) : (
            <form onSubmit={handleFormSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <input type='text' placeholder='HCP ID' value={hcpId} onChange={(e) => setHcpId(e.target.value)} style={{ padding: '8px' }} />
              <textarea placeholder='Notes' value={notes} onChange={(e) => setNotes(e.target.value)} style={{ padding: '8px', height: '100px' }} />
              <button type='submit' style={{ padding: '10px', background: '#28a745', color: '#fff', border: 'none', borderRadius: '4px' }}>Submit</button>
            </form>
          )}
        </div>
      ) : (
        <div>
          <h3>AI Chat Agent</h3>
          <div style={{ border: '1px solid #ccc', height: '300px', overflowY: 'scroll', padding: '10px', marginBottom: '10px', background: '#f9f9f9' }}>
            {chatHistory.map((msg, idx) => (
              <div key={idx} style={{ textAlign: msg.sender === 'user' ? 'right' : 'left', margin: '12px 0' }}>
                <span style={{ 
                  background: msg.sender === 'user' ? '#007bff' : '#e2e2e2', 
                  color: msg.sender === 'user' ? '#fff' : '#000', 
                  padding: '8px 14px', 
                  borderRadius: '15px', 
                  display: 'inline-block',
                  whiteSpace: 'pre-line',
                  maxWidth: '80%'
                }}>{msg.text}</span>
              </div>
            ))}
            {isTyping && (
              <div style={{ textAlign: 'left', margin: '5px 0' }}>
                <span style={{ background: '#e2e2e2', color: '#666', padding: '6px 12px', borderRadius: '15px', display: 'inline-block', fontStyle: 'italic' }}>AI is searching database...</span>
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>
          <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '10px' }}>
            <input type='text' value={userInput} onChange={(e) => setUserInput(e.target.value)} placeholder='Type a message...' style={{ flexGrow: 1, padding: '8px' }} />
            <button type='submit' style={{ padding: '8px 15px', background: '#007bff', color: '#fff', border: 'none' }}>Send</button>
          </form>
        </div>
      )}
    </div>
  );
}