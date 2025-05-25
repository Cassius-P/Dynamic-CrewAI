"""Tests for the ToolRegistry class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.core.tool_registry import ToolRegistry


class TestToolRegistry:
    """Test cases for the ToolRegistry class."""

    def test_init(self):
        """Test ToolRegistry initialization."""
        registry = ToolRegistry()
        assert registry is not None
        assert hasattr(registry, '_tools')
        assert isinstance(registry._tools, dict)

    def test_get_available_tools(self):
        """Test getting list of available tools."""
        registry = ToolRegistry()
        tools = registry.get_available_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check that all expected categories are present
        categories = {tool['category'] for tool in tools}
        expected_categories = {'filesystem', 'web', 'search', 'development', 'utility'}
        assert expected_categories.issubset(categories)
        
        # Check structure of tool entries
        for tool in tools:
            assert 'name' in tool
            assert 'description' in tool
            assert 'category' in tool
            assert 'class_name' in tool

    def test_get_tool_by_name_valid(self):
        """Test getting a tool by valid name."""
        registry = ToolRegistry()
        
        # Test with FileReadTool
        tool_info = registry.get_tool_by_name('file_read_tool')
        assert tool_info is not None
        assert tool_info['name'] == 'file_read_tool'
        assert tool_info['category'] == 'filesystem'
        assert 'FileReadTool' in tool_info['class_name']

    def test_get_tool_by_name_invalid(self):
        """Test getting a tool by invalid name."""
        registry = ToolRegistry()
        
        tool_info = registry.get_tool_by_name('nonexistent_tool')
        assert tool_info is None

    def test_get_tools_by_category(self):
        """Test getting tools by category."""
        registry = ToolRegistry()
        
        # Test filesystem tools
        filesystem_tools = registry.get_tools_by_category('filesystem')
        assert isinstance(filesystem_tools, list)
        assert len(filesystem_tools) > 0
        
        for tool in filesystem_tools:
            assert tool['category'] == 'filesystem'
        
        # Test invalid category
        invalid_tools = registry.get_tools_by_category('invalid_category')
        assert isinstance(invalid_tools, list)
        assert len(invalid_tools) == 0

    @patch('app.core.tool_registry.FileReadTool')
    def test_create_tool_file_read(self, mock_file_read):
        """Test creating FileReadTool instance."""
        registry = ToolRegistry()
        
        # Mock the tool class
        mock_instance = Mock()
        mock_file_read.return_value = mock_instance
        
        # Create tool
        tool = registry.create_tool('file_read_tool')
        
        assert tool == mock_instance
        mock_file_read.assert_called_once()

    @patch('app.core.tool_registry.FileWriteTool')
    def test_create_tool_file_write(self, mock_file_write):
        """Test creating FileWriteTool instance."""
        registry = ToolRegistry()
        
        mock_instance = Mock()
        mock_file_write.return_value = mock_instance
        
        tool = registry.create_tool('file_write_tool')
        
        assert tool == mock_instance
        mock_file_write.assert_called_once()

    @patch('app.core.tool_registry.DirectoryReadTool')
    def test_create_tool_directory_read(self, mock_dir_read):
        """Test creating DirectoryReadTool instance."""
        registry = ToolRegistry()
        
        mock_instance = Mock()
        mock_dir_read.return_value = mock_instance
        
        tool = registry.create_tool('directory_read_tool')
        
        assert tool == mock_instance
        mock_dir_read.assert_called_once()

    @patch('app.core.tool_registry.SerperDevTool')
    def test_create_tool_serper_search(self, mock_serper):
        """Test creating SerperDevTool instance."""
        registry = ToolRegistry()
        
        mock_instance = Mock()
        mock_serper.return_value = mock_instance
        
        tool = registry.create_tool('serper_search_tool')
        
        assert tool == mock_instance
        mock_serper.assert_called_once()

    @patch('app.core.tool_registry.WebsiteSearchTool')
    def test_create_tool_website_search(self, mock_website_search):
        """Test creating WebsiteSearchTool instance."""
        registry = ToolRegistry()
        
        mock_instance = Mock()
        mock_website_search.return_value = mock_instance
        
        tool = registry.create_tool('website_search_tool')
        
        assert tool == mock_instance
        mock_website_search.assert_called_once()

    @patch('app.core.tool_registry.ScrapeWebsiteTool')
    def test_create_tool_scrape_website(self, mock_scrape):
        """Test creating ScrapeWebsiteTool instance."""
        registry = ToolRegistry()
        
        mock_instance = Mock()
        mock_scrape.return_value = mock_instance
        
        tool = registry.create_tool('scrape_website_tool')
        
        assert tool == mock_instance
        mock_scrape.assert_called_once()

    def test_create_tool_invalid(self):
        """Test creating tool with invalid name."""
        registry = ToolRegistry()
        
        tool = registry.create_tool('nonexistent_tool')
        assert tool is None

    @patch('app.core.tool_registry.FileReadTool')
    @patch('app.core.tool_registry.FileWriteTool')
    def test_create_tools_multiple(self, mock_file_write, mock_file_read):
        """Test creating multiple tools."""
        registry = ToolRegistry()
        
        # Mock instances
        mock_read_instance = Mock()
        mock_write_instance = Mock()
        mock_file_read.return_value = mock_read_instance
        mock_file_write.return_value = mock_write_instance
        
        # Create multiple tools
        tools = registry.create_tools(['file_read_tool', 'file_write_tool'])
        
        assert isinstance(tools, list)
        assert len(tools) == 2
        assert mock_read_instance in tools
        assert mock_write_instance in tools
        
        mock_file_read.assert_called_once()
        mock_file_write.assert_called_once()

    def test_create_tools_with_invalid(self):
        """Test creating tools with some invalid names."""
        registry = ToolRegistry()
        
        tools = registry.create_tools(['file_read_tool', 'invalid_tool'])
        
        assert isinstance(tools, list)
        assert len(tools) == 1  # Only valid tool should be created

    def test_create_tools_empty_list(self):
        """Test creating tools with empty list."""
        registry = ToolRegistry()
        
        tools = registry.create_tools([])
        
        assert isinstance(tools, list)
        assert len(tools) == 0

    @patch('app.core.tool_registry.FileReadTool')
    def test_create_tool_with_exception(self, mock_file_read):
        """Test tool creation when exception occurs."""
        registry = ToolRegistry()
        
        # Make the tool class raise an exception
        mock_file_read.side_effect = Exception("Tool creation failed")
        
        tool = registry.create_tool('file_read_tool')
        assert tool is None

    def test_tool_categories_coverage(self):
        """Test that all major tool categories are covered."""
        registry = ToolRegistry()
        tools = registry.get_available_tools()
        
        categories = {tool['category'] for tool in tools}
        
        # Ensure we have tools in major categories
        assert 'filesystem' in categories
        assert 'web' in categories
        assert 'search' in categories
        
        # Ensure we have a good number of tools
        assert len(tools) >= 10

    def test_tool_names_uniqueness(self):
        """Test that all tool names are unique."""
        registry = ToolRegistry()
        tools = registry.get_available_tools()
        
        names = [tool['name'] for tool in tools]
        assert len(names) == len(set(names)), "Tool names should be unique"

    def test_tool_info_completeness(self):
        """Test that all tool information is complete."""
        registry = ToolRegistry()
        tools = registry.get_available_tools()
        
        for tool in tools:
            assert tool['name'], f"Tool {tool} missing name"
            assert tool['description'], f"Tool {tool} missing description"
            assert tool['category'], f"Tool {tool} missing category"
            assert tool['class_name'], f"Tool {tool} missing class_name"
            
            # Check that description is meaningful
            assert len(tool['description']) > 10, f"Tool {tool['name']} has too short description"
