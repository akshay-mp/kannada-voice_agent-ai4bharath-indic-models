"""
Voice Agent Implementation
Uses Nebius AI (Qwen) via LangChain OpenAI with Tavily Search.
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent

load_dotenv()

# Initialize Nebius (Qwen) client via LangChain
llm = ChatOpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY"),
    model="Qwen/Qwen3-235B-A22B-Instruct-2507",
    temperature=0,
    streaming=True,
)

# Initialize Search Tool
search_tool = TavilySearch(max_results=3)
tools = [search_tool]

# System prompt for the agent
SYSTEM_PROMPT = """You are a helpful assistant. You can use the search tool to find information.
If you need to search for current events or specific data, use the search tool.
Answer concisely only based on the search results you get.
Always answer in plain English without formatting the response.
IMPORTANT: Convert all numbers to their word equivalent (e.g., say 'eleven' instead of '11', 'twenty five' instead of '25')."""

# Create React Agent using langgraph with prompt parameter
agent_executor = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)


async def run_agent(user_query: str) -> str:
    """
    Run Agent with Search capabilities.
    
    Args:
        user_query: User's question in English
    
    Returns:
        Agent's response text
    """
    try:
        # Run agent executor
        result = await agent_executor.ainvoke({"messages": [("user", user_query)]})
        
        # Extract text response from the last message
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                return last_message.content
        
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
        result = agent_executor.invoke({"messages": [("user", user_query)]})
        
        # Extract text response from the last message
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                return last_message.content
        
        return "I couldn't find an answer to that question."
        
    except Exception as e:
        print(f"Agent error: {e}")
        return f"Sorry, I encountered an error: {str(e)}"
