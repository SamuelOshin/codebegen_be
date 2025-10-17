# Frontend API Migration Guide - URGENT UPDATES REQUIRED

**Date:** October 15, 2025  
**Status:** 🚨 CRITICAL - Immediate Action Required  
**Backend Version:** Current (Unified Router Deprecated)  
**Frontend Version:** Outdated (Using deprecated endpoints)

---

## 🚨 EXECUTIVE SUMMARY

The frontend is currently using **DEPRECATED API endpoints** that are marked for removal. This document outlines all required changes to migrate to the current, stable API structure.

### Critical Issues Identified

1. ❌ **Using Deprecated Unified Router** (`/api/v2/generation/*`)
2. ❌ **Incorrect SSE endpoint** for streaming
3. ❌ **Missing file management endpoints** integration
4. ❌ **No version management** implementation
5. ❌ **Incomplete generation metadata** handling
6. ✅ **Authentication endpoints** - OK (no changes needed)
7. ✅ **Project endpoints** - OK (no changes needed)
8. ✅ **Template endpoints** - OK (no changes needed)

---

## 📋 BREAKING CHANGES - IMMEDIATE ACTION REQUIRED

### 1. ❌ DEPRECATED: Unified Generation Endpoint

**Current Frontend Code (INCORRECT):**
```typescript
// lib/api/services/generation.ts - OUTDATED
async startGeneration(request: GenerationRequest): Promise<GenerationResponse> {
  return apiClient.post<GenerationResponse>(
    "/api/v2/generation/generate",  // ❌ DEPRECATED!
    request
  )
}
```

**✅ CORRECT Backend Endpoint:**
```typescript
// UPDATED - Use this instead
async startGeneration(request: GenerationRequest): Promise<GenerationResponse> {
  return apiClient.post<GenerationResponse>(
    "/generations/generate",  // ✅ CURRENT
    request
  )
}
```

**API Endpoint Change:**
- ❌ OLD: `POST /api/v2/generation/generate`
- ✅ NEW: `POST /generations/generate`

**Response Schema Change:**
```typescript
// OLD Response (v2 - DEPRECATED)
interface OldGenerationResponse {
  id: string
  user_id: string
  project_id: string
  prompt: string
  status: "pending" | "processing" | "completed" | "failed"
  context: any
  output_files: {}
  quality_score: number
  created_at: string
  updated_at: string
}

// ✅ NEW Response (Current)
interface UnifiedGenerationResponse {
  generation_id: string          // Changed from 'id'
  status: GenerationStatus
  message: string                 // New field
  user_id: string
  project_id: string
  prompt: string
  context: any
  generation_mode: GenerationMode // New field
  ab_group?: string              // New field
  enhanced_features?: string[]    // New field
  is_iteration: boolean          // New field
  parent_generation_id?: string  // New field
  created_at: datetime
  updated_at: datetime
}
```

---

### 2. ❌ DEPRECATED: SSE Streaming Endpoint

**Current Frontend Code (INCORRECT):**
```typescript
// lib/generation-monitor.ts - OUTDATED
startStreaming(): void {
  const url = `${baseUrl}/api/v2/generation/generate/${generationId}/stream`  // ❌ DEPRECATED!
  const authUrl = `${url}?token=${encodeURIComponent(token)}`
  
  this.eventSource = new EventSource(authUrl)
}
```

**✅ CORRECT Backend Endpoint:**
```typescript
// UPDATED - Use this instead
startStreaming(): void {
  const url = `${baseUrl}/generations/generate/${generationId}/stream`  // ✅ CURRENT
  const authUrl = `${url}?token=${encodeURIComponent(token)}`
  
  this.eventSource = new EventSource(authUrl)
}
```

**API Endpoint Change:**
- ❌ OLD: `GET /api/v2/generation/generate/{id}/stream`
- ✅ NEW: `GET /generations/generate/{generation_id}/stream`

**SSE Event Format (Updated):**
```typescript
// Current SSE event structure
interface StreamingProgressEvent {
  generation_id: string
  status: "pending" | "processing" | "completed" | "failed"
  stage: "context_analysis" | "code_generation" | "quality_assessment" | "complete"
  progress: number              // 0.0 to 1.0
  message: string
  ab_group?: string
  enhanced_features?: string[]
  generation_mode?: string
  timestamp: string
}
```

**Stage Names Changed:**
- ❌ OLD: `"parsing_schema"`, `"generating_code"`, `"reviewing_code"`, `"generating_docs"`, `"finalizing_files"`
- ✅ NEW: `"context_analysis"`, `"code_generation"`, `"quality_assessment"`, `"complete"`

---

### 3. ❌ DEPRECATED: Polling Status Endpoint

**Current Frontend Code (INCORRECT):**
```typescript
// lib/generation-monitor.ts - OUTDATED
private async poll(): Promise<void> {
  const response = await fetch(
    `${baseUrl}/api/v2/generation/${generationId}/status`,  // ❌ DEPRECATED!
    { headers: { 'Authorization': `Bearer ${token}` } }
  )
}
```

**✅ CORRECT Implementation:**
```typescript
// UPDATED - Use generation detail endpoint instead
private async poll(): Promise<void> {
  const response = await fetch(
    `${baseUrl}/generations/${generationId}`,  // ✅ CURRENT
    { headers: { 'Authorization': `Bearer ${token}` } }
  )
  
  const generation = await response.json()
  
  // Extract progress from generation status
  this.onProgress({
    generation_id: generation.id,
    status: generation.status,
    progress: this.calculateProgress(generation.status),
    message: this.getStatusMessage(generation.status),
    timestamp: new Date().toISOString()
  })
}

private calculateProgress(status: string): number {
  switch (status) {
    case 'pending': return 0.1
    case 'processing': return 0.5
    case 'completed': return 1.0
    case 'failed': return 0.0
    default: return 0.0
  }
}
```

**API Endpoint Change:**
- ❌ OLD: `GET /api/v2/generation/{id}/status` (dedicated polling endpoint)
- ✅ NEW: `GET /generations/{generation_id}` (use main detail endpoint)

---

### 4. ❌ DEPRECATED: Iteration Endpoint

**Current Frontend Code (INCORRECT):**
```typescript
// lib/api/services/generation.ts - OUTDATED
async iterateGeneration(request: IterationRequest): Promise<GenerationResponse> {
  return apiClient.post<GenerationResponse>(
    "/api/v2/generation/iterate",  // ❌ DEPRECATED!
    request
  )
}
```

**✅ CORRECT Backend Endpoint:**
```typescript
// UPDATED - Use this instead
async iterateGeneration(request: IterationRequest): Promise<GenerationResponse> {
  return apiClient.post<GenerationResponse>(
    "/generations/iterate",  // ✅ CURRENT
    request
  )
}
```

**API Endpoint Change:**
- ❌ OLD: `POST /api/v2/generation/iterate`
- ✅ NEW: `POST /generations/iterate`

**Request Schema (Same structure, just verify):**
```typescript
interface IterationRequest {
  prompt: string                    // New iteration prompt
  parent_generation_id: string      // Required
  project_id?: string              // Optional
  tech_stack: TechStack
  domain: DomainType
  context?: any
  is_iteration: true               // Must be true
  generation_mode?: GenerationMode
}
```

---

### 5. ⚠️ MISSING: File Management Endpoints

**Current Frontend Issue:**
The frontend has placeholders for file content loading but **endpoints may not be implemented correctly**.

**Current Frontend Code:**
```typescript
// app/generations/[id]/page.tsx - PARTIAL IMPLEMENTATION
try {
  const content = await generationService.getFileContent(generationId, filePath)
  setFileContent(content.content)
} catch (apiError) {
  setFileContent(getSampleFileContent(filePath))  // ❌ Hardcoded fallback
}
```

**✅ CORRECT Implementation Required:**

#### A. Get File Tree
```typescript
// lib/api/services/generation.ts - ADD THIS METHOD
async getFileTree(generationId: string): Promise<FileTreeResponse> {
  return apiClient.get<FileTreeResponse>(
    `/generations/${generationId}/files`
  )
}

interface FileTreeResponse {
  files: {
    root: FileNode
  }
}

interface FileNode {
  path: string
  type: "file" | "folder"
  children?: FileNode[]
  size?: number
  language?: string
}
```

**Backend Endpoint:**
- `GET /generations/{generation_id}/files`

#### B. Get Individual File Content
```typescript
// lib/api/services/generation.ts - ADD THIS METHOD
async getFileContent(
  generationId: string, 
  filePath: string
): Promise<GenerationFileResponse> {
  const encodedPath = encodeURIComponent(filePath)
  return apiClient.get<GenerationFileResponse>(
    `/generations/${generationId}/files/${encodedPath}`
  )
}

interface GenerationFileResponse {
  generation_id: string
  file_path: string
  content: string
  language: string
  size_bytes: number
  mime_type: string
  encoding: string
  last_modified: string
}
```

**Backend Endpoint:**
- `GET /generations/{generation_id}/files/{file_path}`

**❌ Remove Hardcoded Fallbacks:**
```typescript
// DELETE THIS FUNCTION
function getSampleFileContent(filePath: string): string {
  // Hardcoded sample code - REMOVE
}
```

---

### 6. ⚠️ MISSING: Version Management Endpoints

**Current Frontend:** Does NOT implement version management

**✅ REQUIRED Implementation:**

#### A. List Project Versions
```typescript
// lib/api/services/projects.ts - ADD THIS METHOD
async getProjectVersions(projectId: string): Promise<VersionListResponse> {
  return apiClient.get<VersionListResponse>(
    `/generations/projects/${projectId}/versions`
  )
}

interface VersionListResponse {
  project_id: string
  total_versions: number
  active_version: number
  latest_version: number
  versions: GenerationSummary[]
}

interface GenerationSummary {
  id: string
  version: number
  version_name?: string
  status: GenerationStatus
  is_active: boolean
  file_count: number
  quality_score: number
  created_at: string
  prompt_preview: string
}
```

**Backend Endpoint:**
- `GET /generations/projects/{project_id}/versions`

#### B. Get Active Version
```typescript
// lib/api/services/projects.ts - ADD THIS METHOD
async getActiveVersion(projectId: string): Promise<GenerationResponse> {
  return apiClient.get<GenerationResponse>(
    `/generations/projects/${projectId}/versions/active`
  )
}
```

**Backend Endpoint:**
- `GET /generations/projects/{project_id}/versions/active`

#### C. Activate Specific Version
```typescript
// lib/api/services/projects.ts - ADD THIS METHOD
async activateVersion(
  projectId: string, 
  generationId: string
): Promise<ActivateGenerationResponse> {
  return apiClient.post<ActivateGenerationResponse>(
    `/generations/projects/${projectId}/versions/${generationId}/activate`,
    {}
  )
}

interface ActivateGenerationResponse {
  success: boolean
  generation_id: string
  version: number
  message: string
  previous_active_id?: string
}
```

**Backend Endpoint:**
- `POST /generations/projects/{project_id}/versions/{generation_id}/activate`

#### D. Compare Versions
```typescript
// lib/api/services/projects.ts - ADD THIS METHOD
async compareVersions(
  projectId: string,
  fromVersion: number,
  toVersion: number
): Promise<VersionComparisonResponse> {
  return apiClient.get<VersionComparisonResponse>(
    `/generations/projects/${projectId}/versions/compare/${fromVersion}/${toVersion}`
  )
}

interface VersionComparisonResponse {
  project_id: string
  from_version: number
  to_version: number
  files_added: string[]
  files_removed: string[]
  files_modified: string[]
  files_unchanged: string[]
  size_change_bytes: number
  file_count_change: number
  quality_score_change: number
  unified_diff: string
  diff_summary: string
  time_between_versions: number
  created_at_from: string
  created_at_to: string
}
```

**Backend Endpoint:**
- `GET /generations/projects/{project_id}/versions/compare/{from_version}/{to_version}`

---

### 7. ⚠️ MISSING: Additional Generation Endpoints

**Current Frontend:** Missing several important generation endpoints

**✅ REQUIRED Implementation:**

#### A. Download Generation as ZIP
```typescript
// lib/api/services/generation.ts - UPDATE THIS METHOD
async downloadProject(generationId: string): Promise<Blob> {
  const response = await fetch(
    `${baseUrl}/generations/${generationId}/download`,  // ✅ CORRECT
    {
      headers: {
        'Authorization': `Bearer ${AuthUtils.getAccessToken()}`
      }
    }
  )
  
  if (!response.ok) {
    throw new Error('Download failed')
  }
  
  return await response.blob()
}
```

**Backend Endpoint:**
- `GET /generations/{generation_id}/download`

#### B. Search Within Files
```typescript
// lib/api/services/generation.ts - ADD THIS METHOD
async searchFiles(
  generationId: string,
  searchRequest: GenerationSearchRequest
): Promise<GenerationSearchResponse> {
  return apiClient.post<GenerationSearchResponse>(
    `/generations/${generationId}/search`,
    searchRequest
  )
}

interface GenerationSearchRequest {
  query: string
  case_sensitive?: boolean
  regex?: boolean
  file_pattern?: string
  max_results?: number
}

interface GenerationSearchResponse {
  generation_id: string
  query: string
  total_matches: number
  files_with_matches: number
  matches: SearchMatch[]
}

interface SearchMatch {
  file_path: string
  line_number: number
  line_content: string
  match_start: number
  match_end: number
  context_before: string[]
  context_after: string[]
}
```

**Backend Endpoint:**
- `POST /generations/{generation_id}/search`

#### C. Get Code Review
```typescript
// lib/api/services/generation.ts - ADD THIS METHOD
async getCodeReview(generationId: string): Promise<CodeReviewResponse> {
  return apiClient.get<CodeReviewResponse>(
    `/generations/${generationId}/review`
  )
}

interface CodeReviewResponse {
  generation_id: string
  quality_report: {
    overall_score: number
    overall_level: "poor" | "fair" | "good" | "excellent"
    total_files: number
    total_lines: number
    issues: CodeIssue[]
    metrics: {
      code_complexity: number
      test_coverage: number
      documentation_score: number
    }
    recommendations: string[]
  }
}

interface CodeIssue {
  file: string
  line: number
  severity: "error" | "warning" | "info"
  category: string
  message: string
  suggestion: string
}
```

**Backend Endpoint:**
- `GET /generations/{generation_id}/review`

#### D. Cancel Generation
```typescript
// lib/api/services/generation.ts - ADD THIS METHOD
async cancelGeneration(
  generationId: string,
  reason?: string
): Promise<GenerationResponse> {
  return apiClient.post<GenerationResponse>(
    `/generations/${generationId}/cancel`,
    { reason }
  )
}
```

**Backend Endpoint:**
- `POST /generations/{generation_id}/cancel`

#### E. Delete Generation
```typescript
// lib/api/services/generation.ts - ADD THIS METHOD
async deleteGeneration(
  generationId: string,
  options?: {
    cascade_files?: boolean
    cascade_metrics?: boolean
    cascade_iterations?: boolean
    force_delete?: boolean
    deletion_reason?: string
  }
): Promise<void> {
  const params = new URLSearchParams()
  if (options?.cascade_files !== undefined) {
    params.append('cascade_files', String(options.cascade_files))
  }
  if (options?.cascade_metrics !== undefined) {
    params.append('cascade_metrics', String(options.cascade_metrics))
  }
  if (options?.cascade_iterations !== undefined) {
    params.append('cascade_iterations', String(options.cascade_iterations))
  }
  if (options?.force_delete) {
    params.append('force_delete', 'true')
  }
  if (options?.deletion_reason) {
    params.append('deletion_reason', options.deletion_reason)
  }
  
  await apiClient.delete(`/generations/${generationId}?${params.toString()}`)
}
```

**Backend Endpoint:**
- `DELETE /generations/{generation_id}`

#### F. List Recent Generations
```typescript
// lib/api/services/generation.ts - ADD THIS METHOD
async getRecentGenerations(limit: number = 10): Promise<GenerationResponse[]> {
  return apiClient.get<GenerationResponse[]>(
    `/generations/recent?limit=${limit}`
  )
}
```

**Backend Endpoint:**
- `GET /generations/recent`

#### G. Get Generation Statistics
```typescript
// lib/api/services/generation.ts - ADD THIS METHOD
async getGenerationStatistics(): Promise<GenerationStatsResponse> {
  return apiClient.get<GenerationStatsResponse>('/generations/statistics')
}

interface GenerationStatsResponse {
  total_generations: number
  completed_generations: number
  failed_generations: number
  total_files_generated: number
  average_quality_score: number
  total_iterations: number
  most_used_tech_stack: string
  most_used_domain: string
}
```

**Backend Endpoint:**
- `GET /generations/statistics`

---

## 📊 COMPLETE API ENDPOINT MAPPING

### ✅ AUTHENTICATION (No Changes - Already Correct)

| Method | Current Frontend | Backend Endpoint | Status |
|--------|------------------|------------------|--------|
| POST | `/auth/login` | `/auth/login` | ✅ OK |
| POST | `/auth/register` | `/auth/register` | ✅ OK |
| POST | `/auth/refresh` | `/auth/refresh` | ✅ OK |
| GET | `/auth/me` | `/auth/me` | ✅ OK |
| POST | `/auth/logout` | `/auth/logout` | ✅ OK |

### ✅ PROJECTS (No Changes - Already Correct)

| Method | Current Frontend | Backend Endpoint | Status |
|--------|------------------|------------------|--------|
| GET | `/api/v1/projects/` | `/api/v1/projects/` | ✅ OK |
| POST | `/api/v1/projects/` | `/api/v1/projects/` | ✅ OK |
| GET | `/api/v1/projects/{id}/` | `/api/v1/projects/{id}` | ✅ OK |
| PUT | `/api/v1/projects/{id}/` | `/api/v1/projects/{id}` | ✅ OK |
| DELETE | `/api/v1/projects/{id}/` | `/api/v1/projects/{id}` | ✅ OK |
| GET | `/api/v1/projects/{id}/stats/` | `/api/v1/projects/{id}/stats` | ✅ OK |
| GET | `/api/v1/projects/search/` | `/api/v1/projects/search` | ✅ OK |

### ❌ GENERATIONS (CRITICAL CHANGES REQUIRED)

| Method | Current Frontend | Backend Endpoint | Status |
|--------|------------------|------------------|--------|
| POST | `/api/v2/generation/generate` | `/generations/generate` | ❌ **UPDATE** |
| GET | `/api/v2/generation/generate/{id}/stream` | `/generations/generate/{id}/stream` | ❌ **UPDATE** |
| GET | `/api/v2/generation/{id}/status` | `/generations/{id}` | ❌ **UPDATE** |
| POST | `/api/v2/generation/iterate` | `/generations/iterate` | ❌ **UPDATE** |
| GET | `/api/v1/generations/{id}` | `/generations/{id}` | ⚠️ **VERIFY** |
| GET | `/generations/` | `/generations/` | ✅ OK |
| GET | `/generations/{id}/download` | `/generations/{id}/download` | ✅ OK |
| GET | N/A | `/generations/{id}/files` | ❌ **ADD** |
| GET | N/A | `/generations/{id}/files/{path}` | ❌ **ADD** |
| POST | N/A | `/generations/{id}/search` | ❌ **ADD** |
| GET | N/A | `/generations/{id}/review` | ❌ **ADD** |
| POST | N/A | `/generations/{id}/cancel` | ❌ **ADD** |
| DELETE | N/A | `/generations/{id}` | ❌ **ADD** |
| GET | N/A | `/generations/recent` | ❌ **ADD** |
| GET | N/A | `/generations/statistics` | ❌ **ADD** |
| GET | N/A | `/generations/{id}/iterations` | ❌ **ADD** |

### ❌ VERSION MANAGEMENT (NOT IMPLEMENTED IN FRONTEND)

| Method | Current Frontend | Backend Endpoint | Status |
|--------|------------------|------------------|--------|
| GET | N/A | `/generations/projects/{id}/versions` | ❌ **ADD** |
| GET | N/A | `/generations/projects/{id}/versions/{version}` | ❌ **ADD** |
| GET | N/A | `/generations/projects/{id}/versions/active` | ❌ **ADD** |
| POST | N/A | `/generations/projects/{id}/versions/{gen_id}/activate` | ❌ **ADD** |
| GET | N/A | `/generations/projects/{id}/versions/compare/{v1}/{v2}` | ❌ **ADD** |

### ✅ TEMPLATES (No Changes - Already Correct)

| Method | Current Frontend | Backend Endpoint | Status |
|--------|------------------|------------------|--------|
| GET | `/templates/` | `/templates/` | ✅ OK |
| GET | `/templates/{name}` | `/templates/{name}` | ⚠️ **VERIFY** |
| GET | `/templates/search` | `/templates/search` | ✅ OK |

---

## 🔧 IMPLEMENTATION CHECKLIST

### Phase 1: Critical Fixes (IMMEDIATE - Within 24 hours)

- [ ] **Update generation service endpoint** (`/api/v2/generation/generate` → `/generations/generate`)
- [ ] **Update SSE streaming endpoint** (`/api/v2/generation/generate/{id}/stream` → `/generations/generate/{id}/stream`)
- [ ] **Remove polling status endpoint** (`/api/v2/generation/{id}/status`) - Use `/generations/{id}` instead
- [ ] **Update iteration endpoint** (`/api/v2/generation/iterate` → `/generations/iterate`)
- [ ] **Update response type handling** (Change `id` to `generation_id`, add new fields)
- [ ] **Update SSE event stage names** (parsing_schema → context_analysis, etc.)

### Phase 2: File Management (HIGH PRIORITY - Within 48 hours)

- [ ] **Implement file tree endpoint** (`GET /generations/{id}/files`)
- [ ] **Implement file content endpoint** (`GET /generations/{id}/files/{path}`)
- [ ] **Remove hardcoded file content fallbacks**
- [ ] **Update file tree building logic** to use new structure
- [ ] **Add proper error handling** for missing files

### Phase 3: Additional Features (MEDIUM PRIORITY - Within 1 week)

- [ ] **Add file search endpoint** (`POST /generations/{id}/search`)
- [ ] **Add code review endpoint** (`GET /generations/{id}/review`)
- [ ] **Add cancel generation** (`POST /generations/{id}/cancel`)
- [ ] **Add delete generation** (`DELETE /generations/{id}`)
- [ ] **Add recent generations** (`GET /generations/recent`)
- [ ] **Add statistics endpoint** (`GET /generations/statistics`)
- [ ] **Add iterations list** (`GET /generations/{id}/iterations`)

### Phase 4: Version Management (LOW PRIORITY - Within 2 weeks)

- [ ] **Add version list UI component**
- [ ] **Implement version list endpoint** (`GET /generations/projects/{id}/versions`)
- [ ] **Implement active version endpoint** (`GET /generations/projects/{id}/versions/active`)
- [ ] **Implement version activation** (`POST /generations/projects/{id}/versions/{gen_id}/activate`)
- [ ] **Implement version comparison** (`GET /generations/projects/{id}/versions/compare/{v1}/{v2}`)
- [ ] **Add diff viewer component**

---

## 🧪 TESTING REQUIREMENTS

### API Integration Tests

```typescript
// tests/api/generation.test.ts
describe('Generation API Migration', () => {
  it('should use correct generation endpoint', async () => {
    const response = await generationService.startGeneration(mockRequest)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/generations/generate'),
      expect.any(Object)
    )
  })
  
  it('should handle new response format', async () => {
    const response = await generationService.startGeneration(mockRequest)
    expect(response).toHaveProperty('generation_id')
    expect(response).toHaveProperty('generation_mode')
    expect(response).toHaveProperty('ab_group')
  })
  
  it('should use correct SSE endpoint', () => {
    const monitor = new GenerationMonitor(generationId, token, onProgress, onError, onComplete)
    monitor.startStreaming()
    expect(EventSource).toHaveBeenCalledWith(
      expect.stringContaining('/generations/generate/')
    )
  })
})
```

### UI Component Tests

```typescript
// tests/components/generation-view.test.tsx
describe('Generation View', () => {
  it('should load file tree from correct endpoint', async () => {
    render(<GenerationView generationId="test-id" />)
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/generations/test-id/files'),
        expect.any(Object)
      )
    })
  })
  
  it('should load file content on click', async () => {
    const { getByText } = render(<GenerationView generationId="test-id" />)
    
    fireEvent.click(getByText('main.py'))
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/generations/test-id/files/main.py'),
        expect.any(Object)
      )
    })
  })
})
```

---

## 📚 UPDATED TYPE DEFINITIONS

Create or update `lib/api/types.ts`:

```typescript
// ===== GENERATION TYPES =====

export interface UnifiedGenerationRequest {
  prompt: string
  tech_stack?: TechStack
  domain?: DomainType
  context?: ProjectContext
  generation_mode?: GenerationMode
  is_iteration?: boolean
  parent_generation_id?: string
  project_id?: string
  constraints?: string[]
}

export interface UnifiedGenerationResponse {
  generation_id: string
  status: GenerationStatus
  message: string
  user_id: string
  project_id: string
  prompt: string
  context?: any
  generation_mode: GenerationMode
  ab_group?: string
  enhanced_features?: string[]
  is_iteration: boolean
  parent_generation_id?: string
  created_at: string
  updated_at: string
}

export type GenerationStatus = "pending" | "processing" | "completed" | "failed" | "cancelled"
export type GenerationMode = "auto" | "classic" | "enhanced"

export interface StreamingProgressEvent {
  generation_id: string
  status: GenerationStatus
  stage: "context_analysis" | "code_generation" | "quality_assessment" | "complete"
  progress: number
  message: string
  ab_group?: string
  enhanced_features?: string[]
  generation_mode?: GenerationMode
  timestamp: string
}

// ===== FILE MANAGEMENT TYPES =====

export interface FileTreeResponse {
  files: {
    root: FileNode
  }
}

export interface FileNode {
  path: string
  type: "file" | "folder"
  children?: FileNode[]
  size?: number
  language?: string
}

export interface GenerationFileResponse {
  generation_id: string
  file_path: string
  content: string
  language: string
  size_bytes: number
  mime_type: string
  encoding: string
  last_modified: string
}

// ===== SEARCH TYPES =====

export interface GenerationSearchRequest {
  query: string
  case_sensitive?: boolean
  regex?: boolean
  file_pattern?: string
  max_results?: number
}

export interface GenerationSearchResponse {
  generation_id: string
  query: string
  total_matches: number
  files_with_matches: number
  matches: SearchMatch[]
}

export interface SearchMatch {
  file_path: string
  line_number: number
  line_content: string
  match_start: number
  match_end: number
  context_before: string[]
  context_after: string[]
}

// ===== VERSION MANAGEMENT TYPES =====

export interface VersionListResponse {
  project_id: string
  total_versions: number
  active_version: number
  latest_version: number
  versions: GenerationSummary[]
}

export interface GenerationSummary {
  id: string
  version: number
  version_name?: string
  status: GenerationStatus
  is_active: boolean
  file_count: number
  quality_score: number
  created_at: string
  prompt_preview: string
}

export interface ActivateGenerationResponse {
  success: boolean
  generation_id: string
  version: number
  message: string
  previous_active_id?: string
}

export interface VersionComparisonResponse {
  project_id: string
  from_version: number
  to_version: number
  files_added: string[]
  files_removed: string[]
  files_modified: string[]
  files_unchanged: string[]
  size_change_bytes: number
  file_count_change: number
  quality_score_change: number
  unified_diff: string
  diff_summary: string
  time_between_versions: number
  created_at_from: string
  created_at_to: string
}

// ===== CODE REVIEW TYPES =====

export interface CodeReviewResponse {
  generation_id: string
  quality_report: {
    overall_score: number
    overall_level: "poor" | "fair" | "good" | "excellent"
    total_files: number
    total_lines: number
    issues: CodeIssue[]
    metrics: {
      code_complexity: number
      test_coverage: number
      documentation_score: number
    }
    recommendations: string[]
  }
}

export interface CodeIssue {
  file: string
  line: number
  severity: "error" | "warning" | "info"
  category: string
  message: string
  suggestion: string
}

// ===== STATISTICS TYPES =====

export interface GenerationStatsResponse {
  total_generations: number
  completed_generations: number
  failed_generations: number
  total_files_generated: number
  average_quality_score: number
  total_iterations: number
  most_used_tech_stack: string
  most_used_domain: string
}
```

---

## 🎯 MIGRATION TIMELINE

### Week 1 (Days 1-2): Critical Fixes
- **Day 1:** Update all deprecated generation endpoints
- **Day 2:** Update SSE streaming, fix response handling, test thoroughly

### Week 1 (Days 3-5): File Management
- **Day 3:** Implement file tree endpoint integration
- **Day 4:** Implement file content loading, remove fallbacks
- **Day 5:** Test file viewing functionality

### Week 2 (Days 6-10): Additional Features
- **Days 6-7:** Add search, review, cancel, delete endpoints
- **Days 8-9:** Add recent generations, statistics
- **Day 10:** Integration testing

### Week 3 (Days 11-15): Version Management
- **Days 11-12:** Implement version list and activation
- **Days 13-14:** Implement version comparison and diff viewer
- **Day 15:** Final testing and documentation

---

## ⚠️ DEPRECATION WARNINGS

The following endpoints are **DEPRECATED** and will be removed:

```typescript
// ❌ DO NOT USE THESE ENDPOINTS
POST /api/v2/generation/generate
GET  /api/v2/generation/generate/{id}/stream
GET  /api/v2/generation/{id}/status
POST /api/v2/generation/iterate
```

**Timeline:**
- **Now:** Deprecated (still work but marked for removal)
- **30 days:** Warning logs added
- **60 days:** Endpoints removed entirely

**Action Required:** Migrate immediately to avoid service disruption.

---

## 📞 SUPPORT & QUESTIONS

For questions or issues during migration:

1. **Review this document** thoroughly
2. **Check backend endpoint list** in previous response
3. **Test endpoints** using Postman/curl before implementing
4. **Document any issues** encountered
5. **Update this guide** as needed

---

**Document Version:** 1.0  
**Last Updated:** October 15, 2025  
**Author:** Backend API Team  
**Status:** 🚨 CRITICAL - IMMEDIATE ACTION REQUIRED
