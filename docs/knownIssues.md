                                                                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ # Known Issues and Limitations - Sprint 2                                                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ ## Current Limitations                                                                                                                                  │ │
│ │                                                                                                                                                         │ │
│ │ ### 1. Cloud Simulation Only                                                                                                                            │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: The system currently uses local filesystem simulation of cloud storage rather than real AWS S3, GCP GCS, or Azure Blob storage.              │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**:                                                                                                                                             │ │
│ │ - Cannot test real cloud network latency                                                                                                                │ │
│ │ - Cannot test cloud-specific failure modes                                                                                                              │ │
│ │ - Cannot measure actual cross-cloud transfer costs                                                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Use environment variables to simulate different clouds                                                                                  │ │
│ │ ```bash                                                                                                                                                 │ │
│ │ export CLOUD_PROVIDER=aws  # or gcp, azure                                                                                                              │ │
│ │ ```                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Sprint 3 - Real cloud integration                                                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 2. No Authentication/Authorization                                                                                                                  │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: The system has no authentication or authorization mechanisms.                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**:                                                                                                                                             │ │
│ │ - All nodes trust each other completely                                                                                                                 │ │
│ │ - No access control on data                                                                                                                             │ │
│ │ - No audit logging of access                                                                                                                            │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Run in isolated/trusted network environment                                                                                             │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Sprint 3+ - Implement cloud IAM integration                                                                                            │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 3. Mock Node Registry                                                                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Tests use SimpleNamespace mock objects instead of real Sprint 1 node registry.                                                               │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**:                                                                                                                                             │ │
│ │ - Cannot test real distributed coordination                                                                                                             │ │
│ │ - Health checks are simulated                                                                                                                           │ │
│ │ - Network topology is static                                                                                                                            │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Tests validate logic with mock data                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Integration tests with real node registry in future sprints                                                                            │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 4. Simulated Network Failures                                                                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Network failures in tests are simulated with random chance, not controlled.                                                                  │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**:                                                                                                                                             │ │
│ │ - Tests can be flaky (though mitigated with retry logic)                                                                                                │ │
│ │ - Cannot test specific failure scenarios deterministically                                                                                              │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Tests use success rate thresholds (80%+) instead of 100%                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Deterministic failure injection framework                                                                                              │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 5. Limited Scalability Testing                                                                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Tests run with 2-4 nodes maximum due to local machine constraints.                                                                           │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**:                                                                                                                                             │ │
│ │ - Cannot validate performance with 10+ nodes                                                                                                            │ │
│ │ - Cannot test true multi-cloud scale                                                                                                                    │ │
│ │ - Cannot measure coordination overhead at scale                                                                                                         │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Performance tests use smaller datasets and node counts                                                                                  │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Sprint 3 - Deploy to real clouds for scale testing                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ## Minor Issues                                                                                                                                         │ │
│ │                                                                                                                                                         │ │
│ │ ### 6. Checkpoint Interval Logic                                                                                                                        │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Checkpoints trigger based on modulo of stored chunks, which may not fire if batch completes early.                                           │ │
│ │                                                                                                                                                         │ │
│ │ **Location**: `src/pipeline/storage_manager.py:233`                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ **Example**:                                                                                                                                            │ │
│ │ ```python                                                                                                                                               │ │
│ │ if self.create_checkpoints and len(self.stored_chunks) % self.checkpoint_interval == 0:                                                                 │ │
│ │     await self._create_checkpoint()                                                                                                                     │ │
│ │ ```                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Checkpoints may be missed for small batches                                                                                                 │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Set lower checkpoint interval (e.g., 10 instead of 1000)                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Time-based or completion-based checkpoints                                                                                             │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 7. Cleanup Timing                                                                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Automatic cleanup runs during storage, which can slow down the pipeline.                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ **Location**: `src/pipeline/storage_manager.py:237-238`                                                                                                 │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Minor performance impact during storage stage                                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Set `enable_auto_cleanup: false` in config for performance testing                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Background cleanup thread/task                                                                                                         │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 8. No Compression                                                                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Data is not compressed during transfer or storage despite config flag.                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ **Location**: `config/storage_config.yml` - `compress_old_data: true` (not implemented)                                                                 │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Higher storage usage and network bandwidth                                                                                                  │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Use pre-compressed data if needed                                                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Implement compression in storage backend                                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 9. Single Log File Per Day                                                                                                                          │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: All pipeline runs on same day share one log file, which can get large.                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ **Location**: `src/monitoring/pipeline_logger.py:35`                                                                                                    │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Large log files on active days                                                                                                              │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Log rotation or manual cleanup                                                                                                          │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Log rotation based on size or run count                                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 10. Dashboard Not Persistent                                                                                                                        │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Status dashboard only shows current state, no historical view.                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ **Location**: `src/monitoring/status_dashboard.py`                                                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Cannot review past pipeline runs from dashboard                                                                                             │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Use PipelineMonitor to query historical runs                                                                                            │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Dashboard with historical view and run selection                                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ## Performance Limitations                                                                                                                              │ │
│ │                                                                                                                                                         │ │
│ │ ### 11. Sequential Stage Execution                                                                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Pipeline stages execute sequentially (Ingestion → Processing → Distribution → Storage), not in streaming fashion.                            │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Cannot start processing while ingestion is still running                                                                                    │ │
│ │                                                                                                                                                         │ │
│ │ **Example**: 1GB file must be fully ingested before any processing begins                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: None currently                                                                                                                          │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Sprint 3+ - Streaming pipeline with overlapped stages                                                                                  │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 12. Memory Usage for Large Files                                                                                                                    │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Entire chunks are held in memory during processing.                                                                                          │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: 100MB chunk = 100MB+ RAM per chunk in flight                                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ **Example**: 10 concurrent chunks = 1GB+ RAM                                                                                                            │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Reduce `max_concurrent_chunks` in config                                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Streaming reads/writes for large chunks                                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 13. No Adaptive Chunking                                                                                                                            │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Fixed 100MB chunk size regardless of data characteristics.                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Suboptimal for very small files (<100MB) or very large files (>10GB)                                                                        │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Adjust `chunk_size_mb` in config per use case                                                                                           │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Adaptive chunking based on file size and system load                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ## Test-Specific Issues                                                                                                                                 │ │
│ │                                                                                                                                                         │ │
│ │ ### 14. Test Data Cleanup                                                                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Test data directories (`test_data/`, `storage/`, `received_chunks/`) persist after tests.                                                    │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Disk space usage accumulates, old files can cause test failures                                                                             │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Manual cleanup or run `rm -rf test_data/ storage/ received_chunks/`                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Pytest fixture for automatic cleanup                                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 15. Slow Tests                                                                                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Full test suite takes 3+ minutes due to 1GB dataset tests.                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Slow development feedback loop                                                                                                              │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Use `pytest -m "not slow"` to skip large-scale tests                                                                                    │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Parallel test execution, smaller datasets for fast tests                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 16. Coverage Gaps                                                                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Some error paths and edge cases lack test coverage.                                                                                          │ │
│ │                                                                                                                                                         │ │
│ │ **Current Coverage**: 80%+                                                                                                                              │ │
│ │                                                                                                                                                         │ │
│ │ **Missing Coverage**:                                                                                                                                   │ │
│ │ - Real network failure scenarios                                                                                                                        │ │
│ │ - Concurrent node failures (>2 nodes)                                                                                                                   │ │
│ │ - Storage backend exhaustion                                                                                                                            │ │
│ │ - Extremely large files (>10GB)                                                                                                                         │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Manual testing for edge cases                                                                                                           │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Expand test scenarios in Sprint 3                                                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ## Configuration Issues                                                                                                                                 │ │
│ │                                                                                                                                                         │ │
│ │ ### 17. Configuration File Paths                                                                                                                        │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Config files must be in `config/` directory relative to working directory.                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Running from subdirectory fails to find configs                                                                                             │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Always run from project root                                                                                                            │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Search multiple paths or use environment variable for config dir                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 18. Hard-Coded Paths                                                                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Some paths are hard-coded (e.g., `./storage/data`, `./test_data`).                                                                           │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Cannot easily relocate storage or test data                                                                                                 │ │
│ │                                                                                                                                                         │ │
│ │ **Example**: `storage_manager.py:199` - `self.metadata_path = Path('./storage/metadata')`                                                               │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Edit config files                                                                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Make all paths configurable                                                                                                            │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ## Documentation Gaps                                                                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ ### 19. API Documentation                                                                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: No API documentation (docstrings exist but no generated docs).                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Harder for new developers to understand APIs                                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Read source code and docstrings                                                                                                         │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Generate Sphinx or pdoc documentation                                                                                                  │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 20. Performance Tuning Guide                                                                                                                        │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Limited guidance on performance tuning for different workloads.                                                                              │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Users may not achieve optimal performance                                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: See `docs/setup.md` for basic tuning tips                                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Comprehensive performance tuning guide                                                                                                 │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ## Technical Debt                                                                                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ ### 21. Mixed Synchronous/Asynchronous Code                                                                                                             │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Some components mix sync and async patterns inconsistently.                                                                                  │ │
│ │                                                                                                                                                         │ │
│ │ **Example**: Config loading is synchronous but could block event loop                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Minor performance impact, potential event loop blocking                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Audit and refactor to consistent async patterns                                                                                        │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 22. Error Messages Could Be More Specific                                                                                                           │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Some error messages are generic.                                                                                                             │ │
│ │                                                                                                                                                         │ │
│ │ **Example**: "Write operation failed" without details                                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Harder to debug issues                                                                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Enhance error messages with context                                                                                                    │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 23. No Metrics Persistence                                                                                                                          │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: PipelineMonitor metrics are only in-memory, lost on restart.                                                                                 │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Cannot analyze trends across multiple runs/days                                                                                             │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Parse log files for historical metrics                                                                                                  │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Persist metrics to database or time-series store                                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 24. Limited Retry Strategy                                                                                                                          │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Simple retry with fixed delay, no exponential backoff.                                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ **Location**: All components - `retry_attempts: 3`, `retry_delay_seconds: 5`                                                                            │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: May retry too quickly for transient failures                                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Exponential backoff with jitter                                                                                                        │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 25. No Circuit Breaker                                                                                                                              │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: No circuit breaker pattern for failing nodes/services.                                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: System continues trying to use failing nodes                                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Manual node removal from registry                                                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Implement circuit breaker pattern                                                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ## Security Concerns                                                                                                                                    │ │
│ │                                                                                                                                                         │ │
│ │ ### 26. No Data Encryption                                                                                                                              │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Data transferred and stored in plaintext.                                                                                                    │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Sensitive data could be compromised                                                                                                         │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Run in secure/isolated environment                                                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: TLS for transfer, encryption at rest                                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 27. No Input Validation                                                                                                                             │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Limited validation of configuration and input data.                                                                                          │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Potential for crashes or undefined behavior with invalid inputs                                                                             │ │
│ │                                                                                                                                                         │ │
│ │ **Example**: Negative chunk sizes, invalid paths                                                                                                        │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Ensure valid configuration                                                                                                              │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Comprehensive input validation with clear error messages                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ## Monitoring Limitations                                                                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ ### 28. No Alerting                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Monitoring collects data but doesn't send alerts on failures.                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Must manually monitor for issues                                                                                                            │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Check logs and performance reports                                                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Integrate with alerting systems (email, Slack, PagerDuty)                                                                              │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 29. Dashboard Requires Manual Refresh                                                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: Dashboard doesn't auto-refresh, only shows point-in-time state.                                                                              │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Must manually call `display_pipeline_status()` repeatedly                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Call in loop with sleep                                                                                                                 │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Live dashboard with auto-refresh                                                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ### 30. No Distributed Tracing                                                                                                                          │ │
│ │                                                                                                                                                         │ │
│ │ **Issue**: No distributed tracing across nodes/stages.                                                                                                  │ │
│ │                                                                                                                                                         │ │
│ │ **Impact**: Hard to debug cross-node issues                                                                                                             │ │
│ │                                                                                                                                                         │ │
│ │ **Workaround**: Correlate logs by run_id                                                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ **Planned Fix**: Integrate OpenTelemetry or similar                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ## Priority for Sprint 3                                                                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ ### High Priority                                                                                                                                       │ │
│ │ 1. Real cloud integration (AWS S3, GCP GCS)                                                                                                             │ │
│ │ 2. Performance optimization and caching                                                                                                                 │ │
│ │ 3. Streaming pipeline execution                                                                                                                         │ │
│ │ 4. Circuit breaker and better retry logic                                                                                                               │ │
│ │                                                                                                                                                         │ │
│ │ ### Medium Priority                                                                                                                                     │ │
│ │ 5. Data encryption                                                                                                                                      │ │
│ │ 6. Input validation                                                                                                                                     │ │
│ │ 7. Alerting system                                                                                                                                      │ │
│ │ 8. Better error messages                                                                                                                                │ │
│ │                                                                                                                                                         │ │
│ │ ### Low Priority                                                                                                                                        │ │
│ │ 9. API documentation                                                                                                                                    │ │
│ │ 10. Dashboard improvements                                                                                                                              │ │
│ │ 11. Configuration path flexibility                                                                                                                      │ │
│ │ 12. Compression implementation                                                                                                                          │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ## Reporting Issues                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ If you discover new issues:                                                                                                                             │ │
│ │                                                                                                                                                         │ │
│ │ 1. Check if already documented here                                                                                                                     │ │
│ │ 2. Verify it's reproducible                                                                                                                             │ │
│ │ 3. Note Sprint 2 commit hash                                                                                                                            │ │
│ │ 4. Create detailed issue with:                                                                                                                          │ │
│ │    - Steps to reproduce                                                                                                                                 │ │
│ │    - Expected vs actual behavior                                                                                                                        │ │
│ │    - Environment details                                                                                                                                │ │
│ │    - Relevant logs                                                                                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ## Workaround Summary                                                                                                                                   │ │
│ │                                                                                                                                                         │ │
│ │ **Quick Reference for Common Issues**:                                                                                                                  │ │
│ │                                                                                                                                                         │ │
│ │ ```bash                                                                                                                                                 │ │
│ │ # Clean up test artifacts                                                                                                                               │ │
│ │ rm -rf test_data/ storage/ received_chunks/ logs/                                                                                                       │ │
│ │                                                                                                                                                         │ │
│ │ # Skip slow tests                                                                                                                                       │ │
│ │ pytest -m "not slow" tests/                                                                                                                             │ │
│ │                                                                                                                                                         │ │
│ │ # Debug mode                                                                                                                                            │ │
│ │ export LOG_LEVEL=DEBUG                                                                                                                                  │ │
│ │                                                                                                                                                         │ │
│ │ # Disable monitoring for faster tests                                                                                                                   │ │
│ │ # In code: PipelineOrchestrator(registry, enable_monitoring=False)                                                                                      │ │
│ │                                                                                                                                                         │ │
│ │ # Run from project root                                                                                                                                 │ │
│ │ cd /path/to/MultiCLoudTestsingSystem                                                                                                                    │ │
│ │ export PYTHONPATH=.                                                                                                                                     │ │
│ │ pytest tests/                                                                                                                                           │ │
│ │ ```                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ ---                                                                                                                                                     │ │
│ │                                                                                                                                                         │ │
│ │ **Last Updated**: Sprint 2 Completion                                                                                                                   │ │
│ │ **Next Review**: Sprint 3 Planning                                                                                                                      │ │
│ │                                    