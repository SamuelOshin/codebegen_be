# 🚀 CodebeGen - AI-Powered FastAPI Backend Generator

![Python](https://img.shields.io/badge/python-v3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-v0.104+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)

**CodebeGen** is an advanced AI-powered platform that transforms natural language descriptions into production-ready FastAPI backend projects. Leveraging a multi-model AI pipeline, it generates complete backend architectures including authentication, database models, APIs, tests, and deployment configurations in minutes.

## 🌟 Key Features

### 🤖 Multi-Model AI Pipeline
- **Schema Extraction**: Llama-3.1-8B for intelligent entity and relationship parsing
- **Code Generation**: Qwen2.5-Coder-32B (fine-tuned) for high-quality FastAPI code
- **Code Review**: Starcoder2-15B for security and best practices validation
- **Documentation**: Mistral-7B-Instruct for comprehensive project documentation

### 🏗️ Production-Ready Architecture
- **Clean Architecture**: Modular design with clear separation of concerns
- **Authentication & Authorization**: JWT-based auth with role-based access control
- **Database Integration**: PostgreSQL with SQLAlchemy 2.0 and async support
- **API Documentation**: Automatic OpenAPI/Swagger generation
- **Testing**: Comprehensive test suites with pytest and async testing
- **Deployment Ready**: Docker configurations and deployment scripts

### 🔥 Advanced Capabilities
- **Real-time Generation**: WebSocket streaming for live progress updates
- **Iterative Refinement**: AI-powered code iteration and improvement
- **Multi-Template Support**: FastAPI with PostgreSQL, MongoDB, and more
- **GitHub Integration**: Direct repository creation and deployment
- **Quality Assurance**: Automated code review and quality scoring

## 🛠️ Technology Stack

### Backend Framework
- **FastAPI** - High-performance async web framework
- **Python 3.11+** - Latest Python features and performance
- **Uvicorn** - Lightning-fast ASGI server

### Database & Storage
- **PostgreSQL** - Primary database with advanced features
- **SQLAlchemy 2.0** - Modern ORM with async support
- **Alembic** - Database migrations and schema management
- **Redis** - Caching and background task management

### AI & Machine Learning
- **Qwen2.5-Coder-32B** - Primary code generation model
- **Llama-3.1-8B** - Schema extraction and parsing
- **Starcoder2-15B** - Code review and quality analysis
- **Mistral-7B-Instruct** - Documentation generation

### Authentication & Security
- **JWT Tokens** - Secure authentication with python-jose
- **Bcrypt** - Password hashing with passlib
- **Rate Limiting** - SlowAPI for request throttling
- **CORS & Security Headers** - Production security measures

### Development & Testing
- **Poetry** - Dependency management and packaging
- **Pytest** - Comprehensive testing framework
- **Black & isort** - Code formatting and import sorting
- **MyPy** - Static type checking
- **Pre-commit** - Git hooks for code quality

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/codebegen-be.git
cd codebegen-be
```

2. **Install dependencies with Poetry**
```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Set up the database**
```bash
# Run database migrations
poetry run alembic upgrade head

# Optional: Seed with sample data
poetry run python scripts/seed_data.py
```

5. **Start the development server**
```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

## 📁 Project Structure

```
codebegen_be/
├── app/                          # Main application package
│   ├── main.py                   # FastAPI app entry point
│   ├── auth/                     # Authentication & authorization
│   │   ├── dependencies.py       # Auth dependencies
│   │   ├── handlers.py          # Auth handlers
│   │   └── models.py            # Auth models
│   ├── core/                     # Core application components
│   │   ├── config.py            # Configuration management
│   │   ├── database.py          # Database connection
│   │   ├── exceptions.py        # Custom exceptions
│   │   └── security.py          # Security utilities
│   ├── models/                   # SQLAlchemy database models
│   │   ├── base.py              # Base model class
│   │   ├── user.py              # User model
│   │   ├── project.py           # Project model
│   │   ├── generation.py        # AI generation model
│   │   └── organization.py      # Organization model
│   ├── repositories/             # Data access layer
│   │   ├── base.py              # Base repository
│   │   ├── user_repository.py   # User data operations
│   │   ├── project_repository.py # Project data operations
│   │   └── generation_repository.py # Generation data operations
│   ├── routers/                  # API route handlers
│   │   ├── auth.py              # Authentication routes
│   │   ├── projects.py          # Project management routes
│   │   ├── generations.py       # Code generation routes
│   │   ├── ai.py                # AI service routes
│   │   └── webhooks.py          # Webhook handlers
│   ├── schemas/                  # Pydantic schemas/DTOs
│   │   ├── base.py              # Base schemas
│   │   ├── user.py              # User schemas
│   │   ├── project.py           # Project schemas
│   │   ├── generation.py        # Generation schemas
│   │   └── ai.py                # AI request/response schemas
│   ├── services/                 # Business logic layer
│   │   ├── ai_orchestrator.py   # AI pipeline coordination
│   │   ├── code_generator.py    # Code generation service
│   │   ├── code_reviewer.py     # Code review service
│   │   ├── docs_generator.py    # Documentation service
│   │   ├── github_service.py    # GitHub integration
│   │   ├── billing_service.py   # Billing and subscriptions
│   │   └── schema_parser.py     # Schema extraction service
│   └── utils/                    # Utility functions
│       ├── file_utils.py        # File operations
│       ├── formatters.py        # Code formatting
│       └── validators.py        # Input validation
├── ai_models/                    # AI model implementations
│   ├── qwen_generator.py        # Qwen code generation model
│   ├── llama_parser.py          # Llama schema parser
│   ├── starcoder_reviewer.py    # Starcoder code reviewer
│   ├── mistral_docs.py          # Mistral documentation generator
│   └── model_loader.py          # Model loading utilities
├── alembic/                      # Database migrations
│   ├── versions/                # Migration files
│   └── env.py                   # Alembic configuration
├── templates/                    # Project templates
│   ├── fastapi_basic/           # Basic FastAPI template
│   ├── fastapi_mongo/           # FastAPI + MongoDB template
│   └── fastapi_sqlalchemy/      # FastAPI + SQLAlchemy template
├── tests/                        # Test suites
│   ├── test_auth/               # Authentication tests
│   ├── test_services/           # Service layer tests
│   ├── test_ai/                 # AI pipeline tests
│   └── test_integration/        # Integration tests
├── infra/                        # Infrastructure & deployment
│   ├── docker-compose.yml       # Local development setup
│   ├── Dockerfile               # Container configuration
│   └── nginx.conf               # Nginx configuration
├── docs/                         # Documentation
│   ├── architecture.md          # System architecture
│   ├── deployment.md            # Deployment guide
│   └── openapi.yaml             # API specification
├── scripts/                      # Utility scripts
│   ├── migrate.py               # Database migration runner
│   ├── seed_data.py             # Sample data seeder
│   └── setup.py                 # Environment setup
└── requirements/                 # Dependency files
    ├── base.txt                 # Core dependencies
    ├── dev.txt                  # Development dependencies
    └── prod.txt                 # Production dependencies
```

## 🔌 API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user
- `POST /auth/refresh` - Refresh access token

### Projects
- `GET /projects/` - List user projects
- `POST /projects/` - Create new project
- `GET /projects/{id}` - Get project details
- `PUT /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project
- `GET /projects/public` - List public projects
- `GET /projects/search` - Search projects

### AI Generation
- `POST /generations/` - Start code generation
- `GET /generations/{id}` - Get generation status
- `GET /generations/{id}/stream` - Stream generation progress
- `POST /generations/{id}/iterate` - Iterate on generation
- `GET /generations/{id}/files` - Download generated files

### AI Services
- `POST /ai/generate` - Generate project from prompt
- `POST /ai/iterate` - Iterate and improve code
- `GET /ai/models` - List available AI models

## 🔧 Configuration

### Environment Variables

```bash
# Application Settings
APP_NAME=codebegen
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-here

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/codebegen
REDIS_URL=redis://localhost:6379

# AI Model Paths
QWEN_MODEL_PATH=Qwen/Qwen2.5-Coder-32B
LLAMA_MODEL_PATH=meta-llama/Llama-3.1-8B
STARCODER_MODEL_PATH=bigcode/starcoder2-15b
MISTRAL_MODEL_PATH=mistralai/Mistral-7B-Instruct-v0.1

# GitHub Integration
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# External Services
STRIPE_SECRET_KEY=your-stripe-key
```

## 🧪 Testing

### Run All Tests
```bash
poetry run pytest
```

### Run Specific Test Suites
```bash
# Authentication tests
poetry run pytest tests/test_auth/

# Service layer tests
poetry run pytest tests/test_services/

# Integration tests
poetry run pytest tests/test_integration/

# AI pipeline tests
poetry run pytest tests/test_ai/
```

### Test Coverage
```bash
poetry run pytest --cov=app --cov-report=html
```

## 🐳 Docker Deployment

### Development Environment
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Deployment
```bash
# Build production image
docker build -f infra/Dockerfile -t codebegen:latest .

# Run with production settings
docker run -d \
  --name codebegen \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e DATABASE_URL=your-production-db-url \
  codebegen:latest
```

## 🤝 Development Workflow

### Phase Implementation Status

#### ✅ Phase 1: Core Infrastructure (Completed)
- [x] FastAPI application setup
- [x] Database models and migrations
- [x] Authentication system
- [x] Basic API structure
- [x] Testing framework

#### ✅ Phase 2: Project Management (Completed)
- [x] Project CRUD operations
- [x] User management
- [x] API endpoints
- [x] Data validation
- [x] Repository pattern

#### 🚧 Phase 3: AI Integration (In Progress)
- [ ] AI model loading and inference
- [ ] Multi-model pipeline implementation
- [ ] Code generation service
- [ ] Real-time streaming
- [ ] Quality scoring

#### 📋 Phase 4: Advanced Features (Planned)
- [ ] GitHub integration
- [ ] Template system
- [ ] Billing integration
- [ ] Advanced analytics
- [ ] Performance optimization

### Code Quality Standards

#### Formatting & Linting
```bash
# Format code
poetry run black .
poetry run isort .

# Type checking
poetry run mypy app/

# Run pre-commit hooks
poetry run pre-commit run --all-files
```

#### Git Workflow
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/your-feature-name
```

## 📊 Performance & Monitoring

### Metrics Tracked
- **Generation Time**: End-to-end code generation performance
- **Quality Scores**: AI-generated code quality metrics
- **User Engagement**: Project creation and iteration rates
- **Model Performance**: Individual AI model accuracy and speed

### Health Monitoring
- **Health Check**: `GET /health` - System status
- **Database**: Connection pool and query performance
- **Redis**: Cache hit rates and connection status
- **AI Models**: Model loading status and inference times

## 🔒 Security Features

### Authentication & Authorization
- JWT token-based authentication
- Role-based access control (RBAC)
- Secure password hashing with bcrypt
- Token refresh mechanism

### API Security
- Rate limiting on all endpoints
- CORS configuration
- Request validation with Pydantic
- SQL injection prevention
- XSS protection headers

### Data Protection
- Encrypted sensitive data storage
- Secure environment variable handling
- Database connection encryption
- API key rotation support

## 🤖 AI Pipeline Details

### Schema Extraction (Llama-3.1-8B)
- Parses natural language requirements
- Extracts entities, relationships, and constraints
- Generates database schema suggestions
- Handles complex domain modeling

### Code Generation (Qwen2.5-Coder-32B)
- Fine-tuned on FastAPI and clean architecture patterns
- Generates complete project structures
- Implements best practices and patterns
- Supports multiple tech stacks

### Code Review (Starcoder2-15B)
- Security vulnerability detection
- Performance optimization suggestions
- Code quality assessment
- Best practices validation

### Documentation (Mistral-7B-Instruct)
- README generation
- API documentation
- Code comments and docstrings
- Deployment guides

## 🌐 API Examples

### Generate a Complete FastAPI Project

```python
import httpx

# Authentication
auth_response = httpx.post("http://localhost:8000/auth/login", json={
    "username": "user@example.com",
    "password": "your-password"
})
token = auth_response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# Create a project
project_response = httpx.post(
    "http://localhost:8000/projects/",
    json={
        "name": "E-commerce API",
        "description": "A complete e-commerce backend with products, orders, and payments",
        "domain": "ecommerce",
        "tech_stack": ["FastAPI", "PostgreSQL", "Redis"],
        "is_public": False
    },
    headers=headers
)
project_id = project_response.json()["id"]

# Start AI generation
generation_response = httpx.post(
    "http://localhost:8000/generations/",
    json={
        "project_id": project_id,
        "prompt": """
        Create a complete e-commerce API with:
        - User authentication and profiles
        - Product catalog with categories and inventory
        - Shopping cart functionality
        - Order processing and payment integration
        - Admin dashboard for management
        - Inventory tracking
        - Email notifications
        - Comprehensive testing
        """,
        "context": {
            "complexity": "high",
            "include_tests": True,
            "include_docs": True,
            "deployment_target": "docker"
        }
    },
    headers=headers
)

generation_id = generation_response.json()["id"]

# Monitor progress via WebSocket or polling
status_response = httpx.get(
    f"http://localhost:8000/generations/{generation_id}",
    headers=headers
)
print(status_response.json())
```

### Stream Generation Progress

```javascript
// WebSocket connection for real-time updates
const ws = new WebSocket(`ws://localhost:8000/generations/${generationId}/stream`);

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log(`Progress: ${data.progress}% - ${data.stage}`);
    
    if (data.status === 'completed') {
        console.log('Generation completed!');
        console.log('Files generated:', data.files);
    }
};
```

## 📚 Documentation Links

- **[Architecture Guide](docs/architecture.md)** - Detailed system architecture
- **[Deployment Guide](docs/deployment.md)** - Production deployment instructions
- **[API Reference](docs/openapi.yaml)** - Complete API documentation
- **[Development Setup](docs/development.md)** - Local development guide

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Style
- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write comprehensive docstrings
- Maintain test coverage above 90%

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** team for the excellent framework
- **Hugging Face** for the transformer models
- **SQLAlchemy** team for the powerful ORM
- **OpenAI** for inspiration in AI-powered development

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/codebegen-be/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/codebegen-be/discussions)
- **Email**: support@codebegen.com

---

**Built with ❤️ by the CodebeGen Team**

*Transform your ideas into production-ready backends with the power of AI.*
