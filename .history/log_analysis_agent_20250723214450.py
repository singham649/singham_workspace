"""
Log Analysis Agent for Spring Boot Applications

This agent reads SLF4J log files and extracts exception information including:
- Exception type and message
- Full stack trace
- Surrounding log context
- Timestamp and log level
"""

import re
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


@dataclass
class ExceptionInfo:
    """Data class to hold extracted exception information"""
    timestamp: str
    log_level: str
    exception_type: str
    exception_message: str
    stack_trace: List[str]
    surrounding_context: List[str]
    file_path: str
    line_number: Optional[int] = None
    method_name: Optional[str] = None
    class_name: Optional[str] = None


class LogAnalysisAgent:
    """Agent responsible for analyzing Spring Boot log files and extracting exception information"""
    
    def __init__(self):
        #self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        
        # Common Spring Boot log patterns
        self.log_patterns = {
            # Standard Spring Boot log pattern: timestamp [level] pid --- [thread] logger : message
            'spring_boot': re.compile(
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(\w+)\s+\d+\s+---\s+\[([^\]]+)\]\s+([^:]+)\s*:\s*(.*)'
            ),
            # Alternative log pattern
            'alternative': re.compile(
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.*)'
            ),
            # Simple timestamp pattern
            'simple': re.compile(
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(.*)'
            )
        }
        
        # Exception patterns
        self.exception_patterns = {
            'exception_line': re.compile(r'(\w+(?:\.\w+)*Exception):\s*(.*?)(?:\s+at\s+|$)'),
            'caused_by': re.compile(r'Caused by:\s+(\w+(?:\.\w+)*Exception):\s*(.*?)(?:\s+at\s+|$)'),
            'stack_trace': re.compile(r'\s+at\s+([^(]+)\(([^:]+):(\d+)\)'),
            'more_lines': re.compile(r'\s+\.\.\.\s+(\d+)\s+more')
        }
    
    def read_log_file(self, file_path: str) -> List[str]:
        """Read log file and return lines"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.readlines()
        except Exception as e:
            raise Exception(f"Error reading log file {file_path}: {str(e)}")
    
    def parse_log_line(self, line: str) -> Optional[Dict[str, str]]:
        """Parse a single log line and extract timestamp, level, and message"""
        line = line.strip()
        if not line:
            return None
            
        # Try different log patterns
        for pattern_name, pattern in self.log_patterns.items():
            match = pattern.match(line)
            if match:
                if pattern_name == 'spring_boot':
                    return {
                        'timestamp': match.group(1),
                        'level': match.group(2),
                        'thread': match.group(3),
                        'logger': match.group(4),
                        'message': match.group(5),
                        'raw_line': line
                    }
                elif pattern_name == 'alternative':
                    return {
                        'timestamp': match.group(1),
                        'level': match.group(2),
                        'message': match.group(3),
                        'raw_line': line
                    }
                elif pattern_name == 'simple':
                    return {
                        'timestamp': match.group(1),
                        'level': 'INFO',  # Default level
                        'message': match.group(2),
                        'raw_line': line
                    }
        
        # If no pattern matches, treat as continuation line
        return {
            'timestamp': '',
            'level': '',
            'message': line,
            'raw_line': line,
            'is_continuation': True
        }
    
    def is_exception_line(self, message: str) -> bool:
        """Check if a log message contains an exception (but not stack trace lines)"""
        # Don't treat stack trace lines as new exceptions
        if message.strip().startswith('at ') or message.strip().startswith('...'):
            return False
            
        # Look for actual exception declarations
        exception_patterns = [
            r'\w+Exception:',
            r'\w+Error:',
            r'Caused by:\s+\w+',
            r'Exception in thread',
            r'java\.lang\.\w+Exception',
            r'java\.io\.\w+Exception',
            r'java\.sql\.\w+Exception',
            r'org\.springframework\.\w+Exception'
        ]
        
        return any(re.search(pattern, message) for pattern in exception_patterns)
    
    def extract_exception_details(self, lines: List[Dict[str, str]], start_index: int) -> ExceptionInfo:
        """Extract detailed exception information starting from the exception line"""
        exception_line = lines[start_index]
        stack_trace = []
        surrounding_context = []
        
        # Get surrounding context (5 lines before)
        context_start = max(0, start_index - 5)
        for i in range(context_start, start_index):
            if i < len(lines):
                surrounding_context.append(lines[i]['raw_line'])
        
        # Extract exception type and message
        exception_type = "Unknown"
        exception_message = exception_line['message']
        
        # Try to parse exception type and message
        for pattern_name, pattern in self.exception_patterns.items():
            if pattern_name in ['exception_line', 'caused_by']:
                match = pattern.search(exception_line['message'])
                if match:
                    exception_type = match.group(1)
                    exception_message = match.group(2) if match.group(2) else exception_line['message']
                    break
        
        # Extract stack trace (lines following the exception)
        current_index = start_index + 1
        while current_index < len(lines):
            line = lines[current_index]
            message = line['message']
            
            # Check if this is a stack trace line
            if self.exception_patterns['stack_trace'].match(message):
                stack_trace.append(message.strip())
            elif self.exception_patterns['more_lines'].match(message):
                stack_trace.append(message.strip())
            elif message.strip().startswith('at '):
                stack_trace.append(message.strip())
            elif 'Caused by:' in message:
                # This is a nested exception, include it in stack trace
                stack_trace.append(message.strip())
            elif line.get('is_continuation', False) and message.strip():
                # Continuation of exception message
                stack_trace.append(message.strip())
            else:
                # End of stack trace
                break
                
            current_index += 1
        
        # Extract file path, line number, method, and class from first stack trace line
        file_path = ""
        line_number = None
        method_name = None
        class_name = None
        
        if stack_trace:
            first_stack_line = stack_trace[0]
            stack_match = self.exception_patterns['stack_trace'].search(first_stack_line)
            if stack_match:
                method_full = stack_match.group(1)
                file_name = stack_match.group(2)
                line_number = int(stack_match.group(3))
                
                # Extract class and method name
                if '.' in method_full:
                    parts = method_full.rsplit('.', 1)
                    class_name = parts[0]
                    method_name = parts[1]
                else:
                    method_name = method_full
                
                file_path = file_name
        
        return ExceptionInfo(
            timestamp=exception_line['timestamp'],
            log_level=exception_line['level'],
            exception_type=exception_type,
            exception_message=exception_message,
            stack_trace=stack_trace,
            surrounding_context=surrounding_context,
            file_path=file_path,
            line_number=line_number,
            method_name=method_name,
            class_name=class_name
        )
    
    def analyze_log_file(self, file_path: str) -> List[ExceptionInfo]:
        """Main method to analyze a log file and extract all exceptions"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Log file not found: {file_path}")
        
        raw_lines = self.read_log_file(file_path)
        parsed_lines = []
        
        # Parse all lines
        for line in raw_lines:
            parsed = self.parse_log_line(line)
            if parsed:
                parsed_lines.append(parsed)
        
        # Find and extract exceptions
        exceptions = []
        i = 0
        while i < len(parsed_lines):
            line = parsed_lines[i]
            if self.is_exception_line(line['message']):
                try:
                    exception_info = self.extract_exception_details(parsed_lines, i)
                    exceptions.append(exception_info)
                except Exception as e:
                    print(f"Error extracting exception at line {i}: {str(e)}")
            i += 1
        
        return exceptions
    
    def format_exception_summary(self, exception: ExceptionInfo) -> str:
        """Format exception information for display"""
        summary = f"""
Exception Summary:
- Timestamp: {exception.timestamp}
- Level: {exception.log_level}
- Type: {exception.exception_type}
- Message: {exception.exception_message}
- File: {exception.file_path}
- Line: {exception.line_number}
- Method: {exception.method_name}
- Class: {exception.class_name}

Stack Trace:
{chr(10).join(exception.stack_trace[:10])}  # Show first 10 lines

Context:
{chr(10).join(exception.surrounding_context)}
"""
        return summary
    
    @tool
    def analyze_logs(self, log_file_path: str) -> Dict[str, Any]:
        """
        Tool to analyze Spring Boot log files and extract exception information.
        
        Args:
            log_file_path: Path to the log file to analyze
            
        Returns:
            Dictionary containing extracted exceptions and summary
        """
        try:
            exceptions = self.analyze_log_file(log_file_path)
            
            result = {
                "success": True,
                "file_path": log_file_path,
                "total_exceptions": len(exceptions),
                "exceptions": []
            }
            
            for exc in exceptions:
                result["exceptions"].append({
                    "timestamp": exc.timestamp,
                    "log_level": exc.log_level,
                    "exception_type": exc.exception_type,
                    "exception_message": exc.exception_message,
                    "stack_trace": exc.stack_trace,
                    "surrounding_context": exc.surrounding_context,
                    "file_path": exc.file_path,
                    "line_number": exc.line_number,
                    "method_name": exc.method_name,
                    "class_name": exc.class_name,
                    "summary": self.format_exception_summary(exc)
                })
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": log_file_path
            }


# Example usage and testing
if __name__ == "__main__":
    agent = LogAnalysisAgent()
    
    # Test with a sample log file (will be created in testing phase)
    print("Log Analysis Agent initialized successfully!")
    print("Available methods:")
    print("- analyze_log_file(file_path): Analyze a log file and return exceptions")
    print("- analyze_logs(file_path): Tool version for LangGraph integration")

