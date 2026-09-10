import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import ChatRequest, ChatResponse, ToolCallLog, ResetRequest

# LLM_PROVIDER = "anthropic" (Claude API, needs ANTHROPIC_API_KEY) or
# "ollama" (local model via a running `ollama serve`, needs OLLAMA_MODEL).
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic").lower()

if LLM_PROVIDER == "ollama":
    import agent_ollama as agent
else:
    import agent

app = FastAPI(
    title="AI E-Commerce Customer Support Agent",
    description="Agentic AI backend for automated customer support.",
    version="1.0.0",
)

# Allow the local static frontend (and any dev server) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "llm_provider": LLM_PROVIDER}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    result = agent.handle_message(req.session_id, req.message)

    return ChatResponse(
        session_id=req.session_id,
        reply=result["reply"],
        escalated=result["escalated"],
        tool_calls=[ToolCallLog(**tc) for tc in result["tool_calls"]],
    )


@app.post("/reset")
def reset(req: ResetRequest):
    agent.reset_session(req.session_id)
    return {"status": "reset", "session_id": req.session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
