# Validation Test Quickstart

This guide explains how to use the validation scaffolding (metrics logging and A/B assignment) during the two-week test.

## Components

- `app/services/validation_metrics.py`: JSONL metrics logger
- `app/services/ab_test.py`: Deterministic A/B assignment
- `app/services/template_selector.py`: Picks base template and features
- `configs/domains/*.yaml`: Domain configs

## Usage Patterns (Pseudo-Code)

1) Assign a user to a test group
```
from app.services.ab_test import ABTestManager
ab = ABTestManager()
assignment = ab.assign(user_id)
print(assignment.group)  # control | enhanced_templates | better_prompts | full_enhancement
```

2) Log generation outcomes
```
from app.services.validation_metrics import ValidationMetrics
metrics = ValidationMetrics()

metrics.track_generation_success(generation_id, user_id, success=True, duration_ms=2350)
metrics.track_user_modifications(generation_id, user_id, files_modified=["app/routers/items.py"]) 
metrics.track_abandonment(generation_id, user_id, stage="customization")
metrics.track_metric(generation_id, user_id, name="satisfaction", value=8.5)
```

3) Select template and features
```
from app.services.template_selector import TemplateSelector
selector = TemplateSelector()

decision = selector.decide(prompt, tech_stack=["fastapi", "postgresql", "sqlalchemy"])
print(decision)
```

## Logs

- Metrics are appended to `logs/validation_metrics.jsonl`
- One JSON record per event, safe to tail/ingest into analytics

## Next Steps

- Wire calls into your generation flow in `app/services/ai_orchestrator.py`
- Roll out A/B groups via feature flags or simple route guards
- After 2 weeks, aggregate JSONL to compute improvement scores as per `docs/two-week-validation-test.md`
