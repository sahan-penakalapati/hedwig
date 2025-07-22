# Hedwig: Multi-Agent Task Execution System

Hedwig is a local desktop application that orchestrates specialist agents to handle various tasks including document generation, web research, code creation, and terminal command automation.

## 🚧 Development Status

**Current Phase: Phase 6 - Specialized Agents (COMPLETED)**

### ✅ Completed Features

#### Phase 1: Core Foundation
- **Project Structure**: Full Python package with proper organization
- **Core Data Models**: TaskInput, TaskOutput, ToolOutput, Artifact classes
- **Artifact Registry**: Thread-scoped artifact tracking with auto-opening logic
- **Persistence System**: Thread and artifact persistence with JSON serialization
- **Configuration Management**: Environment-based configuration with defaults
- **Logging Infrastructure**: Structured logging with file rotation
- **Error Handling**: Standardized exception framework with error codes
- **CLI Interface**: Basic command-line interface for testing
- **Unit Tests**: Comprehensive test coverage for core components

#### Phase 2: Tool System Foundation
- **Tool Infrastructure**: Base Tool class with standardized interface
- **Tool Registry**: Centralized tool management and discovery
- **Security Gateway**: Risk-based security mediation with user confirmation
- **Basic Tools**: FileReader and ListArtifacts tools

#### Phase 3: Agent System Core
- **Base Agent Framework**: Abstract base class with consistent interface
- **Agent Executor**: LangChain-based agent execution with tool integration
- **Dispatcher Agent**: Intelligent task routing to appropriate specialists
- **General Agent**: Multi-purpose agent for diverse tasks

#### Phase 4: Application Layer
- **HedwigApp**: Main application orchestrating threads and artifacts
- **Thread Management**: Persistent conversation threads with isolated contexts
- **Enhanced CLI**: Interactive command-line interface with session management
- **Agent Integration**: Full integration between app, agents, and tools

#### Phase 5: Tool Expansion
- **Document Generation**: PDFGeneratorTool and MarkdownGeneratorTool
- **Code Tools**: CodeGeneratorTool with multi-language support and syntax validation
- **Execution Tools**: PythonExecuteTool and BashTool with security controls
- **Dynamic Risk Assessment**: Enhanced SecurityGateway with command-specific risk analysis
- **Comprehensive Testing**: Full test coverage for all Phase 5 tools

#### Phase 6: Specialized Agents
- **SWEAgent**: Software engineering specialist for code development, debugging, and refactoring
- **ResearchAgent**: Research specialist for information gathering and report generation
- **Enhanced Dispatching**: Structured agent descriptions for intelligent task routing
- **Research Tools**: FirecrawlResearchTool and BrowserTool for web research and automation
- **Agent Integration**: Full integration of specialized agents with HedwigApp
- **Comprehensive Testing**: Full test coverage for specialized agents and routing logic

### 🏗️ Next Phase: Phase 7 - GUI and Polish

Upcoming features:
- Desktop GUI application with modern interface
- Enhanced web research integration with real APIs
- Performance optimizations and monitoring
- Advanced artifact visualization and management

## 📁 Project Structure

```
hedwig/
├── src/hedwig/
│   ├── core/               # Core system components
│   │   ├── models.py       # Data models and structures
│   │   ├── artifact_registry.py  # Artifact tracking
│   │   ├── persistence.py  # Thread persistence
│   │   ├── config.py       # Configuration management
│   │   ├── logging_config.py     # Logging setup
│   │   └── exceptions.py   # Error handling
│   ├── agents/             # Agent implementations (future)
│   ├── tools/              # Tool implementations (future)
│   ├── gui/                # GUI components (future)
│   └── cli.py              # Command-line interface
├── tests/
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests (future)
├── artifacts/              # Generated artifacts directory
└── requirements.txt        # Python dependencies
```

## 🚀 Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd hedwig
```

2. Install dependencies:
```bash
pip install -e .
```

3. Initialize configuration:
```bash
hedwig init
```

4. Configure your environment:
   - Copy `.env.template` to `.env`
   - Add your API keys (OpenAI/Anthropic)

### Basic Usage

Start an interactive chat session:
```bash
hedwig chat
```

List all chat threads:
```bash
hedwig threads
```

Clean up old threads:
```bash
hedwig cleanup --keep-days 30
```

## 🧪 Testing

Run the test suite:
```bash
pytest tests/
```

Run tests with coverage:
```bash
pytest tests/ --cov=hedwig --cov-report=html
```

## 📖 Architecture Overview

Hedwig follows a "team of specialists" architecture:

- **HedwigApp**: Main application managing threads and artifacts
- **DispatcherAgent**: Routes tasks to appropriate specialist agents
- **Specialist Agents**: Handle specific types of tasks (coding, research, etc.)
- **Tools**: Perform specific actions (file operations, code execution, etc.)
- **Security Gateway**: Mediates tool execution with risk assessment
- **Artifact System**: Tracks and manages generated files

### Key Design Principles

1. **Thread-Scoped Context**: Each conversation maintains its own history and artifacts
2. **Structured Communication**: Tools return structured data instead of text parsing
3. **Security First**: All tool execution goes through security validation
4. **Local-First**: Designed for secure local desktop operation
5. **Extensible**: Easy to add new agents and tools

## 🔧 Configuration

Hedwig uses environment variables for configuration:

```bash
# LLM Provider
HEDWIG_LLM__PROVIDER=openai          # or anthropic
HEDWIG_LLM__MODEL=gpt-4              # Model to use
HEDWIG_LLM__API_KEY=your_key_here    # API key

# Application
HEDWIG_LOG_LEVEL=INFO                # Logging level
HEDWIG_DATA_DIR=~/.hedwig            # Data storage directory
HEDWIG_MAX_RETRIES=3                 # Task retry limit
```

See `.env.template` for all available options.

## 🛡️ Security Model

Hedwig implements a multi-tiered security approach:

- **Risk Tiers**: READ_ONLY → WRITE → EXECUTE → DESTRUCTIVE
- **User Confirmation**: Required for high-risk operations
- **Dynamic Assessment**: Command pattern analysis for additional risk
- **Fail-Safe Design**: Operations denied by default on timeout

## 📝 Development Guidelines

### Adding New Components

1. **Data Models**: Add to `core/models.py` with Pydantic validation
2. **Tools**: Inherit from base Tool class (future implementation)
3. **Agents**: Inherit from BaseAgent with structured description
4. **Tests**: Add comprehensive unit tests for new components

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Document classes and methods with docstrings
- Prefer composition over inheritance

## 🗺️ Roadmap

### Phase 2: Tool System Foundation
- [ ] Tool infrastructure and registry
- [ ] Security Gateway implementation
- [ ] Basic read-only tools

### Phase 3: Agent System Core
- [ ] BaseAgent and AgentExecutor
- [ ] DispatcherAgent routing logic
- [ ] Basic GeneralAgent implementation

### Phase 4: Application Layer
- [ ] HedwigApp main class
- [ ] Thread management and persistence
- [ ] Enhanced CLI interface

### Phase 5: Tool Expansion ✅
- [x] Document generation tools (PDF, Markdown)
- [x] Code generation and execution tools
- [x] Enhanced security features with dynamic risk assessment

### Phase 6: Specialized Agents ✅
- [x] SWEAgent for software development tasks
- [x] ResearchAgent for web research and data gathering
- [x] Enhanced agent descriptions and routing logic
- [x] Research tools (FirecrawlResearchTool, BrowserTool)

### Phase 7: GUI and Polish
- [ ] Desktop GUI application
- [ ] Web research integration
- [ ] Performance optimizations

## 📄 License

[License information to be added]

## 🤝 Contributing

[Contributing guidelines to be added]

## 📞 Support

[Support information to be added]