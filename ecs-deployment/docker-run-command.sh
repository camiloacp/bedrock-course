# 1. Crear el repositorio en AWS ECR (si ya existe, ignorará este paso)
aws ecr create-repository --repository-name genai-apps --region us-east-1 || true

# 1. Construir la imagen con el nombre correcto
docker buildx build --provenance=false --platform linux/amd64 -t genai-meta-chatbot .

# 2. (Opcional) Probar localmente usando el mismo nombre
docker run -p 8501:8501 -v ~/.aws:/root/.aws genai-meta-chatbot

# 3. Autenticarse en AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin {id-account}.dkr.ecr.us-east-1.amazonaws.com

# 4. Asignar el tag correcto (corregido genai-meta-chatbot)
docker tag genai-meta-chatbot:latest {id-account}.dkr.ecr.us-east-1.amazonaws.com/genai-apps:genai-meta-chatbot

# 5. Subir la imagen a AWS ECR
docker push {id-account}.dkr.ecr.us-east-1.amazonaws.com/genai-apps:genai-meta-chatbot


# aws ecr batch-delete-image \
#     --repository-name genai-apps \
#     --image-ids imageDigest=sha256:df07b5746d6bc905ef30afc4dfcd02f608ee6fc5588d692523aba9617c60cd42 \
#     --region us-east-1

## No olvidar permisos de vps para peurto streamlit