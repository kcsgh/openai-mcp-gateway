import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MCP_SERVER_URL = os.environ.get(
    "MCP_SERVER_URL",
    "https://mysql-mcp-server.onrender.com/mcp"
)
MCP_AUTHORIZATION = os.environ.get("MCP_AUTHORIZATION")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable is required.")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Chrome → OpenAI → MCP Gateway")

# Prototype setting. Tighten CORS after the extension ID is stable.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    question: str

@app.get("/")
def health():
    return {
        "status": "ok",
        "mcp_server": MCP_SERVER_URL
    }

@app.post("/ask")
def ask(req: AskRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    mcp_tool = {
        "type": "mcp",
        "server_label": "mysql_mcp",
        "server_description": "Remote MCP server that exposes tools for the user's MySQL database.",
        "server_url": MCP_SERVER_URL,
        "require_approval": "never"
    }

    # If your MCP server requires an OAuth bearer access token,
    # set MCP_AUTHORIZATION in Render.
    if MCP_AUTHORIZATION:
        mcp_tool["authorization"] = MCP_AUTHORIZATION

    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            tools=[mcp_tool],
            input=question
        )
        return {"answer": response.output_text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
