import { configureStore, createSlice, createAsyncThunk } from '@reduxjs/toolkit';

export const sendAgentMessage = createAsyncThunk('interaction/sendAgentMessage', async ({ message, threadId }) => {
  const response = await fetch('http://localhost:8000/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, thread_id: threadId }),
  });
  return response.json();
});

export const submitStructuredForm = createAsyncThunk('interaction/submitStructuredForm', async (formData) => {
  const response = await fetch('http://localhost:8000/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: 'Direct submission: Log interaction for HCP ID ' + formData.hcpId + '. Notes: ' + formData.notes, thread_id: 'structured_form_thread' }),
  });
  return response.json();
});

const interactionSlice = createSlice({
  name: 'interaction',
  initialState: { chatHistory: [{ sender: 'agent', text: 'Hello! I am your Healthcare CRM Agent. How can I help you today?' }], threadId: 'thread_' + Date.now(), status: 'idle', error: null, formSuccess: false },
  reducers: {
    addMessage: (state, action) => { state.chatHistory.push(action.payload); },
    resetFormState: (state) => { state.formSuccess = false; state.error = null; }
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendAgentMessage.pending, (state) => { state.status = 'loading'; })
      .addCase(sendAgentMessage.fulfilled, (state, action) => { state.status = 'idle'; state.chatHistory.push({ sender: 'agent', text: action.payload.response }); })
      .addCase(sendAgentMessage.rejected, (state) => { state.status = 'failed'; state.chatHistory.push({ sender: 'agent', text: 'System connection error. Unable to reach agent.' }); })
      .addCase(submitStructuredForm.pending, (state) => { state.status = 'loading'; })
      .addCase(submitStructuredForm.fulfilled, (state) => { state.status = 'idle'; state.formSuccess = true; })
      .addCase(submitStructuredForm.rejected, (state) => { state.status = 'failed'; });
  }
});

export const { addMessage, resetFormState } = interactionSlice.actions;
export const store = configureStore({ reducer: { interaction: interactionSlice.reducer } });