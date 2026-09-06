import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")

MCP_SERVER_URL = os.environ.get(
    "MCP_SERVER_URL",
    "https://mysql-mcp-server.onrender.com/mcp"
)
MCP_AUTHORIZATION = os.environ.get("MCP_AUTHORIZATION")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable is required.")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Chrome → OpenAI → MCP Gateway")

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
        "model": OPENAI_MODEL,
        "mcp_server": MCP_SERVER_URL
    }

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "table": {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "rows": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    },
                    "required": ["title", "columns", "rows"],
                    "additionalProperties": False
                },
                {"type": "null"}
            ]
        }
    },
    "required": ["answer", "table"],
    "additionalProperties": False
}

@app.post("/ask")
def ask(req: AskRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    mcp_tool = {
        "type": "mcp",
        "server_label": "mysql_mcp",
        "server_description": (
            "A read-only MySQL MCP server that can list tables, "
            "describe table structures, and run SELECT queries."
        ),
        "server_url": MCP_SERVER_URL,
        "require_approval": "never"
    }

    if MCP_AUTHORIZATION:
        mcp_tool["authorization"] = MCP_AUTHORIZATION

    instructions = """
You are a database assistant connected to MySQL through MCP tools.

Rules:
1. For questions about database contents, schemas, tables, columns, or rows,
   use the MCP tools rather than guessing.
2. Never invent table names, column names, values, totals, or query results.
3. If data is naturally tabular, return it in the `table` object.
4. The `columns` array contains column headings.
5. Every row must contain values in the same order as `columns`.
6. Convert all table cell values to strings. Represent SQL NULL as an empty string.
7. If the answer is not naturally tabular, set `table` to null.
8. Keep `answer` brief when the table already contains the result.
9. Do not put a Markdown table inside `answer`; the UI renders the table separately.
"""

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=instructions,
            tools=[mcp_tool],
            input=question,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "database_answer",
                    "strict": True,
                    "schema": ANSWER_SCHEMA
                }
            }
        )

        raw = response.output_text
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"answer": raw, "table": None}

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
