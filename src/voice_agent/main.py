"""
Kannada Voice Agent - Main Entry Point

Start the voice agent server:
    python -m src.voice_agent.main

Or run directly:
    python src/voice_agent/main.py
"""
import sys
import os

if __name__ == "__main__" and __package__ is None:
    # Add project root to path to allow relative imports or absolute imports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    sys.path.append(project_root)
    
    # Use absolute import instead of relative
    from src.voice_agent.server import main, app
else:
    from .server import main, app


if __name__ == "__main__":
    main()
