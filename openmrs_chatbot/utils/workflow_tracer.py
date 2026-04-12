"""
Comprehensive workflow tracing system for detailed backend processing visibility.
Captures every step of query processing from input to response generation.
"""

import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Thread-local storage for current trace context
_trace_context = threading.local()

# Global trace storage (limited to last N queries for memory efficiency)
_trace_history: Dict[str, Dict[str, Any]] = {}
_max_traces = 50
_trace_lock = threading.Lock()


class WorkflowTracer:
    """Captures and manages workflow traces for each query."""
    
    def __init__(self, query_id: str, question: str, user_role: str, patient_id: Optional[str] = None):
        self.query_id = query_id
        self.question = question
        self.user_role = user_role
        self.patient_id = patient_id
        self.start_time = time.time()
        self.steps: List[Dict[str, Any]] = []
        self.stages: Dict[str, Dict[str, Any]] = {}
        self.metadata = {
            "query_id": query_id,
            "question": question,
            "user_role": user_role,
            "patient_id": patient_id,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "total_duration_ms": None,
        }
    
    def add_step(self, stage: str, action: str, details: Dict[str, Any] = None, 
                 duration_ms: float = None, status: str = "success"):
        """Log a single step in the workflow."""
        step = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "action": action,
            "status": status,
            "details": details or {},
            "duration_ms": duration_ms,
        }
        self.steps.append(step)
        
        # Log to file logger
        log_msg = f"[TRACE] {stage} → {action} ({status})"
        if duration_ms:
            log_msg += f" ({duration_ms:.2f}ms)"
        if details:
            log_msg += f" | {json.dumps(details)}"
        logger.info(log_msg)
    
    def start_stage(self, stage_name: str, description: str = ""):
        """Mark the start of a processing stage."""
        if stage_name not in self.stages:
            self.stages[stage_name] = {
                "name": stage_name,
                "description": description,
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "duration_ms": None,
                "agents_involved": [],
                "data_sources": [],
                "substeps": [],
            }
        logger.info(f"[STAGE START] {stage_name}")
    
    def end_stage(self, stage_name: str):
        """Mark the end of a processing stage."""
        if stage_name in self.stages:
            end_time = time.time()
            stage = self.stages[stage_name]
            start = datetime.fromisoformat(stage["start_time"])
            duration_ms = (end_time - start.timestamp()) * 1000
            stage["end_time"] = datetime.now().isoformat()
            stage["duration_ms"] = duration_ms
            logger.info(f"[STAGE END] {stage_name} ({duration_ms:.2f}ms)")
    
    def add_agent_involvement(self, stage_name: str, agent_name: str, action: str, 
                             result_summary: str = "", duration_ms: float = None):
        """Track agent involvement in a stage."""
        if stage_name in self.stages:
            self.stages[stage_name]["agents_involved"].append({
                "agent": agent_name,
                "action": action,
                "result": result_summary,
                "duration_ms": duration_ms,
            })
            logger.info(f"[AGENT] {agent_name} in {stage_name}: {action}")
    
    def add_data_source(self, stage_name: str, source_name: str, query_type: str = "", 
                       record_count: int = 0, duration_ms: float = None):
        """Track data fetches from external sources."""
        if stage_name in self.stages:
            self.stages[stage_name]["data_sources"].append({
                "source": source_name,
                "query_type": query_type,
                "records_retrieved": record_count,
                "duration_ms": duration_ms,
            })
            logger.info(f"[DATA SOURCE] {source_name} in {stage_name}: {record_count} records ({duration_ms:.2f}ms)")
    
    def add_substep(self, stage_name: str, step_description: str, details: Dict = None):
        """Add a detailed substep within a stage."""
        if stage_name in self.stages:
            self.stages[stage_name]["substeps"].append({
                "description": step_description,
                "timestamp": datetime.now().isoformat(),
                "details": details or {},
            })
    
    def finalize(self, response: str, sources: List[str], processing_info: Dict = None):
        """Complete the trace with final response info."""
        end_time = time.time()
        duration_ms = (end_time - self.start_time) * 1000
        
        self.metadata["end_time"] = datetime.now().isoformat()
        self.metadata["total_duration_ms"] = duration_ms
        self.metadata["response_length"] = len(response)
        self.metadata["sources"] = sources
        if processing_info:
            self.metadata.update(processing_info)
        
        logger.info(f"[TRACE COMPLETE] Query {self.query_id} completed in {duration_ms:.2f}ms")
        
        # Store in history
        self._store_in_history()
    
    def _store_in_history(self):
        """Store trace in global history with size limit."""
        with _trace_lock:
            _trace_history[self.query_id] = self.to_dict()
            
            # Remove oldest if exceeds max
            if len(_trace_history) > _max_traces:
                oldest_key = min(_trace_history.keys(), 
                               key=lambda k: _trace_history[k]["metadata"]["start_time"])
                del _trace_history[oldest_key]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for API responses."""
        return {
            "metadata": self.metadata,
            "stages": self.stages,
            "steps": self.steps,
        }


def get_current_tracer() -> Optional[WorkflowTracer]:
    """Get the current trace context for the running thread."""
    return getattr(_trace_context, 'tracer', None)


def set_current_tracer(tracer: WorkflowTracer):
    """Set the trace context for the running thread."""
    _trace_context.tracer = tracer


def create_tracer(question: str, user_role: str, patient_id: Optional[str] = None) -> WorkflowTracer:
    """Create a new tracer and set it as current context."""
    import uuid
    query_id = str(uuid.uuid4())[:12]
    tracer = WorkflowTracer(query_id, question, user_role, patient_id)
    set_current_tracer(tracer)
    return tracer


def get_trace(query_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a completed trace by query ID."""
    with _trace_lock:
        return _trace_history.get(query_id)


def get_all_traces() -> Dict[str, Dict[str, Any]]:
    """Get all stored traces."""
    with _trace_lock:
        # Return copies to avoid external modifications
        return {k: v for k, v in _trace_history.items()}


def clear_traces():
    """Clear all stored traces (useful for testing)."""
    with _trace_lock:
        _trace_history.clear()


# Decorator for tracing function execution
def trace_execution(stage_name: str, action_name: str = None):
    """Decorator to automatically trace function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_current_tracer()
            if not tracer:
                return func(*args, **kwargs)
            
            action = action_name or func.__name__
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                
                # Extract useful details from result
                details = {}
                if isinstance(result, dict):
                    if "count" in result:
                        details["count"] = result["count"]
                    if "error" in result:
                        details["error"] = result["error"]
                
                tracer.add_step(stage_name, action, details, duration_ms, "success")
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                tracer.add_step(stage_name, action, {"error": str(e)}, duration_ms, "error")
                raise
        
        return wrapper
    return decorator
