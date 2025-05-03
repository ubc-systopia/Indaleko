"""
Base agent interface for data generation agents.

This module provides the foundation for all domain-specific agents
that generate metadata for the Indaleko system.
"""

import json
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from ..core.llm import LLMProvider
from ..core.tools import ToolRegistry


class Agent(ABC):
    """Base class for all agents."""
    
    def __init__(self, llm_provider: LLMProvider, tool_registry: ToolRegistry, config: Optional[Dict[str, Any]] = None):
        """Initialize the agent.
        
        Args:
            llm_provider: LLM provider instance
            tool_registry: Tool registry instance
            config: Optional agent configuration
        """
        self.llm = llm_provider
        self.tools = tool_registry
        self.config = config or {}
        self.state: Dict[str, Any] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.agent_id = str(uuid.uuid4())
        
        # Truth records tracking
        self.truth_list: List[str] = []
    
    def initialize(self) -> bool:
        """Initialize the agent.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        self.logger.info(f"Initializing agent: {self.__class__.__name__}")
        return True
    
    def run(self, instruction: str, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run the agent with the given instruction and input data.
        
        Args:
            instruction: The instruction for the agent
            input_data: Optional input data
            
        Returns:
            Agent execution result
        """
        context = self._build_context(instruction, input_data)
        self.logger.debug(f"Running agent with context: {context[:100]}...")
        
        response = self.llm.generate(context, tools=self.tools.get_tool_schemas())
        result = self._process_response(response)
        
        return result
    
    def _build_context(self, instruction: str, input_data: Optional[Dict[str, Any]]) -> str:
        """Build the context for the LLM.
        
        Args:
            instruction: The instruction for the agent
            input_data: Optional input data
            
        Returns:
            Context string for the LLM
        """
        context = f"Instruction: {instruction}\n\n"
        
        if input_data:
            context += f"Input data: {json.dumps(input_data, indent=2)}\n\n"
        
        # Add agent state if available
        if self.state:
            context += f"Current state: {json.dumps(self.state, indent=2)}\n\n"
        
        return context
    
    def _process_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process the response from the LLM.
        
        Args:
            response: LLM response
            
        Returns:
            Processed response
        """
        result = {
            "content": response.get("content", ""),
            "actions": []
        }
        
        # Process tool calls
        tool_calls = response.get("tool_calls", [])
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name")
            if not tool_name:
                continue
                
            arguments_str = tool_call.get("function", {}).get("arguments", "{}")
            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                self.logger.error(f"Invalid tool call arguments: {arguments_str}")
                continue
                
            self.logger.debug(f"Executing tool: {tool_name}")
            try:
                tool_result = self.tools.execute_tool(tool_name, arguments)
                
                result["actions"].append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": tool_result
                })
            except Exception as e:
                self.logger.error(f"Error executing tool {tool_name}: {str(e)}")
                result["actions"].append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "error": str(e)
                })
        
        return result
    
    @abstractmethod
    def generate(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate metadata records.
        
        Args:
            count: Number of records to generate
            criteria: Optional criteria for generation
            
        Returns:
            List of generated records
        """
        pass
    
    @abstractmethod
    def generate_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate truth records that match specific criteria.
        
        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy
            
        Returns:
            List of generated truth records
        """
        pass


class DomainAgent(Agent):
    """Base class for domain-specific agents."""
    
    def __init__(self, llm_provider: LLMProvider, tool_registry: ToolRegistry, config: Optional[Dict[str, Any]] = None):
        """Initialize the domain agent.
        
        Args:
            llm_provider: LLM provider instance
            tool_registry: Tool registry instance
            config: Optional agent configuration
        """
        super().__init__(llm_provider, tool_registry, config)
        self.collection_name = ""  # Should be set by subclasses
    
    def _get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for the agent's collection.
        
        Returns:
            Collection statistics
        """
        if not self.collection_name:
            return {}
            
        tool = self.tools.get_tool("database_query")
        if not tool:
            self.logger.warning("Database query tool not available")
            return {}
            
        try:
            result = tool.execute({
                "query": f"RETURN {{ count: COUNT(FOR doc IN {self.collection_name} RETURN 1) }}"
            })
            
            if result and len(result) > 0:
                return result[0]
            
            return {"count": 0}
        except Exception as e:
            self.logger.error(f"Error getting collection stats: {str(e)}")
            return {"count": 0, "error": str(e)}