import os
import json
from datetime import datetime
from typing import Annotated, Sequence, TypedDict
from pydantic import BaseModel, Field

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from database import SessionLocal, HCPProfile, Interaction

# --- LangGraph Agent State ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# --- AI Tool Definitions ---

@tool
def log_interaction(hcp_id: int, interaction_raw_text: str) -> str:
    """Logs a new communication interaction with an HCP. Summarizes the raw text, 
    extracts relevant clinical/business entities, and saves it in the database."""
    extraction_llm = ChatGroq(
        model_name="gemma2-9b-it", 
        temperature=0.1, 
        groq_api_key=os.getenv("GROQ_API_KEY")
    )
    
    extraction_prompt = (
        f"Analyze this healthcare interaction text: '{interaction_raw_text}'\n"
        "Provide a JSON response with exactly two keys:\n"
        "1. 'summary': A concise summary of the key discussion items.\n"
        "2. 'extracted_entities': A list of entities discussed (e.g., drug names, symptoms, trial IDs, requests).\n"
        "Output ONLY raw JSON."
    )
    
    try:
        response = extraction_llm.invoke(extraction_prompt)
        parsed = json.loads(response.content)
    except Exception:
        parsed = {
            "summary": interaction_raw_text[:200],
            "extracted_entities": []
        }

    db = SessionLocal()
    try:
        db_interaction = Interaction(
            hcp_id=hcp_id,
            summary=parsed.get("summary", ""),
            extracted_entities=json.dumps(parsed.get("extracted_entities", [])),
            notes=interaction_raw_text
        )
        db.add(db_interaction)
        db.commit()
        db.refresh(db_interaction)
        return f"Success: Logged interaction #{db_interaction.id} for HCP ID {hcp_id}."
    except Exception as e:
        return f"Database error: {str(e)}"
    finally:
        db.close()

@tool
def edit_interaction(interaction_id: int, new_notes: str) -> str:
    """Edits an existing interaction entry by updating its notes and regenerating its summary."""
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return f"Error: Interaction #{interaction_id} not found."
        
        interaction.notes = new_notes
        
        # Regenerate summary using LLM
        extraction_llm = ChatGroq(
            model_name="gemma2-9b-it", 
            temperature=0.1, 
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        response = extraction_llm.invoke(f"Summarize this updated text in 1-2 sentences: {new_notes}")
        interaction.summary = response.content.strip()
        
        db.commit()
        return f"Success: Interaction #{interaction_id} updated successfully."
    except Exception as e:
        return f"Error updating database: {str(e)}"
    finally:
        db.close()

@tool
def schedule_follow_up(interaction_id: int, follow_up_date_iso: str) -> str:
    """Schedules or updates a follow-up date (ISO format, e.g., 'YYYY-MM-DD') for a specific interaction."""
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return f"Error: Interaction #{interaction_id} not found."
        
        dt = datetime.fromisoformat(follow_up_date_iso)
        interaction.follow_up_date = dt
        db.commit()
        return f"Success: Follow-up for interaction #{interaction_id} scheduled for {follow_up_date_iso}."
    except Exception as e:
        return f"Error scheduling follow-up: {str(e)}"
    finally:
        db.close()

@tool
def view_hcp_profile(hcp_id: int) -> str:
    """Retrieves full profile information, credentials, and demographics for an HCP by their database ID."""
    db = SessionLocal()
    try:
        hcp = db.query(HCPProfile).filter(HCPProfile.id == hcp_id).first()
        if not hcp:
            return f"HCP Profile with ID {hcp_id} not found."
        return json.dumps({
            "id": hcp.id,
            "name": f"{hcp.first_name} {hcp.last_name}",
            "specialty": hcp.specialty,
            "hospital": hcp.hospital,
            "email": hcp.email,
            "phone": hcp.phone
        })
    finally:
        db.close()

@tool
def search_past_interactions(hcp_id: int, query: str) -> str:
    """Searches through past logged interactions for a specific HCP using a keyword match filter."""
    db = SessionLocal()
    try:
        results = db.query(Interaction).filter(
            Interaction.hcp_id == hcp_id,
            (Interaction.summary.ilike(f"%{query}%")) | (Interaction.notes.ilike(f"%{query}%"))
        ).all()
        
        if not results:
            return f"No matching past interactions found for HCP ID {hcp_id} with query '{query}'."
        
        records = []
        for r in results:
            records.append({
                "interaction_id": r.id,
                "summary": r.summary,
                "notes": r.notes,
                "logged_at": r.created_at.isoformat(),
                "follow_up": r.follow_up_date.isoformat() if r.follow_up_date else None
            })
        return json.dumps(records)
    finally:
        db.close()

# --- Graph Flow Construction ---

tools = [log_interaction, edit_interaction, schedule_follow_up, view_hcp_profile, search_past_interactions]
tool_node = ToolNode(tools)

# Initialize Groq LLM and bind tools
model = ChatGroq(
    model_name="gemma2-9b-it", 
    temperature=0, 
    groq_api_key=os.getenv("GROQ_API_KEY")
).bind_tools(tools)

# Conditional routing logic to determine next execution state
def should_continue(state: AgentState):
    messages = state['messages']
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END

# We added explicit system instructions here so the LLM knows it MUST call the tools
def call_model(state: AgentState):
    messages = state['messages']
    
    system_instruction = SystemMessage(
        content=(
            "You are an AI-first Healthcare CRM Assistant. "
            "When the user describes an interaction or meeting, you MUST call the log_interaction tool. "
            "When the user corrects a mistake or asks to edit details, you MUST call the edit_interaction tool. "
            "Do not talk to the user or greet them if they are describing an interaction. Instead, immediately call the tool."
        )
    )
    
    response = model.invoke([system_instruction] + list(messages))
    return {"messages": [response]}

# Assemble the StateGraph workflow
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

compiled_agent = workflow.compile()