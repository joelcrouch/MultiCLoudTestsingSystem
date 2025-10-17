# Sprint 2: Building a Multi-Cloud Data Pipeline (The Foundation)

## The Challenge
Sprint 1 gave me distributed node coordination across AWS and GCP. Sprint 2's goal: turn that coordination layer into a **complete 4-stage data pipeline** that can actually process ML training data end-to-end.

**The real-world problem:** Moving large amounts of training data across clouds requires ingestion, processing, distribution, and storage — all working together with proper error handling and basic observability.

---

## What I Built: A 4-Stage Distributed Pipeline

### 1. **Ingestion Engine** (199 LOC, 79% coverage)
- Chunks large files (1GB+) into manageable 100MB segments
- Distributes chunks across available nodes via distributed queue
- Handles multiple data sources (local files, cloud storage)

### 2. **Processing Worker Pool** (212 LOC, 92% coverage)
- Parallel execution across AWS and GCP nodes
- Data transformation, validation, and checksumming
- Work queue management with retry logic

### 3. **Distribution Coordinator** (243 LOC, 90% coverage)
- Routes processed data to target nodes
- 3× replication for fault tolerance
- Tracks placement and verifies distribution success

### 4. **Storage Manager** (263 LOC, 84% coverage)
- Persistent storage with integrity verification (SHA-256)
- Cleanup and garbage collection
- Idempotent operations for reliability

### 5. **Pipeline Orchestrator** (171 LOC, 89% coverage)
- Coordinates all 4 stages end-to-end
- Manages stage transitions and error propagation
- Tracks pipeline state across distributed nodes

---

## Basic Observability Foundation

Built the instrumentation that makes the system debuggable:

### Monitoring Components:
- **Pipeline Monitor** (156 LOC, 86% coverage): Tracks stage performance, detects bottlenecks, generates reports
- **Pipeline Logger** (112 LOC, 79% coverage): Structured logging with context (stage, node, chunk ID)
- **Status Dashboard** (140 LOC, 72% coverage): Basic web interface for pipeline state

### What This Provides:
- Per-stage timing and success rates
- Bottleneck identification
- Structured logs with full context
- Basic performance reporting

**The win:** When tests fail, I get "Processing stage failed on chunk 42 at aws-node-3" instead of "Test failed somewhere." Basic instrumentation makes debugging actually possible.

---

## Testing Achievement: 61/61 Tests, 81% Coverage

**Goal:** 50% coverage  
**Achieved:** 81% coverage (exceeded by 31 percentage points)

### Coverage Breakdown:
```
Module                              Lines   Missed   Coverage
─────────────────────────────────────────────────────────────
pipeline/processing_workers.py        212      17      92%
pipeline/distribution_coordinator.py  243      25      90%
pipeline/pipeline_orchestrator.py     171      18      89%
monitoring/pipeline_monitor.py        156      22      86%
pipeline/storage_manager.py           263      43      84%
pipeline/ingestion_engine.py          199      41      79%
monitoring/pipeline_logger.py         112      23      79%
monitoring/status_dashboard.py        140      39      72%
─────────────────────────────────────────────────────────────
Total                                1571     299      81%
```

### Test Distribution:

**Unit Tests (48 tests):** Individual component logic, data transformations, error handling paths

**Integration Tests (10 tests):** End-to-end pipeline flow, cross-cloud transfers, node failure scenarios

**Basic Failure Tests (3 tests):** Node failures during processing, network issues, resource constraints

**Result:** All 61 tests pass consistently. The pipeline works end-to-end with basic fault tolerance.

---

## What I Learned Building This

### 1. **Test Coverage Happened Naturally**
- Didn't aim for 81%, just tested critical paths thoroughly
- Integration tests drove most of the coverage gains
- High coverage reflects good component boundaries, not just "testing everything"

### 2. **Basic Instrumentation Is Essential**
- Added timing and logging from day one
- Structured logs with context (stage, node, chunk) make debugging 10× faster
- Don't need fancy dashboards yet — basic metrics and logs get you 80% there

### 3. **Distributed Coordination Is Hard**
- Orchestrator took 3 rewrites to get stage transitions right
- Error propagation across stages is tricky (when to retry vs fail?)
- Queue management is powerful but requires careful tuning

### 4. **The Code Quality Shows In Tests**
- Processing workers: 92% coverage (cleanest code)
- Dashboard UI: 72% coverage (harder to unit test, will add integration tests)
- Most untested lines are error edge cases (will address in chaos testing)

### 5. **Cross-Cloud Adds Complexity Everywhere**
- Can't assume symmetric network behavior
- Need to track which cloud each node is in
- Data locality matters for performance (will optimize in Sprint 3)

---

## What's Working

✅ **Complete end-to-end pipeline** from ingestion to storage  
✅ **Cross-cloud coordination** between AWS and GCP nodes  
✅ **Basic fault tolerance** with retry logic and replication  
✅ **Debuggable system** with structured logging and metrics  
✅ **Solid test foundation** (61 tests, 81% coverage)  

---

## What's Next: Sprint 3 Focus

Now that the pipeline **works**, Sprint 3 makes it **production-ready**:

### Fault Tolerance & Optimization (Weeks 5-6)
- **Automatic failover:** Survive 20% simultaneous node failures
- **Performance optimization:** Dynamic load balancing, network-aware routing
- **Data consistency:** Checkpointing, write-ahead logging, zero data loss guarantees
- **Chaos engineering:** Systematic failure injection to find what breaks

### Surprise Add-ON!
I have 1 month of free Azure services, so i will be adding in Azure  nodes into the mix.  I will probably end up taking a morning to add in all the logic for it.  That will also help/force me to remember how that works.  Maybe I will be able to write a little script, such that i can automate adding in Ubuntu/ibm/other cloud service to this little test bed I am making.

### SURPRISE ADD-ON #2:  
(what am i, a project manager?) I am creating a couple easy to model ML models to acutally use real training loads across the 2/3 different clouds. I have a very rudimentary protein folder predictor, a chatbot, and some other easy to code ML model tbd.  Maybe a small(very small) LLM.

### Testing Goals:
- **75% coverage target** (allready at 81% — adding chaos tests)
- Comprehensive failure scenario testing
- Performance benchmarking with realistic workloads
- Network partition and cascading failure tests

### What I'll Learn:
- Actual performance characteristics under load
- Real failure modes and recovery times
- Network behavior patterns (AWS↔GCP latency, throughput)
- Optimal replication strategies and load balancing algorithms

**That's when I'll have real performance data to share.**

---

## Technical Stack

- **Language:** Python 3.11
- **Communication:** gRPC for inter-node RPC
- **Storage:** S3-compatible object storage
- **Monitoring:** Custom metrics collector (expanding in Sprint 4)
- **Testing:** pytest with custom distributed testing fixtures
- **Deployment:** Docker containers on AWS EC2 and GCP Compute Engine

---

## The Honest Bottom Line

Sprint 2 delivered:
- ✅ A working 4-stage pipeline (1,571 LOC)
- ✅ 81% test coverage (61/61 tests passing)
- ✅ Basic observability for debugging
- ✅ Cross-cloud coordination that actually functions

**What I don't know yet:**
- Real-world performance under load
- Actual failure modes and recovery times
- Optimal configuration for throughput vs reliability
- How it behaves during network partitions or cascading failures

**That's Sprint 3's job:** Stress test this system, find the breaking points, and make it bulletproof.

---

## Why This Matters

Built the foundation that makes everything else possible:
- Sprint 3 can do chaos engineering because the pipeline works
- Sprint 4 can build real observability because basic instrumentation exists
- The high test coverage means I can refactor confidently

**The boring truth:** Sprint 2 was about getting all the pieces working together. Sprint 3 is where it gets interesting — when I start breaking things on purpose to see what happens.

Full code and architecture details → [link to blog/repo]
FYI: the repo is a bit of a mess right now, but I will clean that up as we progrees along.
---

**Next post:** Sprint 3 chaos engineering — breaking my own pipeline to make it unbreakable 🔥

#DistributedSystems #MLInfrastructure #CloudEngineering #BuildInPublic