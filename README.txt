RENDER SERVICE #1 SETUP

Create a NEW Render Web Service from this folder/repository.

Environment variables:
  OPENAI_API_KEY = your OpenAI API key
  MCP_SERVER_URL = https://mysql-mcp-server.onrender.com/mcp

Optional:
  MCP_AUTHORIZATION = OAuth/Bearer access token, if your MCP server requires it

Build command:
  pip install -r requirements.txt

Start command:
  uvicorn app:app --host 0.0.0.0 --port $PORT

After deployment:
  1. Open https://YOUR-SERVICE-1.onrender.com/
  2. You should see JSON with "status": "ok"
  3. Put that service URL into the Chrome extension's manifest.json and popup.js.
