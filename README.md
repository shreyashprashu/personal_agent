# Personal Agent

A private, web-research assistant API. Phase 1 uses Azure Foundry's OpenAI-compatible Responses API with its built-in web search tool, LangGraph for the request workflow, and Azure Speech for optional spoken answers.

## Local development

1. Copy .env.example to .env.
2. Put only freshly rotated Azure credentials and a separate random ASSISTANT_API_KEY in .env. Never commit .env.
3. Fill in the Azure project endpoint, deployment name, and Speech region from the Azure portal.
4. Run:

    uv sync --locked
    uv run uvicorn personal_agent.app:agent_app --reload

Health:
- GET /health/live checks that the process is running.
- GET /health/ready checks required model and API-auth configuration.

Assistant:
- POST /v1/assistant/turn
- Send the caller key using the X-API-Key header.
- JSON body: {"query": "What are the latest AI news stories today?", "read_aloud": true}
- Response contains the answer, source citations, and optional base64-encoded audio/mpeg.

The API key that callers use is separate from Azure credentials. Do not expose this service publicly until TLS, API authentication, and key rotation are in place.

## Container image

Build from the repository root:

    docker build -t personal-agent:0.2.0 .

The image runs as a non-root user and listens on port 8000. It reads runtime configuration from environment variables; no credentials are baked into the image.

## Kubernetes

The initial manifest is deploy/k8s/app.yaml. It creates a single-replica Deployment and internal ClusterIP Service with probes and resource/security limits. It intentionally contains no Secret object or public Ingress.

Before applying it:
- Set non-secret values in the ConfigMap.
- Create the personal-agent-runtime Secret out of band with AZURE_AI_API_KEY, AZURE_SPEECH_KEY, and ASSISTANT_API_KEY.
- Build/import the image into the single-node k3s container runtime.
- Confirm /health/ready is healthy before exposing traffic.

Use kubectl port-forward for the first private smoke check. Add a TLS Ingress only after choosing a domain and certificate approach. A single-node k3s setup is useful for learning Kubernetes and running this personal service; it is not host-level high availability.

## Architecture notes

The web search tool is provided by the Azure Responses API in this first version. The graph only exposes that search capability; web pages cannot call arbitrary local tools. A separate MCP server integration remains a planned milestone and will use the current LangChain MCP API when added.
