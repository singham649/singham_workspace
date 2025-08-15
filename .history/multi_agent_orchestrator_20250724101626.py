"""
Multi-Agent Orchestrator for Spring Boot Log Analysis and Code Fixing

This module implements a LangGraph-based supervisor architecture that orchestrates
the Log Analysis Agent and Code Fixing Agent to provide end-to-end exception
analysis and code fixing capabilities.
"""

import json
import os
from typing import List, Dict, Any, Literal, TypedDict, Annotated
from dataclasses import asdict
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain-google-genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool

from log_analysis_agent import LogAnalysisAgent, ExceptionInfo
from code_fixing_agent import CodeFixingAgent, CodeFix


class AgentState(TypedDict):
    """State shared between agents in the workflow"""
    messages: Annotated[List[Dict[str, Any]], "Messages in the conversation"]
    log_file_path: str
    exceptions: List[Dict[str, Any]]
    fixes: List[Dict[str, Any]]
    current_step: str
    error_message: str
    total_exceptions: int
    total_fixes: int
    workflow_complete: bool


class SpringBootLogAnalyzer:
    """Main orchestrator class that manages the multi-agent workflow"""
    
    def __init__(self):
        self.log_agent = LogAnalysisAgent()
        self.fix_agent = CodeFixingAgent()
        #self.supervisor_llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
        self.supervisor_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for multi-agent orchestration"""
        
        # Define the workflow graph
        workflow = StateGraph(AgentState)
        
        # Add nodes for each agent and supervisor
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("log_analysis", self._log_analysis_node)
        workflow.add_node("code_fixing", self._code_fixing_node)
        workflow.add_node("report_generation", self._report_generation_node)
        
        # Define the workflow edges
        workflow.add_edge(START, "supervisor")
        workflow.add_conditional_edges(
            "supervisor",
            self._supervisor_decision,
            {
                "log_analysis": "log_analysis",
                "code_fixing": "code_fixing", 
                "report_generation": "report_generation",
                "end": END
            }
        )
        workflow.add_edge("log_analysis", "supervisor")
        workflow.add_edge("code_fixing", "supervisor")
        workflow.add_edge("report_generation", END)
        
        return workflow.compile()
    
    def _supervisor_node(self, state: AgentState) -> AgentState:
        """Supervisor node that decides which agent to call next"""
        
        # Determine the next step based on current state
        if not state.get("log_file_path"):
            state["error_message"] = "No log file path provided"
            state["workflow_complete"] = True
            return state
        
        if state["current_step"] == "start":
            state["current_step"] = "log_analysis"
            state["messages"].append({
                "role": "supervisor",
                "content": f"Starting log analysis for file: {state['log_file_path']}"
            })
        
        elif state["current_step"] == "log_analysis_complete":
            if state["total_exceptions"] > 0:
                state["current_step"] = "code_fixing"
                state["messages"].append({
                    "role": "supervisor", 
                    "content": f"Log analysis complete. Found {state['total_exceptions']} exceptions. Starting code fixing..."
                })
            else:
                state["current_step"] = "report_generation"
                state["messages"].append({
                    "role": "supervisor",
                    "content": "No exceptions found in log file. Generating report..."
                })
        
        elif state["current_step"] == "code_fixing_complete":
            state["current_step"] = "report_generation"
            state["messages"].append({
                "role": "supervisor",
                "content": f"Code fixing complete. Generated {state['total_fixes']} fixes. Generating final report..."
            })
        
        elif state["current_step"] == "report_complete":
            state["workflow_complete"] = True
            state["messages"].append({
                "role": "supervisor",
                "content": "Workflow completed successfully!"
            })
        
        return state
    
    def _supervisor_decision(self, state: AgentState) -> Literal["log_analysis", "code_fixing", "report_generation", "end"]:
        """Decision function for supervisor routing"""
        
        if state.get("workflow_complete", False) or state.get("error_message"):
            return "end"
        
        current_step = state.get("current_step", "start")
        
        if current_step == "log_analysis":
            return "log_analysis"
        elif current_step == "code_fixing":
            return "code_fixing"
        elif current_step == "report_generation":
            return "report_generation"
        else:
            return "end"
    
    def _log_analysis_node(self, state: AgentState) -> AgentState:
        """Node that handles log analysis using the Log Analysis Agent"""
        
        try:
            # Analyze the log file
            exceptions = self.log_agent.analyze_log_file(state["log_file_path"])
            
            # Convert exceptions to dictionaries for state storage
            exceptions_data = []
            for exc in exceptions:
                exc_dict = asdict(exc)
                exceptions_data.append(exc_dict)
            
            # Update state
            state["exceptions"] = exceptions_data
            state["total_exceptions"] = len(exceptions)
            state["current_step"] = "log_analysis_complete"
            
            state["messages"].append({
                "role": "log_analyst",
                "content": f"Successfully analyzed log file. Found {len(exceptions)} exceptions.",
                "data": {
                    "exceptions_count": len(exceptions),
                    "exception_types": list(set([exc.exception_type for exc in exceptions]))
                }
            })
            
        except Exception as e:
            state["error_message"] = f"Log analysis failed: {str(e)}"
            state["messages"].append({
                "role": "log_analyst",
                "content": f"Error during log analysis: {str(e)}"
            })
        
        return state
    
    def _code_fixing_node(self, state: AgentState) -> AgentState:
        """Node that handles code fixing using the Code Fixing Agent"""
        
        try:
            # Convert exception dictionaries back to ExceptionInfo objects
            exceptions = []
            for exc_data in state["exceptions"]:
                exception = ExceptionInfo(
                    timestamp=exc_data.get("timestamp", ""),
                    log_level=exc_data.get("log_level", ""),
                    exception_type=exc_data.get("exception_type", ""),
                    exception_message=exc_data.get("exception_message", ""),
                    stack_trace=exc_data.get("stack_trace", []),
                    surrounding_context=exc_data.get("surrounding_context", []),
                    file_path=exc_data.get("file_path", ""),
                    line_number=exc_data.get("line_number"),
                    method_name=exc_data.get("method_name"),
                    class_name=exc_data.get("class_name")
                )
                exceptions.append(exception)
            
            # Filter to main exceptions (avoid duplicates)
            main_exceptions = [exc for exc in exceptions if exc.stack_trace and len(exc.stack_trace) > 5]
            
            # Generate fixes for main exceptions
            fixes = self.fix_agent.analyze_multiple_exceptions(main_exceptions)
            
            # Convert fixes to dictionaries for state storage
            fixes_data = []
            for fix in fixes:
                fix_dict = asdict(fix)
                fixes_data.append(fix_dict)
            
            # Update state
            state["fixes"] = fixes_data
            state["total_fixes"] = len(fixes)
            state["current_step"] = "code_fixing_complete"
            
            state["messages"].append({
                "role": "code_fixer",
                "content": f"Successfully generated {len(fixes)} code fixes.",
                "data": {
                    "fixes_count": len(fixes),
                    "avg_confidence": sum([fix.confidence_score for fix in fixes]) / len(fixes) if fixes else 0
                }
            })
            
        except Exception as e:
            state["error_message"] = f"Code fixing failed: {str(e)}"
            state["messages"].append({
                "role": "code_fixer",
                "content": f"Error during code fixing: {str(e)}"
            })
        
        return state
    
    def _report_generation_node(self, state: AgentState) -> AgentState:
        """Node that generates the final analysis report"""
        
        try:
            # Generate comprehensive report
            report = self._generate_comprehensive_report(state)
            
            # Save report to file
            report_path = f"analysis_report_{os.path.basename(state['log_file_path'])}.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            state["current_step"] = "report_complete"
            state["messages"].append({
                "role": "reporter",
                "content": f"Generated comprehensive analysis report: {report_path}",
                "data": {
                    "report_path": report_path,
                    "total_exceptions": state["total_exceptions"],
                    "total_fixes": state["total_fixes"]
                }
            })
            
        except Exception as e:
            state["error_message"] = f"Report generation failed: {str(e)}"
            state["messages"].append({
                "role": "reporter",
                "content": f"Error during report generation: {str(e)}"
            })
        
        return state
    
    def _generate_comprehensive_report(self, state: AgentState) -> str:
        """Generate a comprehensive analysis report"""
        
        report = f"""# Spring Boot Log Analysis Report

## Summary
- **Log File**: {state['log_file_path']}
- **Total Exceptions Found**: {state['total_exceptions']}
- **Code Fixes Generated**: {state['total_fixes']}
- **Analysis Date**: {os.popen('date').read().strip()}

## Exception Analysis

"""
        
        if state["exceptions"]:
            for i, exc in enumerate(state["exceptions"], 1):
                if exc.get("stack_trace") and len(exc.get("stack_trace", [])) > 5:  # Main exceptions only
                    report += f"""### Exception {i}: {exc.get('exception_type', 'Unknown')}

**Message**: {exc.get('exception_message', 'No message')}
**Timestamp**: {exc.get('timestamp', 'Unknown')}
**Location**: {exc.get('class_name', 'Unknown')}.{exc.get('method_name', 'Unknown')}() at {exc.get('file_path', 'Unknown')}:{exc.get('line_number', 'Unknown')}

**Stack Trace** (first 10 lines):
```
{chr(10).join(exc.get('stack_trace', [])[:10])}
```

"""
        else:
            report += "No exceptions found in the log file.\n\n"
        
        report += "## Code Fix Recommendations\n\n"
        
        if state["fixes"]:
            for i, fix in enumerate(state["fixes"], 1):
                report += f"""### Fix {i}: {fix.get('exception_type', 'Unknown')}

**Root Cause**: {fix.get('root_cause', 'Unknown')}

**Fix Description**: {fix.get('fix_description', 'No description')}

**Confidence Score**: {fix.get('confidence_score', 0):.2f}

**Code Suggestions**:
"""
                
                for j, suggestion in enumerate(fix.get('code_suggestions', []), 1):
                    report += f"""
{j}. **File**: {suggestion.get('file', 'Unknown')}
   **Method**: {suggestion.get('method', 'Unknown')}
   **Description**: {suggestion.get('description', 'No description')}
   
   **Fixed Code**:
   ```java
   {suggestion.get('fixed_code', 'No code provided')}
   ```
   
   **Explanation**: {suggestion.get('explanation', 'No explanation')}
"""
                
                report += f"""
**Prevention Tips**:
"""
                for tip in fix.get('prevention_tips', []):
                    report += f"- {tip}\n"
                
                report += "\n---\n\n"
        else:
            report += "No code fixes were generated.\n\n"
        
        report += """## Workflow Messages

"""
        for msg in state["messages"]:
            report += f"**{msg['role'].title()}**: {msg['content']}\n\n"
        
        return report
    
    def analyze_log_file(self, log_file_path: str) -> Dict[str, Any]:
        """Main entry point to analyze a log file using the multi-agent workflow"""
        
        if not os.path.exists(log_file_path):
            return {
                "success": False,
                "error": f"Log file not found: {log_file_path}",
                "workflow_complete": False
            }
        
        # Initialize state
        initial_state = AgentState(
            messages=[],
            log_file_path=log_file_path,
            exceptions=[],
            fixes=[],
            current_step="start",
            error_message="",
            total_exceptions=0,
            total_fixes=0,
            workflow_complete=False
        )
        
        try:
            # Run the workflow
            final_state = self.workflow.invoke(initial_state)
            
            return {
                "success": not bool(final_state.get("error_message")),
                "error": final_state.get("error_message", ""),
                "log_file_path": final_state["log_file_path"],
                "total_exceptions": final_state["total_exceptions"],
                "total_fixes": final_state["total_fixes"],
                "exceptions": final_state["exceptions"],
                "fixes": final_state["fixes"],
                "messages": final_state["messages"],
                "workflow_complete": final_state["workflow_complete"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Workflow execution failed: {str(e)}",
                "workflow_complete": False
            }


# Tool for external integration
@tool
def analyze_spring_boot_logs(log_file_path: str) -> Dict[str, Any]:
    """
    Tool to analyze Spring Boot log files using the multi-agent workflow.
    
    Args:
        log_file_path: Path to the Spring Boot log file to analyze
        
    Returns:
        Dictionary containing analysis results and code fixes
    """
    analyzer = SpringBootLogAnalyzer()
    return analyzer.analyze_log_file(log_file_path)


# Example usage and testing
if __name__ == "__main__":
    analyzer = SpringBootLogAnalyzer()
    
    print("Multi-Agent Spring Boot Log Analyzer initialized successfully!")
    print("Available methods:")
    print("- analyze_log_file(file_path): Analyze a log file using the complete workflow")
    print("- analyze_spring_boot_logs(file_path): Tool version for external integration")

