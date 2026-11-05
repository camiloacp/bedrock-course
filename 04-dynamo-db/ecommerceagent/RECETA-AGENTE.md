# Receta: agente de e-commerce en AgentCore

Un agente que responde preguntas sobre un inventario de productos. Tiene dos herramientas:

| Herramienta | Qué hace | De dónde saca los datos |
|---|---|---|
| `search_products` | Busca productos por marca, categoría o departamento | Tabla DynamoDB `product_inventory` |
| `search_catalog` | Responde con descripciones del catálogo | Knowledge Base de Bedrock |

**Tiempo estimado:** 1 hora. **Región:** `us-east-1` en toda la receta.

---

## Ingredientes

- Cuenta de AWS con permisos para DynamoDB, S3, Bedrock, IAM y CloudFormation.
- AWS CLI v2, Python 3.10+, Node.js y `uv`.
- Acceso a un modelo en Bedrock (ver el paso 0).
- Los archivos de la carpeta `04-dynamo-db/`:
  `01-generate_csv.py`, `02-ingest-dynamo.py`, `simulated_products.csv`
  y `brand-category-inventory-description.txt`.

---

## Paso 0: Credenciales y acceso al modelo

1. Crea un usuario IAM (no uses el usuario root) y genera sus access keys.
2. Configura el CLI y verifica:
   ```bash
   aws configure
   aws sts get-caller-identity
   ```
3. En la consola, abre **Bedrock → Model catalog** y confirma que puedes usar un modelo.
   - **Modelos de Anthropic (Claude):** AWS pide llenar un formulario de caso de uso. Tarda unos 15 minutos en activarse.
     Si no lo has llenado, las llamadas fallan con *"Model use case details have not been submitted"*.
   - **Amazon Nova:** funciona sin formulario. Esta receta usa `us.amazon.nova-pro-v1:0`.
4. Prueba el modelo desde la terminal:
   ```bash
   aws bedrock-runtime converse --region us-east-1 \
     --model-id us.amazon.nova-pro-v1:0 \
     --messages '[{"role":"user","content":[{"text":"hola"}]}]' \
     --inference-config '{"maxTokens":50}'
   ```

> Siempre fija `maxTokens`. Si no lo haces, el modelo reserva su máximo y puedes recibir errores de throttling.

---

## Paso 1: La tabla de DynamoDB

1. En la consola, **DynamoDB → Create table**:
   - Nombre: `product_inventory`
   - Partition key: `product_id` (String)
   - Sort key: `created_at_uuid` (String)
   - Capacidad: **On-demand**.

   Las llaves se deducen de cómo `02-ingest-dynamo.py` arma cada registro. Si la ingesta falla por las llaves, revisa ese script.
2. Genera los datos y cárgalos (desde `04-dynamo-db/`):
   ```bash
   python 01-generate_csv.py        # crea simulated_products.csv (500 productos)
   python 02-ingest-dynamo.py       # carga la tabla
   ```
3. Verifica:
   ```bash
   aws dynamodb scan --table-name product_inventory --max-items 1 --region us-east-1
   ```

---

## Paso 2: La Knowledge Base

1. Crea un bucket de S3 (el nombre debe ser único) y sube el catálogo:
   ```bash
   aws s3 mb s3://<tu-bucket> --region us-east-1
   aws s3 cp brand-category-inventory-description.txt s3://<tu-bucket>/
   ```
2. En la consola, **Bedrock → Knowledge bases → Create**:
   - Nombre: `ecommerce_product_information`
   - Fuente de datos: tu bucket de S3.
   - Modelo de embeddings: Titan Embeddings V2.
   - Vector store: la opción por defecto (OpenSearch Serverless).
3. Cuando termine de crearse, haz **Sync** de la fuente de datos. Sin sync las consultas devuelven vacío.
4. Anota el **Knowledge base ID**. Se usa en el paso 5.
5. Prueba la KB con **Test knowledge base** en la consola.

> **Costo:** OpenSearch Serverless cobra por hora mientras exista la colección, aunque nadie use la KB. Es el recurso más caro de esta receta. Borra la KB y su colección al terminar.

---

## Paso 3: Crear el proyecto del agente

Desde la carpeta donde quieras el proyecto:

```bash
npx -y @aws/agentcore@preview create \
  --project-name ecommerceagent --name ecommerceagent \
  --framework Strands --model-provider Bedrock \
  --memory none --protocol HTTP --build CodeZip --language Python
```

Esto genera la estructura:

```
ecommerceagent/
├── agentcore/
│   ├── agentcore.json        # qué se despliega (runtime, red, protocolo)
│   ├── aws-targets.json      # a qué cuenta y región se despliega
│   └── cdk/                  # infraestructura generada, no hace falta tocarla
└── app/ecommerceagent/
    ├── main.py               # el agente
    └── pyproject.toml        # dependencias de Python
```

Después borra del proyecto generado lo que no usaremos: la carpeta `mcp_client/`, la carpeta `skills/`, la carpeta `model/`, y la dependencia `mcp` del `pyproject.toml`. Luego ejecuta `uv lock` dentro de `app/ecommerceagent/`.

---

## Paso 4: Las herramientas

Crea `app/ecommerceagent/inventory_tools.py`. Cada herramienta es una función de Python con el decorador `@tool`.
**El docstring importa:** el modelo lo lee para decidir cuándo usar la herramienta.

```python
import os
import boto3
from strands import tool

REGION = "us-east-1"
KB_ID = os.environ.get("KB_ID", "<tu-knowledge-base-id>")

_table = boto3.resource("dynamodb", region_name=REGION).Table("product_inventory")
_kb = boto3.client("bedrock-agent-runtime", region_name=REGION)


@tool
def search_products(product_department: str = "", product_brand: str = "", product_category: str = "") -> dict:
    """Search the product inventory by department, brand and/or category.
    Use this for questions like "which Nike products do we have".
    At least one filter is required. Returns product names and retail prices.

    Args:
        product_department: Department name, e.g. "Men". Optional.
        product_brand: Brand name, e.g. "Sony". Optional.
        product_category: Category name, e.g. "Electronics". Optional.
    """
    department, brand, category = (s.strip().lower() for s in
                                   (product_department, product_brand, product_category))
    if not (department or brand or category):
        return {"error": "Provide at least one filter"}

    items, kwargs = [], {}
    while True:                                    # el scan lee máximo 1 MB: hay que paginar
        page = _table.scan(**kwargs)
        items += page.get("Items", [])
        if "LastEvaluatedKey" not in page:
            break
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    matched = [
        {"product_name": i["product_name"], "product_retail_price": float(i["product_retail_price"])}
        for i in items
        if (not department or i.get("product_department", "").lower() == department)
        and (not brand or i.get("product_brand", "").lower() == brand)
        and (not category or i.get("product_category", "").lower() == category)
    ]
    return {"total_matches": len(matched), "matched_products": matched[:25]}


@tool
def search_catalog(question: str) -> dict:
    """Search the product knowledge base for descriptions and general product information.

    Args:
        question: Natural language question or search text.
    """
    resp = _kb.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": question},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 5}},
    )
    return {"results": [{"text": r["content"]["text"]} for r in resp.get("retrievalResults", [])]}
```

---

## Paso 5: El agente (`main.py`)

Reemplaza el contenido de `app/ecommerceagent/main.py`. Tiene cuatro piezas: modelo, instrucciones, entrada y agente.

```python
from strands import Agent
from strands.models.bedrock import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from inventory_tools import search_products, search_catalog

# 1) Modelo
model = BedrockModel(model_id="us.amazon.nova-pro-v1:0", max_tokens=2048)

# 2) Instrucciones
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

    # 4) Agente = modelo + instrucciones + herramientas.
    # Se crea en cada petición para que no comparta historial entre usuarios.
    agent = Agent(model=model, system_prompt=SYSTEM_PROMPT,
                  tools=[search_products, search_catalog])
    return {"response": str(agent(prompt))}


if __name__ == "__main__":
    app.run()
```

> **Error común:** crear el `Agent` fuera de `invoke`. Entonces todas las sesiones comparten un único historial dentro de la misma instancia.

---

## Paso 6: Configurar el destino

Edita `agentcore/aws-targets.json` con tu cuenta (12 dígitos) y región:

```json
[{ "name": "default", "account": "<tu-account-id>", "region": "us-east-1" }]
```

> Este archivo contiene tu ID de cuenta. Agrégalo al `.gitignore` si el repo es público.

---

## Paso 7: Desplegar

Desde la carpeta `ecommerceagent/`:

```bash
npx -y @aws/agentcore@preview deploy -y
```

La primera vez prepara el bootstrap de CDK, un bucket de S3 y un repositorio de ECR. Tarda unos 3 minutos.
Al terminar muestra el **ARN del runtime** y el **nombre del rol** del agente. Anótalos.

---

## Paso 8: Dar permisos al rol del agente

El rol que crea el CLI solo puede invocar el modelo. Hay que permitirle leer la tabla y consultar la KB.
**Este paso es el que más se olvida:** sin él, el agente falla al usar las herramientas.

```bash
cat > policy.json <<'EOF'
{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":["dynamodb:Scan"],
  "Resource":"arn:aws:dynamodb:us-east-1:<tu-account-id>:table/product_inventory"},
 {"Effect":"Allow","Action":["bedrock:Retrieve"],
  "Resource":"arn:aws:bedrock:us-east-1:<tu-account-id>:knowledge-base/<tu-knowledge-base-id>"}]}
EOF

aws iam put-role-policy --role-name <nombre-del-rol-del-agente> \
  --policy-name ecommerce-tools-access --policy-document file://policy.json
```

---

## Paso 9: Probar

Desde la terminal:

```bash
npx -y @aws/agentcore@preview invoke --prompt "¿Qué productos Nike hay en el departamento Men? Dame 3 con precio."
npx -y @aws/agentcore@preview invoke --prompt "Según el catálogo, ¿qué es Running Shoes Max?"
```

Desde Python o un notebook:

```python
import boto3, json, uuid

client = boto3.client("bedrock-agentcore", region_name="us-east-1")
response = client.invoke_agent_runtime(
    agentRuntimeArn="<arn-del-runtime>",
    runtimeSessionId=str(uuid.uuid4()),          # mínimo 33 caracteres
    payload=json.dumps({"prompt": "¿Qué productos Sony hay en Electronics?"}).encode(),
)
print(json.loads(response["response"].read())["response"])
```

**Cómo saber que funciona:**
- La primera pregunta devuelve productos con precios reales de tu tabla.
- La segunda devuelve una descripción tomada del catálogo.

---

## Problemas conocidos

| Síntoma | Causa | Solución |
|---|---|---|
| *Bedrock Agents is in Maintenance Mode* | Los agentes clásicos de Bedrock ya no se crean en cuentas nuevas | Usa AgentCore, como en esta receta |
| *Model use case details have not been submitted* | Falta el formulario de Anthropic | Llénalo y espera 15 min, o usa Amazon Nova |
| El agente responde pero no encuentra productos o falla al usar una herramienta | Falta el paso 8 (permisos del rol) | Agrega la política inline |
| La KB devuelve resultados vacíos | No hiciste Sync de la fuente de datos | Haz Sync en la consola |
| *Profile bedrock could not be found* | Solo existe el perfil `default` | Usa `aws configure` sin `--profile`, o expórtalo con `AWS_PROFILE` |
| El agente "recuerda" entre usuarios | `Agent` creado fuera de `invoke` | Créalo dentro de `invoke` |
| Aparece `<thinking>…</thinking>` en la respuesta | Es el estilo de Nova Pro | Se quita al usar Claude |

---

## Paso final: Borrar todo (para no pagar)

Haz esto en orden. Cada paso se puede verificar con el comando `list` del servicio.

```bash
# 1. Política inline y stack del agente
aws iam delete-role-policy --role-name <nombre-del-rol-del-agente> --policy-name ecommerce-tools-access
aws cloudformation delete-stack --stack-name AgentCore-ecommerceagent-default

# 2. Knowledge Base (primero la fuente de datos, luego la KB)
aws bedrock-agent delete-data-source --knowledge-base-id <kb-id> --data-source-id <ds-id>
aws bedrock-agent delete-knowledge-base --knowledge-base-id <kb-id>

# 3. Colección de OpenSearch Serverless (es lo que más cuesta)
aws opensearchserverless list-collections
aws opensearchserverless delete-collection --id <collection-id>

# 4. Tabla de DynamoDB
aws dynamodb delete-table --table-name product_inventory

# 5. Buckets de S3 (el de datos, el de AgentCore y el de CDK)
aws s3 rb s3://<tu-bucket> --force
# El bucket de CDK tiene versionado: hay que borrar todas las versiones antes de borrarlo.

# 6. Bootstrap de CDK
aws ecr delete-repository --repository-name cdk-hnb659fds-container-assets-<account>-us-east-1 --force
aws cloudformation delete-stack --stack-name CDKToolkit
```

Revisa también:
- Log groups de CloudWatch del agente (`/aws/bedrock-agentcore/runtimes/...`).
- Roles y políticas de IAM que dejó la KB (`AmazonBedrockExecutionRoleForKnowledgeBase_*`).
- El deploy activa **CloudWatch Transaction Search** en la cuenta y borrar el stack no lo apaga.

---

## Siguientes pasos (para complicarlo poco a poco)

1. **Memoria:** hoy el agente no recuerda mensajes anteriores. Agrega AgentCore Memory (`--memory shortTerm`).
2. **Streaming:** devuelve la respuesta por partes en vez de esperar a que termine.
3. **Más herramientas:** por ejemplo consultar el stock o crear pedidos.
4. **Gateway / Lambda:** mueve una herramienta a una Lambda detrás de un AgentCore Gateway, para reusarla desde otros agentes.
5. **Guardrails:** filtra temas fuera de alcance. Hoy el agente responde preguntas ajenas al inventario.
6. **Pasar a Claude:** cambia el `model_id` cuando tengas el formulario de Anthropic aprobado.
