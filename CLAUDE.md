The project: Trove, a local LLM AI agent for non-technical users powered by the new Gemma 4 models.

The focuses: accessibility, reach, overcoming the digital divide and empowering non-technical users in facilities like schools, care homes, prisons etc to access the power of AI for simple tasks.

Core ideas:

* ability to define unitary tasks - a single prompt, structured inputs and optionally outputs. No iteration. We are working with short context windows and relatively less powerful models

* multimodal inputs (images and audio allowed)

* no-code. The user only types in a prompt, adds arguments (Jinja template syntax, possibly aided via UI) and then the agent is programmatically constructed

* document archiving supported. MCP server with documents uploaded by the user, and the AI itself can generate classification taglines. MCP organised in folders/subfolders, with each task given optional access to only some of them (configurable)

* server-client architecture. One single server operating on a more powerful machine on a local network. Every other device (mobile etc) connects via that network. Some configuration required (fixed IP etc) but once it's set up, it just works. There is a server application and a mobile-first client

Tech stack:

Ollama for model running (automate the set up)
Python for serving
Pydantic AI for agentic workflows
Markitdown for converting documents in different formats to text for addition to the MCP
App framework for the clients to decide - can we use something like Streamlit or is it too constraining? Should we go full client-server with FastAPI + React Native frontend?

Read the document in tmp_docs/ for a more in depth discussion.