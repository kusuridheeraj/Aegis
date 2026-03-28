import os
import logging
from typing import TypedDict, Annotated, List, Union
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Internal Aegis Services
from services.embedding_service import model as embedding_model
from services.qdrant_service import client as qdrant_client
from config import QDRANT_COLLECTION, ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize the "Brain" using OpenRouter (Gemma 3 27B)
# We use ChatOpenAI as a wrapper for OpenRouter compatibility
llm = ChatOpenAI(
    base_url=ANTHROPIC_BASE_URL,
    api_key=ANTHROPIC_API_KEY,
    model=ANTHROPIC_MODEL,
    temperature=0.1
)

# --- 1. Define State ---

class AgentState(TypedDict):
    """The persistent state of our autonomous agent."""
    query: str
    search_queries: List[str]
    context: str
    history: List[BaseMessage]
    summary: str
    iteration_count: int
    is_sufficient: bool

# --- 2. Define Nodes (The "Brain Cells") ---

def generate_search_query(state: AgentState):
    """Node: Analyzes the user query and generates optimized search terms."""
    logger.info("Node: Generating optimized search queries...")
    
    prompt = ChatPromptTemplate.from_messages([
        ("user", "INSTRUCTION: You are a search expert. Convert the user's question into 3 high-impact search terms for a vector database. Output ONLY the terms separated by commas. QUESTION: {query}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"query": state["query"]})
    queries = [q.strip() for q in response.content.split(",")]
    
    return {
        "search_queries": queries,
        "iteration_count": state.get("iteration_count", 0) + 1
    }

def retrieve_context(state: AgentState):
    """Node: Pulls data from Qdrant using the generated queries."""
    logger.info(f"Node: Retrieving context for queries: {state['search_queries']}")
    
    all_context = []
    for q in state["search_queries"]:
        vector = embedding_model.encode(q).tolist()
        hits = qdrant_client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=vector,
            limit=2
        )
        all_context.extend([h.payload.get("text") for h in hits])
    
    # Strategy C: Combine current hits with any existing summary
    combined_context = f"PREVIOUS SUMMARY: {state.get('summary', 'None')}\n\nNEW CONTEXT:\n" + "\n---\n".join(set(all_context))
    return {"context": combined_context}

def evaluate_context(state: AgentState):
    """Node: Checks if retrieved data actually answers the question (Self-Correction)."""
    logger.info("Node: Evaluating context sufficiency...")
    
    # If we've tried 3 times, stop looping to avoid token waste
    if state["iteration_count"] >= 3:
        return {"is_sufficient": True}
        
    prompt = f"""
    INSTRUCTION: Analyze the context below. Does it contain enough information to answer this question: '{state['query']}'?
    Respond ONLY with 'YES' or 'NO'.
    
    CONTEXT:
    {state['context']}
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    is_ok = "YES" in response.content.upper()
    return {"is_sufficient": is_ok}

def summarize_and_answer(state: AgentState):
    """Node: Synthesizes the final answer and updates the rolling summary."""
    logger.info("Node: Finalizing answer and updating summary...")
    
    # 1. Generate Final Answer
    answer_prompt = f"""
    INSTRUCTION: You are the Aegis Enterprise AI. Answer the question using the context provided.
    QUESTION: {state['query']}
    CONTEXT: {state['context']}
    """
    response = llm.invoke([HumanMessage(content=answer_prompt)])
    
    # 2. Strategy A: Generate a new summary for Strategy C storage
    summary_prompt = f"INSTRUCTION: Summarize the key facts from this interaction for long-term memory: {response.content}"
    new_summary = llm.invoke([HumanMessage(content=summary_prompt)]).content
    
    return {
        "history": state["history"] + [HumanMessage(content=state["query"]), AIMessage(content=response.content)],
        "summary": new_summary,
        "is_sufficient": True
    }

# --- 3. Build Graph ---

workflow = StateGraph(AgentState)

workflow.add_node("planner", generate_search_query)
workflow.add_node("retriever", retrieve_context)
workflow.add_node("evaluator", evaluate_context)
workflow.add_node("finalizer", summarize_and_answer)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "retriever")
workflow.add_edge("retriever", "evaluator")

# The Self-Correction Loop
workflow.add_conditional_edges(
    "evaluator",
    lambda x: "finalizer" if x["is_sufficient"] else "planner"
)
workflow.add_edge("finalizer", END)

# --- 4. Persistence Toggle (Redis vs Memory) ---

redis_url = os.getenv("REDIS_URL")
if redis_url:
    try:
        from langgraph.checkpoint.postgres import PostgresSaver # Simplified for now
        # Production Note: For true Redis persistence, we would use RedisSaver
        # For this local prototype, we use the robust MemorySaver but scaffold the check
        logger.info(f"Production Mode: Redis detected at {redis_url}")
        checkpointer = MemorySaver() 
    except:
        checkpointer = MemorySaver()
else:
    logger.info("Development Mode: Using In-Memory Persistence.")
    checkpointer = MemorySaver()

# Compile the Brain
aegis_brain = workflow.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    # Test the Autonomous Loop
    config = {"configurable": {"thread_id": "test_session_1"}}
    query = "What did Jennifer Doudna win in 2020?"
    
    print(f"\n--- Starting Autonomous Agent Run for: '{query}' ---")
    final_state = aegis_brain.invoke(
        {"query": query, "history": [], "summary": "", "iteration_count": 0},
        config=config
    )
    
    print("\n--- FINAL BRAIN RESPONSE ---")
    print(final_state["history"][-1].content)
    print(f"\n--- UPDATED LONG-TERM SUMMARY ---\n{final_state['summary']}")
