import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def load_env():
    """Load environment variables from .env file"""
    # Look for .env in the project root
    env_path = Path("/opt/youtube_scraper/.env")
    
    if not env_path.exists():
        # Try current directory
        env_path = Path(".env")
        
    if not env_path.exists():
        logger.warning(f".env file not found")
        return False
    
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"')
                    os.environ[key] = value
        
        logger.info(f"Loaded environment from {env_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error loading .env file: {e}")
        return False