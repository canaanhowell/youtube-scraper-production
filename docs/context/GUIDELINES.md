# Master Development Guidelines - AI Tracker Projects

**Core principles for building production-ready, maintainable code that works with AI coding agents.**

Last Updated: 2025-08-02

---

## 🚨 ABSOLUTE RULES - NO EXCEPTIONS

### Rule #1: Real Data or Error - Never Fake Data
**ERRORS ARE ALWAYS PREFERRED OVER FAKE DATA**

```python
# ❌ NEVER DO THIS
try:
    response = api.get_user_data(user_id)
    return response.json()
except:
    return {"name": "Unknown User", "email": "test@example.com"}  # FORBIDDEN

# ✅ ALWAYS DO THIS
try:
    response = api.get_user_data(user_id)
    response.raise_for_status()
    return response.json()
except requests.exceptions.RequestException as e:
    logger.error(f"Failed to fetch user {user_id}: {e}")
    raise UserDataFetchError(f"Could not retrieve user data: {e}")
```

### Rule #2: 100x Scale Test
**Every line of code must work at 100x current scale**

Before writing any code, ask:
- Will this work with 100x more data?
- Will this work with 100x more users?
- Will this work with 100x more requests?

```python
# ❌ Fails scale test
for user in users:
    send_email(user.email)  # Synchronous, will break at scale

# ✅ Passes scale test
async def send_bulk_emails(users):
    chunks = [users[i:i+50] for i in range(0, len(users), 50)]
    for chunk in chunks:
        await asyncio.gather(*[send_email(user.email) for user in chunk])
        await asyncio.sleep(1)  # Rate limiting
```

### Rule #3: Root Cause Only
**Fix the cause, not the symptom**

Use 5-Why analysis for every issue:
1. Why did X fail? → Rate limit exceeded
2. Why rate limit exceeded? → Too many requests
3. Why too many requests? → No throttling
4. Why no throttling? → Didn't plan for scale
5. Why no scale planning? → No capacity requirements

---

## 🏗️ PROJECT STRUCTURE (Required)

### ⚠️ CRITICAL: NO FILES IN ROOT DIRECTORY
**NOTHING should be saved in the project root. ALL files must be organized in appropriate subdirectories.**

```
project_name/
├── src/
│   ├── api/           # API clients and integrations
│   │   ├── __init__.py
│   │   ├── base_client.py
│   │   └── reddit_api.py
│   ├── services/      # Business logic
│   │   ├── __init__.py
│   │   └── keyword_service.py
│   ├── models/        # Data models and schemas
│   │   ├── __init__.py
│   │   └── keyword.py
│   ├── utils/         # Shared utilities
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   └── config.py
│   └── scripts/       # Executable scripts
├── database_management/  # Database utilities and management scripts
│   ├── check_*.py
│   └── view_*.py
├── deployment/        # Deployment configurations and scripts
│   ├── *.sh
│   └── *.py
├── docs/              # Documentation
│   ├── context/
│   └── deployment/
├── logs/              # Application logs
│   ├── app.log
│   ├── error.log
│   └── network.log
├── tests/             # Test files
├── config/            # Configuration files
├── .github/           # GitHub Actions workflows
│   └── workflows/
├── .env               # Environment variables (gitignored)
├── .gitignore
├── requirements.txt
└── README.md
```

### File Organization Rules:
1. **Root Directory**: Only configuration files (.env, .gitignore, requirements.txt, README.md)
2. **Source Code**: ALL Python scripts go in `src/` subdirectories
3. **Scripts**: Executable scripts in `src/scripts/`, NOT in root
4. **Database Tools**: Management scripts in `database_management/`
5. **Deployment**: All deployment scripts in `deployment/`
6. **Documentation**: All docs in `docs/` with appropriate subdirectories

---

## 📋 QUICK REFERENCE - AI AGENTS

**When generating code, always include:**

✅ Type hints and docstrings
✅ Proper error handling with logging
✅ Input validation
✅ Constants instead of magic numbers
✅ Async when dealing with I/O
✅ Rate limiting for external APIs

```python
# Perfect AI-generated function template
async def fetch_keyword_metrics(
    keyword_id: str,
    time_window: str = "24h"
) -> KeywordMetrics:
    """
    Fetches metrics for a specific keyword.

    Args:
        keyword_id: Unique identifier for keyword
        time_window: Time window for metrics (24h, 7d, 30d)

    Returns:
        KeywordMetrics object with trend data

    Raises:
        ValueError: If keyword_id is invalid
        APIError: If external API fails
    """
    if not keyword_id or not keyword_id.strip():
        raise ValueError("keyword_id cannot be empty")

    logger.info(f"Fetching metrics for keyword {keyword_id}")

    try:
        async with rate_limiter:
            response = await api_client.get_metrics(keyword_id, time_window)

        if not response:
            raise APIError(f"No data returned for keyword {keyword_id}")

        logger.info(f"Successfully fetched metrics for {keyword_id}")
        return KeywordMetrics.from_dict(response)

    except APIError as e:
        logger.error(f"API error fetching keyword {keyword_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching keyword {keyword_id}: {e}")
        raise APIError(f"Failed to fetch keyword metrics: {e}")
```

---

## 🔧 STANDARD PATTERNS

### 1. Logging Setup (Copy This Exactly)

```python
# utils/logger.py
import logging
import os
from pathlib import Path

def setup_logging():
    """Initialize logging with proper handlers and formatters."""

    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # File handlers
    app_handler = logging.FileHandler('logs/app.log')
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(detailed_formatter)

    error_handler = logging.FileHandler('logs/error.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)

    # Network logger (separate)
    network_logger = logging.getLogger('network')
    network_logger.setLevel(logging.INFO)
    network_logger.propagate = False

    network_handler = logging.FileHandler('logs/network.log')
    network_handler.setFormatter(detailed_formatter)
    network_logger.addHandler(network_handler)

    return logging.getLogger(__name__)

# Use in every file
logger = setup_logging()
```

### 2. API Client Pattern (Use This Template)

```python
# api/base_client.py
import asyncio
import aiohttp
import time
from typing import Dict, Any, Optional
from utils.logger import setup_logging

logger = setup_logging()

class BaseAPIClient:
    """Base class for all API clients with proper error handling."""

    def __init__(self, base_url: str, rate_limit: int = 60):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = asyncio.Semaphore(rate_limit)

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'YourApp/1.0',
                'Accept': 'application/json'
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with proper error handling and logging."""

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        start_time = time.time()

        async with self.rate_limiter:
            try:
                logger.info(f"{method} {url}")

                async with self.session.request(method, url, **kwargs) as response:
                    duration = time.time() - start_time

                    # Log response
                    logger.info(f"{method} {url} - {response.status} - {duration:.2f}s")

                    # Handle errors
                    if response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        return await self._make_request(method, endpoint, **kwargs)

                    response.raise_for_status()

                    # Return JSON
                    try:
                        return await response.json()
                    except aiohttp.ContentTypeError:
                        text = await response.text()
                        raise APIError(f"Invalid JSON response: {text[:200]}")

            except aiohttp.ClientError as e:
                duration = time.time() - start_time
                logger.error(f"{method} {url} - FAILED - {duration:.2f}s - {e}")
                raise APIError(f"Request failed: {e}")
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{method} {url} - ERROR - {duration:.2f}s - {e}")
                raise

class APIError(Exception):
    """Custom exception for API errors."""
    pass
```

### 3. Data Models Pattern

```python
# models/keyword.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class KeywordMetrics:
    """Represents keyword metrics data."""

    trend_score: float
    hourly_velocity: float
    acceleration: float
    post_count: int
    updated_at: datetime

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KeywordMetrics':
        """Create KeywordMetrics from dictionary with validation."""

        required_fields = ['trend_score', 'hourly_velocity', 'acceleration', 'post_count']

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        try:
            return cls(
                trend_score=float(data['trend_score']),
                hourly_velocity=float(data['hourly_velocity']),
                acceleration=float(data['acceleration']),
                post_count=int(data['post_count']),
                updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid data format: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'trend_score': self.trend_score,
            'hourly_velocity': self.hourly_velocity,
            'acceleration': self.acceleration,
            'post_count': self.post_count,
            'updated_at': self.updated_at.isoformat()
        }
```

### 4. Configuration Pattern

```python
# utils/config.py
import os
from typing import Dict, Any

class Config:
    """Application configuration with validation."""

    # API Settings
    REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
    REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')

    # Rate Limits
    REDDIT_RATE_LIMIT = int(os.getenv('REDDIT_RATE_LIMIT', '60'))  # requests per minute

    # Trend Calculation
    TREND_VELOCITY_WEIGHT = float(os.getenv('TREND_VELOCITY_WEIGHT', '0.6'))
    TREND_ACCELERATION_WEIGHT = float(os.getenv('TREND_ACCELERATION_WEIGHT', '0.4'))
    MAX_TREND_SCORE = int(os.getenv('MAX_TREND_SCORE', '100'))

    # Database
    FIRESTORE_PROJECT_ID = os.getenv('FIRESTORE_PROJECT_ID')

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration is present."""
        required_vars = [
            'REDDIT_CLIENT_ID',
            'REDDIT_CLIENT_SECRET',
            'FIRESTORE_PROJECT_ID'
        ]

        missing = [var for var in required_vars if not getattr(cls, var)]

        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Return configuration as dictionary (excluding secrets)."""
        return {
            'reddit_rate_limit': cls.REDDIT_RATE_LIMIT,
            'trend_velocity_weight': cls.TREND_VELOCITY_WEIGHT,
            'trend_acceleration_weight': cls.TREND_ACCELERATION_WEIGHT,
            'max_trend_score': cls.MAX_TREND_SCORE
        }
```

---

## 🧪 TESTING STANDARDS

### Test Template (Copy for Every Module)

```python
# tests/test_keyword_service.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from services.keyword_service import KeywordService
from models.keyword import KeywordMetrics

class TestKeywordService:
    """Test suite for KeywordService."""

    @pytest.fixture
    def service(self):
        return KeywordService()

    @pytest.mark.asyncio
    async def test_fetch_metrics_success(self, service):
        """Test successful metrics fetch."""

        # Mock successful API response
        mock_response = {
            'trend_score': 85.5,
            'hourly_velocity': 12.3,
            'acceleration': 2.1,
            'post_count': 1500
        }

        with patch.object(service.api_client, 'get_metrics', return_value=mock_response):
            result = await service.fetch_keyword_metrics('test_keyword')

            assert isinstance(result, KeywordMetrics)
            assert result.trend_score == 85.5
            assert result.post_count == 1500

    @pytest.mark.asyncio
    async def test_fetch_metrics_api_error(self, service):
        """Test API error handling - should raise, not return fake data."""

        with patch.object(service.api_client, 'get_metrics', side_effect=Exception("API Error")):
            with pytest.raises(Exception):
                await service.fetch_keyword_metrics('test_keyword')

    @pytest.mark.asyncio
    async def test_fetch_metrics_invalid_data(self, service):
        """Test invalid data handling - should raise, not guess values."""

        # Missing required field
        invalid_response = {
            'trend_score': 85.5,
            # Missing other required fields
        }

        with patch.object(service.api_client, 'get_metrics', return_value=invalid_response):
            with pytest.raises(ValueError):
                await service.fetch_keyword_metrics('test_keyword')
```

---

## 🚫 NEVER DO THESE

### 1. Silent Failures
```python
# ❌ NEVER
try:
    result = risky_operation()
except:
    pass  # Silent failure - FORBIDDEN

# ✅ ALWAYS
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### 2. Magic Numbers
```python
# ❌ NEVER
if retry_count > 5:
    break

# ✅ ALWAYS
MAX_RETRY_ATTEMPTS = 5
if retry_count > MAX_RETRY_ATTEMPTS:
    break
```

### 3. Global State
```python
# ❌ NEVER
global_config = load_config()

def process():
    return global_config.api_key

# ✅ ALWAYS
def process(config: Config):
    return config.api_key
```

### 4. Synchronous I/O at Scale
```python
# ❌ NEVER (fails at scale)
for url in urls:
    response = requests.get(url)
    results.append(response.json())

# ✅ ALWAYS (scales)
async def fetch_all(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_one(session, url) for url in urls]
        return await asyncio.gather(*tasks)
```

---

## ✅ PRE-COMMIT CHECKLIST

Before any code goes to production:

- [ ] **No fake/mock/placeholder data anywhere**
- [ ] **All errors logged and propagated properly**
- [ ] **Passes 100x scale test**
- [ ] **Root cause analysis completed (5-Why)**
- [ ] **Type hints and docstrings added**
- [ ] **Constants used instead of magic numbers**
- [ ] **Async used for I/O operations**
- [ ] **Rate limiting implemented for external APIs**
- [ ] **Input validation on all public functions**
- [ ] **Tests cover error scenarios**
- [ ] **Environment variables used for config**
- [ ] **Proper project structure followed**

---

## 🚀 PROJECT SETUP SCRIPT

Run this to start any new project:

```python
#!/usr/bin/env python3
# setup_project.py

import os
from pathlib import Path

def setup_project():
    """Initialize project with proper structure and files."""

    # Create directory structure
    directories = [
        'src/api',
        'src/services',
        'src/models',
        'src/utils',
        'src/scripts',
        'tests',
        'logs',
        'config'
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

        # Add __init__.py to src directories
        if directory.startswith('src/'):
            init_file = Path(directory) / '__init__.py'
            init_file.touch()

    # Create essential files
    files = {
        'requirements.txt': '''aiohttp>=3.8.0
asyncio
pytest>=7.0.0
pytest-asyncio
python-dotenv
''',
        '.env.example': '''# Copy to .env and fill in values
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
FIRESTORE_PROJECT_ID=your_project_id
REDDIT_RATE_LIMIT=60
''',
        '.gitignore': '''__pycache__/
*.pyc
.env
.env.local
logs/
.pytest_cache/
'''
    }

    for filename, content in files.items():
        Path(filename).write_text(content)

    print("✅ Project structure created")
    print("Next steps:")
    print("1. Copy .env.example to .env and configure")
    print("2. pip install -r requirements.txt")
    print("3. Start coding following the guidelines!")

if __name__ == '__main__':
    setup_project()
```

---

**Remember: Quality over speed. Real data or error - no middle ground.**