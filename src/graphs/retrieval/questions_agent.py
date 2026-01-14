"""Questions retrieval sub-agent.

This sub-agent retrieves practice questions from the knowledge base.
Currently mocked for hackathon P0.
"""

import json
from typing import Any, Dict, List

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

from src.graphs.state import GraphState, Message
from src.graphs.utils.messages import create_tool_message


# Mock questions data for P0
MOCK_QUESTIONS = [
    {
        "id": "q1",
        "topic": "história",
        "question": "Em que ano Pedro Álvares Cabral chegou ao território que hoje conhecemos como Brasil?",
        "alternatives": [
            "A) 1492",
            "B) 1500",
            "C) 1530",
            "D) 1822"
        ],
        "correct_answer": "B",
        "explanation": "A esquadra de Pedro Álvares Cabral chegou ao Brasil em 22 de abril de 1500."
    },
    {
        "id": "q2",
        "topic": "história",
        "question": "Qual era o principal objetivo oficial da esquadra de Cabral ao zarpar de Portugal?",
        "alternatives": [
            "A) Explorar o interior da Amazônia",
            "B) Colonizar a região do Rio da Prata",
            "C) Estabelecer uma rota comercial com as Índias",
            "D) Encontrar ouro nas Minas Gerais"
        ],
        "correct_answer": "C",
        "explanation": "O objetivo principal da expedição era seguir para as Índias para estabelecer relações comerciais e trazer especiarias."
    },
    {
        "id": "q3",
        "topic": "história",
        "question": "Qual foi o primeiro nome dado pelos portugueses à terra descoberta, antes de ser chamada de Brasil?",
        "alternatives": [
            "A) Ilha de Vera Cruz",
            "B) Terra de Santa Cruz",
            "C) Província de São Vicente",
            "D) Capitania Geral"
        ],
        "correct_answer": "A",
        "explanation": "Inicialmente, acreditando tratar-se de uma ilha, os portugueses chamaram a terra de Ilha de Vera Cruz."
    },
    {
        "id": "q4",
        "topic": "história",
        "question": "Quem era o rei de Portugal na época do descobrimento do Brasil?",
        "alternatives": [
            "A) D. Pedro II",
            "B) D. João VI",
            "C) D. Manuel I",
            "D) D. Afonso Henriques"
        ],
        "correct_answer": "C",
        "explanation": "D. Manuel I, o Venturoso, era o monarca português no ano de 1500."
    },
    {
        "id": "q5",
        "topic": "história",
        "question": "A famosa carta que relatava o descobrimento ao rei de Portugal foi escrita por quem?",
        "alternatives": [
            "A) Pedro Álvares Cabral",
            "B) Pero Vaz de Caminha",
            "C) Américo Vespúcio",
            "D) Fernão de Magalhães"
        ],
        "correct_answer": "B",
        "explanation": "Pero Vaz de Caminha era o escrivão da frota e escreveu a detalhada carta relatando o achamento da terra."
    },
    {
        "id": "q6",
        "topic": "história",
        "question": "Qual foi o primeiro recurso natural explorado intensivamente pelos portugueses no litoral brasileiro?",
        "alternatives": [
            "A) Cana-de-açúcar",
            "B) Ouro",
            "C) Pau-brasil",
            "D) Café"
        ],
        "correct_answer": "C",
        "explanation": "O pau-brasil, madeira que fornecia um pigmento vermelho muito valorizado na Europa, foi o primeiro foco de exploração."
    },
    {
        "id": "q7",
        "topic": "história",
        "question": "Como se chamava o primeiro monte avistado pela esquadra de Cabral ao se aproximar do litoral?",
        "alternatives": [
            "A) Pão de Açúcar",
            "B) Monte Pascoal",
            "C) Pico da Neblina",
            "D) Morro do Chapéu"
        ],
        "correct_answer": "B",
        "explanation": "O monte foi batizado de Monte Pascoal por ter sido avistado na época da Páscoa."
    },
    {
        "id": "q8",
        "topic": "história",
        "question": "Que povo indígena habitava majoritariamente o litoral brasileiro no momento da chegada dos portugueses?",
        "alternatives": [
            "A) Incas",
            "B) Astecas",
            "C) Tupis/Tupinambás",
            "D) Maias"
        ],
        "correct_answer": "C",
        "explanation": "Os povos de tronco linguístico Tupi, como os Tupinambás, eram os principais habitantes do litoral em 1500."
    },
    {
        "id": "q9",
        "topic": "história",
        "question": "Quantas embarcações faziam parte da frota original liderada por Pedro Álvares Cabral?",
        "alternatives": [
            "A) 3",
            "B) 7",
            "C) 13",
            "D) 20"
        ],
        "correct_answer": "C",
        "explanation": "A esquadra de Cabral era composta por 13 embarcações (9 naus, 3 caravelas e 1 naveta de mantimentos)."
    },
    {
        "id": "q10",
        "topic": "história",
        "question": "Em que local do atual estado da Bahia a esquadra de Cabral aportou pela primeira vez?",
        "alternatives": [
            "A) Salvador",
            "B) Porto Seguro (Cabrália)",
            "C) Ilhéus",
            "D) Itacaré"
        ],
        "correct_answer": "B",
        "explanation": "A frota ancorou primeiro na região de Porto Seguro, especificamente na Baía de Cabrália."
    }
]


def _mock_retrieve(query: str) -> List[Dict[str, Any]]:
    """Mock retrieve function for questions.
    
    In production, this would query MongoDB/vector search.
    
    Args:
        query: Search query
        
    Returns:
        List of matching questions as JSON
    """
    query_lower = query.lower()
    
    # Simple keyword matching for mock
    results = []
    for q in MOCK_QUESTIONS:
        if (query_lower in q["topic"].lower() or 
            query_lower in q["question"].lower()):
            results.append(q)
    
    # If no matches, return first question as fallback
    if not results:
        results = [MOCK_QUESTIONS[0]]
    
    return results


async def retrieve_questions_node(state: GraphState) -> GraphState:
    """Node that retrieves questions based on the query.
    
    This is the core retrieval logic. It:
    1. Parses the query from the tool call
    2. Calls the (mocked) retrieve function
    3. Returns the results as a tool message
    
    The intermediate retrieve calls stay local - only the final
    output is written to global messages.
    """
    messages = state["conversation_state"]["messages"]
    
    # Get the tool call that routed here
    assistant_msg = None
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            assistant_msg = msg
            break
    
    if not assistant_msg:
        # No tool call found, create error response
        error_msg = create_tool_message(
            content=json.dumps({"error": "No query provided"}),
            role="tool",
            name="routeToQuestions"
        )
        state["conversation_state"]["messages"].append(error_msg)
        return state
    
    # Parse the query
    tool_call = assistant_msg["tool_calls"][0]
    tool_call_id = tool_call["id"]
    arguments = json.loads(tool_call["function"]["arguments"])
    query = arguments.get("query", "")
    
    # Call mocked retrieve
    results = _mock_retrieve(query)
    
    # Create tool response with retrieved questions
    tool_response = create_tool_message(
        content=json.dumps(results, ensure_ascii=False, indent=2),
        role="tool",
        tool_call_id=tool_call_id,
        name="routeToQuestions"
    )
    
    state["conversation_state"]["messages"].append(tool_response)
    return state


def get_questions_agent_graph() -> StateGraph:
    """Build the questions retrieval sub-agent graph.
    
    This is a simple graph that just does retrieval.
    In the future, it could have multiple steps for
    query refinement, filtering, etc.
    
    Returns:
        Compiled StateGraph
    """
    graph = StateGraph(GraphState)
    
    graph.add_node("retrieve", retrieve_questions_node)
    
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", END)
    
    return graph.compile()
