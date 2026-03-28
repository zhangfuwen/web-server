#!/usr/bin/env python3
"""
JSON Schema validation for GTD API endpoints.
Prevents data corruption by validating incoming data before processing.
"""

from jsonschema import validate, ValidationError

# GTD Task schema for individual task operations
TASK_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "content": {"type": "string", "minLength": 1, "maxLength": 500},
        "text": {"type": "string", "minLength": 1, "maxLength": 500},
        "category": {"type": "string", "enum": ["Projects", "Next Actions", "Waiting For", "Someday/Maybe", 
                                                "projects", "next_actions", "waiting_for", "someday_maybe"]},
        "done": {"type": "boolean"},
        "completed": {"type": "boolean"},
        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
        "due_date": {"type": "string", "format": "date"},
        "comments": {"type": "array", "items": {"type": "object"}},
        "created_at": {"type": "string", "format": "date-time"},
        "createdAt": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"},
        "updatedAt": {"type": "string", "format": "date-time"}
    },
    "required": ["id", "content", "category", "done"],
    "additionalProperties": False
}

# Schema for task creation (content/text required, id optional)
TASK_CREATE_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {"type": "string", "minLength": 1, "maxLength": 500},
        "text": {"type": "string", "minLength": 1, "maxLength": 500},
        "category": {"type": "string", "enum": ["Projects", "Next Actions", "Waiting For", "Someday/Maybe",
                                                "projects", "next_actions", "waiting_for", "someday_maybe"]},
        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
        "due_date": {"type": "string", "format": "date"},
        "comments": {"type": "array", "items": {"type": "object"}}
    },
    "required": ["content"],
    "additionalProperties": False
}

# Schema for task update (all fields optional)
TASK_UPDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "content": {"type": "string", "minLength": 1, "maxLength": 500},
        "text": {"type": "string", "minLength": 1, "maxLength": 500},
        "category": {"type": "string", "enum": ["Projects", "Next Actions", "Waiting For", "Someday/Maybe",
                                                "projects", "next_actions", "waiting_for", "someday_maybe"]},
        "done": {"type": "boolean"},
        "completed": {"type": "boolean"},
        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
        "due_date": {"type": "string", "format": "date"},
        "comments": {"type": "array", "items": {"type": "object"}}
    },
    "additionalProperties": False
}

# Schema for bulk tasks update (entire task list)
BULK_TASKS_SCHEMA = {
    "type": "object",
    "properties": {
        "projects": {"type": "array", "items": {"type": "object"}},
        "next_actions": {"type": "array", "items": {"type": "object"}},
        "waiting_for": {"type": "array", "items": {"type": "object"}},
        "someday_maybe": {"type": "array", "items": {"type": "object"}}
    },
    "required": ["projects", "next_actions", "waiting_for", "someday_maybe"],
    "additionalProperties": False
}

# Schema for URL title extraction
URL_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "pattern": "^https?://[^\\s]+$"}
    },
    "required": ["url"],
    "additionalProperties": False
}


def validate_task(task_data, schema_type="create"):
    """
    Validate task data against the appropriate schema.
    
    Args:
        task_data: Dictionary containing task data
        schema_type: One of "create", "update", "full", "bulk"
    
    Returns:
        Tuple of (is_valid: bool, error_message: str or None)
    """
    schema_map = {
        "create": TASK_CREATE_SCHEMA,
        "update": TASK_UPDATE_SCHEMA,
        "full": TASK_SCHEMA,
        "bulk": BULK_TASKS_SCHEMA
    }
    
    schema = schema_map.get(schema_type, TASK_CREATE_SCHEMA)
    
    try:
        validate(instance=task_data, schema=schema)
        return True, None
    except ValidationError as e:
        return False, str(e.message)


def validate_url(url_data):
    """
    Validate URL data for title extraction.
    
    Args:
        url_data: Dictionary containing URL
    
    Returns:
        Tuple of (is_valid: bool, error_message: str or None)
    """
    try:
        validate(instance=url_data, schema=URL_EXTRACT_SCHEMA)
        return True, None
    except ValidationError as e:
        return False, str(e.message)


def get_validation_error_response(error_message):
    """
    Generate a standardized error response for validation failures.
    
    Args:
        error_message: The validation error message
    
    Returns:
        Dictionary with error details suitable for JSON response
    """
    return {
        "success": False,
        "error": "Validation failed",
        "message": error_message,
        "status_code": 400
    }
