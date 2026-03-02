# GTD API Input Validation

**Version:** 1.0  
**Created:** 2026-03-02  
**Last Updated:** 2026-03-02

---

## Overview

All GTD API endpoints now validate incoming data using JSON Schema validation. This prevents data corruption and ensures data integrity across the system.

Invalid requests receive a `400 Bad Request` response with detailed error messages.

---

## Validation Rules

### Task Creation (`POST /api/gtd/tasks`)

**Schema:** `TASK_CREATE_SCHEMA`

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `content` | string | **Yes** | 1-500 characters |
| `text` | string | No (alias for content) | 1-500 characters |
| `category` | string | No | Must be one of: `Projects`, `Next Actions`, `Waiting For`, `Someday/Maybe`, `projects`, `next_actions`, `waiting_for`, `someday_maybe` |
| `priority` | string | No | Must be one of: `high`, `medium`, `low` |
| `due_date` | string | No | ISO 8601 date format (YYYY-MM-DD) |
| `comments` | array | No | Array of objects |

**Example Valid Request:**
```json
{
  "content": "Complete quarterly report",
  "category": "Projects",
  "priority": "high",
  "due_date": "2026-03-15"
}
```

**Example Invalid Request:**
```json
{
  "content": "",  // ERROR: content cannot be empty
  "category": "Invalid Category"  // ERROR: not in allowed values
}
```

---

### Task Update (`PUT /api/gtd/tasks/:id`)

**Schema:** `TASK_UPDATE_SCHEMA`

All fields are optional. Only provided fields will be updated.

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `id` | string | No | Task identifier |
| `content` | string | No | 1-500 characters |
| `text` | string | No | 1-500 characters (alias for content) |
| `category` | string | No | See Task Creation |
| `done` | boolean | No | Task completion status |
| `completed` | boolean | No | Alias for done |
| `priority` | string | No | `high`, `medium`, `low` |
| `due_date` | string | No | ISO 8601 date format |
| `comments` | array | No | Array of comment objects |

**Example Valid Request:**
```json
{
  "id": "abc123",
  "done": true
}
```

---

### Bulk Tasks Update (`PUT /api/gtd/tasks`)

**Schema:** `BULK_TASKS_SCHEMA`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `projects` | array | **Yes** | List of project tasks |
| `next_actions` | array | **Yes** | List of next action tasks |
| `waiting_for` | array | **Yes** | List of waiting tasks |
| `someday_maybe` | array | **Yes** | List of someday/maybe tasks |

**Example Valid Request:**
```json
{
  "projects": [
    {"id": "1", "text": "Project A", "completed": false}
  ],
  "next_actions": [],
  "waiting_for": [],
  "someday_maybe": []
}
```

---

### URL Title Extraction (`GET /api/gtd/extract-title?url=...`)

**Schema:** `URL_EXTRACT_SCHEMA`

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `url` | string | **Yes** | Valid URI format |

**Example Valid Request:**
```
GET /api/gtd/extract-title?url=https://example.com/article
```

**Example Invalid Request:**
```
GET /api/gtd/extract-title  // ERROR: URL parameter required
```

---

## Error Responses

All validation errors return HTTP `400 Bad Request` with the following structure:

```json
{
  "success": false,
  "error": "Validation failed",
  "message": "<detailed error description>",
  "status_code": 400
}
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `'' should be non-empty` | Empty string in required field | Provide a non-empty value |
| `'<value>' is not one of [...]` | Invalid enum value | Use one of the allowed values |
| `'<field>' is a required property` | Missing required field | Include the required field |
| `Additional properties are not allowed` | Unknown field in request | Remove unrecognized fields |
| `'<value>' is not a 'uri'` | Invalid URL format | Provide a valid URL |
| `'<value>' is not a 'date'` | Invalid date format | Use YYYY-MM-DD format |
| `'<value>' is not a 'date-time'` | Invalid datetime format | Use ISO 8601 format |

---

## Implementation Details

### Files Modified

- **`schema.py`** - JSON Schema definitions and validation functions
- **`gtd.py`** - API handlers with validation integration
- **`requirements.txt`** - Added `jsonschema>=4.17.0` dependency

### Validation Flow

```
1. Client sends HTTP request with JSON body
2. Server parses JSON
3. Server validates against appropriate schema
4. If valid: Process request normally
5. If invalid: Return 400 with error details
```

### Code Example

```python
from schema import validate_task, get_validation_error_response

def add_gtd_task(self):
    # Parse incoming JSON
    data = json.loads(body)
    
    # Validate
    is_valid, error_message = validate_task(data, schema_type="create")
    if not is_valid:
        self.send_response(400)
        error_response = get_validation_error_response(error_message)
        self.wfile.write(json.dumps(error_response).encode('utf-8'))
        return
    
    # Process valid data...
```

---

## Testing Validation

### Test Valid Task Creation

```bash
curl -X POST http://localhost:8000/api/gtd/tasks \
  -H "Content-Type: application/json" \
  -d '{"content": "Test task", "category": "next_actions"}'
```

**Expected:** `201 Created` with task object

### Test Invalid Task Creation

```bash
curl -X POST http://localhost:8000/api/gtd/tasks \
  -H "Content-Type: application/json" \
  -d '{"content": "", "category": "invalid"}'
```

**Expected:** `400 Bad Request` with validation error

### Test Invalid JSON

```bash
curl -X POST http://localhost:8000/api/gtd/tasks \
  -H "Content-Type: application/json" \
  -d 'not valid json'
```

**Expected:** `400 Bad Request` with JSON parse error

---

## Security Considerations

1. **Input Sanitization:** Validation prevents malformed data but doesn't sanitize content. XSS protection should be implemented separately.

2. **Size Limits:** String length limits prevent buffer overflow and DoS attacks.

3. **Type Safety:** Strict type checking prevents type confusion attacks.

4. **Additional Properties:** `additionalProperties: False` prevents injection of unexpected fields.

---

## Future Enhancements

- [ ] Add request rate limiting
- [ ] Implement content sanitization (HTML escaping)
- [ ] Add custom validation error codes for programmatic handling
- [ ] Create OpenAPI/Swagger specification with schema definitions
- [ ] Add automated validation test suite

---

## Related Documentation

- [ARCHITECTURE_ROADMAP.md](ARCHITECTURE_ROADMAP.md) - Phase 1.5 implementation
- [GTD_MODULE.md](GTD_MODULE.md) - GTD module overview
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development guidelines

---

**Status:** ✅ Implemented  
**Test Coverage:** Manual testing complete  
**Next Review:** 2026-04-02
