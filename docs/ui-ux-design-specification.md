# CodeBEGen UI/UX Design Specification

## 🎨 Design System Overview

### Brand Identity
- **Product Name**: CodeBEGen
- **Tagline**: "All-in-One AI Backend Platform"
- **Mission**: Generate powerful backend code with AI. Seamlessly test it inside. CodeBEGen — no need to jump between tools!

### Visual Identity
- **Logo**: Dollar sign ($) with "CodeBEGen" in modern sans-serif typography
- **Style**: Modern, developer-focused, professional with tech-forward aesthetics
- **Target Audience**: Developers, technical teams, startup founders, enterprise development teams

## 🌈 Color Palette

### Primary Colors
```css
/* Primary Green - Brand Color */
--primary-green: #00FF88        /* Bright electric green for CTAs and highlights */
--primary-green-hover: #00E67A  /* Hover state for primary green */
--primary-green-light: #33FF9A  /* Light variant for backgrounds */
--primary-green-dark: #00CC6A   /* Dark variant for text */

/* Background Colors */
--bg-primary: #0A0A0A          /* Deep black primary background */
--bg-secondary: #1A1A1A        /* Secondary dark background */
--bg-tertiary: #2A2A2A         /* Elevated surface background */
--bg-code: #161616             /* Code editor background */

/* Text Colors */
--text-primary: #FFFFFF         /* Primary white text */
--text-secondary: #B3B3B3       /* Secondary gray text */
--text-muted: #666666          /* Muted text for less important content */
--text-accent: #00FF88         /* Accent text color */
```

### Semantic Colors
```css
/* Status Colors */
--success: #00FF88             /* Success states */
--warning: #FFB800             /* Warning states */
--error: #FF3333               /* Error states */
--info: #00B8FF                /* Information states */

/* Code Syntax Colors */
--syntax-keyword: #FF6B9D       /* Keywords in code */
--syntax-string: #00FF88        /* Strings */
--syntax-comment: #666666       /* Comments */
--syntax-function: #00B8FF      /* Functions */
--syntax-variable: #FFFFFF      /* Variables */
```

## 📱 Typography

### Font Stack
```css
/* Primary Font - Interface */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

/* Monospace Font - Code */
font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace;

/* Display Font - Headlines */
font-family: 'Manrope', 'Inter', sans-serif;
```

### Typography Scale
```css
/* Headlines */
--text-4xl: 3.5rem    /* 56px - Hero headlines */
--text-3xl: 2.5rem    /* 40px - Section headlines */
--text-2xl: 2rem      /* 32px - Page titles */
--text-xl: 1.5rem     /* 24px - Card titles */

/* Body Text */
--text-lg: 1.125rem   /* 18px - Large body text */
--text-base: 1rem     /* 16px - Default body text */
--text-sm: 0.875rem   /* 14px - Small text */
--text-xs: 0.75rem    /* 12px - Captions */

/* Code Text */
--code-lg: 1rem       /* 16px - Large code blocks */
--code-base: 0.875rem /* 14px - Default code */
--code-sm: 0.75rem    /* 12px - Inline code */
```

## 🏗 Layout System

### Grid System
- **Container Max Width**: 1440px
- **Breakpoints**:
  - Mobile: 320px - 768px
  - Tablet: 768px - 1024px
  - Desktop: 1024px - 1440px
  - Wide: 1440px+

### Spacing Scale
```css
/* Spacing Units */
--space-1: 0.25rem   /* 4px */
--space-2: 0.5rem    /* 8px */
--space-3: 0.75rem   /* 12px */
--space-4: 1rem      /* 16px */
--space-6: 1.5rem    /* 24px */
--space-8: 2rem      /* 32px */
--space-12: 3rem     /* 48px */
--space-16: 4rem     /* 64px */
--space-24: 6rem     /* 96px */
```

## 📄 Page Structure & User Flow

### 1. Landing Page

#### Hero Section
```
[Header Navigation]
┌─────────────────────────────────────────────────────────────┐
│ [$] CodeBEGen                           [Features] [Docs] [Get Started] │
└─────────────────────────────────────────────────────────────┘

[Hero Content - Full Viewport Height]
┌─────────────────────────────────────────────────────────────┐
│                                                               │
│    🚀 Ready for Launch                 [Phone Mockup 1]      │
│    ─────────────────────               [Phone Mockup 2]      │
│    All-in-One AI                                             │
│    Backend Platform                                          │
│                                                               │
│    Generate powerful backend code with AI. Seamlessly test   │
│    it inside.                                                │
│    CodeBEGen — no need to jump between tools!               │
│                                                               │
│    [Get Started] ←─ Primary CTA                              │
│                                                               │
│    [Sidebar: Ready endpoint management and code             │
│     editing. Take your backend development anywhere.]        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### Features Section
```
┌─────────────────────────────────────────────────────────────┐
│                     🎯 Core Features                         │
│                                                               │
│  [🤖 AI Code Generation]  [⚡ Real-time Testing]  [🔧 Templates] │
│   Generate production-      Test your APIs           Pre-built    │
│   ready backend code       instantly without        templates    │
│   with AI assistance       leaving the platform      for common   │
│                                                      use cases    │
│                                                               │
│  [📊 Analytics]          [🔐 Authentication]     [🚀 Deploy]     │
│   Track performance       Built-in auth             One-click     │
│   and usage metrics       and security             deployment    │
│                          features                              │
└─────────────────────────────────────────────────────────────┘
```

### 2. Template Selection Page

#### Layout Structure
```
[Header with Progress Indicator]
┌─────────────────────────────────────────────────────────────┐
│ [$] CodeBEGen    Step 1 of 3: Choose Template   [Dashboard] │
└─────────────────────────────────────────────────────────────┘

[Main Content Area]
┌─────────────────────────────────────────────────────────────┐
│                                                               │
│  🎯 Select Your Project Template                            │
│  ────────────────────────────────                           │
│  Choose a starting point for your backend project           │
│                                                               │
│  [Search Templates...                              ] 🔍      │
│                                                               │
│  📂 Categories:                                              │
│  [All] [Web APIs] [Microservices] [E-commerce] [SaaS] [More] │
│                                                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │   FastAPI   │ │   FastAPI   │ │   FastAPI   │            │
│  │    Basic    │ │   MongoDB   │ │ SQLAlchemy  │            │
│  │             │ │             │ │             │            │
│  │ ⭐⭐⭐⭐⭐    │ │ ⭐⭐⭐⭐☆    │ │ ⭐⭐⭐⭐⭐    │            │
│  │ [Use This]  │ │ [Use This]  │ │ [Use This]  │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │   Django    │ │   Express   │ │   Custom    │            │
│  │     REST    │ │   Node.js   │ │  Template   │            │
│  │             │ │             │ │             │            │
│  │ ⭐⭐⭐⭐☆    │ │ ⭐⭐⭐☆☆    │ │ ⭐⭐⭐⭐⭐    │            │
│  │ [Use This]  │ │ [Use This]  │ │ [Use This]  │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                               │
│                            [Continue →]                      │
└─────────────────────────────────────────────────────────────┘
```

### 3. Prompt & Configuration Page

#### Layout Structure
```
[Header with Progress]
┌─────────────────────────────────────────────────────────────┐
│ [$] CodeBEGen   Step 2 of 3: Configure Project  [Dashboard] │
└─────────────────────────────────────────────────────────────┘

[Split Layout - Configuration Left, Preview Right]
┌─────────────────────────┬───────────────────────────────────┐
│                         │                                   │
│  🎯 Project Details     │  📋 Preview Configuration        │
│  ─────────────────      │  ──────────────────────          │
│                         │                                   │
│  Project Name:          │  Template: FastAPI SQLAlchemy    │
│  [My Backend Project]   │  Features: 6 selected            │
│                         │  Entities: 3 defined             │
│  Description:           │  Endpoints: 12 generated         │
│  [Describe your...]     │                                   │
│                         │  ┌─────────────────────────┐      │
│  🔧 Features            │  │ POST /auth/login        │      │
│  ──────────             │  │ GET  /users/{id}        │      │
│  ☑ Authentication       │  │ POST /products          │      │
│  ☑ File Upload         │  │ GET  /products          │      │
│  ☑ Payments            │  │ PUT  /products/{id}     │      │
│  ☐ Real-time Updates   │  │ DELETE /products/{id}   │      │
│  ☑ Caching             │  │ ...                     │      │
│  ☐ Search              │  └─────────────────────────┘      │
│  ☐ Notifications       │                                   │
│  ☑ Admin Dashboard     │  Dependencies:                    │
│                         │  • fastapi                       │
│  📊 Data Models         │  • sqlalchemy                    │
│  ──────────────         │  • pydantic                      │
│  User:                  │  • python-multipart              │
│  • name: string         │  • python-jose                   │
│  • email: string        │  • passlib                       │
│  • password: string     │  • stripe                        │
│                         │  • redis                         │
│  Product:               │                                   │
│  • name: string         │                                   │
│  • price: decimal       │                                   │
│  • description: text    │                                   │
│                         │                                   │
│  [+ Add Model]          │                                   │
│                         │                                   │
│  [← Back] [Generate →]  │                                   │
│                         │                                   │
└─────────────────────────┴───────────────────────────────────┘
```

### 4. Code Generation & File Tree Page

#### Layout Structure
```
[Header with Progress]
┌─────────────────────────────────────────────────────────────┐
│ [$] CodeBEGen   Step 3 of 3: Generated Code     [Dashboard] │
└─────────────────────────────────────────────────────────────┘

[Three-Panel Layout]
┌─────────────┬─────────────────────────────┬─────────────────┐
│             │                             │                 │
│  📁 Files   │  📝 Code Editor            │  🔧 Actions     │
│  ────────   │  ────────────────           │  ─────────      │
│             │                             │                 │
│ my-project/ │  app/main.py               │  [⬇ Download]   │
│ ├📁 app/    │  ┌─────────────────────┐   │  [📋 Copy All]  │
│ │├📄main.py │  │"""                  │   │  [🚀 Deploy]    │
│ │├📁core/   │  │FastAPI application  │   │  [🧪 Test API]  │
│ ││├config.py│  │generated by         │   │                 │
│ ││└database │  │Advanced Template    │   │  📊 Statistics  │
│ │├📁models/ │  │System               │   │  ─────────────  │
│ ││├user.py  │  │"""                  │   │                 │
│ ││└product  │  │                     │   │  Files: 23      │
│ │├📁routers│  │from fastapi import  │   │  Lines: 1,847   │
│ ││├auth.py  │  │FastAPI              │   │  Features: 6    │
│ ││├users.py │  │from fastapi.middle  │   │  Models: 3      │
│ ││└products │  │ware.cors import     │   │                 │
│ │├📁services│  │CORSMiddleware       │   │  🧪 Quick Test  │
│ ││├auth_srv │  │                     │   │  ─────────────  │
│ ││└file_upl │  │# Feature router     │   │                 │
│ │├📁schemas│  │imports              │   │  GET /health    │
│ ││├auth.py  │  │from app.routers.auth│   │  [▶ Test]       │
│ ││└user.py  │  │import router as     │   │                 │
│ │└📁middlew │  │auth_router          │   │  POST /auth/    │
│ │ └auth_mid │  │from app.routers.    │   │  login          │
│ ├📄require  │  │file_upload import   │   │  [▶ Test]       │
│ ├📄.env.ex  │  │router as file_up    │   │                 │
│ └📄README   │  │load_router          │   │  GET /users     │
│             │  │                     │   │  [▶ Test]       │
│ [Expand All]│  │app = FastAPI(       │   │                 │
│ [Collapse]  │  │    title="Generated │   │  [View All →]   │
│             │  │    API",            │   │                 │
│             │  │    description="API │   │                 │
│             │  │    generated using  │   │                 │
│             │  └─────────────────────┘   │                 │
│             │                             │                 │
│             │  Syntax: Python ▼          │                 │
│             │  Theme: Dark ▼             │                 │
│             │                             │                 │
└─────────────┴─────────────────────────────┴─────────────────┘
```

## 🎨 Component Design System

### Buttons
```css
/* Primary Button - Green CTA */
.btn-primary {
  background: linear-gradient(135deg, #00FF88 0%, #00E67A 100%);
  color: #0A0A0A;
  font-weight: 600;
  border-radius: 8px;
  padding: 12px 24px;
  border: none;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(0, 255, 136, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 255, 136, 0.4);
}

/* Secondary Button - Outline */
.btn-secondary {
  background: transparent;
  color: #FFFFFF;
  border: 2px solid #2A2A2A;
  border-radius: 8px;
  padding: 10px 22px;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  border-color: #00FF88;
  color: #00FF88;
}

/* Ghost Button - Minimal */
.btn-ghost {
  background: transparent;
  color: #B3B3B3;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.btn-ghost:hover {
  background: #1A1A1A;
  color: #FFFFFF;
}
```

### Cards
```css
.card {
  background: #1A1A1A;
  border: 1px solid #2A2A2A;
  border-radius: 12px;
  padding: 24px;
  transition: all 0.3s ease;
}

.card:hover {
  border-color: #00FF88;
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(0, 255, 136, 0.1);
}

.card-template {
  text-align: center;
  cursor: pointer;
}

.card-template.selected {
  border-color: #00FF88;
  background: rgba(0, 255, 136, 0.05);
}
```

### Form Elements
```css
.input {
  background: #161616;
  border: 2px solid #2A2A2A;
  border-radius: 8px;
  padding: 12px 16px;
  color: #FFFFFF;
  font-size: 14px;
  transition: all 0.2s ease;
}

.input:focus {
  border-color: #00FF88;
  outline: none;
  box-shadow: 0 0 0 3px rgba(0, 255, 136, 0.1);
}

.checkbox {
  position: relative;
  width: 20px;
  height: 20px;
}

.checkbox:checked {
  background: #00FF88;
  border-color: #00FF88;
}

.checkbox:checked::after {
  content: "✓";
  color: #0A0A0A;
  font-weight: bold;
}
```

### Code Editor Theme
```css
.code-editor {
  background: #161616;
  border: 1px solid #2A2A2A;
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  line-height: 1.5;
}

.code-line-numbers {
  color: #666666;
  user-select: none;
  padding-right: 16px;
}

.code-content {
  color: #FFFFFF;
  padding: 16px;
}

/* Syntax Highlighting */
.keyword { color: #FF6B9D; }
.string { color: #00FF88; }
.comment { color: #666666; }
.function { color: #00B8FF; }
.variable { color: #FFFFFF; }
.operator { color: #FFB800; }
```

### File Tree
```css
.file-tree {
  background: #1A1A1A;
  border-radius: 8px;
  padding: 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
}

.file-tree-item {
  padding: 4px 8px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.file-tree-item:hover {
  background: #2A2A2A;
}

.file-tree-item.selected {
  background: rgba(0, 255, 136, 0.1);
  color: #00FF88;
}

.file-tree-icon {
  margin-right: 8px;
  width: 16px;
  display: inline-block;
}

.folder-icon::before { content: "📁"; }
.file-icon::before { content: "📄"; }
.python-icon::before { content: "🐍"; }
.config-icon::before { content: "⚙️"; }
```

## 🎭 Interactive States & Animations

### Micro-Interactions
```css
/* Button Press Animation */
@keyframes button-press {
  0% { transform: scale(1); }
  50% { transform: scale(0.95); }
  100% { transform: scale(1); }
}

/* Success State Animation */
@keyframes success-pulse {
  0% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(0, 255, 136, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); }
}

/* Loading Spinner */
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-spinner {
  border: 3px solid #2A2A2A;
  border-top: 3px solid #00FF88;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  animation: spin 1s linear infinite;
}

/* Code Generation Progress */
@keyframes progress-glow {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.progress-bar {
  background: linear-gradient(
    90deg,
    #2A2A2A 25%,
    #00FF88 50%,
    #2A2A2A 75%
  );
  background-size: 200% 100%;
  animation: progress-glow 2s ease-in-out infinite;
}
```

### Hover Effects
```css
/* Template Card Hover */
.template-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 
    0 20px 40px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(0, 255, 136, 0.5);
}

/* File Tree Item Hover */
.file-item:hover {
  background: linear-gradient(90deg, transparent, rgba(0, 255, 136, 0.1), transparent);
  border-left: 3px solid #00FF88;
}

/* Button Glow Effect */
.btn-primary:hover {
  box-shadow: 
    0 6px 20px rgba(0, 255, 136, 0.4),
    0 0 0 1px rgba(0, 255, 136, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}
```

## 📱 Responsive Design

### Mobile Layout Adaptations

#### Mobile Landing Page
```css
@media (max-width: 768px) {
  .hero-section {
    flex-direction: column;
    text-align: center;
    padding: 60px 20px;
  }
  
  .hero-title {
    font-size: 2.5rem;
    line-height: 1.2;
  }
  
  .hero-phones {
    display: none; /* Hide phone mockups on mobile */
  }
  
  .features-grid {
    grid-template-columns: 1fr;
    gap: 20px;
  }
}
```

#### Mobile Template Selection
```css
@media (max-width: 768px) {
  .template-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .template-card {
    padding: 20px;
  }
  
  .category-tabs {
    overflow-x: auto;
    padding-bottom: 10px;
  }
}
```

#### Mobile Code Editor
```css
@media (max-width: 768px) {
  .code-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr auto;
  }
  
  .file-tree {
    max-height: 200px;
    overflow-y: auto;
  }
  
  .code-editor {
    min-height: 400px;
  }
  
  .actions-panel {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #1A1A1A;
    border-top: 1px solid #2A2A2A;
    padding: 16px;
  }
}
```

## 🔧 Technical Implementation Notes

### Performance Considerations
1. **Code Editor**: Use virtual scrolling for large files
2. **File Tree**: Lazy loading for deeply nested structures
3. **Syntax Highlighting**: Web Workers for large code blocks
4. **Real-time Preview**: Debounced updates (300ms delay)

### Accessibility Features
1. **Keyboard Navigation**: Full keyboard support for all interactions
2. **Screen Readers**: Proper ARIA labels and descriptions
3. **High Contrast**: Alternative high-contrast theme option
4. **Focus Management**: Clear focus indicators and logical tab order

### Browser Support
- **Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Fallbacks**: Graceful degradation for older browsers
- **Progressive Enhancement**: Core functionality works without JavaScript

## 🚀 Future Enhancements

### Phase 2 Features
1. **Dark/Light Theme Toggle**: User preference system
2. **Collaborative Editing**: Real-time multi-user code editing
3. **Version History**: Git-like version control for generated code
4. **Custom Themes**: User-defined color schemes and layouts

### Phase 3 Features
1. **AI Code Explanation**: Hover tooltips explaining generated code
2. **Code Optimization Suggestions**: AI-powered code improvement hints
3. **Integration Marketplace**: Third-party integrations and plugins
4. **Advanced Analytics**: Detailed usage and performance metrics

## 📋 Implementation Checklist

### Design System Setup
- [ ] Define CSS custom properties for all colors and spacing
- [ ] Create reusable component library (buttons, cards, inputs)
- [ ] Set up typography scale and font loading
- [ ] Implement responsive grid system

### Page Implementation
- [ ] Landing page with hero section and features
- [ ] Template selection with filtering and search
- [ ] Configuration page with real-time preview
- [ ] Code generation with three-panel layout

### Interactive Features
- [ ] Template selection and customization
- [ ] Real-time code preview and syntax highlighting
- [ ] File tree navigation with expand/collapse
- [ ] Copy/download functionality for generated code

### Testing & Optimization
- [ ] Cross-browser testing and compatibility
- [ ] Mobile responsiveness and touch interactions
- [ ] Performance optimization and lazy loading
- [ ] Accessibility testing and ARIA implementation

---

*This design specification serves as the foundation for building a modern, developer-focused UI that emphasizes clarity, efficiency, and visual appeal while maintaining the brand's tech-forward aesthetic.*
