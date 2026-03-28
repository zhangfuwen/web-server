"""
Tests for Schema validation module.
"""

import pytest
from schema import (
    validate_task, validate_url, get_validation_error_response,
    TASK_SCHEMA, TASK_CREATE_SCHEMA, TASK_UPDATE_SCHEMA, BULK_TASKS_SCHEMA, URL_EXTRACT_SCHEMA
)


class TestSchemaValidationValid:
    """Test validation of valid data."""
    
    def test_valid_task_create(self, sample_task_create):
        """Test validating a valid task creation request."""
        is_valid, error = validate_task(sample_task_create, schema_type="create")
        assert is_valid is True
        assert error is None
    
    def test_valid_task_full(self, sample_task):
        """Test validating a valid full task."""
        is_valid, error = validate_task(sample_task, schema_type="full")
        assert is_valid is True
        assert error is None
    
    def test_valid_task_update(self):
        """Test validating a valid task update."""
        update_data = {
            "id": "test-123",
            "content": "Updated content",
            "done": True
        }
        is_valid, error = validate_task(update_data, schema_type="update")
        assert is_valid is True
        assert error is None
    
    def test_valid_bulk_tasks(self, sample_bulk_tasks):
        """Test validating valid bulk tasks."""
        is_valid, error = validate_task(sample_bulk_tasks, schema_type="bulk")
        assert is_valid is True
        assert error is None
    
    def test_valid_url(self, valid_url_data):
        """Test validating a valid URL."""
        is_valid, error = validate_url(valid_url_data)
        assert is_valid is True
        assert error is None
    
    def test_valid_task_with_all_optional_fields(self):
        """Test validating task with all optional fields."""
        task = {
            "content": "Complete task",
            "category": "Projects",
            "priority": "high",
            "due_date": "2024-12-31",
            "comments": [{"id": "c1", "text": "Comment"}]
        }
        is_valid, error = validate_task(task, schema_type="create")
        assert is_valid is True
    
    def test_valid_task_different_categories(self):
        """Test validating tasks with different valid categories."""
        categories = ["Projects", "Next Actions", "Waiting For", "Someday/Maybe",
                     "projects", "next_actions", "waiting_for", "someday_maybe"]
        
        for category in categories:
            task = {"content": "Test", "category": category}
            is_valid, error = validate_task(task, schema_type="create")
            assert is_valid is True, f"Category {category} should be valid"
    
    def test_valid_task_priorities(self):
        """Test validating tasks with different valid priorities."""
        priorities = ["high", "medium", "low"]
        
        for priority in priorities:
            task = {"content": "Test", "priority": priority}
            is_valid, error = validate_task(task, schema_type="create")
            assert is_valid is True, f"Priority {priority} should be valid"


class TestSchemaValidationInvalid:
    """Test validation of invalid data."""
    
    def test_invalid_task_missing_content(self):
        """Test that task without content is rejected."""
        task = {"category": "Projects"}
        is_valid, error = validate_task(task, schema_type="create")
        assert is_valid is False
        assert error is not None
    
    def test_invalid_task_empty_content(self):
        """Test that task with empty content is rejected."""
        task = {"content": "", "category": "Projects"}
        is_valid, error = validate_task(task, schema_type="create")
        assert is_valid is False
    
    def test_invalid_task_content_too_long(self):
        """Test that task with content > 500 chars is rejected."""
        task = {"content": "x" * 501, "category": "Projects"}
        is_valid, error = validate_task(task, schema_type="create")
        assert is_valid is False
    
    def test_invalid_task_category(self):
        """Test that task with invalid category is rejected."""
        task = {"content": "Test", "category": "Invalid Category"}
        is_valid, error = validate_task(task, schema_type="create")
        assert is_valid is False
    
    def test_invalid_task_priority(self):
        """Test that task with invalid priority is rejected."""
        task = {"content": "Test", "priority": "urgent"}
        is_valid, error = validate_task(task, schema_type="create")
        assert is_valid is False
    
    def test_invalid_task_done_type(self):
        """Test that task with non-boolean done is rejected."""
        task = {"id": "1", "content": "Test", "category": "Projects", "done": "yes"}
        is_valid, error = validate_task(task, schema_type="full")
        assert is_valid is False
    
    def test_invalid_bulk_tasks_missing_category(self):
        """Test that bulk tasks missing a category is rejected."""
        bulk = {
            "projects": [],
            "next_actions": [],
            "waiting_for": []
            # Missing someday_maybe
        }
        is_valid, error = validate_task(bulk, schema_type="bulk")
        assert is_valid is False
    
    def test_invalid_url_missing_url(self):
        """Test that URL validation fails without url field."""
        data = {}
        is_valid, error = validate_url(data)
        assert is_valid is False
    
    def test_invalid_url_not_a_url(self, invalid_url_data):
        """Test that invalid URL format is rejected."""
        print(f"Invalid URL data: {invalid_url_data}")
        is_valid, error = validate_url(invalid_url_data)
        assert is_valid is False
    
    def test_invalid_task_additional_properties(self):
        """Test that task with additional properties is rejected."""
        task = {
            "content": "Test",
            "category": "Projects",
            "invalid_field": "should not be here"
        }
        is_valid, error = validate_task(task, schema_type="create")
        assert is_valid is False


class TestSchemaEdgeCases:
    """Test edge cases in schema validation."""
    
    def test_task_content_exactly_500_chars(self):
        """Test task with content exactly 500 characters."""
        task = {"content": "x" * 500, "category": "Projects"}
        is_valid, error = validate_task(task, schema_type="create")
        assert is_valid is True
    
    def test_task_content_exactly_1_char(self):
        """Test task with content exactly 1 character."""
        task = {"content": "x", "category": "Projects"}
        is_valid, error = validate_task(task, schema_type="create")
        assert is_valid is True
    
    def test_task_with_unicode_content(self):
        """Test task with unicode content."""
        task = {"content": "任务测试 🚀", "category": "Projects"}
        is_valid, error = validate_task(task, schema_type="create")
        assert is_valid is True
    
    def test_task_with_special_characters(self):
        """Test task with special characters."""
        task = {"content": "Test <>&\"' task", "category": "Projects"}
        is_valid, error = validate_task(task, schema_type="create")
        assert is_valid is True
    
    def test_task_with_newlines(self):
        """Test task with newlines in content."""
        task = {"content": "Line 1\nLine 2\nLine 3", "category": "Projects"}
        is_valid, error = validate_task(task, schema_type="create")
        assert is_valid is True
    
    def test_task_with_whitespace_only(self):
        """Test task with whitespace-only content."""
        task = {"content": "   ", "category": "Projects"}
        is_valid, error = validate_task(task, schema_type="create")
        # Whitespace is technically valid (minLength=1 is satisfied)
        assert is_valid is True
    
    def test_task_null_values(self):
        """Test task with null values."""
        task = {"content": None, "category": "Projects"}
        is_valid, error = validate_task(task, schema_type="create")
        assert is_valid is False
    
    def test_bulk_tasks_empty_arrays(self):
        """Test bulk tasks with all empty arrays."""
        bulk = {
            "projects": [],
            "next_actions": [],
            "waiting_for": [],
            "someday_maybe": []
        }
        is_valid, error = validate_task(bulk, schema_type="bulk")
        assert is_valid is True
    
    def test_url_with_query_params(self):
        """Test URL with query parameters."""
        data = {"url": "https://example.com/path?query=value&other=123"}
        is_valid, error = validate_url(data)
        assert is_valid is True
    
    def test_url_with_fragment(self):
        """Test URL with fragment."""
        data = {"url": "https://example.com/page#section"}
        is_valid, error = validate_url(data)
        assert is_valid is True
    
    def test_url_http_protocol(self):
        """Test URL with HTTP protocol."""
        data = {"url": "http://example.com"}
        is_valid, error = validate_url(data)
        assert is_valid is True
    
    def test_url_https_protocol(self):
        """Test URL with HTTPS protocol."""
        data = {"url": "https://example.com"}
        is_valid, error = validate_url(data)
        assert is_valid is True


class TestSchemaValidationErrorResponse:
    """Test validation error response generation."""
    
    def test_error_response_format(self):
        """Test error response has correct format."""
        response = get_validation_error_response("Test error message")
        
        assert response["success"] is False
        assert response["error"] == "Validation failed"
        assert response["message"] == "Test error message"
        assert response["status_code"] == 400
    
    def test_error_response_with_different_messages(self):
        """Test error response with various error messages."""
        messages = [
            "Field required",
            "Value too long",
            "Invalid category",
            "Must be a boolean"
        ]
        
        for msg in messages:
            response = get_validation_error_response(msg)
            assert response["message"] == msg
            assert response["status_code"] == 400


class TestSchemaTypes:
    """Test schema type definitions."""
    
    def test_task_schema_is_dict(self):
        """Test TASK_SCHEMA is a dictionary."""
        assert isinstance(TASK_SCHEMA, dict)
        assert TASK_SCHEMA["type"] == "object"
    
    def test_task_create_schema_is_dict(self):
        """Test TASK_CREATE_SCHEMA is a dictionary."""
        assert isinstance(TASK_CREATE_SCHEMA, dict)
        assert TASK_CREATE_SCHEMA["type"] == "object"
    
    def test_task_update_schema_is_dict(self):
        """Test TASK_UPDATE_SCHEMA is a dictionary."""
        assert isinstance(TASK_UPDATE_SCHEMA, dict)
        assert TASK_UPDATE_SCHEMA["type"] == "object"
    
    def test_bulk_tasks_schema_is_dict(self):
        """Test BULK_TASKS_SCHEMA is a dictionary."""
        assert isinstance(BULK_TASKS_SCHEMA, dict)
        assert BULK_TASKS_SCHEMA["type"] == "object"
    
    def test_url_extract_schema_is_dict(self):
        """Test URL_EXTRACT_SCHEMA is a dictionary."""
        assert isinstance(URL_EXTRACT_SCHEMA, dict)
        assert URL_EXTRACT_SCHEMA["type"] == "object"


class TestSchemaRequiredFields:
    """Test required field validation."""
    
    def test_create_schema_requires_content(self):
        """Test create schema requires content field."""
        assert "content" in TASK_CREATE_SCHEMA["required"]
    
    def test_full_schema_required_fields(self):
        """Test full schema required fields."""
        required = TASK_SCHEMA["required"]
        assert "id" in required
        assert "content" in required
        assert "category" in required
        assert "done" in required
    
    def test_bulk_schema_required_fields(self):
        """Test bulk schema required fields."""
        required = BULK_TASKS_SCHEMA["required"]
        assert "projects" in required
        assert "next_actions" in required
        assert "waiting_for" in required
        assert "someday_maybe" in required
    
    def test_url_schema_required_fields(self):
        """Test URL schema required fields."""
        required = URL_EXTRACT_SCHEMA["required"]
        assert "url" in required
    
    def test_update_schema_no_required_fields(self):
        """Test update schema has no required fields."""
        required = TASK_UPDATE_SCHEMA.get("required", [])
        assert len(required) == 0


class TestSchemaEnumValues:
    """Test enum value validation."""
    
    def test_category_enum_values(self):
        """Test category enum has all expected values."""
        categories = TASK_CREATE_SCHEMA["properties"]["category"]["enum"]
        
        expected = ["Projects", "Next Actions", "Waiting For", "Someday/Maybe",
                   "projects", "next_actions", "waiting_for", "someday_maybe"]
        
        for exp in expected:
            assert exp in categories, f"Missing category: {exp}"
    
    def test_priority_enum_values(self):
        """Test priority enum has all expected values."""
        priorities = TASK_CREATE_SCHEMA["properties"]["priority"]["enum"]
        
        assert "high" in priorities
        assert "medium" in priorities
        assert "low" in priorities
