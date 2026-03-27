import logging
import sys
from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from services.embedding_service import model
from services.qdrant_service import client as qdrant_client
from config import QDRANT_COLLECTION, OPENAI_API_KEY, ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL

# Attempt to import LLM providers
try:
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    logger.warning("LLM libraries not fully installed. Falling back to Mock mode.")

logger = logging.getLogger("aegis-agent")
logging.basicConfig(level=logging.INFO)

# Define the state for our LangGraph Agent
class AgentState(TypedDict):
    query: str
    context: str
    reasoning: str
    report: str
    iteration: int

def retrieve_context(state: AgentState):
    """
    Node: Semantic Search
    Queries the local Qdrant Vector DB via mathematical vector similarity.
    """
    logger.info(f"--- NODE: RETRIEVAL ---")
    logger.info(f"Querying Qdrant for: {state['query']}")
    
    # Generate vector for the user query
    query_vector = model.encode(state['query']).tolist()
    
    # Perform search
    search_result = qdrant_client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=query_vector,
        limit=5 
    )
    
    # Format the found chunks
    context_parts = []
    for hit in search_result:
        text = hit.payload.get('text', '')
        source = hit.payload.get('object_id', 'Unknown')
        context_parts.append(f"SOURCE [{source}]:\n{text}")
    
    full_context = "\n\n---\n\n".join(context_parts)
    return {"context": full_context, "iteration": state.get("iteration", 0) + 1}

def analyze_and_reason(state: AgentState):
    """
    Node: Reasoning & Intelligence
    Uses an LLM (if available) to synthesize the retrieved context into an answer.
    """
    logger.info(f"--- NODE: REASONING ---")
    
    context = state["context"]
    query = state["query"]
    
    if not context.strip():
        return {"reasoning": "No relevant data found in the Vector Database."}

    llm = None
    
    # 1. OpenRouter Detection & Logic
    # OpenRouter uses the OpenAI protocol for ALL models (Claude, Nemotron, etc.)
    if ANTHROPIC_API_KEY and "openrouter.ai" in ANTHROPIC_BASE_URL:
        logger.info(f"Using OpenRouter model '{ANTHROPIC_MODEL}'...")
        # Ensure base_url is exactly 'https://openrouter.ai/api/v1' for ChatOpenAI
        base_url = ANTHROPIC_BASE_URL.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url += "/v1"
            
        llm = ChatOpenAI(
            model=ANTHROPIC_MODEL,
            api_key=ANTHROPIC_API_KEY,
            base_url=base_url
        )
    
    # 2. Standard Anthropic Logic (Direct)
    elif ANTHROPIC_API_KEY:
        logger.info(f"Using direct Anthropic model '{ANTHROPIC_MODEL}'...")
        llm = ChatAnthropic(
            model=ANTHROPIC_MODEL, 
            api_key=ANTHROPIC_API_KEY,
            base_url=ANTHROPIC_BASE_URL
        )
        
    # 3. Standard OpenAI Logic (Direct)
    elif OPENAI_API_KEY:
        logger.info("Using direct OpenAI (GPT-4o-mini)...")
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)
    
    if llm:
        system_prompt = (
            "You are the Aegis Autonomous Intelligence Agent. Your job is to answer the user's "
            "question using ONLY the provided document context from our enterprise Qdrant database. "
            "If the answer is not in the context, say so. Be concise, technical, and professional."
        )
        user_prompt = f"CONTEXT:\n{context}\n\nUSER QUESTION: {query}"
        
        try:
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            return {"reasoning": response.content}
        except Exception as e:
            logger.error(f"LLM Reasoning Failed: {e}")
            return {"reasoning": f"Error during AI reasoning: {str(e)}"}
    
    # Fallback: Headless/Mock Reasoning (Useful for CI/CD or Local Dev without keys)
    logger.warning("No API Keys found. Generating a structural summary instead of AI reasoning.")
    mock_summary = f"Synthesized analysis of {len(context.split('---'))} retrieved document chunks."
    return {"reasoning": mock_summary}

def format_final_report(state: AgentState):
    """
    Node: Reporting
    Formats the final output for delivery (e.g., to a Slack hook, email, or CLI).
    """
    logger.info(f"--- NODE: REPORTING ---")
    
    report_header = "========================================\n"
    report_header += "       AEGIS INTELLIGENCE REPORT        \n"
    report_header += "========================================\n"
    
    final_report = f"{report_header}\nQUERY: {state['query']}\n\nANALYSIS:\n{state['reasoning']}\n\n[End of Report]"
    return {"report": final_report}

# Build the LangGraph
workflow = StateGraph(AgentState)

# Add nodes to the graph
workflow.add_node("retrieve", retrieve_context)
workflow.add_node("reason", analyze_and_reason)
workflow.add_node("report", format_final_report)

# Define the control flow (The State Machine)
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "reason")
workflow.add_edge("reason", "report")
workflow.add_edge("report", END)

# Compile the autonomous agent
autonomous_agent = workflow.compile()

def run_agent_cli():
    """CLI interface for the autonomous agent."""
    if len(sys.argv) < 2:
        print("\nUsage: python agent.py \"Your question here\"")
        print("Example: python agent.py \"How does Aegis handle Dead Letter Queues?\"\n")
        return

    query = sys.argv[1]
    print(f"\n[*] Aegis Agent waking up...")
    print(f"[*] Objective: {query}")
    
    initial_state = {"query": query, "iteration": 0}
    
    # Execute the graph
    try:
        final_state = autonomous_agent.invoke(initial_state)
        print("\n" + final_state["report"] + "\n")
    except Exception as e:
        logger.error(f"Agent Execution Failed: {e}")

if __name__ == "__main__":
    run_agent_cli()
