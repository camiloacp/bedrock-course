from strands import Agent
from strands.models.bedrock import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from inventory_tools import search_products, search_catalog

# 1) Modelo
model = BedrockModel(
    model_id="us.amazon.nova-pro-v1:0",
    max_tokens=2048,
)

# 2) Instrucciones del agente
SYSTEM_PROMPT = """
You are an e-commerce product assistant. Answer in the user's language.
- For inventory questions (products by brand, category or department, prices) use search_products.
- For questions about product descriptions or catalog information use search_catalog.
- Only answer from tool results. If nothing matches, say so instead of guessing.
"""

# 3) Punto de entrada para AgentCore Runtime
app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload):
    prompt = payload.get("prompt", "")

    # Agente = modelo + instrucciones + herramientas.
    # Se crea en cada petición: así no guarda historial entre mensajes ni entre usuarios.
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[search_products, search_catalog],
    )
    result = agent(prompt)
    return {"response": str(result)}


if __name__ == "__main__":
    app.run()
