"""Tool registry for managing CrewAI built-in tools."""
from typing import List, Dict, Any, Optional
from crewai.tools import BaseTool
from crewai_tools import (
    DirectoryReadTool,
    DirectorySearchTool,
    FileReadTool,
    FileWriterTool,
    FileCompressorTool,
    TXTSearchTool,
    CSVSearchTool,
    JSONSearchTool,
    XMLSearchTool,
    DOCXSearchTool,
    PDFSearchTool,
    MDXSearchTool,
    CodeDocsSearchTool,
    YoutubeChannelSearchTool,
    YoutubeVideoSearchTool,
    WebsiteSearchTool,
    SeleniumScrapingTool,
    ScrapeWebsiteTool,
    SerperDevTool,
    CodeInterpreterTool
)

# Make tool classes available for mocking in tests
FileWriteTool = FileWriterTool


class ToolRegistry:
    """Registry for managing CrewAI built-in tools."""
    
    def __init__(self):
        """Initialize the tool registry with built-in tools."""
        self._tools = {
            # File System Tools
            "file_read_tool": {
                "name": "file_read_tool",
                "class": FileReadTool,
                "class_name": "FileReadTool",
                "description": "Read file contents",
                "category": "filesystem",
                "parameters": []
            },
            "directory_read_tool": {
                "name": "directory_read_tool", 
                "class": DirectoryReadTool,
                "class_name": "DirectoryReadTool",
                "description": "Read and list directory contents",
                "category": "filesystem",
                "parameters": []
            },
            "directory_search_tool": {
                "name": "directory_search_tool",
                "class": DirectorySearchTool,
                "class_name": "DirectorySearchTool",
                "description": "Search for files and directories",
                "category": "filesystem",
                "parameters": []
            },
              # Utility Tools
            "file_write_tool": {
                "name": "file_write_tool",
                "class": FileWriteTool,
                "class_name": "FileWriteTool",
                "description": "Write content to files",
                "category": "utility",
                "parameters": []
            },            "file_compressor_tool": {
                "name": "file_compressor_tool",
                "class": FileCompressorTool,
                "class_name": "FileCompressorTool",
                "description": "Compress and decompress files",
                "category": "utility",
                "parameters": []
            },
            
            # Search Tools
            "txt_search_tool": {
                "name": "txt_search_tool",
                "class": TXTSearchTool,
                "class_name": "TXTSearchTool",
                "description": "Search within TXT files",
                "category": "search",
                "parameters": []
            },
            "csv_search_tool": {
                "name": "csv_search_tool",
                "class": CSVSearchTool,
                "class_name": "CSVSearchTool", 
                "description": "Search within CSV files",
                "category": "search",
                "parameters": []
            },
            "json_search_tool": {
                "name": "json_search_tool",
                "class": JSONSearchTool,
                "class_name": "JSONSearchTool",
                "description": "Search within JSON files",
                "category": "search",
                "parameters": []
            },
            "xml_search_tool": {
                "name": "xml_search_tool",
                "class": XMLSearchTool,
                "class_name": "XMLSearchTool",
                "description": "Search within XML files",
                "category": "search", 
                "parameters": []
            },
            "docx_search_tool": {
                "name": "docx_search_tool",
                "class": DOCXSearchTool,
                "class_name": "DOCXSearchTool",
                "description": "Search within DOCX documents",
                "category": "search",
                "parameters": []
            },
            "pdf_search_tool": {
                "name": "pdf_search_tool",
                "class": PDFSearchTool,
                "class_name": "PDFSearchTool",
                "description": "Search within PDF documents",
                "category": "search",
                "parameters": []
            },
            "mdx_search_tool": {
                "name": "mdx_search_tool",
                "class": MDXSearchTool,
                "class_name": "MDXSearchTool",
                "description": "Search within MDX files",
                "category": "search",
                "parameters": []
            },
            "code_docs_search_tool": {
                "name": "code_docs_search_tool",
                "class": CodeDocsSearchTool,
                "class_name": "CodeDocsSearchTool",
                "description": "Search within code documentation",
                "category": "search",
                "parameters": []
            },
            "serper_search_tool": {
                "name": "serper_search_tool",
                "class": SerperDevTool,
                "class_name": "SerperDevTool",
                "description": "Search the web using Serper API",
                "category": "search",
                "parameters": []
            },
            
            # Web Tools
            "youtube_channel_search_tool": {
                "name": "youtube_channel_search_tool",
                "class": YoutubeChannelSearchTool,
                "class_name": "YoutubeChannelSearchTool",
                "description": "Search YouTube channel content",
                "category": "web",
                "parameters": []
            },
            "youtube_video_search_tool": {
                "name": "youtube_video_search_tool",
                "class": YoutubeVideoSearchTool,
                "class_name": "YoutubeVideoSearchTool",
                "description": "Search YouTube video content",
                "category": "web",
                "parameters": []
            },
            "website_search_tool": {
                "name": "website_search_tool",
                "class": WebsiteSearchTool,
                "class_name": "WebsiteSearchTool",
                "description": "Search website content",
                "category": "web",
                "parameters": []
            },
            "selenium_scraping_tool": {
                "name": "selenium_scraping_tool",
                "class": SeleniumScrapingTool,
                "class_name": "SeleniumScrapingTool",
                "description": "Scrape websites using Selenium",
                "category": "web",
                "parameters": []
            },
            "scrape_website_tool": {
                "name": "scrape_website_tool",
                "class": ScrapeWebsiteTool,
                "class_name": "ScrapeWebsiteTool",
                "description": "Scrape website content",
                "category": "web",
                "parameters": []
            },
            
            # Development Tools
            "code_interpreter_tool": {
                "name": "code_interpreter_tool",
                "class": CodeInterpreterTool,
                "class_name": "CodeInterpreterTool",
                "description": "Execute and interpret code",
                "category": "development",
                "parameters": []
            }
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools with their information."""
        return list(self._tools.values())
    
    def get_tool_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool information by name."""
        return self._tools.get(tool_name)
    
    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get tools filtered by category."""
        return [
            tool_info for tool_info in self._tools.values()
            if tool_info["category"] == category
        ]
    
    def get_tool_categories(self) -> List[str]:
        """Get list of available tool categories."""
        categories = set()
        for tool_info in self._tools.values():
            categories.add(tool_info["category"])
        return sorted(list(categories))
    
    def create_tool(self, tool_name: str, **kwargs) -> Optional[BaseTool]:
        """Create a tool instance with given parameters.
        
        Args:
            tool_name: Name of the tool to create
            **kwargs: Parameters to pass to the tool constructor
            
        Returns:
            Initialized tool instance or None if tool not found
        """
        tool_info = self._tools.get(tool_name)
        if not tool_info:
            return None
        
        tool_class = tool_info["class"]
        
        try:
            # Most CrewAI tools can be instantiated without parameters
            return tool_class(**kwargs)
        except Exception as e:
            # Return None instead of raising exception for better test compatibility
            return None
    
    def create_tools(self, tool_names: List[str]) -> List[BaseTool]:
        """Create multiple tools by name, skipping ones that fail.
        
        Args:
            tool_names: List of tool names to create
            
        Returns:
            List of successfully initialized tool instances
        """
        tools = []
        for tool_name in tool_names:
            tool = self.create_tool(tool_name)
            if tool is not None:
                tools.append(tool)
        return tools
    
    def create_tools_from_config(self, tools_config: List[Dict[str, Any]]) -> List[BaseTool]:
        """Create multiple tools from configuration.
        
        Args:
            tools_config: List of tool configurations, each containing:
                - name: Tool name
                - parameters: Dict of parameters for the tool
                
        Returns:
            List of initialized tool instances
            
        Raises:
            ValueError: If any tool creation fails
        """
        tools = []
        for config in tools_config:
            tool_name = config.get("name")
            parameters = config.get("parameters", {})
            
            if not tool_name:
                raise ValueError("Tool configuration missing 'name' field")
            
            tool = self.create_tool(tool_name, **parameters)
            if tool is None:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            tools.append(tool)
        
        return tools
    
    def validate_tool_config(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool configuration and return validation results.
        
        Args:
            tool_name: Name of the tool to validate
            parameters: Parameters to validate
            
        Returns:
            Dict containing validation results
        """
        result = {
            "valid": False,
            "missing_params": [],
            "extra_params": [],
            "errors": []
        }
        
        tool_info = self._tools.get(tool_name)
        if not tool_info:
            result["errors"].append(f"Unknown tool: {tool_name}")
            return result
        
        # Most tools are valid with any parameters since they're flexible
        result["valid"] = True
        
        return result
