import json
import boto3

# Corrección: Se eliminaron los espacios en el nombre de la variable
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

kb_id = "ECSKINQEOJ"
model_id = "amazon.nova-lite-v1:0"

model_arn = f'arn:aws:bedrock:us-east-1::foundation-model/{model_id}'
max_results = 3


default_prompt = """
You are a helpful assistant who helps users address questions related to AI. Only refer to the provided data while responding to the questions.
$search_results$
"""

def lambda_handler(event, context):
    print("Incoming event:", json.dumps(event))

    try:
        # Extraer el body de la petición (soporta API Gateway u origen directo)
        if event.get("body"):
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        else:
            body = event

        # Corrección: Se cambió el guion (-) por el signo de igual (=)
        query = body.get("query")
        
        if not query:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing 'query' in request"})
            }

        # Corrección: Se cerraron correctamente todas las llaves de los diccionarios
        response = bedrock_agent_runtime_client.retrieve_and_generate(
            input={
                'text': query
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kb_id,
                    'modelArn': model_arn,
                    'retrievalConfiguration': {
                        'vectorSearchConfiguration': {
                            'numberOfResults': max_results
                        }
                    },
                    'generationConfiguration': {
                        'promptTemplate': {
                            'textPromptTemplate': default_prompt
                        }
                    }
                }
            }
        )

        # Corrección: Se eliminaron los espacios extra en las llaves del diccionario
        generated_text = response['output']['text']

        return {
            "statusCode": 200,
            "body": json.dumps({"answer": generated_text})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }