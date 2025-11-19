# backend/main.py
import sqlite3
import re
import sys 
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal

# --- AÑADIDO: Importaciones para Monitorización ---
from prometheus_fastapi_instrumentator import Instrumentator
from loguru import logger

# LangChain
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_ollama.llms import OllamaLLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough

# --- AÑADIDO: CONFIGURACIÓN DE LOGGING ESTRUCTURADO ---
logger.remove()
logger.add(sys.stdout, serialize=True, enqueue=True)

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.log(level, record.getMessage())

logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
logging.getLogger("uvicorn").handlers = [InterceptHandler()]
logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]


# --- CONFIGURACIÓN Y MODELOS ---
VECTOR_STORE_DIR = "vector_store"
DB_PATH = "tickets.db"
app = FastAPI(title="Corporate EPIS Pilot API - Advanced Flow")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- AÑADIDO: INSTRUMENTACIÓN DE PROMETHEUS ---
Instrumentator().instrument(app).expose(app)


llm = OllamaLLM(model="llama3.1:8b", temperature=0, base_url="http://host.docker.internal:11434")
embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")
vector_store = Chroma(persist_directory=VECTOR_STORE_DIR, embedding_function=embeddings)
retriever = vector_store.as_retriever()

# --- LÓGICA DE LANGCHAIN (MODIFICADA) ---
rag_prompt_template = "Usa el siguiente contexto para responder en español de forma concisa y útil a la pregunta.\nContexto: {context}\nPregunta: {question}\nRespuesta:"
rag_prompt = PromptTemplate.from_template(rag_prompt_template)
rag_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, chain_type_kwargs={"prompt": rag_prompt})

def create_support_ticket(description: str) -> str:
    """Crea un ticket de soporte y devuelve un mensaje de confirmación."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    problem_description = description.replace("ACTION_CREATE_TICKET:", "").strip()
    if not problem_description:
        problem_description = "Problema no especificado por el usuario."

    cursor.execute("INSERT INTO tickets (description, status) VALUES (?, ?)", (problem_description, "Abierto"))
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return f"De acuerdo. He creado el ticket de soporte #{ticket_id} con tu problema: '{problem_description}'. El equipo técnico se pondrá en contacto contigo."

# El router ahora es más simple
# CAMBIO 1: Añadimos la nueva intención 'despedida'
class RouteQuery(BaseModel):
    intent: Literal["pregunta_general", "reporte_de_problema", "despedida"] = Field(description="La intención del usuario.")

output_parser = JsonOutputParser(pydantic_object=RouteQuery)
# CAMBIO 2: Actualizamos el prompt para que el LLM sepa qué es una 'despedida'
router_prompt = PromptTemplate(
    template="""
    Clasifica la pregunta del usuario en 'pregunta_general', 'reporte_de_problema' o 'despedida'. Responde solo con JSON.
    'pregunta_general': El usuario pide información (¿qué es?, ¿cuántos?, ¿cómo?).
    'reporte_de_problema': El usuario describe un problema, algo está roto o no funciona.
    'despedida': El usuario expresa gratitud o se despide (gracias, adiós, perfecto, vale).
    Pregunta: {question}
    Formato: {format_instructions}
    """,
    input_variables=["question"],
    partial_variables={"format_instructions": output_parser.get_format_instructions()},
)
def extract_json_from_string(text: str) -> str:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    # Si no encuentra JSON o la pregunta es muy corta, es probable que sea una despedida
    if not match and len(text) < 20:
        return '{"intent": "despedida"}'
    return match.group(0) if match else '{"intent": "pregunta_general"}'

router_chain = router_prompt | llm | RunnableLambda(extract_json_from_string) | output_parser

chain_with_preserved_input = RunnablePassthrough.assign(decision=router_chain)

problem_chain = RunnableLambda(lambda x: {"query": x["question"]}) | rag_chain

# --- ENDPOINT DE LA API (MODIFICADO) ---
@app.get("/ask")
def ask_question(question: str):
    try:
        if question.startswith("ACTION_CREATE_TICKET:"):
            description = question.split(":", 1)[1]
            return {"answer": create_support_ticket(description), "follow_up_required": False}

        decision_result = chain_with_preserved_input.invoke({"question": question})
        intent = decision_result["decision"]["intent"]
        
        answer = ""
        follow_up = False

        if intent == "pregunta_general":
            result = problem_chain.invoke(decision_result)
            answer = result.get("result", "No se encontró respuesta.")
        elif intent == "reporte_de_problema":
            result = problem_chain.invoke(decision_result)
            solution = result.get("result", "No he encontrado una solución específica en mis documentos.")
            answer = f"{solution}\n\n¿Esta información soluciona tu problema?"
            follow_up = True
        # CAMBIO 3: Añadimos el manejo de la nueva intención
        elif intent == "despedida":
            answer = "De nada, ¡un placer ayudar! Si tienes cualquier otra consulta, aquí estaré. 😊"
            follow_up = False
            
        return {"answer": answer, "follow_up_required": follow_up}

    except Exception as e:
        # AÑADIDO: Usamos logger en lugar de print para un registro estructurado
        logger.error(f"Error en el endpoint /ask: {e}")
        return {"answer": "Lo siento, ha ocurrido un error.", "follow_up_required": False}