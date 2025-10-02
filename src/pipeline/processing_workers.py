import asyncio
import hashlib
import random
import time
import yaml
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Callable, Dict, Optional

class ProcessingStatus(Enum):
    PENDING= "pending"
    PROCESSING="processing"
    COMPLETED="completed"
    FAILED="failed"
    RETRYING="retrying"

@dataclass
class ProcessingTask:
    task_id: str
    chunk_id: str
    chunk_data: bytes
    status: ProcessingStatus=ProcessingStatus.PENDING
    assigned_node: Optional[str]=None
    attempts: int=0
    start_time:Optional[float]=None
    end_time: Optional[float]=None
    error_message: Optional[str]=None
    result:Optional[bytes]=None
    
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

@dataclass
class NodeWorkload:
    node_id:str
    cloud_provider: str
    active_tasks: int=0
    completed_tasks: int=0
    failed_tasks: int=0
    current_load: float=0.0 #o.oto 1.0

    def calculate_load(self, max_workers:int)-> float:
        return self.active_tasks / max_workers if max_workers >0 else 0.0


class ProceessingFunction:
    """base class for data processing funcs"""

    def __init__(self, name: str, config:Dict):
        self.name=name
        self.config=config
        self.timeout=config.get('timeout_seconds',60)

    async def process(self, data:bytes)-> bytes:
        """essesntially an absttact fucn"""
        raise NotImplementedError("Subclasses need to implement this")
    
class DataValidator(ProceessingFunction):
    """"vlaidate data integreiyt"""

    async def process(self, data: bytes) -> bytes:
        if not data or len(data)==0:
            raise ValueError("data is empty/corrupted")
        #calc checksume
        checksum=hashlib.md5(data).hexdigest()
        print(f" Validated data: {len(data)} bytes, checksum: {checksum[:8]}...")
        return data  #no mods

class DataTransformer(ProceessingFunction):
    """Transform data (preprocessing for ML training)"""
    
    async def process(self, data: bytes) -> bytes:
        """Transform data for ML training"""
        # Simulate preprocessing operations:
        # - Normalization
        # - Feature extraction
        # - Data augmentation
        
        print(f"   ⚡ Transforming data: {len(data)} bytes")
        
        # For Sprint 2: simulate transformation with small modification
        # In real implementation: apply actual ML preprocessing
        transformed_data = data  # Actual transformation would happen here
        
        return transformed_data
    
class DataCompressor(ProceessingFunction):
    """compress data to save storgage/bandwidht"""
    async def process(self, data:bytes)->bytes:
        import zlib  #putin reqs.txt?
        compressed = zllib.compression(data, level=6)  #tunable see if this makes a difference
        compression_ratio=len(compressed) / len(data)

        print(f"   🗜️  Compressed data: {len(data)} → {len(compressed)} bytes ({compression_ratio:.1%})")

        return compressed
    
class ProcessingWorkerPool:
    """Distributed processing worker pool across multi-cloud nodes -wahatttt"""
    def __init__(self, node_registry, config_path: str='config/processing_config.yml'):
            self.node_registry=node_registry
            #load/get config
            with open(config_path, 'r') as f:
                self.config=yaml.safe_load(f)

            processing_config=self.config.get('processing', {})
            self.max_workers_per_node=processing_config.get('max_workers+per_node', 4)
            self.worker_timeout = processing_config.get('worker_timeout_seconds', 300)
            self.max_concurrent_tasks = processing_config.get('max_concurrent_tasks', 20)
        
            # Load balancing configuration
            lb_config = processing_config.get('load_balancing', {})
            self.load_balancing_strategy = lb_config.get('strategy', 'least_loaded')
            self.rebalance_threshold = lb_config.get('rebalance_threshold', 0.3)
            
            # Failure handling configuration
            failure_config = processing_config.get('failure_handling', {})
            self.max_retries = failure_config.get('max_retries', 3)
            self.retry_delay = failure_config.get('retry_delay_seconds', 5)
            self.exponential_backoff = failure_config.get('retry_exponential_backoff', True)
            self.redistribute_on_failure = failure_config.get('redistribute_on_failure', True)
            
            # Processing pipeline
            self.processing_pipeline = self._initialize_processing_pipeline()
            
            # Track node workloads
            self.node_workloads: Dict[str, NodeWorkload] = {}
            
            # Task tracking
            self.pending_tasks: List[ProcessingTask] = []
            self.active_tasks: Dict[str, ProcessingTask] = {}
            self.completed_tasks: List[ProcessingTask] = []
            self.failed_tasks: List[ProcessingTask] = []
            
            # Simulation mode (for Sprint 2 testing)
            self.simulate_processing = self.config.get('simulate_processing', True)
            self.simulated_processing_time = self.config.get('simulated_processing_time_ms', 100) / 1000.0
            
            print(f"⚡ Processing Worker Pool initialized")
            print(f"   Max workers per node: {self.max_workers_per_node}")
            print(f"   Load balancing: {self.load_balancing_strategy}")
            print(f"   Processing pipeline: {len(self.processing_pipeline)} steps")
            print(f"   Simulation mode: {self.simulate_processing}")
    
    def _initialize_processing_pipeline(self)-> List[ProceessingFunction]:
        """Initialize prcs funcs form config"""
        pipeline=[]
        pipeline_config = self.config.get('processing', {}).get('processing_pipeline', [])

        for step_config in pipeline_config:
            if not step_config.get('enabled', True):
                continue

            step_name=step_config['name']

            #now create prcs func based on nname
            if step_name == 'validate_data':
                pipeline.append(DataValidator(step_name, step_config))
            elif step_name == 'transform_data':
                pipeline.append(DataTransformer(step_name, step_config))
            elif step_name == 'compress_data':
                pipeline.append(DataCompressor(step_name, step_config))
            else:
                print(f"   ⚠️  Unknown processing function: {step_name}")

        return pipeline


    def _initialize_node_workloads(self):
        """initialzie workload tracking for all of the nodes"""
        for node_id, node_info, in self.node_registry.nodes.items():
            if node_info.status=='healthy':
                self.node_workloads[node_id]=NodeWorkload(
                    node_id=node_id,
                    cloud_provider=node_info.cloud_provider
                )


    async def process_chunks(self, chunks: List) -> List[ProceessingFunction]:
        """main entry: here is whrere we will process all chunks
        across all the available nodes
        Args: chunks: list of datachunk objects from ingestion engine
        Returns:List of ProcessingTask results"""

        print(f"\n⚡ Starting distributed processing of {len(chunks)} chunks...")
        #initialisze node work load tracking
        self._initialize_node_workloads()

        #make procssing tasks form the chunks
        self.pending_tasks=[ 
            ProcessingTask(
                task_id=f"task_{i}",
                chunk_id=chunk.chunk_id,
                chunk_data=chunk.data
            )
            for i, chunk in enumerate(chunks) #not sure about htis for loop location
            #i get it but will future me get it/like it/swear  at me? yes
        ]

        await self._process_tasks_with_concurrency()

        #make summaryy

        total_tasks = len(self.completed_tasks) + len(self.failed_tasks)
        success_rate = len(self.completed_tasks) / total_tasks if total_tasks > 0 else 0
        
        print(f"\n✅ Processing complete:")
        print(f"   Total tasks: {total_tasks}")
        print(f"   Completed: {len(self.completed_tasks)}")
        print(f"   Failed: {len(self.failed_tasks)}")
        print(f"   Success rate: {success_rate:.1%}")
        
        return self.completed_tasks + self.failed_tasks

    async def _process_tasks_with_concurrency(self):
        """Process takes within/at concurrencty limit"""
        while self.pending_tasks or self.active_tasks:
            #strt new tasks up to concurrency limit
            while (len(self.active_tasks) < self.max_concurrent_tasks and 
                   self.pending_tasks):
                
                task = self.pending_tasks.pop(0)
                
                # Select node for this task
                selected_node = self.select_node_for_task(task)
                
                if not selected_node:
                    # No available nodes, put task back
                    self.pending_tasks.insert(0, task)
                    break
                
                # Assign task to node
                task.assigned_node = selected_node
                task.status = ProcessingStatus.PROCESSING
                self.active_tasks[task.task_id] = task
                
                # Update node workload
                self.node_workloads[selected_node].active_tasks += 1
                self.node_workloads[selected_node].current_load = \
                    self.node_workloads[selected_node].calculate_load(self.max_workers_per_node)
                
                # Start processing task
                asyncio.create_task(self._process_task(task))
            
            # Wait a bit before checking again
            await asyncio.sleep(0.1)

    # this next function will be an area of interest, selecting nodes optimally 
    # will be a tunable feature (i htink)also tuning based on laod balancing 
    #strategy
    def select_node_for_task(self, task: ProcessingTask) -> Optional[str]:
        available_nodes = [
            node_id for node_id, workload in self.node_workloads.items()
            if workload.active_tasks < self.max_workers_per_node
        ]
        
        if not available_nodes:
            return None
        
        if self.load_balancing_strategy == 'round_robin':
            # Simple round-robin selection
            return available_nodes[len(self.completed_tasks) % len(available_nodes)]
        
        elif self.load_balancing_strategy == 'least_loaded':
            # Select node with lowest current load
            least_loaded = min(
                available_nodes,
                key=lambda node_id: self.node_workloads[node_id].current_load
            )
            return least_loaded
        
        elif self.load_balancing_strategy == 'random':
            # Random selection (for testing/comparison)
            return random.choice(available_nodes)
        
        else:
            # Default to least loaded
            return available_nodes[0]

    async def _process_task(self, task: ProcessingTask):
        """process sngle task on assigned node"""
        #this might be problemeatic b/c time is nto reliable  we will find out
        task.start_time = time.time()
        
        try:
            # Execute processing pipeline
            processed_data = await self._execute_processing_pipeline(
                task.chunk_data,
                task.assigned_node
            )
            
            # Task completed successfully
            task.status = ProcessingStatus.COMPLETED
            task.result = processed_data
            task.end_time = time.time()
            
            # Move to completed
            del self.active_tasks[task.task_id]
            self.completed_tasks.append(task)
            
            # Update node workload
            node_workload = self.node_workloads[task.assigned_node]
            node_workload.active_tasks -= 1
            node_workload.completed_tasks += 1
            node_workload.current_load = node_workload.calculate_load(self.max_workers_per_node)
            
        except Exception as e:
            # Task failed
            task.status = ProcessingStatus.FAILED
            task.error_message = str(e)
            task.end_time = time.time()
            task.attempts += 1
            
            # Update node workload
            node_workload = self.node_workloads[task.assigned_node]
            node_workload.active_tasks -= 1
            node_workload.failed_tasks += 1
            node_workload.current_load = node_workload.calculate_load(self.max_workers_per_node)
            
            # Handle retry
            if task.attempts < self.max_retries:
                print(f"   ⚠️  Task {task.task_id} failed (attempt {task.attempts}/{self.max_retries}): {e}")
                
                # Calculate retry delay with exponential backoff
                if self.exponential_backoff:
                    delay = self.retry_delay * (2 ** (task.attempts - 1))
                else:
                    delay = self.retry_delay
                
                await asyncio.sleep(delay)
                
                # Retry the task
                task.status = ProcessingStatus.RETRYING
                task.assigned_node = None  # Will be reassigned
                
                del self.active_tasks[task.task_id]
                self.pending_tasks.append(task)
                
            else:
                # Max retries exceeded
                print(f"   ❌ Task {task.task_id} failed permanently after {task.attempts} attempts")
                del self.active_tasks[task.task_id]
                self.failed_tasks.append(task)


    async def _execute_processing_pipeline(self, data: bytes, node_id: str) -> bytes:
        """Execute the processing pipeline on data"""
        
        if self.simulate_processing:
            # Sprint 2: Simulate processing
            await asyncio.sleep(self.simulated_processing_time)
            return data  # Return data unchanged in simulation
        
        else:
            # Real processing: Execute each step in pipeline
            current_data = data
            
            for processing_func in self.processing_pipeline:
                try:
                    # Execute processing function with timeout
                    current_data = await asyncio.wait_for(
                        processing_func.process(current_data),
                        timeout=processing_func.timeout
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(f"Processing step '{processing_func.name}' timed out")
                except Exception as e:
                    raise RuntimeError(f"Processing step '{processing_func.name}' failed: {e}")
            
            return current_data
        

    def get_processing_statistics(self) -> Dict:
        """Get processing statistics for monitoring"""
        
        total_tasks = len(self.completed_tasks) + len(self.failed_tasks)
        
        # Calculate average processing time
        completed_durations = [t.duration_seconds() for t in self.completed_tasks]
        avg_duration = sum(completed_durations) / len(completed_durations) if completed_durations else 0
        
        # Node-level statistics
        node_stats = {}
        for node_id, workload in self.node_workloads.items():
            node_stats[node_id] = {
                'completed_tasks': workload.completed_tasks,
                'failed_tasks': workload.failed_tasks,
                'current_load': workload.current_load,
                'total_tasks': workload.completed_tasks + workload.failed_tasks
            }
        
        return {
            'total_tasks': total_tasks,
            'completed': len(self.completed_tasks),
            'failed': len(self.failed_tasks),
            'success_rate': len(self.completed_tasks) / total_tasks if total_tasks > 0 else 0,
            'average_duration_seconds': avg_duration,
            'node_statistics': node_stats
        }

