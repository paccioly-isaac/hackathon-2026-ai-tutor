"""Graph runner utility for LangGraph execution.

Provides a reusable function to run or resume a graph,
encapsulating the logic of checking if it's first execution or continuation.
"""

from typing import Any

from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command


async def run_or_resume_graph(
    graph: CompiledStateGraph,
    config: dict,
    initial_state: dict | None = None,
    resume_value: Any = None,
) -> dict:
    """Run a graph from scratch or resume from an interrupt.
    
    For first execution: invokes with initial_state
    For subsequent executions: resumes with Command(resume=resume_value)
    
    Args:
        graph: The compiled LangGraph graph to execute
        config: Configuration dict with at least {"configurable": {"thread_id": ...}}
        initial_state: State to use for first execution (required if first execution)
        resume_value: Value to resume the interrupt with (use empty dict if no value)
        
    Returns:
        dict: The graph execution result
        
    Raises:
        ValueError: If first execution but initial_state is None
    """
    thread_id = config["configurable"]["thread_id"]
    # LangGraph doesn't accept None as resume value, use empty dict as placeholder
    actual_resume_value = resume_value if resume_value is not None else {}
    
    # Check if this is the first execution by looking at existing state
    existing_state = await graph.aget_state(config)
    is_first_execution = existing_state.values == {}
    
    if is_first_execution:
        if initial_state is None:
            raise ValueError(
                f"initial_state is required for first execution (thread_id={thread_id})"
            )
        return await graph.ainvoke(initial_state, config=config)
    else:
        return await graph.ainvoke(Command(resume=actual_resume_value), config=config)
