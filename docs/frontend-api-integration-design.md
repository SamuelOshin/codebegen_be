# 🎨 Frontend API Integration Design

## 📋 Overview

This document outlines the complete frontend API integration strategy for CodeBEGen, covering all user flow pages and their corresponding backend interactions. The design leverages the unified generation router for code generation while providing a seamless user experience across the application.

---

## 🌊 User Flow & API Mapping

### Page Flow Summary
1. **Landing Page** → Authentication & User Status
2. **Template Selection** (Step 1/3) → Template Management APIs  
3. **Configuration** (Step 2/3) → Project Creation & Validation APIs
4. **Code Generation** (Step 3/3) → Unified Generation Router & File Management

### 🔄 Data Flow Between Steps

**Critical Integration Pattern**: Each step preserves and builds upon data from previous steps:

```typescript
// Step 1: Template Selection
const selectedTemplate = {
  name: "fastapi_sqlalchemy",
  display_name: "FastAPI with SQLAlchemy",
  tech_stack: ["fastapi", "postgresql", "sqlalchemy"]
};

// Step 2: Configuration (preserves template + adds config)
const projectConfig = {
  name: "My E-commerce API",
  domain: "ecommerce",
  tech_stack: selectedTemplate.tech_stack,  // Inherited from Step 1
  settings: {
    selected_template: selectedTemplate.name,  // ⭐ Template preserved
    features: ["authentication", "crud", "testing"],
    data_models: [/* user-defined models */],
    api_endpoints: [/* user-defined endpoints */]
  }
};

// Step 3: Generation (combines all previous data)
const generationRequest = {
  prompt: "Create an e-commerce API with user management",
  project_id: projectConfig.id,               // Links to saved project
  context: {
    project_config: projectConfig,            // ⭐ Complete config from Step 2
    selected_template: selectedTemplate.name, // ⭐ Template from Step 1
    user_preferences: userCustomizations      // Additional customizations
  },
  tech_stack: projectConfig.tech_stack,       // Derived from template
  domain: projectConfig.domain,               // From configuration
  generation_mode: "enhanced"
};
```

**Key Integration Points:**
- 🔗 **Template → Configuration**: Template choice influences available features and tech stack options
- 🔗 **Configuration → Generation**: Project config becomes generation context
- 🔗 **Preservation**: Both template and configuration data are preserved in the final generation request

---

## 🔐 Authentication Flow

### Initial App Load
```typescript
// Check authentication status on app startup
interface AuthenticationCheck {
  endpoint: 'GET /auth/me'
  purpose: 'Validate existing JWT token and get user data'
  response: UserResponse | 401
  frontend_action: 'Redirect to login or proceed to dashboard'
}
```

### User Registration/Login
```typescript
// Registration flow
interface UserRegistration {
  endpoint: 'POST /auth/register'
  payload: {
    username: string
    email: string
    password: string
    full_name: string
  }
  response: UserResponse
  frontend_action: 'Auto-login and redirect to dashboard'
}

// Login flow  
interface UserLogin {
  endpoint: 'POST /auth/login'
  payload: {
    username: string  // OAuth2PasswordRequestForm format
    password: string
  }
  response: {
    access_token: string
    token_type: "bearer"
    expires_in: number
  }
  frontend_action: 'Store token and redirect to dashboard'
}
```

---

## 🏠 Landing Page API Integration

### User Dashboard Data
```typescript
interface DashboardData {
  user_info: {
    endpoint: 'GET /auth/me'
    purpose: 'Get current user profile and subscription status'
  }
  
  recent_projects: {
    endpoint: 'GET /projects/?limit=5&sort_by=updated_at'
    purpose: 'Show user\'s 5 most recent projects'
  }
  
  quick_stats: {
    endpoint: 'GET /projects/stats'  // Custom aggregation endpoint
    purpose: 'Show total projects, generations, etc.'
  }
}
```

### Implementation Pattern
```typescript
// Frontend service for landing page
class LandingPageService {
  async loadDashboardData(): Promise<DashboardData> {
    const [user, projects, stats] = await Promise.all([
      this.authService.getCurrentUser(),
      this.projectService.getRecentProjects(5),
      this.projectService.getStats()
    ]);
    
    return { user, projects, stats };
  }
}
```

---

## 📋 Template Selection Page (Step 1/3)

### Template Discovery
```typescript
interface TemplateSelection {
  // Get available templates
  load_templates: {
    endpoint: 'GET /templates/'
    purpose: 'Load all available project templates with metadata'
    response: {
      templates: Array<{
        name: string                    // "fastapi_basic", "fastapi_sqlalchemy" 
        display_name: string           // "FastAPI Basic"
        description: string            // Human readable description
        tech_stack: string[]          // ["fastapi", "postgresql", "sqlalchemy"]
      }>
    }
  }
  
  // Search and filter templates
  search_templates: {
    endpoint: 'GET /templates/search'
    query_params: {
      query?: string                 // Search query (min 2, max 100 chars)
      domain?: string               // Filter by domain
      tech_stack?: string[]         // Filter by tech stack
      complexity?: string           // Filter by complexity (low, medium, high)
      features?: string[]           // Filter by features
    }
    purpose: 'Enable template search and filtering'
    response_model: 'TemplateSearchResponse'
  }
}
```

### Frontend Implementation
```typescript
class TemplateSelectionService {
  async loadTemplates(): Promise<Template[]> {
    const response = await this.apiClient.get('/templates/');
    return response.data.templates;
  }
  
  async searchTemplates(searchParams: {
    query?: string;
    domain?: string;
    tech_stack?: string[];
    complexity?: string;
    features?: string[];
  }): Promise<TemplateSearchResponse> {
    const params = new URLSearchParams();
    
    if (searchParams.query) params.append('query', searchParams.query);
    if (searchParams.domain) params.append('domain', searchParams.domain);
    if (searchParams.tech_stack) {
      searchParams.tech_stack.forEach(stack => params.append('tech_stack', stack));
    }
    if (searchParams.complexity) params.append('complexity', searchParams.complexity);
    if (searchParams.features) {
      searchParams.features.forEach(feature => params.append('features', feature));
    }
    
    const response = await this.apiClient.get(`/templates/search?${params}`);
    return response.data;
  }
}
```

---

## ⚙️ Configuration Page (Step 2/3)

### Project Configuration
```typescript
interface ProjectConfiguration {
  // Create project draft (save configuration)
  create_project_draft: {
    endpoint: 'POST /projects/'
    payload: {
      name: string
      description: string
      domain: DomainType                    // From unified_generation schema
      tech_stack: string[]                  // Selected tech stack components
      constraints: Record<string, any>      // Domain-specific constraints
      settings: {
        selected_template: string
        features: string[]                  // Enabled features
        data_models: Array<{
          name: string
          fields: Array<{
            name: string
            type: string
            required: boolean
            description?: string
          }>
        }>
        api_endpoints: Array<{
          method: string
          path: string
          description: string
          enabled: boolean
        }>
      }
      status: "draft"                       // Mark as draft initially
    }
    purpose: 'Save configuration before generation'
  }
  
  // Validate configuration
  validate_configuration: {
    endpoint: 'POST /projects/validate'     // New endpoint for validation
    payload: 'Same as create_project_draft'
    purpose: 'Validate configuration without saving'
    response: {
      valid: boolean
      errors: Array<{
        field: string
        message: string
        code: string
      }>
      warnings: Array<{
        field: string
        message: string
        suggestion: string
      }>
      estimated_files: number
      estimated_endpoints: number
      estimated_generation_time: number
    }
  }
  
  // Get configuration preview
  configuration_preview: {
    endpoint: 'POST /projects/preview'      // New endpoint for preview
    payload: 'Same as create_project_draft'
    purpose: 'Generate preview of what will be created'
    response: {
      file_structure: Array<{
        path: string
        type: "file" | "folder"
        description: string
        estimated_lines: number
      }>
      endpoints: Array<{
        method: string
        path: string
        description: string
        request_schema?: any
        response_schema?: any
      }>
      dependencies: Array<{
        package: string
        version: string
        purpose: string
      }>
    }
  }
}
```

### Real-time Validation
```typescript
class ConfigurationService {
  // Real-time validation as user types
  async validateConfiguration(config: ProjectConfiguration): Promise<ValidationResult> {
    try {
      const response = await this.apiClient.post('/projects/validate', config);
      return response.data;
    } catch (error) {
      return {
        valid: false,
        errors: [{ field: 'general', message: 'Validation failed', code: 'VALIDATION_ERROR' }],
        warnings: [],
        estimated_files: 0,
        estimated_endpoints: 0,
        estimated_generation_time: 0
      };
    }
  }
  
  // Debounced validation for real-time feedback
  validateConfigurationDebounced = debounce(this.validateConfiguration.bind(this), 500);
  
  // Generate preview
  async getConfigurationPreview(config: ProjectConfiguration): Promise<ConfigurationPreview> {
    const response = await this.apiClient.post('/projects/preview', config);
    return response.data;
  }
}
```

---

## 🚀 Code Generation Page (Step 3/3)

### Generation Process Flow
```typescript
interface CodeGenerationFlow {
  // Step 1: Initiate generation using Unified Router
  start_generation: {
    endpoint: 'POST /api/v2/generation/generate'  // Unified Generation Router
    payload: {
      prompt: string                    // Detailed project description
      tech_stack: TechStack            // From unified_generation schema  
      domain: DomainType               // From unified_generation schema
      context: {
        project_config: any             // From configuration page
        selected_template: string       // From template selection
        user_preferences: any           // User customizations
      }
      constraints: string[]             // Technical constraints
      generation_mode: "enhanced"       // Use enhanced mode for UI
      project_id?: string              // Link to created project
    }
    response: {
      generation_id: string
      status: GenerationStatus
      estimated_completion_time: number
      stream_url: string               // For real-time updates
    }
  }
  
  // Step 2: Stream real-time progress
  stream_progress: {
    endpoint: 'GET /api/v2/generation/generate/{id}/stream'
    purpose: 'Real-time generation progress updates'
    response_stream: StreamingProgressEvent[]
    event_types: [
      "generation_started",
      "parsing_schema", 
      "generating_code",
      "reviewing_code",
      "generating_docs",
      "finalizing_files",
      "generation_complete",
      "generation_error"
    ]
  }
  
  // Step 3: Get generation results
  get_results: {
    endpoint: 'GET /generations/{generation_id}'
    purpose: 'Get final generation results'
    response: {
      id: string
      status: GenerationStatus
      artifacts: Array<{
        type: ArtifactType
        file_path: string
        content: string
        language: string
        description: string
      }>
      quality_score: number
      review_comments: string[]
      execution_time: number
      created_at: string
    }
  }
  
  // Step 4: Download/Export options
  download_project: {
    endpoint: 'GET /generations/{generation_id}/download'
    purpose: 'Download complete project as ZIP'
    response: 'Binary ZIP file'
  }
  
  deploy_to_github: {
    endpoint: 'POST /generations/{generation_id}/deploy/github'
    payload: {
      repository_name: string
      description: string
      private: boolean
      initialize_readme: boolean
    }
    purpose: 'Deploy directly to GitHub repository'
  }
}
```

### Real-time Generation UI
```typescript
class GenerationService {
  async startGeneration(config: GenerationConfig): Promise<GenerationResponse> {
    // Build context from previous steps
    const generationContext = {
      project_config: config.project_config,     // Complete config from Step 2
      selected_template: config.selected_template, // Template from Step 1
      user_preferences: config.user_preferences   // Any additional customizations
    };
    
    const response = await this.apiClient.post('/api/v2/generation/generate', {
      prompt: this.buildPromptFromConfig(config),
      tech_stack: config.tech_stack,              // Derived from template
      domain: config.domain,                      // From configuration
      context: generationContext,                 // ⭐ Combined data from all steps
      constraints: config.constraints,
      generation_mode: "enhanced",
      project_id: config.project_id               // Links to saved project
    });
    
    return response.data;
  }
  
  // Helper to build enhanced prompt from template + config
  private buildPromptFromConfig(config: GenerationConfig): string {
    const template = config.selected_template;
    const features = config.project_config.settings.features;
    const models = config.project_config.settings.data_models;
    
    return `Generate a ${config.domain} project using ${template} template. 
            Include features: ${features.join(', ')}.
            Data models: ${models.map(m => m.name).join(', ')}.
            ${config.prompt}`;
  }
  
  // Server-Sent Events for real-time progress
  subscribeToProgress(generationId: string): EventSource {
    const eventSource = new EventSource(`/api/v2/generation/generate/${generationId}/stream`);
    
    eventSource.onmessage = (event) => {
      const progressEvent: StreamingProgressEvent = JSON.parse(event.data);
      this.handleProgressUpdate(progressEvent);
    };
    
    return eventSource;
  }
  
  private handleProgressUpdate(event: StreamingProgressEvent) {
    switch (event.event_type) {
      case "generation_started":
        this.updateUI("Initializing generation...", 0);
        break;
      case "parsing_schema":
        this.updateUI("Analyzing project requirements...", 15);
        break;
      case "generating_code":
        this.updateUI("Generating code files...", 40);
        break;
      case "reviewing_code":
        this.updateUI("Reviewing code quality...", 70);
        break;
      case "generating_docs":
        this.updateUI("Creating documentation...", 85);
        break;
      case "finalizing_files":
        this.updateUI("Finalizing project structure...", 95);
        break;
      case "generation_complete":
        this.updateUI("Generation complete!", 100);
        this.loadGenerationResults(event.generation_id);
        break;
      case "generation_error":
        this.handleGenerationError(event.error_message);
        break;
    }
  }
}
```

---

## 🗂️ File Explorer & Code Viewer

### File Management APIs
```typescript
interface FileManagement {
  // Get file tree structure
  get_file_tree: {
    endpoint: 'GET /generations/{generation_id}/files'
    purpose: 'Get hierarchical file structure'
    response: {
      root: FileNode
    }
  }
  
  // Get individual file content
  get_file_content: {
    endpoint: 'GET /generations/{generation_id}/files/{file_path}'
    purpose: 'Get content of specific file'
    response: {
      content: string
      language: string
      size: number
      last_modified: string
    }
  }
  
  // Search within generated files
  search_files: {
    endpoint: 'GET /generations/{generation_id}/search'
    query_params: {
      q: string                        // Search query
      file_types?: string[]           // Filter by file types
      case_sensitive?: boolean
    }
    purpose: 'Search for text within generated files'
  }
}

interface FileNode {
  name: string
  path: string
  type: "file" | "folder"
  children?: FileNode[]
  size?: number
  language?: string
  description?: string
}
```

### File Explorer Component
```typescript
class FileExplorerService {
  async getFileTree(generationId: string): Promise<FileNode> {
    const response = await this.apiClient.get(`/generations/${generationId}/files`);
    return response.data.root;
  }
  
  async getFileContent(generationId: string, filePath: string): Promise<FileContent> {
    const response = await this.apiClient.get(`/generations/${generationId}/files/${encodeURIComponent(filePath)}`);
    return response.data;
  }
  
  async searchFiles(generationId: string, query: string, options?: SearchOptions): Promise<SearchResult[]> {
    const params = new URLSearchParams({ q: query });
    if (options?.file_types) options.file_types.forEach(type => params.append('file_types', type));
    if (options?.case_sensitive) params.append('case_sensitive', 'true');
    
    const response = await this.apiClient.get(`/generations/${generationId}/search?${params}`);
    return response.data.results;
  }
}
```

---

## 🔄 Iteration & Enhancement Flow

### Iterative Improvements
```typescript
interface IterationFlow {
  // Request code iteration/modification  
  iterate_generation: {
    endpoint: 'POST /api/v2/generation/iterate'  // Unified Router iteration endpoint
    payload: {
      prompt: string                    // Modification request
      tech_stack: TechStack
      domain: DomainType 
      parent_generation_id: string      // Original generation to modify
      project_id: string               // Associated project
      is_iteration: true
      context: {
        modification_type: "add_feature" | "fix_bug" | "refactor" | "optimize"
        target_files?: string[]         // Specific files to modify
        preserve_files?: string[]       // Files to keep unchanged
      }
      constraints: string[]
      generation_mode: "enhanced"
    }
    purpose: 'Create modified version of existing generation'
  }
  
  // Compare versions
  compare_generations: {
    endpoint: 'GET /generations/compare/{generation_id_1}/{generation_id_2}'
    purpose: 'Compare two generations to show differences'
    response: {
      added_files: string[]
      modified_files: Array<{
        path: string
        changes: {
          additions: number
          deletions: number
          diff: string             // Unified diff format
        }
      }>
      deleted_files: string[]
      summary: string
    }
  }
}
```

---

## 📊 Project Management Integration

### Project Lifecycle APIs
```typescript
interface ProjectLifecycle {
  // Update project after generation
  update_project_status: {
    endpoint: 'PUT /projects/{project_id}'
    payload: {
      status: "active"                  // Change from draft to active
      github_repo_url?: string         // If deployed to GitHub
      last_generation_id: string       // Link to latest generation
      settings: {
        // Updated settings after generation
      }
    }
    purpose: 'Mark project as active after successful generation'
  }
  
  // Get project generations history
  get_project_generations: {
    endpoint: 'GET /projects/{project_id}/generations'
    purpose: 'Get all generations for a project'
    response: {
      generations: Array<{
        id: string
        status: GenerationStatus
        created_at: string
        quality_score: number
        is_iteration: boolean
        parent_generation_id?: string
      }>
      total: number
      page: number
    }
  }
  
  // Project analytics
  get_project_analytics: {
    endpoint: 'GET /projects/{project_id}/analytics'
    purpose: 'Get project metrics and usage statistics'
    response: {
      total_generations: number
      successful_generations: number
      average_quality_score: number
      most_used_features: string[]
      generation_trend: Array<{
        date: string
        count: number
      }>
    }
  }
}
```

---

## 🔧 Error Handling & User Experience

### Error Scenarios & Recovery
```typescript
interface ErrorHandling {
  // Handle authentication errors
  auth_errors: {
    401: "Token expired - redirect to login"
    403: "Insufficient permissions - show upgrade prompt"
  }
  
  // Handle validation errors
  validation_errors: {
    422: {
      action: "Show field-specific error messages"
      fields: "Map error.field to form field"
      recovery: "User can fix and retry"
    }
  }
  
  // Handle generation errors
  generation_errors: {
    500: "AI service error - retry with different parameters"
    503: "Service unavailable - queue for retry"
    timeout: "Generation timeout - partial results may be available"
  }
  
  // Handle rate limiting
  rate_limit_errors: {
    429: {
      action: "Show rate limit message with retry time"
      header: "Check Retry-After header"
      recovery: "Automatic retry or upgrade prompt"
    }
  }
}
```

### Loading States & Feedback
```typescript
class UserExperienceService {
  // Show appropriate loading states
  showLoadingState(operation: string, estimatedTime?: number) {
    switch (operation) {
      case "template_loading":
        return "Loading templates...";
      case "validation":
        return "Validating configuration...";
      case "generation":
        return `Generating code... (${estimatedTime}s estimated)`;
      case "file_loading":
        return "Loading files...";
    }
  }
  
  // Progressive enhancement for slow connections
  optimizeForConnection(connectionSpeed: "slow" | "normal" | "fast") {
    if (connectionSpeed === "slow") {
      // Reduce real-time updates frequency
      // Load files on-demand only
      // Use compression for API responses
    }
  }
}
```

---

## 🌐 API Client Configuration

### Base API Client Setup
```typescript
class CodeBEGenAPIClient {
  private baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  private client: AxiosInstance;
  
  constructor() {
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,  // 30 second timeout
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    // Request interceptor for auth
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
    
    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // Token expired, try to refresh
          await this.handleTokenRefresh();
        }
        return Promise.reject(error);
      }
    );
  }
  
  private async handleTokenRefresh() {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        const response = await this.client.post('/auth/refresh', {
          refresh_token: refreshToken
        });
        localStorage.setItem('access_token', response.data.access_token);
      }
    } catch (error) {
      // Refresh failed, redirect to login
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
  }
}
```

---

## 📱 State Management Strategy

### Global State Structure
```typescript
interface AppState {
  // Authentication state
  auth: {
    user: User | null
    isAuthenticated: boolean
    loading: boolean
  }
  
  // Template selection state
  templates: {
    available: Template[]
    selected: Template | null
    loading: boolean
    filters: TemplateFilters
  }
  
  // Project configuration state
  project: {
    current: ProjectConfiguration | null
    validation: ValidationResult | null
    preview: ConfigurationPreview | null
    loading: boolean
  }
  
  // Generation state
  generation: {
    current: GenerationResponse | null
    progress: StreamingProgressEvent[]
    files: FileNode | null
    selectedFile: FileContent | null
    loading: boolean
    error: string | null
  }
  
  // UI state
  ui: {
    currentStep: 1 | 2 | 3
    sidebarOpen: boolean
    theme: "light" | "dark"
    notifications: Notification[]
  }
}
```

### Redux/Zustand Store Actions
```typescript
// Example with Zustand
interface AppStore extends AppState {
  // Authentication actions
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
  
  // Template actions
  loadTemplates: () => Promise<void>
  selectTemplate: (template: Template) => void
  filterTemplates: (filters: TemplateFilters) => void
  
  // Project actions
  updateProjectConfig: (config: Partial<ProjectConfiguration>) => void
  validateConfiguration: () => Promise<void>
  saveProjectDraft: () => Promise<void>
  
  // Generation actions
  startGeneration: () => Promise<void>
  subscribeToProgress: (generationId: string) => void
  loadGenerationResults: (generationId: string) => Promise<void>
  selectFile: (filePath: string) => Promise<void>
  
  // UI actions
  setCurrentStep: (step: 1 | 2 | 3) => void
  toggleSidebar: () => void
  addNotification: (notification: Notification) => void
}
```

---

## 🎯 Implementation Checklist

### Phase 1: Core Integration (Week 1)
- [ ] Set up API client with authentication
- [ ] Implement authentication flow
- [ ] Create template selection page with API integration
- [ ] Build project configuration form with validation
- [ ] Test unified generation router integration

### Phase 2: Advanced Features (Week 2)
- [ ] Implement real-time generation progress
- [ ] Build file explorer and code viewer
- [ ] Add iteration and comparison features
- [ ] Integrate project management APIs
- [ ] Add download and GitHub deployment

### Phase 3: Polish & Optimization (Week 3)
- [ ] Implement comprehensive error handling
- [ ] Add loading states and user feedback
- [ ] Optimize for performance and slow connections
- [ ] Add analytics and user experience tracking
- [ ] Complete testing and documentation

---

## 🔗 Summary

This design provides a comprehensive frontend API integration strategy that:

1. **Leverages the Unified Generation Router** for all code generation operations
2. **Follows the UI/UX design specification** for the 3-step user flow
3. **Provides real-time feedback** through streaming progress updates
4. **Handles all error scenarios** gracefully with appropriate user feedback
5. **Supports iterative development** with comparison and modification features
6. **Integrates with project management** for complete lifecycle tracking

The frontend will have clear, predictable API interactions with robust error handling and an excellent user experience throughout the code generation process.
