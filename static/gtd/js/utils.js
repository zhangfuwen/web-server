// GTD Desktop - Utility Functions

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} text - Text to escape
 * @returns {string} - Escaped HTML string
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format ISO timestamp to human-readable relative time
 * @param {string} isoString - ISO date string
 * @returns {string} - Formatted time string (e.g., "5m ago", "2h ago")
 */
function formatTime(isoString) {
    try {
        const date = new Date(isoString);
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return 'just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 7) return `${days}d ago`;
        return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    } catch (e) {
        return '';
    }
}

/**
 * Extract due date from task comments
 * @param {Array} comments - Task comments array
 * @returns {string|null} - Due date in YYYY-MM-DD format or null
 */
function extractDueDate(comments) {
    if (!comments || comments.length === 0) return null;
    
    for (const comment of comments) {
        const commentText = typeof comment === 'string' ? comment : (comment.text || '');
        const dueDateMatch = commentText.match(/(?:due|截止日期)[:：]\s*(\d{4}-\d{2}-\d{2})/i);
        if (dueDateMatch) {
            return dueDateMatch[1];
        }
    }
    
    return null;
}

/**
 * Extract subtasks from task comments
 * @param {Array} comments - Task comments array
 * @returns {Array} - Array of subtask objects with text and completed status
 */
function extractSubtasks(comments) {
    if (!comments || comments.length === 0) return [];
    
    const subtasks = [];
    for (const comment of comments) {
        const commentText = typeof comment === 'string' ? comment : (comment.text || '');
        const subtaskMatch = commentText.match(/^subtask:\s*(.+?)(?:\s*\[([x ])\])?$/i);
        if (subtaskMatch) {
            subtasks.push({
                text: subtaskMatch[1],
                completed: subtaskMatch[2] === 'x'
            });
        }
    }
    
    return subtasks;
}

/**
 * Compare two due dates (earlier dates first)
 * @param {string} dateA - First date string
 * @param {string} dateB - Second date string
 * @returns {number} - Comparison result for sorting
 */
function compareDueDates(dateA, dateB) {
    if (!dateA && !dateB) return 0;
    if (!dateA) return 1;
    if (!dateB) return -1;
    return new Date(dateA) - new Date(dateB);
}

/**
 * Compare two due dates (near to far)
 * @param {string} dateA - First date string
 * @param {string} dateB - Second date string
 * @returns {number} - Comparison result for sorting
 */
function compareDueDatesNearToFar(dateA, dateB) {
    if (!dateA && !dateB) return 0;
    if (!dateA) return 1;
    if (!dateB) return -1;
    return new Date(dateA) - new Date(dateB);
}

/**
 * Compare two due dates (far to near)
 * @param {string} dateA - First date string
 * @param {string} dateB - Second date string
 * @returns {number} - Comparison result for sorting
 */
function compareDueDatesFarToNear(dateA, dateB) {
    if (!dateA && !dateB) return 0;
    if (!dateA) return -1;
    if (!dateB) return 1;
    return new Date(dateB) - new Date(dateA);
}

/**
 * Capitalize first letter of each word
 * @param {string} str - String to capitalize
 * @returns {string} - Capitalized string
 */
function capitalizeWords(str) {
    return str.replace(/\b\w/g, l => l.toUpperCase());
}
