# Building a Prompt-Based Crypto Trading Platform with RAG and Reddit Sentiment Analysis using Haystack

In today's fast-paced crypto market, having data-driven insights can make the difference between profit and loss. In this blog post, I'll walk you through a project that combines natural language processing, sentiment analysis, and automated trading in one cohesive system.

Note : This is **Demo** Project. Some processes not completely usefull .Like document store (InMemoryDocumentStore).

## Project Overview

This project is a prompt-based crypto trading platform that leverages the power of Retrieval Augmented Generation (RAG) to analyze Reddit sentiment and execute trades on Binance. The system allows users to input natural language commands to open trading positions while providing sentiment analysis from Reddit discussions to inform their decisions.

### Key Features:

- **Natural Language Trading Instructions**: Execute trades using simple text prompts
- **Reddit Sentiment Analysis**: Analyze cryptocurrency sentiment from multiple subreddits
- **Real-time Market Data**: Stream and process live crypto market data
- **Automated Trade Execution**: Connect directly to Binance API for trading
- **Web Interface**: Flask backend with database persistence

## Architecture and Data Flow

Here's an overview of how data flows through the system:

```
[Reddit Data] → [Sentiment Analysis] → [Document Store]
                                            ↓
[User Prompts] → [RAG Pipeline] → [Trading Decisions] → [Binance API]
                       ↑
                   [Market Data]
                       ↓
[Flask API] ← → [SQLAlchemy DB] ← → [Web Interface]
```

## Core Technologies and Frameworks

The project uses several powerful frameworks and libraries:

### 1. Haystack
[Haystack](https://haystack.deepset.ai/) forms the backbone of our RAG system. It provides pipelines for processing documents, embedding text, and retrieving relevant information.

```python
# Setting up the Haystack pipeline
indexing_pipeline = Pipeline()
indexing_pipeline.add_component(instance=DocumentCleaner(), name="cleaner")
indexing_pipeline.add_component(instance=SentenceTransformersDocumentEmbedder(model='sentence-transformers/all-mpnet-base-v2'), name="embeder")
indexing_pipeline.add_component(instance=DocumentWriter(policy=DuplicatePolicy.OVERWRITE, document_store=self.document_store), name='writer')
indexing_pipeline.connect("cleaner", "embeder")
indexing_pipeline.connect("embeder", "writer")
```

### 2. Binance API
I created a custom module (`binance_future_process`) to handle all trading operations through the Binance API:

```python
# Import custom Binance module functions
from binance_future_process import connect_future_binance
from binance_future_process import connect_binance
from binance_future_process import precision_asset
from binance_future_process import new_order
from binance_future_process import change_leverage
# ... and more
```

This module handles everything from connecting to the API, retrieving market data, placing orders, and managing positions.

### 3. Flask and SQLAlchemy
The backend is built on Flask with SQLAlchemy for database operations:

```python
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# Database models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    # ...
```

Our Flask API handles authentication, data persistence, and provides endpoints for the frontend to interact with.

### 4. Reddit API and Sentiment Analysis
For sentiment analysis, we collect data from Reddit using `asyncpraw` and analyze it using a transformer-based sentiment model:

```python
# Sentiment analysis
sentiment_model = pipeline("sentiment-analysis",
                           model="cardiffnlp/twitter-roberta-base-sentiment",
                           truncation=True,
                           tokenizer="cardiffnlp/twitter-roberta-base-sentiment",
                           max_length=512)
```

## The RAG Architecture

The heart of this project is the Retrieval Augmented Generation (RAG) pipeline built with Haystack. This system processes user prompts and generates appropriate trading actions while incorporating Reddit sentiment data.

Here's how it works:

1. **Document Processing**: Reddit posts are collected, analyzed for sentiment, and stored in the document store
2. **User Prompts**: Users input natural language trading instructions
3. **Retrieval**: The system retrieves relevant sentiment data based on the prompt
4. **Generation**: A Gemini model interprets the prompt and sentiment data to produce trading actions

```python
def rag(self):
    prompt_template = """
    {% if mode == "parse" %}
        # Parsing logic for trading instructions
    {% elif mode == "sentiment" %}
        # Sentiment analysis processing
    {% endif %}
    """

    advanced_rag = Pipeline(max_runs_per_component=5)
    advanced_rag.add_component("embeder", SentenceTransformersTextEmbedder())
    advanced_rag.add_component("retriever", InMemoryEmbeddingRetriever(document_store=document_store))
    advanced_rag.add_component("prompt_builder", ChatPromptBuilder(template=prompt))
    advanced_rag.add_component("llm", GoogleAIGeminiChatGenerator(model="gemini-1.5-flash"))
    # ... connect components
    
    return advanced_rag
```

## Asynchronous Operations

The system handles multiple operations concurrently using Python's asyncio:

```python
async def all_requests():
    realtime_task = asyncio.create_task(
        periodic_task(token_manager, f'{host}/api/data/post_realtime', 2, post_realtime))
    
    positions_task = asyncio.create_task(
        periodic_task(token_manager, f'{host}/api/data/post_open_positions', 5, post_openPosition))
    
    # ... more tasks
    
    await asyncio.gather(realtime_task, positions_task, assets_task, prompt_task)
```

## Thread Management

To ensure stability, a ThreadManager class handles different concurrent processes:

```python
class ThreadManager:
    def __init__(self):
        # Thread'ler için stop event'ları
        self.stop_events = {
            "websocket": threading.Event(),
            "flask_app": threading.Event(),
            "streamlit_app": threading.Event()
        }
        
        # Thread tanımlamaları
        self.thread_dict = {
            "websocket": None,
            "flask_app": None,
            "streamlit_app": None
        }
    
    # ... thread management methods
```

## Data Security

The Flask backend implements token-based authentication and encryption for sensitive data:

```python
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        # ... token validation logic
    return decorated

def encrypt_sensitive_data(data):
    json_data = json.dumps(data)
    encrypted_data = cipher.encrypt(json_data.encode())
    return encrypted_data.decode()
```

## Visual Flow Diagram

```
┌─────────────────┐           ┌───────────────────┐
│                 │           │                   │
│  Reddit Data    │◄────────► │ Sentiment Analysis│
│  (asyncpraw)    │           │ (Roberta model)   │
│                 │           │  (Optinal)        │
└────────┬────────┘           └─────────┬─────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐           ┌───────────────────┐
│                 │           │                   │
│  Document Store │◄────────► │ Haystack Pipeline │
│  (In-Memory)    │           │                   │
│                 │           │                   │
└────────┬────────┘           └─────────┬─────────┘
         │                              │
         │                              ▼
         │                    ┌───────────────────┐
         │                    │                   │
         └───────────────────►│ User Prompt       │
                              │ Processing        │
                              │                   │
                              └─────────┬─────────┘
                                        │
                                        ▼
┌─────────────────┐           ┌───────────────────┐
│                 │           │                   │
│  Binance API    │◄────────► │ Trading Execution │
│  Module         │           │                   │
│                 │           │                   │
└────────┬────────┘           └─────────┬─────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐           ┌───────────────────┐
│                 │           │                   │
│  Flask API      │◄────────► │ SQLAlchemy DB     │
│  (Backend)      │           │                   │
│                 │           │                   │
└─────────────────┘           └───────────────────┘
```

## How It Works in Practice

1. A user inputs a natural language trading instruction like: "BTC 45000$ long position 5x leverage 1000$"
2. The system parses this into a structured format
3. Recent Reddit sentiment about Bitcoin is retrieved from the document store
4. The sentiment data is summarized and presented to the user
5. The trading order is executed on Binance
6. Results are stored in the database and presented to the user

## Conclusion

This project demonstrates the power of combining natural language processing with trading automation. The RAG architecture provides a flexible way to interpret user intents while incorporating external data sources like Reddit sentiment.

The modular design allows for easy extension - you could add more data sources, improve the sentiment analysis, or enhance the trading strategies.

If you're interested in exploring the full codebase or contributing, feel free to reach out. Happy trading!

---

*Disclaimer: This project is for educational purposes only. Automated trading carries significant financial risks. Always thoroughly test any trading system with paper trading before using real funds.*
