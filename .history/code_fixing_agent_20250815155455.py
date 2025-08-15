"""
Code Fixing Agent for Spring Boot Applications

This agent analyzes exception information and generates Java code fixes using LLM capabilities.
It understands Spring Boot context and provides meaningful code suggestions.
"""

import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from log_analysis_agent import ExceptionInfo


@dataclass
class CodeFix:
    """Data class to hold code fix information"""
    exception_type: str
    exception_message: str
    root_cause: str
    fix_description: str
    code_suggestions: List[Dict[str, str]]  # [{"file": "...", "method": "...", "code": "..."}]
    prevention_tips: List[str]
    confidence_score: float  # 0.0 to 1.0


class CodeFixingAgent:
    """Agent responsible for analyzing exceptions and generating Java code fixes"""
    
    def __init__(self):
        #self.llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.1)
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
        
        # System prompt for code fixing
        self.system_prompt = """You are an expert Java and Spring Boot developer with extensive experience in debugging and fixing application issues. Your task is to analyze exception information from Spring Boot applications and provide practical, actionable code fixes.

When analyzing exceptions, consider:
1. The specific exception type and message
2. The stack trace to understand the call flow
3. Spring Boot best practices and common patterns
4. Potential root causes and prevention strategies
5. Code quality and maintainability

Provide fixes that are:
- Specific and actionable
- Following Spring Boot conventions
- Including proper error handling
- Considering edge cases
- Production-ready

Format your response as a structured analysis with clear code examples."""

        # Create the prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", """Analyze the following exception from a Spring Boot application and provide a comprehensive fix:

Exception Details:
- Type: {exception_type}
- Message: {exception_message}
- Timestamp: {timestamp}
- Log Level: {log_level}
- File: {file_path}
- Line: {line_number}
- Method: {method_name}
- Class: {class_name}

Stack Trace:
{stack_trace}

Surrounding Context:
{surrounding_context}

Please provide:
1. Root cause analysis
2. Specific code fixes with examples
3. Prevention strategies
4. Best practices recommendations

Format your response as JSON with the following structure:
{{
    "root_cause": "Detailed explanation of what caused this exception",
    "fix_description": "High-level description of the fix approach",
    "code_suggestions": [
        {{
            "file": "filename or class name",
            "method": "method name where fix should be applied",
            "description": "What this fix does",
            "original_issue": "The problematic code pattern",
            "fixed_code": "The corrected Java code",
            "explanation": "Why this fix works"
        }}
    ],
    "prevention_tips": [
        "Tip 1 for preventing similar issues",
        "Tip 2 for preventing similar issues"
    ],
    "confidence_score": 0.85
}}""")
        ])
    
    def analyze_exception(self, exception_info: ExceptionInfo) -> CodeFix:
        """Analyze a single exception and generate code fixes"""
        
        # Prepare the input data
        stack_trace_str = "\n".join(exception_info.stack_trace[:15])  # Limit to first 15 lines
        context_str = "\n".join(exception_info.surrounding_context)
        
        # Create the prompt
        prompt = self.prompt_template.format_messages(
            exception_type=exception_info.exception_type,
            exception_message=exception_info.exception_message,
            timestamp=exception_info.timestamp,
            log_level=exception_info.log_level,
            file_path=exception_info.file_path or "Unknown",
            line_number=exception_info.line_number or "Unknown",
            method_name=exception_info.method_name or "Unknown",
            class_name=exception_info.class_name or "Unknown",
            stack_trace=stack_trace_str,
            surrounding_context=context_str
        )
        
        try:
            # Get the LLM response
            response = self.llm.invoke(prompt)
            print(f"LLM response: {response.content}")
            # Parse the JSON response
            try:
                fix_data = json.loads(response.content)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                fix_data = {
                    "root_cause": "Unable to parse LLM response",
                    "fix_description": response.content[:500],
                    "code_suggestions": [],
                    "prevention_tips": [],
                    "confidence_score": 0.3
                }
            
            # Create CodeFix object
            code_fix = CodeFix(
                exception_type=exception_info.exception_type,
                exception_message=exception_info.exception_message,
                root_cause=fix_data.get("root_cause", "Unknown"),
                fix_description=fix_data.get("fix_description", "No description available"),
                code_suggestions=fix_data.get("code_suggestions", []),
                prevention_tips=fix_data.get("prevention_tips", []),
                confidence_score=fix_data.get("confidence_score", 0.5)
            )
            
            return code_fix
            
        except Exception as e:
            # Return a basic fix if LLM call fails
            return CodeFix(
                exception_type=exception_info.exception_type,
                exception_message=exception_info.exception_message,
                root_cause=f"Error analyzing exception: {str(e)}",
                fix_description="Unable to generate fix due to analysis error",
                code_suggestions=[],
                prevention_tips=[],
                confidence_score=0.0
            )
    
    def analyze_multiple_exceptions(self, exceptions: List[ExceptionInfo]) -> List[CodeFix]:
        """Analyze multiple exceptions and generate fixes for each"""
        fixes = []
        
        for exception in exceptions:
            try:
                fix = self.analyze_exception(exception)
                fixes.append(fix)
            except Exception as e:
                print(f"Error analyzing exception {exception.exception_type}: {str(e)}")
                # Add a placeholder fix
                fixes.append(CodeFix(
                    exception_type=exception.exception_type,
                    exception_message=exception.exception_message,
                    root_cause=f"Analysis failed: {str(e)}",
                    fix_description="Unable to generate fix",
                    code_suggestions=[],
                    prevention_tips=[],
                    confidence_score=0.0
                ))
        
        return fixes
    
    def format_fix_report(self, fix: CodeFix) -> str:
        """Format a code fix as a readable report"""
        report = f"""
=== CODE FIX ANALYSIS ===
Exception: {fix.exception_type}
Message: {fix.exception_message}
Confidence: {fix.confidence_score:.2f}

ROOT CAUSE:
{fix.root_cause}

FIX DESCRIPTION:
{fix.fix_description}

CODE SUGGESTIONS:
"""
        
        for i, suggestion in enumerate(fix.code_suggestions, 1):
            report += f"""
{i}. File: {suggestion.get('file', 'Unknown')}
   Method: {suggestion.get('method', 'Unknown')}
   Description: {suggestion.get('description', 'No description')}
   
   Issue: {suggestion.get('original_issue', 'Not specified')}
   
   Fixed Code:
   ```java
   {suggestion.get('fixed_code', 'No code provided')}
   ```
   
   Explanation: {suggestion.get('explanation', 'No explanation')}
"""
        
        report += "\nPREVENTION TIPS:\n"
        for i, tip in enumerate(fix.prevention_tips, 1):
            report += f"{i}. {tip}\n"
        
        return report
    
    @tool
    def fix_exceptions(self, exceptions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Tool to analyze exceptions and generate code fixes.
        
        Args:
            exceptions_data: List of exception dictionaries from log analysis
            
        Returns:
            Dictionary containing code fixes and analysis
        """
        try:
            # Convert dictionaries back to ExceptionInfo objects
            exceptions = []
            for exc_data in exceptions_data:
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
            
            # Generate fixes
            fixes = self.analyze_multiple_exceptions(exceptions)
            
            # Format result
            result = {
                "success": True,
                "total_exceptions": len(exceptions),
                "total_fixes": len(fixes),
                "fixes": []
            }
            
            for fix in fixes:
                result["fixes"].append({
                    "exception_type": fix.exception_type,
                    "exception_message": fix.exception_message,
                    "root_cause": fix.root_cause,
                    "fix_description": fix.fix_description,
                    "code_suggestions": fix.code_suggestions,
                    "prevention_tips": fix.prevention_tips,
                    "confidence_score": fix.confidence_score,
                    "formatted_report": self.format_fix_report(fix)
                })
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_exceptions": 0,
                "total_fixes": 0,
                "fixes": []
            }


# Example usage and testing
if __name__ == "__main__":
    agent = CodeFixingAgent()
    
    print("Code Fixing Agent initialized successfully!")
    print("Available methods:")
    print("- analyze_exception(exception_info): Analyze a single exception")
    print("- analyze_multiple_exceptions(exceptions): Analyze multiple exceptions")
    print("- fix_exceptions(exceptions_data): Tool version for LangGraph integration")

