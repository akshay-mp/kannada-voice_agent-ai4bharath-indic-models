"""
Voice Agent Implementation
Uses Nebius AI (Qwen) via LangChain OpenAI.
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# Initialize Nebius (Qwen) client via LangChain
llm = ChatOpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY"),
    model="Qwen/Qwen3-235B-A22B-Instruct-2507",
    temperature=0,
    streaming=True,
)


async def run_agent(user_query: str) -> str:
    """
    Run Nebius agent.
    
    Args:
        user_query: User's question in English
    
    Returns:
        Agent's response text
    """
    try:
        # Run agent
        response = await llm.ainvoke(user_query)
        
        # Extract text response
        if response.content:
            return response.content
        
        return "I couldn't find an answer to that question."
        
    except Exception as e:
        print(f"Agent error: {e}")
        return f"Sorry, I encountered an error: {str(e)}"


def run_agent_sync(user_query: str) -> str:
    """
    Synchronous version of run_agent for simpler usage.
    
    Args:
        user_query: User's question in English
    
    Returns:
        Agent's response text
    """
    try:
        response = llm.invoke(user_query)
        
        if response.content:
            return response.content
        
        return "I couldn't find an answer to that question."
        
    except Exception as e:
        print(f"Agent error: {e}")
        return f"Sorry, I encountered an error: {str(e)}"
