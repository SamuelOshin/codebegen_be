# 📚 Preview Tab Documentation - Quick Navigation

**Last Updated**: October 20, 2025

---

## 🎯 Quick Links

### For Phase 4 MVP Implementation (NOW)
👉 **[PREVIEW_MVP_PHASE4.md](./PREVIEW_MVP_PHASE4.md)**

**Contains**:
- 🏗️ Lightweight MVP architecture (in-process execution)
- 🔌 7 API endpoints (with real-time SSE logging)
- 📊 Simple database models
- 🚀 2-week implementation plan
- ✅ Acceptance criteria
- 🧪 Testing strategy
- 📝 Detailed code examples
- **✨ Real-time log streaming via SSE** ← Terminal-style UX

**Best For**: Building and shipping the MVP quickly

---

### For SSE Streaming Implementation (CRITICAL MVP FEATURE)
👉 **[SSE_STREAMING_IMPLEMENTATION.md](./SSE_STREAMING_IMPLEMENTATION.md)**

**Contains**:
- 🔌 Why SSE over WebSocket/Polling
- 🏗️ Complete architecture diagram
- 💻 Full backend service implementation
- 🎨 Frontend hook + component
- 🧪 Testing strategies
- 🔧 Troubleshooting guide

**Best For**: Understanding and implementing real-time log streaming (~3-4 hours work)

---

### For Phase 5 Production Upgrade (LATER)
👉 **[PREVIEW_PHASE5_PRODUCTION.md](./PREVIEW_PHASE5_PRODUCTION.md)**

**Contains**:
- 🐳 Docker-based production architecture
- 🔌 12 total endpoints (7 new in Phase 5)
- 📊 Advanced data models with metrics
- 📈 Comprehensive monitoring
- 🚀 2-week production upgrade plan
- 🧪 Advanced testing strategies
- 📚 Migration guide from Phase 4

**Best For**: Planning and executing the Phase 5 upgrade

---

### For Phase 5 Production Upgrade (LATER)
👉 **[PREVIEW_PHASE5_PRODUCTION.md](./PREVIEW_PHASE5_PRODUCTION.md)**

**Contains**:
- 🐳 Docker-based production architecture
- 🔌 12 total endpoints (7 new in Phase 5)
- 📊 Advanced data models with metrics
- 📈 Comprehensive monitoring
- 🚀 2-week production upgrade plan
- 🧪 Advanced testing strategies
- 📚 Migration guide from Phase 4

**Best For**: Planning and executing the Phase 5 upgrade

---

## 📋 Decision Summary: Architectural Choices

### Core Architecture

| Decision | MVP | Phase 5 | Why |
|----------|-----|---------|-----|
| **Runtime** | Python subprocess + Uvicorn | Docker containers | Production isolation & representation |
| **Database** | SQLite (demo mode) | PostgreSQL/MongoDB (production) | Matches generated tech stack |
| **Resource Limits** | Soft (monitoring only) | Hard (enforced by Docker) | Prevent abuse, stable multi-tenant |
| **Logging** | Error-only file logging | Centralized + real-time WebSocket | Debugging & observability |
| **Scalability** | 1 preview per user | 3-5 previews per user | Better UX while manageable |

### Why These Choices?

**MVP prioritizes**:
- ✅ **Speed to ship** - Lightweight, few dependencies
- ✅ **Simplicity** - Easy to understand and debug
- ✅ **No external systems** - Works standalone
- ✅ **Fast iteration** - <3 second launch times

**Phase 5 prioritizes**:
- ✅ **Production quality** - True isolation & resource management
- ✅ **Scalability** - Handle multiple previews
- ✅ **Observability** - Detailed metrics & logging
- ✅ **Enterprise readiness** - Audit trails & monitoring

---

## 🛣️ Implementation Timeline

```
Week 1-2: MVP (Phase 4)
├── Build core infrastructure
├── Implement 5 endpoints
├── Basic testing
└── Ready for user testing

Week 3: Transition Planning
├── Plan Phase 5 architecture
├── Design Docker integration
├── Plan zero-downtime migration
└── Setup feature flags

Week 4-5: Phase 5 Implementation
├── Docker service & containers
├── WebSocket streaming
├── Advanced monitoring
└── Production testing

Week 6: Phase 5 Launch
├── Canary deployment (5% users)
├── Monitor metrics
├── Gradual rollout (25% → 50% → 100%)
└── Cleanup & optimization
```

---

## 🚀 What to Build First (MVP Focus)

### Must-Have (Priority 1)
```
1. Database models (PreviewInstance, PreviewLog)
2. Port allocator utility
3. Launch endpoint ✅
4. Status endpoint ✅
5. Stop endpoint ✅
6. Proxy endpoint ✅
7. Endpoints metadata endpoint ✅
```

### Tests & Polish (Priority 2)
```
8. Unit tests (port allocator, models)
9. Integration tests (all endpoints)
10. Configuration & logging
11. Error handling & recovery
12. Documentation
```

### Nice-to-Have (Priority 3)
```
13. Logs endpoint (basic polling)
14. Config endpoint (stub)
15. Advanced error messages
16. Performance optimization
```

---

## 🔄 MVP → Phase 5 Upgrade Path

### What Changes?
```
Before Phase 5:
- In-process Python execution
- SQLite only
- 1 preview per user
- Error-level logging only
- No resource limits

After Phase 5:
- Docker container execution
- PostgreSQL/MongoDB support
- 3-5 previews per user
- Full centralized logging
- CPU/Memory/Disk limits
```

### What Stays the Same?
```
✅ All API endpoints work identically
✅ Request/response formats unchanged
✅ Authentication method same
✅ User experience familiar
✅ No breaking changes
```

---

## 📊 File Organization

```
docs/previewtab/
├── PREVIEW_MVP_PHASE4.md           # THIS PHASE - Implementation plan
├── PREVIEW_PHASE5_PRODUCTION.md    # NEXT PHASE - Production upgrade
├── QUICK_NAVIGATION.md             # You are here
└── (Future files created during implementation)
    ├── DOCKER_INTEGRATION.md       # After Phase 5 starts
    ├── WEBSOCKET_REFERENCE.md      # After Phase 5 starts
    ├── PERFORMANCE_TUNING.md       # After Phase 5 complete
    ├── RUNBOOK.md                  # For operations team
    └── MVP_TO_PHASE5_UPGRADE.md    # Migration guide
```

---

## 🎯 Key Metrics to Track

### MVP Success Metrics
- Launch time: **< 3 seconds**
- Availability: **> 99%**
- User session duration: **Average 15+ minutes**
- Error rate: **< 1%**
- Test coverage: **> 90%**

### Phase 5 Success Metrics
- Launch time (cold): **< 20 seconds**, (cached: < 3 seconds)
- Availability: **> 99.9%**
- Concurrent instances: **100+**
- Resource utilization: **512MB RAM, 0.5 CPU average**
- WebSocket latency: **< 100ms**

---

## ❓ FAQ: MVP vs Phase 5

### Q: Why not Docker from the start?
**A**: MVP prioritizes shipping fast. Docker adds complexity:
- 20-40 second startup (vs 1-3 seconds)
- Docker daemon dependency
- Build pipeline needed
- More difficult debugging

Better to ship MVP, gather user feedback, then upgrade to Phase 5 in 4 weeks.

---

### Q: Can I skip MVP and go straight to Phase 5?
**A**: **Not recommended**. Reasons:
- Phase 5 is more complex (higher risk of bugs)
- Harder to debug without MVP baseline
- You won't know user needs yet
- Can't gather early feedback
- Better to iterate MVP first, then upgrade

---

### Q: Will MVP still work after Phase 5?
**A**: **Yes**, Phase 5 is backward compatible:
- All MVP endpoints continue to work
- Feature flags allow gradual migration
- Can run both simultaneously during transition
- Easy fallback if Phase 5 issues arise

---

### Q: What if we want to scale MVP?
**A**: Phase 5 handles scaling:
- MVP: 1 preview per user → Phase 5: 3-5 previews
- MVP: No resource limits → Phase 5: Hard limits prevent abuse
- MVP: Lightweight → Phase 5: Production-grade

---

### Q: When should we start Phase 5?
**A**: Timeline:
- **Start Phase 5 code review**: Week 2 of MVP
- **Start Phase 5 implementation**: After MVP ships + 1 week user feedback
- **Phase 5 ready**: Week 6 (4 weeks after MVP launch)

---

### Q: What's the most important MVP feature?
**A**: **SSE Real-time logging**. Without it:
- Users see blank screen for 1-2 seconds
- Feels broken/incomplete
- Bad user experience

With SSE streaming:
- Users see startup happening in real-time
- Errors visible immediately
- Professional, polished feel

---

### Q: How long to implement SSE?
**A**: ~3-4 hours for a junior developer:
- 1.5 hours: Backend service (PreviewLogStreamer)
- 1 hour: Frontend hook + component
- 1.5 hours: Testing + debugging

See **[SSE_STREAMING_IMPLEMENTATION.md](./SSE_STREAMING_IMPLEMENTATION.md)** for detailed guide.

---

### Q: Why not just use WebSocket for MVP?
**A**: WebSocket adds complexity:
- Protocol upgrade (HTTP → WS)
- More complex error handling
- Browser support slightly lower
- Harder to debug

SSE is simpler:
- Pure HTTP (easier to debug)
- Auto-reconnect built-in
- Easier to understand
- Easy upgrade to WebSocket in Phase 5

---

## 🛠️ Development Setup by Phase

### MVP Setup
```bash
# Minimal dependencies
pip install fastapi uvicorn sqlalchemy pydantic

# That's it! Run MVP locally
python -m uvicorn app.main:app --reload
```

### Phase 5 Setup
```bash
# Additional dependencies
pip install docker redis python-websockets prometheus-client

# External services needed
- Docker daemon running
- PostgreSQL for preview DBs
- Redis for caching
- CloudWatch/ELK for logging (optional)
```

---

## 📞 Questions & Decisions

### For MVP Implementation
- How long should previews stay alive? **→ See MVP doc: 1 hour**
- How many concurrent previews? **→ See MVP doc: 1 per user**
- Database for preview? **→ See MVP doc: SQLite**
- Real-time logs? **→ See MVP doc: Polling only**

### For Phase 5 Planning
- How to handle Docker? **→ See Phase 5 doc: Docker daemon**
- Resource limits per user? **→ See Phase 5 doc: By tier**
- WebSocket logs setup? **→ See Phase 5 doc: Full streaming**
- Migration strategy? **→ See Phase 5 doc: Feature flags**

---

## ✅ Checklist Before Starting

### MVP Readiness
- [ ] Read PREVIEW_MVP_PHASE4.md completely
- [ ] Review all 5 endpoints and understand flow
- [ ] Understand database models
- [ ] Review 2-week implementation tasks
- [ ] Confirm team has required skills (FastAPI, SQLAlchemy)

### Phase 5 Preparation (After MVP ships)
- [ ] Read PREVIEW_PHASE5_PRODUCTION.md
- [ ] Learn Docker basics (if unfamiliar)
- [ ] Understand WebSocket implementation
- [ ] Plan feature flag strategy
- [ ] Design migration process

---

## 🚀 Next Steps

### THIS WEEK
1. Review this navigation guide
2. Read PREVIEW_MVP_PHASE4.md completely
3. Schedule team discussion on MVP approach
4. Confirm scope with stakeholders
5. **Start Week 1 implementation tasks**

### NEXT WEEK (After MVP ships)
1. Gather user feedback on MVP
2. Plan Phase 5 upgrades based on usage
3. Review PREVIEW_PHASE5_PRODUCTION.md with team
4. Design zero-downtime migration strategy
5. **Start Phase 5 implementation**

---

## 📚 Related Documentation

- **Backend Architecture**: [../architecture.md](../architecture.md)
- **Generation System**: [../generation-system.md](../generation-system.md)
- **Storage Management**: [../storage-setup.md](../storage-setup.md)
- **API Reference**: [../openapi.yaml](../openapi.yaml)

---

## 👥 Team Coordination

### Backend Team
- Primary focus: Phase 4 MVP
- Responsible for: All endpoints + services
- Timeline: 2 weeks

### Frontend Team
- Awaits: Phase 4 API contracts
- Implements: Preview UI + endpoint testing
- Timeline: Parallel with backend

### DevOps Team
- Prepares for Phase 5: Docker infrastructure
- Sets up: Redis, PostgreSQL instances
- Timeline: After Phase 4, before Phase 5

### QA Team
- MVP testing: Manual + automated tests
- Phase 5: Load testing + Docker testing
- Timeline: Continuous

---

**Last Updated**: October 20, 2025  
**Status**: Ready for implementation  
**Next Review**: After MVP ships (Week 3)
