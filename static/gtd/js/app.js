// GTD Desktop - Main Application Logic

// Global state
window.tasks = [];
window.rawGtdData = {};
window.currentSort = 'none';
window.columns = [
    { id: 'todo', title: 'To Do', icon: 'fa-circle', color: '#64748b' },
    { id: 'doing', title: 'In Progress', icon: 'fa-spinner', color: '#f59e0b' },
    { id: 'done', title: 'Done', icon: 'fa-check-circle', color: '#10b981' }
];

/**
 * Initialize the application when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    loadTasks();
    setupEventListeners();
});

/**
 * Setup global event listeners
 */
function setupEventListeners() {
    // Close sidebar when clicking on nav items on mobile
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                toggleSidebar();
            }
        });
    });
}

/**
 * Parse GTD data from API response into internal task format
 */
function parseGtdData() {
    window.tasks = [];
    
    // Parse projects
    if (window.rawGtdData.projects) {
        window.rawGtdData.projects.forEach((task, idx) => {
            const dueDate = extractDueDate(task.comments);
            window.tasks.push({
                id: `proj-${idx}`,
                title: task.text,
                status: task.completed ? 'done' : 'todo',
                priority: 'medium',
                category: 'projects',
                comments: task.comments || [],
                completed: task.completed,
                dueDate: dueDate
            });
        });
    }
    
    // Parse next actions
    if (window.rawGtdData.next_actions) {
        window.rawGtdData.next_actions.forEach((task, idx) => {
            const isHighPriority = task.comments.some(c => c.text && c.text.includes('优先级高'));
            const dueDate = extractDueDate(task.comments);
            window.tasks.push({
                id: `next-${idx}`,
                title: task.text,
                status: task.completed ? 'done' : 'todo',
                priority: isHighPriority ? 'high' : 'medium',
                category: 'next_actions',
                comments: task.comments || [],
                completed: task.completed,
                dueDate: dueDate
            });
        });
    }
    
    // Parse waiting for
    if (window.rawGtdData.waiting_for) {
        window.rawGtdData.waiting_for.forEach((task, idx) => {
            const dueDate = extractDueDate(task.comments);
            window.tasks.push({
                id: `wait-${idx}`,
                title: task.text,
                status: task.completed ? 'done' : 'doing',
                priority: 'low',
                category: 'waiting_for',
                comments: task.comments || [],
                completed: task.completed,
                dueDate: dueDate
            });
        });
    }
    
    // Parse someday/maybe
    if (window.rawGtdData.someday_maybe) {
        window.rawGtdData.someday_maybe.forEach((task, idx) => {
            const dueDate = extractDueDate(task.comments);
            window.tasks.push({
                id: `some-${idx}`,
                title: task.text,
                status: task.completed ? 'done' : 'todo',
                priority: 'low',
                category: 'someday_maybe',
                comments: task.comments || [],
                completed: task.completed,
                dueDate: dueDate
            });
        });
    }

    // Apply current sort
    applySort();
}

/**
 * Apply current sorting to tasks array
 */
function applySort() {
    if (window.currentSort === 'none') return;
    
    const priorityOrder = { 'high': 3, 'medium': 2, 'low': 1 };
    
    window.tasks.sort((a, b) => {
        switch (window.currentSort) {
            case 'priority':
                const aPriority = priorityOrder[a.priority] || 0;
                const bPriority = priorityOrder[b.priority] || 0;
                if (aPriority !== bPriority) {
                    return aPriority - bPriority;
                }
                return compareDueDates(a.dueDate, b.dueDate);
                
            case 'priority-desc':
                const aPriorityDesc = priorityOrder[a.priority] || 0;
                const bPriorityDesc = priorityOrder[b.priority] || 0;
                if (aPriorityDesc !== bPriorityDesc) {
                    return bPriorityDesc - aPriorityDesc;
                }
                return compareDueDates(a.dueDate, b.dueDate);
                
            case 'due-date':
                return compareDueDatesFarToNear(a.dueDate, b.dueDate);
                
            case 'due-date-desc':
                return compareDueDatesNearToFar(a.dueDate, b.dueDate);
                
            default:
                return 0;
        }
    });
}

/**
 * Sort tasks by specified criteria
 * @param {string} sortType - Sort type: 'none', 'priority', 'priority-desc', 'due-date', 'due-date-desc'
 */
function sortTasks(sortType) {
    window.currentSort = sortType;
    
    // Update button states
    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.sort === sortType) {
            btn.classList.add('active');
        }
    });
    
    // Re-sort and re-render
    parseGtdData();
    renderBoard();
}

/**
 * Handle Enter key press in quick add input
 * @param {Event} event - Keyboard event
 */
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        addTaskFromInput();
    }
}

/**
 * Add task from quick add input
 */
async function addTaskFromInput() {
    const input = document.getElementById('new-task-input');
    const title = input.value.trim();
    
    if (!title) return;

    await addTask(title);
    input.value = '';
    closeQuickAdd();
}

/**
 * Save task from modal form
 */
async function saveTaskFromModal() {
    const taskId = document.getElementById('edit-task-id').value;
    const category = document.getElementById('edit-task-category').value;
    const title = document.getElementById('edit-task-title').value.trim();
    const status = document.getElementById('edit-task-status').value;
    const priority = document.getElementById('edit-task-priority').value;
    const dueDate = document.getElementById('edit-task-due-date').value.trim();
    const commentsText = document.getElementById('edit-task-comments').value.trim();
    
    if (!title) return;

    await saveTask({
        taskId,
        category,
        title,
        status,
        priority,
        dueDate,
        commentsText
    });
    
    closeModal();
}

// Export functions to window for HTML onclick handlers
window.loadTasks = loadTasks;
window.parseGtdData = parseGtdData;
window.renderBoard = renderBoard;
window.updateStats = updateStats;
window.openQuickAdd = openQuickAdd;
window.closeQuickAdd = closeQuickAdd;
window.handleKeyPress = handleKeyPress;
window.addTaskFromInput = addTaskFromInput;
window.sortTasks = sortTasks;
window.openEditModal = openEditModal;
window.closeModal = closeModal;
window.saveTaskFromModal = saveTaskFromModal;
window.toggleComplete = toggleComplete;
window.toggleSidebar = toggleSidebar;
window.toggleDesktopSidebar = toggleDesktopSidebar;
window.updateTaskTitle = updateTaskTitleInline;
window.updateComment = updateCommentInline;
window.addComment = addCommentInline;
window.handleTitleKeypress = handleTitleKeypress;
window.handleCommentKeypress = handleCommentKeypress;
window.handleAddCommentKeypress = handleAddCommentKeypress;
window.toggleSubtaskComment = toggleSubtaskComment;
window.deleteComment = deleteComment;
