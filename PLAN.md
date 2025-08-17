# codebegen: AI-Powered FastAPI Backend Generator

## 🎯 Goal

- Leverage Qwen2.5-Coder-32B (fine-tuned) as the primary code generator for transforming natural language backend requests into full, multi-file FastAPI projects.
- Ensure outputs follow codebegen’s clean architecture templates, handle iteration/refinement prompts, and always deliver working, best-practice code.
- Use schema parser, reviewer, and docs generator models for efficiency, security, and quality.

---

## 1️⃣ Multi-Model Pipeline (MVP)

- **Primary Code Generator:** Qwen2.5-Coder-32B (LoRA fine-tuned on FastAPI/codebegen dataset)
- **Schema Parser:** Llama-3.1-8B or distilled Qwen-7B (for extracting entities/relationships/fields)
- **Reviewer:** Starcoder2-15B (security, standards, and FastAPI best practices)
- **Documentation Generator:** Mistral-7B-Instruct (speedy doc/README/gen)

**Final Pick for MVP:** Qwen2.5-Coder-32B as the main generator for its accuracy, context window, and open weights.

---

## 2️⃣ Dataset Creation

**Sources:**
- 1k–3k high-quality public FastAPI GitHub repos (stars > 20, clean architecture).
- codebegen’s own template packs (full folder structures, meta-tagged).
- 200–500 custom, synthetic prompts (varying complexity, NL descriptions → full project outputs).
- OpenAPI specs from popular APIs (converted to FastAPI).

**Format:**  
All data in JSONL, each with prompt, context, expected architecture, and complete output files.

```json
{
  "id": "fastapi_blog_v1",
  "prompt": "Build a blog API with posts, comments, and user authentication. Use FastAPI, PostgreSQL, and JWT. Include file upload for post images and an admin dashboard with RBAC.",
  "context": {
    "domain": "content_management",
    "complexity": "medium",
    "tech_stack": ["fastapi", "postgresql", "sqlalchemy", "jwt", "s3"],
    "constraints": ["dockerized", "linted", "tested"]
  },
  "expected_architecture": {
    "app": ["main.py", "routers/", "models/", "schemas/", "services/", "repositories/", "auth/"],
    "infra": ["docker-compose.yml", "Dockerfile", ".env.example"],
    "docs": ["README.md", "openapi.yaml"],
    "tests": ["tests/"]
  },
  "output": {
    "files": {
      "app/main.py": "...",
      "app/models/user.py": "...",
      "app/routers/posts.py": "...",
      "Dockerfile": "...",
      "README.md": "..."
    }
  },
  "quality_score": 0.95
}
```

---

## 3️⃣ Preprocessing

- **Tokenize/truncate**: Fit examples in Qwen’s 32K context window.
- **Format normalization**: `black` for Python, yaml lint, strict import/package checks.
- **Meta tags** in prompt for domain, stack, constraints.
- **Consistent output**: Always multi-file, in JSON with `files` dict.

---

## 4️⃣ Fine-Tuning Strategy

- **LoRA adaptation** (not full FT) via Hugging Face `peft` + `transformers`.
- Params: LoRA rank 16–32, lr = 2e-5, batch size 1–2, epochs 3–5, cutoff ~16K tokens.
- Use multi-stage samples: intent→schema, schema→structure, structure→code, code→iteration, code→docs.

---

## 5️⃣ Training Pipeline

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model
from datasets import load_dataset

model_name = "Qwen/Qwen2.5-Coder-32B"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")

lora_config = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.1, task_type="CAUSAL_LM")
model = get_peft_model(model, lora_config)

dataset = load_dataset("json", data_files="fastapi_dataset.jsonl")

def tokenize_fn(example):
    text = f"### Prompt:\n{example['prompt']}\n\n### Output:\n{example['output']}"
    return tokenizer(text, truncation=True, max_length=16000)
dataset = dataset.map(tokenize_fn)

from transformers import TrainingArguments, Trainer
training_args = TrainingArguments(
    output_dir="./qwen_fastapi_lora",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=2e-5,
    num_train_epochs=3,
    fp16=True
)
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    tokenizer=tokenizer
)
trainer.train()
```

---

## 6️⃣ Prompt Templates

**System Prompt:**
```
You are Codebegen, an AI backend engineer that builds production-ready FastAPI backends from natural language requests.
You must:
- Follow PEP8 and use `black` formatting.
- Use the requested tech stack exactly.
- Generate ALL required files for a working project.
- Include Dockerfile and docker-compose.yml when requested.
- Ensure code runs without syntax errors.
- Never invent package names.
- Always separate concerns into models, schemas, routers, services, and repositories.
- Include basic tests and README.md.
Your output must be in JSON with keys: files (dict of file paths → contents).
```

**User Prompt Template:**
```
### API Description:
{user_prompt}

### Technical Context:
Domain: {domain}
Tech Stack: {stack}
Constraints: {constraints}

### Output Format:
Return JSON with:
{
  "files": { "path/to/file.py": "<full code>", ... }
}
```

---

## 7️⃣ Multi-Stage Dataset & Iterative Refinement

- **Stage 1:** Intent → Schema (entities, relationships extraction)
- **Stage 2:** Schema → Folder Structure
- **Stage 3:** Structure → Full Code (all files, clean arch)
- **Stage 4:** Full Code → Add/modify features (iteration)
- **Stage 5:** Full Code → Documentation (README, OpenAPI, setup)

> This lets the model handle both first-gen and iterative refinement prompts with context retention.

---

## 8️⃣ Post-Training Enhancements

- **RAG Layer:** Feed template library/context before each generation.
- **Self-Review:** Auto-run generation through Starcoder2-15B for lint, best practices, security.
- **Eval Harness:** Lint, run tests, launch `/docs` endpoint in a sandbox, auto-score.
- **Continuous Learning:** Collect failed generations, fine-tune every 2–4 weeks, add domain specialization.

---

## 9️⃣ Model Deployment

- Serve LoRA Qwen2.5-Coder-32B with vLLM (`vllm serve Qwen/Qwen2.5-Coder-32B --adapter qwen_fastapi_lora`)
- Integrate with multi-model pipeline:
    1. Schema extraction (Llama-8B)
    2. Code generation (Qwen2.5-Coder-32B LoRA)
    3. Review (Starcoder2-15B)
    4. Docs (Mistral-7B)

---

## 🔟 Why This Outperforms Generic Copilot/ChatGPT

- **Consistent, production-grade multi-file outputs** (not just code snippets)
- **Handles project-level context and iterative changes**
- **Domain and stack specialization**
- **Quality-baked-in** (tests, lint, security review)
- **Template and RAG-aware** (user’s actual folder structures, not hallucinated ones)

---

## 1️⃣1️⃣ Success Metrics

- Generation success rate (runnable code, passes tests)
- First-run test pass rate
- Developer satisfaction/NPS
- Iterative prompt handling accuracy
- Model inference cost

---

## 1️⃣2️⃣ Next Steps

- Finalize dataset schema and begin scraping/curating.
- Build prompt/response pipeline for multi-stage samples.
- Fine-tune Qwen2.5-Coder-32B with LoRA on initial dataset.
- Integrate with codebegen’s backend pipeline and test real user prompts.
- Launch closed alpha, collect feedback, improve.

---

**codebegen will set a new standard for AI-powered, full-project backend code generation.**
