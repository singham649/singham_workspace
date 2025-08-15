# Research Findings: LangGraph Multi-Agent Systems for Log Analysis and Code Fixing

## Overview of Multi-Agent Systems

An agent is a system that uses an LLM to decide the control flow of an application. Multi-agent systems become necessary when:
- Agent has too many tools and makes poor decisions
- Context grows too complex for a single agent
- Need for multiple specialization areas (planner, researcher, expert, etc.)

## Primary Benefits of Multi-Agent Systems

1. **Modularity**: Separate agents make it easier to develop, test, and maintain agentic systems
2. **Specialization**: Expert agents focused on specific domains improve overall system performance
3. **Control**: Explicit control over agent communication (vs relying on function calling)

## Multi-Agent Architectures

### 1. Network Architecture
- Each agent can communicate with every other agent (many-to-many)
- Any agent can decide which other agent to call next
- Good for problems without clear hierarchy or specific sequence

### 2. Supervisor Architecture
- Each agent communicates with a single supervisor agent
- Supervisor makes decisions on which agent should be called next
- Lends itself well to running multiple agents in parallel or map-reduce patterns

### 3. Supervisor (Tool-calling)
- Special case of supervisor architecture
- Individual agents represented as tools
- Supervisor uses tool-calling LLM to decide which agent tools to call

### 4. Hierarchical
- Multi-agent system with supervisor of supervisors
- Generalization of supervisor architecture
- Allows for more complex control flows

### 5. Custom Multi-agent Workflow
- Each agent communicates with only a subset of agents
- Parts of the flow are deterministic
- Only some agents can decide which other agents to call next

## Handoffs in Multi-Agent Systems

Handoffs allow one agent to hand off control to another, specifying:
- **Destination**: Target agent to navigate to
- **Payload**: Information to pass to that agent

Implementation uses `Command` object:
```python
def agent(state) -> Command[Literal["agent", "another_agent"]]:
    goto = get_next_agent(...)
    return Command(
        goto=goto,
        update={"my_state_key": "my_state_value"}
    )
```

## Communication and State Management

Key considerations:
- Message passing between agents
- Sharing full thought process vs only final results
- Indicating agent name in messages
- Representing handoffs in message history
- State management for subagents
- Using different state schemas

## Relevance to Log Analysis and Code Fixing Application

For our Spring Boot log analysis and code fixing application, the **Supervisor Architecture** appears most suitable because:

1. **Clear Specialization**: We have two distinct specialized agents:
   - Log Analysis Agent: Reads SLF4J logs and extracts exceptions
   - Code Fixing Agent: Analyzes exceptions and generates Java code fixes

2. **Sequential Workflow**: The process is naturally sequential:
   - Log analysis must happen first
   - Code fixing depends on the output of log analysis
   - Supervisor can orchestrate this flow

3. **Control and Coordination**: A supervisor can:
   - Manage the workflow between the two agents
   - Handle error cases and retries
   - Coordinate state sharing between agents
   - Provide feedback to users about progress

4. **Modularity**: Each agent can be developed and tested independently while the supervisor handles integration.



## Log Analysis and Exception Handling

### SLF4J and Spring Boot Logging
- SLF4J (Simple Logging Facade for Java) is an abstraction layer for various logging frameworks (e.g., Logback, Log4j).
- Spring Boot uses SLF4J with Logback by default.
- Logs can be configured to write to files in addition to the console.
- Structured logging (e.g., JSON format) is supported in Spring Boot and would greatly simplify parsing.

### Log Parsing in Python
- Python is well-suited for parsing log files.
- The approach will involve reading log files line by line or in chunks.
- Identifying exceptions will require pattern matching for keywords like 'Exception', 'Error', 'Caused by:', and extracting the stack trace.

### Java Exception Analysis and Code Fixing
- Automated exception handling and analysis tools exist in the Java ecosystem.
- The code fixing agent will need to:
    - Understand the context of the exception (e.g., class, method, line number).
    - Analyze the stack trace to pinpoint the root cause.
    - Leverage an LLM to suggest relevant Java code fixes.
    - Consider Spring Boot specific contexts for more accurate fixes.

## Proposed Agentic Application Architecture

Based on the research, a **Supervisor Architecture** using LangGraph is proposed for this application:

1.  **Supervisor Agent (LangGraph Orchestrator)**:
    -   **Role**: Manages the overall workflow, orchestrates the Log Analysis Agent and Code Fixing Agent.
    -   **Inputs**: Triggers (e.g., new log file detected, scheduled run).
    -   **Outputs**: Orchestrates agents, provides progress updates, presents final code fixes.
    -   **Logic**: Decides when to activate the Log Analysis Agent, passes its output to the Code Fixing Agent, and handles the overall flow.

2.  **Log Analysis Agent**:
    -   **Role**: Reads and parses Spring Boot log files to identify and extract exception details.
    -   **Inputs**: Path to log file(s).
    -   **Outputs**: Structured data containing exception type, message, full stack trace, and potentially surrounding log context.
    -   **Tools/Capabilities**: File I/O, regular expressions for pattern matching, potential use of a dedicated log parsing library if available and suitable.

3.  **Code Fixing Agent**:
    -   **Role**: Analyzes the extracted exception details and generates potential Java code fixes.
    -   **Inputs**: Structured exception data from the Log Analysis Agent.
    -   **Outputs**: Proposed Java code snippets for fixing the exception, explanations of the fix, and potentially the relevant file/line number.
    -   **Tools/Capabilities**: Large Language Model (LLM) for code generation and reasoning, potentially a code analysis tool for context (though this might be an advanced feature for later).

### Integration Plan

-   **Data Flow**: The Log Analysis Agent will output a structured representation of exceptions. This structured data will be the input for the Code Fixing Agent.
-   **Orchestration**: LangGraph will define the state machine, allowing the Supervisor Agent to transition between the Log Analysis and Code Fixing phases. Handoffs will be used to pass data and control between agents.
-   **Error Handling**: The Supervisor Agent will be responsible for handling errors at each stage, such as unparseable logs or unfixable exceptions, and reporting them appropriately.

This architecture provides modularity, clear separation of concerns, and leverages LangGraph's orchestration capabilities for a robust multi-agent system.

