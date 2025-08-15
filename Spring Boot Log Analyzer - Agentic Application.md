# Spring Boot Log Analyzer - Agentic Application

**Author**: Manus AI  
**Version**: 1.0.0  
**Date**: July 23, 2025

## Overview

The Spring Boot Log Analyzer is an advanced agentic application built using Python, LangChain, and LangGraph that automatically reads Spring Boot log files, extracts exception information, and generates intelligent code fixes. This multi-agent system leverages Large Language Models (LLMs) to provide developers with actionable insights and code recommendations for resolving application issues.

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Usage Examples](#usage-examples)
6. [API Reference](#api-reference)
7. [Configuration](#configuration)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)
10. [Contributing](#contributing)
11. [License](#license)

## Features

### Core Capabilities

- **Automated Log Analysis**: Parses SLF4J-formatted Spring Boot log files to extract exception information
- **Exception Detection**: Identifies various types of Java exceptions including NullPointerException, SQLException, IOException, and Spring-specific exceptions
- **Stack Trace Analysis**: Extracts complete stack traces with file names, line numbers, and method information
- **Intelligent Code Fixing**: Uses LLM capabilities to generate contextual Java code fixes
- **Multi-Agent Orchestration**: Employs LangGraph for coordinated workflow between specialized agents
- **Comprehensive Reporting**: Generates detailed analysis reports with code suggestions and prevention tips

### Supported Exception Types

- `java.lang.NullPointerException`
- `java.sql.SQLException` and related database exceptions
- `java.io.IOException` and file system exceptions
- `org.springframework.dao.DataAccessResourceFailureException`
- `java.lang.IllegalArgumentException`
- `java.lang.IllegalStateException`
- Custom application exceptions

## Architecture

The application follows a **Supervisor Architecture** pattern using LangGraph, consisting of three main components:

### 1. Log Analysis Agent (`log_analysis_agent.py`)

The Log Analysis Agent is responsible for reading and parsing Spring Boot log files to extract exception information. It implements sophisticated pattern matching to identify exception lines, parse stack traces, and extract contextual information.

**Key Features:**
- Support for multiple log formats (Spring Boot standard, alternative formats)
- Regex-based exception detection and parsing
- Stack trace extraction with file and line number information
- Surrounding context capture for better analysis

**Core Methods:**
- `analyze_log_file(file_path)`: Main analysis method
- `parse_log_line(line)`: Parses individual log lines
- `is_exception_line(message)`: Detects exception indicators
- `extract_exception_details(lines, start_index)`: Extracts complete exception information

### 2. Code Fixing Agent (`code_fixing_agent.py`)

The Code Fixing Agent analyzes extracted exception information and generates intelligent code fixes using LLM capabilities. It understands Spring Boot context and provides production-ready code suggestions.

**Key Features:**
- LLM-powered exception analysis
- Spring Boot-aware code generation
- Confidence scoring for fix suggestions
- Prevention tips and best practices
- Multiple fix suggestions per exception

**Core Methods:**
- `analyze_exception(exception_info)`: Analyzes single exception
- `analyze_multiple_exceptions(exceptions)`: Batch analysis
- `format_fix_report(fix)`: Generates readable reports

### 3. Multi-Agent Orchestrator (`multi_agent_orchestrator.py`)

The Multi-Agent Orchestrator uses LangGraph to coordinate the workflow between the Log Analysis Agent and Code Fixing Agent. It implements a state machine that manages the complete analysis pipeline.

**Workflow States:**
1. **Start**: Initialize workflow with log file path
2. **Log Analysis**: Extract exceptions from log file
3. **Code Fixing**: Generate fixes for extracted exceptions
4. **Report Generation**: Create comprehensive analysis report
5. **Complete**: Finalize workflow and return results

## Installation

### Prerequisites

- Python 3.11 or higher
- OpenAI API key (for LLM functionality)
- Internet connection for package installation

### Step 1: Clone or Download

```bash
# If using git
git clone <repository-url>
cd spring-log-analyzer

# Or download and extract the files to a directory
```

### Step 2: Install Dependencies

```bash
pip install langchain langgraph langchain-openai python-dotenv
```

### Step 3: Environment Setup

Create a `.env` file in the project directory:

```bash
# .env file
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1
```

Alternatively, set environment variables:

```bash
export OPENAI_API_KEY="your_openai_api_key_here"
export OPENAI_API_BASE="https://api.openai.com/v1"
```

## Quick Start

### Basic Usage

```python
from multi_agent_orchestrator import SpringBootLogAnalyzer

# Initialize the analyzer
analyzer = SpringBootLogAnalyzer()

# Analyze a log file
result = analyzer.analyze_log_file('path/to/your/spring-boot.log')

# Check results
if result['success']:
    print(f"Found {result['total_exceptions']} exceptions")
    print(f"Generated {result['total_fixes']} code fixes")
    
    # Access detailed results
    exceptions = result['exceptions']
    fixes = result['fixes']
    messages = result['messages']
else:
    print(f"Analysis failed: {result['error']}")
```

### Command Line Usage

```python
# Simple analysis script
python3 -c "
from multi_agent_orchestrator import SpringBootLogAnalyzer
analyzer = SpringBootLogAnalyzer()
result = analyzer.analyze_log_file('sample_spring_boot.log')
print(f'Success: {result[\"success\"]}')
print(f'Exceptions: {result[\"total_exceptions\"]}')
print(f'Fixes: {result[\"total_fixes\"]}')
"
```

## Usage Examples

### Example 1: Analyzing a NullPointerException

**Input Log:**
```
2024-07-23 10:17:12.456 ERROR 12345 --- [http-nio-8080-exec-2] c.e.controller.UserController : Error processing user request
java.lang.NullPointerException: Cannot invoke "String.length()" because "username" is null
	at com.example.service.UserService.validateUser(UserService.java:45)
	at com.example.controller.UserController.createUser(UserController.java:28)
```

**Generated Fix:**
```java
// Original problematic code
public void validateUser(String username) {
    if (username.length() < 3) {  // NullPointerException here
        throw new IllegalArgumentException("Username too short");
    }
}

// Fixed code
public void validateUser(String username) {
    if (username == null || username.trim().isEmpty()) {
        throw new IllegalArgumentException("Username cannot be null or empty");
    }
    if (username.length() < 3) {
        throw new IllegalArgumentException("Username too short");
    }
}
```

### Example 2: Database Connection Issues

**Input Log:**
```
2024-07-23 10:18:30.890 ERROR 12345 --- [http-nio-8080-exec-3] c.e.service.ProductService : Database connection failed
org.springframework.dao.DataAccessResourceFailureException: Failed to obtain JDBC Connection; nested exception is java.sql.SQLException: Connection refused
```

**Generated Fix:**
```java
// Add connection retry logic and proper error handling
@Retryable(value = {DataAccessResourceFailureException.class}, maxAttempts = 3)
public Product getProduct(Long id) {
    try {
        return productRepository.findById(id);
    } catch (DataAccessResourceFailureException e) {
        log.error("Database connection failed for product ID: {}", id, e);
        throw new ServiceUnavailableException("Database temporarily unavailable");
    }
}
```

### Example 3: Batch Processing Multiple Log Files

```python
import os
from multi_agent_orchestrator import SpringBootLogAnalyzer

def analyze_multiple_logs(log_directory):
    analyzer = SpringBootLogAnalyzer()
    results = []
    
    for filename in os.listdir(log_directory):
        if filename.endswith('.log'):
            log_path = os.path.join(log_directory, filename)
            result = analyzer.analyze_log_file(log_path)
            results.append({
                'file': filename,
                'success': result['success'],
                'exceptions': result['total_exceptions'],
                'fixes': result['total_fixes']
            })
    
    return results

# Usage
results = analyze_multiple_logs('/path/to/logs/')
for result in results:
    print(f"{result['file']}: {result['exceptions']} exceptions, {result['fixes']} fixes")
```

## API Reference

### SpringBootLogAnalyzer Class

#### `__init__()`
Initializes the multi-agent analyzer with default configuration.

#### `analyze_log_file(log_file_path: str) -> Dict[str, Any]`
Analyzes a Spring Boot log file using the complete multi-agent workflow.

**Parameters:**
- `log_file_path` (str): Path to the log file to analyze

**Returns:**
- Dictionary containing analysis results:
  ```python
  {
      "success": bool,
      "error": str,
      "log_file_path": str,
      "total_exceptions": int,
      "total_fixes": int,
      "exceptions": List[Dict],
      "fixes": List[Dict],
      "messages": List[Dict],
      "workflow_complete": bool
  }
  ```

### LogAnalysisAgent Class

#### `analyze_log_file(file_path: str) -> List[ExceptionInfo]`
Analyzes a log file and returns extracted exception information.

#### `analyze_logs(log_file_path: str) -> Dict[str, Any]`
Tool interface for log analysis (LangChain compatible).

### CodeFixingAgent Class

#### `analyze_exception(exception_info: ExceptionInfo) -> CodeFix`
Analyzes a single exception and generates code fixes.

#### `analyze_multiple_exceptions(exceptions: List[ExceptionInfo]) -> List[CodeFix]`
Analyzes multiple exceptions in batch.

#### `fix_exceptions(exceptions_data: List[Dict[str, Any]]) -> Dict[str, Any]`
Tool interface for code fixing (LangChain compatible).

### Data Classes

#### ExceptionInfo
```python
@dataclass
class ExceptionInfo:
    timestamp: str
    log_level: str
    exception_type: str
    exception_message: str
    stack_trace: List[str]
    surrounding_context: List[str]
    file_path: str
    line_number: Optional[int]
    method_name: Optional[str]
    class_name: Optional[str]
```

#### CodeFix
```python
@dataclass
class CodeFix:
    exception_type: str
    exception_message: str
    root_cause: str
    fix_description: str
    code_suggestions: List[Dict[str, str]]
    prevention_tips: List[str]
    confidence_score: float
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key for LLM access | None | Yes |
| `OPENAI_API_BASE` | OpenAI API base URL | https://api.openai.com/v1 | No |

### Model Configuration

The application uses `gpt-4.1-mini` by default. To change the model, modify the initialization in the agent classes:

```python
# In code_fixing_agent.py and multi_agent_orchestrator.py
self.llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.1)
```

### Log Format Support

The application supports multiple log formats:

1. **Spring Boot Standard Format:**
   ```
   2024-07-23 10:15:30.123  INFO 12345 --- [main] com.example.Application : Message
   ```

2. **Alternative Format:**
   ```
   2024-07-23 10:15:30 INFO Message
   ```

3. **Simple Format:**
   ```
   2024-07-23 10:15:30 Message
   ```

## Testing

### Running Tests

The application includes a comprehensive test suite:

```bash
# Run all tests
python3 test_application.py

# Run specific test components
python3 -c "
from test_application import TestLogAnalysisAgent
import unittest
suite = unittest.TestLoader().loadTestsFromTestCase(TestLogAnalysisAgent)
unittest.TextTestRunner(verbosity=2).run(suite)
"
```

### Test Coverage

The test suite covers:

- Log file reading and parsing
- Exception detection and extraction
- Code fix generation
- Multi-agent workflow orchestration
- Error handling and edge cases
- Performance testing

### Sample Test Results

```
============================================================
SPRING BOOT LOG ANALYZER - COMPREHENSIVE TEST SUITE
============================================================

1. Running Unit Tests...
------------------------------
test_log_file_reading ... ok
test_log_line_parsing ... ok
test_exception_detection ... ok
test_full_log_analysis ... ok
test_single_exception_analysis ... ok
test_multiple_exceptions_analysis ... ok
test_complete_workflow ... ok
test_report_generation ... ok

Total tests run: 12
Failures: 0
Errors: 0
Success rate: 100.0%

✅ ALL TESTS PASSED! The application is working correctly.
```

## Troubleshooting

### Common Issues

#### 1. ModuleNotFoundError: No module named 'langchain_openai'

**Solution:**
```bash
pip install langchain-openai
```

#### 2. OpenAI API Key Not Found

**Error:** `Error code: 401 - {'error': 'Unauthorized'}`

**Solution:**
- Ensure your OpenAI API key is set in the environment
- Verify the API key is valid and has sufficient credits
- Check that the `.env` file is in the correct directory

#### 3. Model Not Supported

**Error:** `Error code: 400 - {'error': 'Unsupported model'}`

**Solution:**
- Use a supported model like `gpt-4.1-mini`
- Check the latest supported models in your OpenAI account

#### 4. Log File Not Found

**Error:** `Log file not found: path/to/file.log`

**Solution:**
- Verify the file path is correct
- Ensure the file exists and is readable
- Use absolute paths when possible

#### 5. No Exceptions Found

**Issue:** Analysis completes but finds 0 exceptions

**Solution:**
- Check that the log file contains actual exception stack traces
- Verify the log format is supported
- Ensure exception lines contain keywords like "Exception", "Error", or "Caused by"

### Performance Considerations

- **Large Log Files:** For files > 100MB, consider splitting them into smaller chunks
- **API Rate Limits:** The application respects OpenAI rate limits but may need delays for large batches
- **Memory Usage:** Each exception analysis requires LLM calls, so memory usage scales with exception count

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run analysis with debug output
analyzer = SpringBootLogAnalyzer()
result = analyzer.analyze_log_file('your-log-file.log')
```

## Contributing

### Development Setup

1. Fork the repository
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all function parameters and return values
- Include docstrings for all classes and methods
- Maintain test coverage above 90%

### Submitting Changes

1. Create a feature branch
2. Make your changes with appropriate tests
3. Run the test suite to ensure all tests pass
4. Submit a pull request with a clear description

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For support, questions, or feature requests:

1. Check the troubleshooting section above
2. Review existing issues in the repository
3. Create a new issue with detailed information about your problem
4. Include log files, error messages, and system information

---

**Manus AI** - Advancing AI-powered development tools for modern applications.

