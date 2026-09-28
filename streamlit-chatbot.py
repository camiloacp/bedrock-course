import streamlit as st
import boto3
import json

# Inicializa el cliente de Bedrock
client_bedrock = boto3.client('bedrock-runtime')

def call_bedrock(prompt: str) -> str:
    """
    Llama al modelo de Bedrock y devuelve el texto de respuesta generado.
    """
    # Para los modelos "Instruct" de Llama, es una buena práctica usar sus etiquetas de chat
    # para que el modelo sepa cuándo habla el usuario y cuándo el asistente.
    formatted_prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"

    response = client_bedrock.invoke_model(
        contentType='application/json',
        modelId="us.meta.llama4-maverick-17b-instruct-v1:0",
        body=json.dumps({
            "prompt": formatted_prompt,
            "temperature": 0.9,
            "top_p": 0.75,
            "max_gen_len": 200  # Cambia max_tokens por max_gen_len para modelos Meta
        })
    )
    
    response_body = response["body"].read() 
    result = json.loads(response_body) 
    
    # Los modelos de Meta en Bedrock devuelven la respuesta en la clave "generation"
    if "generation" in result: 
        return result["generation"]
    
    return str(result)

# ========================================================= 
# CONFIGURACIÓN 
# ========================================================= 

st.set_page_config(
    page_title="Mi Chatbot", 
    page_icon="🤖", 
    layout="centered", 
    initial_sidebar_state="expanded"
)

st.title("Bedrock Chatbot - Meta Llama")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.form(key="chat_form"):
    user_input = st.text_input("You:")
    submitted = st.form_submit_button("Send")

    if submitted and user_input:
        # Guardamos el mensaje del usuario
        st.session_state.chat_history.append(("User", user_input))

        # Llamamos al modelo solo cuando se envía el formulario
        try:
            bot_response = call_bedrock(user_input)
        except Exception as e:
            bot_response = f"Error calling Bedrock model: {e}"
        
        # Guardamos la respuesta del bot
        st.session_state.chat_history.append(("Bot", bot_response))

st.markdown("### Conversation History")
for speaker, message in st.session_state.chat_history:
    st.markdown(f" **{speaker}:** {message}")