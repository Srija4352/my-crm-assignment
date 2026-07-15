import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from database import init_db, get_db, HCPProfile
from agent import compiled_agent

app = FastAPI(title="Healthcare CRM Backend", version="1.0")

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables on startup
@app.on_event("startup")
def on_startup():
    init_db()

# --- Request / Response Schemas ---

class AgentQuery(BaseModel):
    message: str
    thread_id: str = "default_user_thread"

class SeedHCPRequest(BaseModel):
    first_name: str
    last_name: str
    specialty: str
    hospital: str
    email: str
    phone: str

# --- HTTP Endpoints ---

@app.post("/api/seed-hcp")
def seed_hcp(hcp_data: SeedHCPRequest, db: Session = Depends(get_db)):
    """Seeds a dummy HCP Profile into the system database to test tool functionality."""
    try:
        existing = db.query(HCPProfile).filter(HCPProfile.email == hcp_data.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="HCP email already exists.")
        
        new_hcp = HCPProfile(**hcp_data.model_dump())
        db.add(new_hcp)
        db.commit()
        db.refresh(new_hcp)
        return {"status": "success", "hcp_id": new_hcp.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_with_agent(query: AgentQuery):
    """Passes messages directly to the LangGraph AI Agent, routing commands through the SQL tools."""
    inputs = {
        "messages": [("user", query.message)]
    }
    
    # Run the transaction workflow under a specific thread ID config
    config = {"configurable": {"thread_id": query.thread_id}}
    
    try:
        result = await compiled_agent.ainvoke(inputs, config=config)
        # Grab the content of the final agent response message
        final_msg = result["messages"][-1].content
        
        # Log conversational steps taken (useful for debugging UI execution state)
        history = []
        for msg in result["messages"]:
            history.append({
                "role": msg.type,
                "content": msg.content,
                "tool_calls": getattr(msg, "tool_calls", None)
            })
            
        return {
            "response": final_msg,
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Make sure GROQ_API_KEY is configured prior to booting
    if not os.getenv("GROQ_API_KEY"):
        print("WARNING: Please set the 'GROQ_API_KEY' environment variable.")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)