# 🦉 Hedwig AI - Multi-Agent Desktop Assistant

Hedwig is a comprehensive desktop application that orchestrates specialist AI agents to handle various tasks including document generation, web research, code creation, and terminal automation. Built with a modern GUI and powered by real API integrations.

## 🚀 **Current Status: Production Ready**

Hedwig is a fully functional desktop application with:
- **Modern GUI** with dark/light themes
- **Multi-agent system** with intelligent task routing  
- **Real API integrations** (OpenAI, Firecrawl, Playwright, Brave Search)
- **Comprehensive tool suite** for diverse tasks
- **Professional user experience** with chat interface and artifact management

---

## 📖 **Table of Contents**

1. [Quick Start](#-quick-start)
2. [Features Overview](#-features-overview)
3. [Architecture](#-architecture)
4. [Installation & Setup](#-installation--setup)
5. [Usage Guide](#-usage-guide)
6. [Configuration](#-configuration)
7. [Development](#-development)
8. [Project Structure](#-project-structure)

---

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.11+ 
- Git
- Internet connection for API access

### **Installation**
```bash
# Clone the repository
git clone <repository-url>
cd hedwig

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
playwright install  # For browser automation
```

### **Configuration**
```bash
# Copy environment template
cp .env.template .env

# Edit .env and add your API keys (OpenAI is required)
# OPENAI_API_KEY=your_openai_key_here
```

### **Launch**
```bash
# Start Desktop GUI (Recommended)
./venv/bin/python launch_gui.py

# Or use CLI mode
./venv/bin/python -m hedwig.cli chat
```

---

## ✨ **Features Overview**

### 🎯 **Core Capabilities**

#### **Multi-Agent Intelligence**
- **DispatcherAgent**: Intelligently routes tasks to appropriate specialists
- **SWEAgent**: Software engineering specialist for code development and debugging
- **ResearchAgent**: Web research specialist for information gathering
- **GeneralAgent**: Handles diverse general-purpose tasks

#### **Comprehensive Tool Suite**
- **Document Generation**: Professional PDF reports, Markdown documentation
- **Web Research**: Intelligent web scraping via Firecrawl API
- **Browser Automation**: Real web interaction using Playwright
- **Code Execution**: Python script execution with security controls
- **Shell Commands**: System command execution with risk assessment
- **File Operations**: Read, write, and manage files and artifacts

#### **Modern Desktop GUI**
- **Chat Interface**: Rich messaging with syntax highlighting and history
- **Artifact Browser**: Visual file management with preview capabilities
- **Settings Management**: Comprehensive configuration interface
- **Theme System**: Professional dark/light themes with instant switching
- **Status Monitoring**: Real-time progress and connection status

### 🔐 **Security & Safety**
- **Risk-Based Security**: Tools classified by risk level (READ_ONLY → WRITE → EXECUTE → DESTRUCTIVE)
- **User Confirmation**: Required for high-risk operations
- **API Key Encryption**: Secure storage of sensitive credentials
- **Sandboxed Execution**: Isolated tool execution environment

### 🌐 **Real API Integrations**
- **OpenAI**: Advanced language model capabilities (GPT-4, GPT-3.5-turbo)
- **Firecrawl**: Professional web scraping and content extraction
- **Playwright**: Cross-browser automation and testing
- **Brave Search**: Privacy-focused web search capabilities
- **ReportLab**: Professional PDF generation and formatting

---

## 🏗 **Architecture**

### **System Design**
Hedwig follows a **"team of specialists"** architecture where a central dispatcher routes tasks to specialized agents based on task analysis.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │───▶│ DispatcherAgent  │───▶│ Specialist      │
└─────────────────┘    └──────────────────┘    │ Agent           │
                                ▲               └─────────────────┘
                                │                        │
                                └────────────────────────┘
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│    Artifacts    │◀───│  Tool Registry   │◀───│ Security        │
│    Registry     │    │  & Execution     │    │ Gateway         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### **Core Components**

#### **Agent System**
- **BaseAgent**: Abstract foundation for all agents with standardized interface
- **AgentExecutor**: LangChain-based execution engine with tool integration
- **Structured Descriptions**: Machine-readable agent capabilities for intelligent routing

#### **Tool System** 
- **Tool Registry**: Centralized tool discovery and management
- **Security Gateway**: Risk assessment and user confirmation system
- **Structured Output**: Tools return `ToolOutput` objects with artifacts for reliable processing

#### **Artifact Management**
- **ArtifactRegistry**: Thread-scoped tracking of generated files
- **Auto-Opening Logic**: Intelligent file opening based on type and context
- **Persistence**: JSON-based storage of artifact metadata and conversation history

### **Technology Stack**
- **Backend**: Python 3.11+ with AsyncIO support
- **GUI Framework**: Tkinter with custom theming system
- **LLM Integration**: OpenAI API via official Python client
- **Web Automation**: Playwright for cross-browser support
- **PDF Generation**: ReportLab for professional document creation
- **Configuration**: Pydantic models with environment variable support

---

## 🛠 **Installation & Setup**

### **System Requirements**
- **Python**: 3.11 or higher
- **Operating System**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 2GB free space for dependencies and artifacts
- **Network**: Internet connection for API access

### **Detailed Installation**

#### **1. Environment Setup**
```bash
# Ensure Python 3.11+
python3 --version

# Clone repository
git clone <repository-url>
cd hedwig

# Create isolated environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

#### **2. Dependencies Installation**
```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Verify installation
python -c "import hedwig; print('Hedwig installed successfully')"
```

#### **3. API Configuration**
```bash
# Copy configuration template
cp .env.template .env

# Edit configuration file
nano .env  # or your preferred editor
```

**Required API Keys:**
- `OPENAI_API_KEY`: OpenAI API key (required)

**Optional API Keys:**
- `FIRECRAWL_API_KEY`: For enhanced web scraping
- `BRAVE_SEARCH_API_KEY`: For web search capabilities
- `ANTHROPIC_API_KEY`: Alternative to OpenAI

#### **4. First Launch**
```bash
# Test basic functionality
./venv/bin/python tests/integration/test_setup.py

# Launch GUI application
./venv/bin/python launch_gui.py
```

---

## 📚 **Usage Guide**

### **Desktop GUI Usage**

#### **Starting the Application**
```bash
./venv/bin/python launch_gui.py
```

#### **Main Interface**
- **Left Panel**: Chat interface for conversation with AI agents
- **Right Panel**: Artifact browser showing generated files
- **Menu Bar**: File operations, settings, and help
- **Status Bar**: Real-time status and progress indicators

#### **Chat Interface**
- **Send Message**: Type message and press Enter (Shift+Enter for new line)
- **Message Types**: Text, code blocks (with syntax highlighting), and links
- **History**: Persistent conversation history with timestamps
- **Export**: Save conversations to text files

#### **Artifact Management**
- **Browse Files**: Tree view of generated artifacts organized by type
- **Preview**: Built-in preview for text, code, and markdown files
- **Actions**: Open, copy path, delete files via context menu
- **Search**: Filter artifacts by name or type

#### **Settings Configuration**
- **Access**: Menu → Edit → Preferences or Ctrl+,
- **API Keys**: Secure management with show/hide functionality
- **Agent Settings**: Model selection, retry limits, timeouts
- **Tool Settings**: Browser options, PDF preferences
- **UI Settings**: Theme selection, logging level, data directory

### **Command Line Usage**

#### **Interactive CLI**
```bash
./venv/bin/python -m hedwig.cli chat
```

#### **Direct Python Integration**
```python
from hedwig.app import HedwigApp

# Initialize application
app = HedwigApp()

# Execute tasks
result = app.run("Create a PDF report about renewable energy trends")
print(result.content)

# Access generated artifacts
for artifact in result.metadata.get('artifacts', []):
    print(f"Generated: {artifact.file_path}")
```

### **Common Use Cases**

#### **Document Generation**
```
"Generate a professional PDF report about artificial intelligence trends in 2024"
"Create a markdown documentation file for this Python project"
"Write a technical specification document for a web API"
```

#### **Web Research**
```
"Research the latest developments in quantum computing and create a summary report"
"Find information about electric vehicle market trends and compile key findings"
"Investigate best practices for cybersecurity in small businesses"
```

#### **Code Development**
```
"Write a Python script to analyze CSV data and generate charts"
"Create a web scraper for product information from e-commerce sites"
"Debug this JavaScript function and suggest improvements"
```

#### **Data Analysis**
```
"Analyze this dataset and create visualizations showing key trends"
"Process this log file and identify error patterns"
"Generate a statistical report from survey data"
```

---

## ⚙️ **Configuration**

### **Environment Variables**
All settings can be configured via `.env` file or environment variables:

#### **Core Settings**
```bash
# Required
OPENAI_API_KEY=your_openai_key

# Application Settings
HEDWIG_LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
HEDWIG_DATA_DIR=~/.hedwig               # Data storage directory
HEDWIG_MAX_RETRIES=3                    # Task retry limit
HEDWIG_SECURITY_TIMEOUT=10              # Security dialog timeout

# Artifact Settings
HEDWIG_ARTIFACTS_DIR=artifacts          # Relative to data directory
HEDWIG_ENABLE_AUTO_OPEN=true           # Auto-open generated files
```

#### **API Configuration**
```bash
# LLM Settings
HEDWIG_LLM_MODEL=gpt-4                 # AI model to use
ANTHROPIC_API_KEY=your_anthropic_key   # Alternative LLM provider

# Web Services
FIRECRAWL_API_KEY=your_firecrawl_key   # Web scraping API
FIRECRAWL_BASE_URL=https://api.firecrawl.dev

BRAVE_SEARCH_API_KEY=your_brave_key    # Web search API
BRAVE_SEARCH_BASE_URL=https://api.search.brave.com/res/v1
```

#### **Tool Configuration**
```bash
# Browser Automation
HEDWIG_BROWSER_HEADLESS=true           # Run browser in headless mode
HEDWIG_BROWSER_TIMEOUT=30              # Browser operation timeout
HEDWIG_BROWSER_USER_AGENT=Mozilla/5.0... # Custom user agent

# PDF Generation
HEDWIG_PDF_PAGE_SIZE=letter            # letter, a4, legal
HEDWIG_PDF_FONT_FAMILY=Helvetica      # Default font family
```

### **Advanced Configuration**

#### **Logging Configuration**
```bash
# Detailed logging for debugging
HEDWIG_LOG_LEVEL=DEBUG

# Log files location: ~/.hedwig/logs/
# - hedwig.log: Application logs
# - agents.log: Agent execution logs
# - tools.log: Tool execution logs
```

#### **Performance Tuning**
```bash
# Thread pool settings (auto-configured)
HEDWIG_THREAD_POOL_SIZE=4              # Background worker threads
HEDWIG_MAX_CONCURRENT_TASKS=2          # Concurrent agent executions
```

---

## 👨‍💻 **Development**

### **Development Setup**
```bash
# Development dependencies
pip install -e .
pip install pytest pytest-cov black isort mypy

# Code formatting
black src/ tests/
isort src/ tests/

# Type checking
mypy src/
```

### **Testing**
```bash
# Run all tests
pytest tests/

# Integration tests
pytest tests/integration/

# Unit tests only
pytest tests/unit/

# With coverage
pytest tests/ --cov=hedwig --cov-report=html
```

### **Project Architecture**

#### **Design Principles**
1. **Modular Design**: Clear separation of concerns between components
2. **Security First**: Risk-based tool execution with user confirmation
3. **Thread Safety**: Safe concurrent execution with proper synchronization
4. **Extensibility**: Easy to add new agents, tools, and capabilities
5. **User Experience**: Professional GUI with intuitive interaction patterns

#### **Adding New Agents**
```python
from hedwig.agents.base import BaseAgent
from hedwig.core.models import TaskInput, TaskOutput

class MyCustomAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "MyCustomAgent"
    
    @property
    def description(self) -> Dict[str, Any]:
        return {
            "agent_name": "MyCustomAgent",
            "purpose": "Handles custom specialized tasks",
            "capabilities": ["custom_task", "specialized_processing"],
            "example_tasks": [
                "Process custom data format",
                "Generate specialized reports"
            ]
        }
    
    def _run(self, task_input: TaskInput) -> TaskOutput:
        # Implementation here
        pass
```

#### **Adding New Tools**
```python
from hedwig.tools.base import Tool
from hedwig.core.models import RiskTier, ToolOutput
from pydantic import BaseModel

class MyToolArgs(BaseModel):
    input_param: str

class MyCustomTool(Tool):
    @property
    def args_schema(self):
        return MyToolArgs
    
    @property
    def risk_tier(self) -> RiskTier:
        return RiskTier.READ_ONLY
    
    @property
    def description(self) -> str:
        return "Performs custom operations"
    
    def _run(self, **kwargs) -> ToolOutput:
        # Implementation here
        pass
```

### **Contributing Guidelines**
1. **Code Style**: Follow PEP 8, use Black for formatting
2. **Testing**: Add tests for new features and bug fixes
3. **Documentation**: Update docstrings and README for new features
4. **Security**: Consider security implications of new tools and features
5. **Performance**: Profile and optimize performance-critical code

---

## 📁 **Project Structure**

```
hedwig/
├── src/hedwig/                 # Main source code
│   ├── agents/                 # AI agent implementations
│   │   ├── base.py            # Base agent class
│   │   ├── dispatcher.py      # Task routing agent
│   │   ├── executor.py        # Agent execution framework
│   │   ├── general.py         # General-purpose agent
│   │   ├── research.py        # Research specialist
│   │   └── swe.py             # Software engineering agent
│   ├── core/                  # Core system components
│   │   ├── artifact_registry.py  # File tracking system
│   │   ├── config.py          # Configuration management
│   │   ├── exceptions.py      # Custom exception classes
│   │   ├── llm_integration.py # OpenAI API integration
│   │   ├── logging_config.py  # Logging configuration
│   │   ├── models.py          # Data models (Pydantic)
│   │   └── persistence.py     # Data persistence layer
│   ├── tools/                 # Tool implementations
│   │   ├── base.py            # Base tool class
│   │   ├── bash_tool.py       # Shell command execution
│   │   ├── browser_tool.py    # Playwright browser automation
│   │   ├── code_generator.py  # Code generation tool
│   │   ├── file_reader.py     # File reading operations
│   │   ├── firecrawl_research.py  # Web scraping tool
│   │   ├── list_artifacts.py  # Artifact discovery
│   │   ├── markdown_generator.py # Markdown generation
│   │   ├── pdf_generator.py   # PDF creation (ReportLab)
│   │   ├── python_execute.py  # Python code execution
│   │   ├── registry.py        # Tool registration system
│   │   └── security.py        # Security gateway
│   ├── gui/                   # Desktop GUI application
│   │   ├── app.py             # Main GUI application
│   │   ├── components/        # UI components
│   │   │   ├── artifact_viewer.py  # File browser
│   │   │   ├── chat_window.py      # Chat interface
│   │   │   └── status_bar.py       # Status display
│   │   ├── dialogs/           # Modal dialogs
│   │   │   └── settings.py    # Configuration dialog
│   │   ├── styles/            # Theme system
│   │   │   └── modern_theme.py     # Dark/light themes
│   │   └── utils/             # GUI utilities
│   │       └── threading_utils.py  # Thread management
│   ├── app.py                 # Main application class
│   └── cli.py                 # Command-line interface
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
├── artifacts/                 # Generated files storage
├── .env.template             # Environment configuration template
├── .env                      # User environment variables
├── requirements.txt          # Python dependencies
├── launch_gui.py            # GUI application launcher
├── setup.py                 # Package configuration
└── README.md               # This file
```

---

## 🔧 **Troubleshooting**

### **Common Issues**

#### **"Module not found" errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### **API Key errors**
```bash
# Verify .env file exists and contains valid keys
cat .env | grep OPENAI_API_KEY

# Test API connectivity
./venv/bin/python tests/integration/test_llm_integration.py
```

#### **GUI won't start**
```bash
# Check Python version (3.11+ required)
python --version

# Verify Tkinter is available
python -c "import tkinter; print('Tkinter available')"

# Install system packages if needed (Ubuntu/Debian)
sudo apt-get install python3-tk
```

#### **Browser automation fails**
```bash
# Install/reinstall Playwright browsers
playwright install

# Check browser installation
playwright install --help
```

### **Performance Issues**
- **High Memory Usage**: Reduce concurrent operations or increase system RAM
- **Slow Response**: Check internet connection and API response times
- **GUI Freezing**: Ensure all long operations use background threads

### **Getting Help**
1. **Check Logs**: `~/.hedwig/logs/hedwig.log`
2. **System Info**: Use GUI menu → Tools → System Info
3. **Debug Mode**: Set `HEDWIG_LOG_LEVEL=DEBUG` in .env
4. **API Status**: Verify API keys and service availability

---

## 📄 **License & Credits**

### **License**
This project is licensed under the MIT License - see the LICENSE file for details.

### **Built With**
- **Python**: Core programming language
- **OpenAI**: Language model capabilities
- **Firecrawl**: Web scraping and content extraction
- **Playwright**: Browser automation
- **ReportLab**: PDF generation
- **Tkinter**: Desktop GUI framework
- **LangChain**: Agent orchestration framework
- **Pydantic**: Data validation and settings

### **Acknowledgments**
- OpenAI for advanced language model capabilities
- The Python community for excellent libraries and tools
- Contributors and testers who helped refine the system

---

**🦉 Hedwig AI - Intelligent Multi-Agent Desktop Assistant**

*Transform your workflow with AI-powered automation, research, and content generation.*