import base64
import datetime
import json
import boto3
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Generador de Imágenes con Bedrock y S3", page_icon="🎨", layout="centered"
)

st.title("🎨 Generador de Imágenes con AWS Bedrock y S3")
st.write(
    "Introduce un prompt para generar una imagen usando **Stable Diffusion 3.5 Large** y guárdala directamente en tu bucket de Amazon S3."
)

# Entrada del usuario para el prompt
prompt = st.text_area(
    "¿Qué imagen te gustaría generar?",
    value="Spiderman fight in a subway with doctor octopus and green goblin",
    height=100,
)

# Nombre del bucket (ajusta el tuyo si es necesario)
bucket_name = st.text_input(
    "Nombre del S3 Bucket", value="851725222540-nl-demo-bedrock"
)
region_bedrock = "us-west-2"

if st.button("🚀 Generar y Guardar en S3", type="primary"):
  if not prompt.strip():
    st.warning("Por favor, introduce un prompt válido.")
  else:
    with st.spinner("Generando imagen con Bedrock y subiendo a S3..."):
      try:
        # 1. Inicializar clientes de AWS
        client_bedrock = boto3.client(
            "bedrock-runtime", region_name=region_bedrock
        )
        client_s3 = boto3.client("s3")

        # 2. Invocar el modelo Stable Diffusion 3.5 Large
        response_bedrock = client_bedrock.invoke_model(
            modelId="stability.sd3-5-large-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "prompt": prompt,
                "mode": "text-to-image",
                "aspect_ratio": "1:1",
                "output_format": "jpeg",
                "seed": 0,
            }),
        )

        # Extraer los bytes de la imagen
        response_body = json.loads(response_bedrock["body"].read())
        
        # 1. Verificamos si AWS realmente nos devolvió la imagen
        if "images" not in response_body or not response_body["images"]:
            # Si no hay imagen, mostramos el error real de AWS en rojo y detenemos el código
            st.error(f"AWS bloqueó el prompt o falló. Respuesta de Bedrock: {response_body}")
            st.stop()
            
        # 2. Si todo salió bien, decodificamos la imagen
        response_bedrock_base64 = response_body["images"][0]
        response_bedrock_finalimage = base64.b64decode(response_bedrock_base64)

        # 3. Asegurar que el bucket existe (opcional, por si acaso)
        try:
          client_s3.create_bucket(Bucket=bucket_name)
        except Exception:
          pass  # Si ya existe o es tuyo, continuamos

        # 4. Definir la ruta y subir la imagen
        image_name = (
            "generated_images/"
            + datetime.datetime.now().strftime("%Y-%m-sd-%H-%M-%S")
            + ".png"
        )

        client_s3.put_object(
            Bucket=bucket_name,
            Body=response_bedrock_finalimage,
            Key=image_name,
            ContentType="image/png",
        )

        # 5. Generar la URL temporal (presigned URL)
        presigned_url = client_s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": image_name},
            ExpiresIn=3600,
        )

        st.success("¡Imagen generada y subida con éxito!")

        # Mostrar resultados en la interfaz
        st.image(
            response_bedrock_finalimage,
            caption=f"Prompt: {prompt}",
            use_container_width=True,
        )

        st.markdown("### 🔗 URL Temporal de S3")
        st.code(presigned_url, language="text")
        st.markdown(
            f"[Abrir imagen en S3 (Enlace directo)]({presigned_url})",
            unsafe_allow_html=True,
        )

      except Exception as e:
        st.error(f"Ocurrió un error al procesar la solicitud: {e}")