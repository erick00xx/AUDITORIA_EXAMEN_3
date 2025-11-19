# backend/main.py
import sqlite3
import re
import sys 
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal

# --- Importaciones para Monitorización ---
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

# --- CONFIGURACIÓN DE LOGGING ESTRUCTURADO ---
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


# --- CONFIGURACIÓN GENERAL ---
VECTOR_STORE_DIR = "vector_store"
DB_PATH = "tickets.db"
app = FastAPI(title="Corporate EPIS Pilot API - Advanced Flow")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- INSTRUMENTACIÓN DE PROMETHEUS ---
Instrumentator().instrument(app).expose(app)

# --- MODELOS E IA (AJUSTADO PARA SMOLLM) ---
# 1. Usamos el modelo solicitado
llm = OllamaLLM(model="smollm:360m", temperature=0, base_url="http://host.docker.internal:11434")

embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")
vector_store = Chroma(persist_directory=VECTOR_STORE_DIR, embedding_function=embeddings)

# 2. OPTIMIZACIÓN: k=2
# Solo recuperamos los 2 fragmentos más relevantes para no saturar al modelo pequeño.
retriever = vector_store.as_retriever(search_kwargs={"k": 2})

# 3. PROMPT ESTRICTO (ANTI-ALUCINACIONES)
rag_prompt_template = """Eres un asistente de soporte técnico útil y directo.
Usa SOLO el siguiente contexto para responder a la pregunta.
Si la respuesta no está en el contexto, di "No tengo información suficiente en mis documentos".
Responde SIEMPRE en Español. Sé conciso (máximo 2 frases).

Contexto:
{context}

Pregunta: {question}
Respuesta:"""

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

# --- DEFINICIONES DEL ROUTER ANTIGUO (Se mantienen para evitar errores de importación) ---
class RouteQuery(BaseModel):
    intent: Literal["pregunta_general", "reporte_de_problema", "despedida"] = Field(description="La intención del usuario.")

output_parser = JsonOutputParser(pydantic_object=RouteQuery)

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
    if not match and len(text) < 20:
        return '{"intent": "despedida"}'
    return match.group(0) if match else '{"intent": "pregunta_general"}'

router_chain = router_prompt | llm | RunnableLambda(extract_json_from_string) | output_parser
chain_with_preserved_input = RunnablePassthrough.assign(decision=router_chain)
problem_chain = RunnableLambda(lambda x: {"query": x["question"]}) | rag_chain


# --- ENDPOINT ACTUALIZADO (ROBUST FOR SMOLLM) ---
@app.get("/ask")
def ask_question(question: str):
    try:
        # 1. DETECCIÓN RÁPIDA DE TICKET (Sin IA)
        if question.startswith("ACTION_CREATE_TICKET:"):
            description = question.split(":", 1)[1]
            return {"answer": create_support_ticket(description), "follow_up_required": False}

        # 2. ROUTER MANUAL (Sin IA - Instantáneo)
        # Reemplazo del LLM Router para evitar Timeouts y errores JSON con Smollm
        q_lower = question.lower()
        intent = "pregunta_general" # Por defecto

        # Palabras clave para detectar problemas
        if any(x in q_lower for x in ["problema", "error", "falla", "no funciona", "roto", "apaga", "enciende", "pantalla", "impresora", "red", "lento"]):
            intent = "reporte_de_problema"
        # Palabras clave para despedidas
        elif any(x in q_lower for x in ["gracias", "adios", "adiós", "chau", "hasta luego", "listo"]):
            intent = "despedida"

        # 3. GENERACIÓN DE RESPUESTA
        answer = ""
        follow_up = False
        
        # Simulamos la estructura de entrada que espera la cadena RAG
        rag_input = {"decision": {"intent": intent}, "question": question}

        logger.info(f"Intención detectada (Manual): {intent}")

        if intent == "pregunta_general":
            result = problem_chain.invoke(rag_input)
            answer = result.get("result", "No se encontró respuesta.")
        elif intent == "reporte_de_problema":
            result = problem_chain.invoke(rag_input)
            solution = result.get("result", "No he encontrado una solución específica.")
            answer = f"{solution}\n\n¿Esta información soluciona tu problema?"
            follow_up = True
        elif intent == "despedida":
            answer = "De nada, ¡un placer ayudar! Si tienes cualquier otra consulta, aquí estaré. 😊"
            follow_up = False
            
        return {"answer": answer, "follow_up_required": follow_up}

    except Exception as e:
        logger.error(f"Error critico en el endpoint /ask: {e}")
        return {"answer": "Lo siento, ha ocurrido un error interno en el servidor.", "follow_up_required": False}


# -------------------------------------------------------------------------
# --- VERSIÓN ANTIGUA DEL ENDPOINT (COMENTADA POR COMPATIBILIDAD/BACKUP) ---
# -------------------------------------------------------------------------
# @app.get("/ask_old_version") 
# def ask_question_legacy(question: str):
#     try:
#         if question.startswith("ACTION_CREATE_TICKET:"):
#             description = question.split(":", 1)[1]
#             return {"answer": create_support_ticket(description), "follow_up_required": False}
#
#         # Esta versión usaba el Router del LLM, que falla con modelos pequeños
#         decision_result = chain_with_preserved_input.invoke({"question": question})
#         intent = decision_result["decision"]["intent"]
#         
#         answer = ""
#         follow_up = False
#
#         if intent == "pregunta_general":
#             result = problem_chain.invoke(decision_result)
#             answer = result.get("result", "No se encontró respuesta.")
#         elif intent == "reporte_de_problema":
#             result = problem_chain.invoke(decision_result)
#             solution = result.get("result", "No he encontrado una solución específica en mis documentos.")
#             answer = f"{solution}\n\n¿Esta información soluciona tu problema?"
#             follow_up = True
#         elif intent == "despedida":
#             answer = "De nada, ¡un placer ayudar! Si tienes cualquier otra consulta, aquí estaré. 😊"
#             follow_up = False
#             
#         return {"answer": answer, "follow_up_required": follow_up}
#
#     except Exception as e:
#         logger.error(f"Error en el endpoint /ask (legacy): {e}")
#         return {"answer": "Lo siento, ha ocurrido un error.", "follow_up_required": False}