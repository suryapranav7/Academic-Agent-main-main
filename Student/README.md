# Student Agent System - MCP Layer

A modular, production-ready MCP (Model Context Protocol) implementation for the Indus Agentic AI System.

## 🏗️ Architecture Overview

The MCP layer provides three core services:

1. **Curriculum MCP** - RAG-based curriculum content management
2. **Question Bank MCP** - Adaptive question management with difficulty inference
3. **Student Data MCP** - Student progress tracking and analytics

## 📋 Prerequisites

- Python 3.10+
- OpenAI API Key
- 2GB disk space (for vector databases)

## 🚀 Quick Start

### 1. Create Project Structure

```bash
python create_structure.py
```

### 2. Install Dependencies

```bash
cd student_agent_system
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.template` to `.env` and add your OpenAI API key:

```bash
cp .env.template .env
```

Edit `.env`:
```
OPENAI_API_KEY=sk-your-key-here
```

### 4. Test MCP Layer

```bash
python test_mcp_layer.py
```

Expected output:
```
============================================================
MCP Initialization Complete: 3/3 successful
============================================================

✅ curriculum_mcp: ...
✅ question_bank_mcp: ...
✅ student_data_mcp: ...
```

## 📂 Project Structure

```
student_agent_system/
├── mcp/                          # Model Context Protocol layer
│   ├── base_mcp.py              # Abstract base class
│   ├── curriculum_mcp.py        # Curriculum management
│   ├── question_bank_mcp.py     # Question bank with adaptive difficulty
│   └── student_data_mcp.py      # Student progress tracking
├── utils/                        # Utility modules
│   └── embedding_utils.py       # OpenAI embedding service
├── config/                       # Configuration
│   └── settings.py              # Environment settings
└── data/                         # Data storage
    ├── vector_db/               # ChromaDB storage
    └── student_records.db       # SQLite database
```

## 🔧 MCP Services API

### Curriculum MCP

```python
from student_agent_system.mcp import curriculum_mcp, Module

# Create a module
module_data = {
    "module_name": "Introduction to Kinematics",
    "subject": "Physics",
    "grade_level": "Grade 11",
    "content": {
        "learning_objectives": [...],
        "core_concepts": [...],
        "explanations": "...",
        "examples": [...]
    }
}
response = await curriculum_mcp.create(module_data)

# Search modules
results = await curriculum_mcp.search("velocity", n_results=5)

# Get module
module = await curriculum_mcp.get(module_id)
```

### Question Bank MCP

```python
from student_agent_system.mcp import question_bank_mcp, Question

# Create question
question_data = {
    "module_id": "...",
    "question_text": "What is velocity?",
    "question_type": "short_answer",
    "correct_answer": "Rate of change of displacement",
    "concept_tags": ["velocity", "kinematics"]
}
response = await question_bank_mcp.create(question_data)

# Get questions by difficulty
questions = await question_bank_mcp.get_questions_by_module(
    module_id,
    difficulty_range=(0.3, 0.5)
)

# Update difficulty inference
await question_bank_mcp.update_difficulty_inference(
    question_id,
    was_correct=True,
    time_taken=45.0
)
```

### Student Data MCP

```python
from student_agent_system.mcp import student_data_mcp, AssessmentData

# Create student profile
profile = await student_data_mcp.create({
    "student_id": "student_001"
})

# Log assessment
interaction = AssessmentData(
    module_id="...",
    question_id="...",
    answer_given="10 m/s",
    is_correct=True,
    time_taken=45.0,
    difficulty_level=0.3
)
await student_data_mcp.log_interaction("student_001", interaction)

# Get analytics
analytics = await student_data_mcp.generate_analytics_summary(
    "student_001",
    summary_type="weekly"
)
```

## 🎯 Key Features

### 1. RAG-Based Retrieval
- Semantic search using OpenAI embeddings
- ChromaDB for efficient vector storage
- Relevance scoring for search results

### 2. Adaptive Difficulty
- Questions self-adjust difficulty based on student performance
- Tracks success rate and time taken
- Infers difficulty from aggregate student data

### 3. Comprehensive Analytics
- Daily/weekly/monthly/term summaries
- Subject-wise and question-wise breakdown
- Mastery gap identification
- Prescriptive recommendations

### 4. Production-Ready
- Async/await for scalability
- Retry logic for API calls
- Standardized error handling
- Type safety with Pydantic models

## 🧪 Running Tests

```bash
# Test all MCPs
python test_mcp_layer.py

# Expected: All tests pass with ✅ markers
```

## 📊 Data Models

### Module Schema
```python
{
    "module_id": "uuid",
    "module_name": "string",
    "subject": "string",
    "grade_level": "string",
    "content": {
        "learning_objectives": ["string"],
        "core_concepts": ["string"],
        "explanations": "text",
        "examples": ["string"],
        "prerequisites": ["module_id"]
    },
    "metadata": {
        "difficulty_level": "easy|medium|hard",
        "estimated_time": 60,
        "ib_alignment": ["codes"],
        "jee_neet_alignment": ["codes"]
    }
}
```

### Question Schema
```python
{
    "question_id": "uuid",
    "module_id": "string",
    "question_text": "string",
    "question_type": "mcq|short_answer|numerical",
    "correct_answer": "string",
    "concept_tags": ["string"],
    "difficulty_metadata": {
        "initial_difficulty": "easy|medium|hard",
        "inferred_difficulty": 0.5,  # 0-1
        "success_rate": 0.5,
        "avg_time_taken": 60.0
    }
}
```

### Student Profile Schema
```python
{
    "student_id": "string",
    "current_module": "module_id",
    "completed_modules": ["module_id"],
    "overall_accuracy": 85.5,
    "concept_mastery": {
        "concept_name": 0.8  # 0-1 score
    },
    "struggle_areas": ["concept_names"]
}
```

## 🎯 Complete System Ready!

The full system is now operational with:
- ✅ MCP Layer (Curriculum, Questions, Student Data)
- ✅ CrewAI Agents (Learning, Assessment, Analytics)
- ✅ Tools Layer (5 intelligent tools)
- ✅ Streamlit Chatbot UI

## 🚀 Running the System

### Quick Start (Recommended)

```bash
# One-command startup
python run_system.py
```

This will:
1. Check dependencies
2. Verify environment configuration
3. Initialize sample data
4. Launch the Streamlit app

### Manual Start

```bash
# 1. Ensure MCP initialization
python test_mcp_layer.py

# 2. Run Streamlit app
streamlit run student_agent_system/ui/streamlit_app.py
```

## 💬 Using the Chatbot

Once the system is running:

1. **Enter Student ID** in sidebar (default: `student_demo_001`)
2. **Click "Start Learning Session"**
3. **Interact naturally** with commands like:
   - "Start a new module on kinematics"
   - "Explain the concept of velocity"
   - "I want to take an assessment"
   - "Show my progress"
   - "Help me understand acceleration"

### Sample Interactions

```
Student: "Start a new module"
Assistant: [Presents available modules]

Student: "Explain velocity"
Assistant: [Provides clear explanation with examples]

Student: "I want to take an assessment"
Assistant: [Starts adaptive assessment]

Student: "10 m/s" [answering question]
Assistant: [Evaluates, provides feedback, next question]

Student: "Show my progress"
Assistant: [Displays analytics and recommendations]
```

## 🤖 System Architecture

### Agents
1. **Student Learning Agent**
   - Delivers curriculum content
   - Answers questions
   - Provides explanations
   - Tools: Curriculum Retriever, Explanation Generator

2. **Assessment Agent**
   - Adaptive questioning
   - Answer evaluation
   - Difficulty adjustment
   - Tools: Question Retriever, Answer Evaluator, Explanation Generator

3. **Analytics Agent**
   - Performance tracking
   - Gap identification
   - Recommendations
   - Tools: Analytics Generator

### Tools
1. **Curriculum Retriever** - RAG-based content search
2. **Question Retriever** - Adaptive difficulty filtering
3. **Explanation Generator** - GPT-4o-mini powered
4. **Answer Evaluator** - Intelligent grading
5. **Analytics Generator** - Performance insights

## 🧪 Testing Features

### Test Learning Flow
```
1. Start module → Learn content → Ask questions
2. Take assessment → Get adaptive questions
3. View analytics → See progress
```

### Test Adaptive Difficulty
```
- Answer correctly → Harder questions
- Answer incorrectly → Easier questions + explanation
- System tracks performance patterns
```

### Test Analytics
```
- Daily/weekly/monthly summaries
- Concept mastery scores
- Learning gap identification
- Prescriptive recommendations
```

## 🐛 Troubleshooting

### "Module not found" errors
```bash
# Ensure you're in the correct directory
cd student_agent_system
python -m pytest  # or your test command
```

### ChromaDB initialization fails
```bash
# Clear vector database
rm -rf data/vector_db/*
python test_mcp_layer.py  # Recreate
```

### OpenAI API errors
- Verify API key in `.env`
- Check rate limits on OpenAI dashboard
- Ensure sufficient credits

## 📝 License

Proprietary - Indus Agentic AI System

## 👥 Authors

Technical Architecture Team - Indus Education

---

**Ready to build the agent layer?** The MCP foundation is complete and tested!

$env:PYTHONIOENCODING="utf-8"; python run_system.py