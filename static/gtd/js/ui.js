// GTD Desktop - UI Rendering Functions

/**
 * Render the task board with all columns
 */
function renderBoard() {
    const board = document.getElementById('task-board');
    const columns = window.columns;
    const tasks = window.tasks;
    
    board.innerHTML = columns.map(column => {
        const columnTasks = tasks.filter(t => t.status === column.id);
        return `
            <div class="task-column">
                <div class="column-header">
                    <div class="column-title">
                        <i class="fas ${column.icon}" style="color: ${column.color}"></i>
                        ${column.title}
                    </div>
                    <span class="column-count">${columnTasks.length}</span>
                </div>
                <div class="task-list">
                    ${columnTasks.length === 0 ? `
                        <div class="empty-state">
                            <i class="fas fa-inbox"></i>
                            <p>No tasks</p>
                        </div>
                    ` : columnTasks.map(task => renderTaskCard(task)).join('')}
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Render a single task card
 * @param {Object} task - Task object
 * @returns {string} - HTML string for task card
 */
function renderTaskCard(task) {
    const priorityClass = `priority-${task.priority || 'low'}`;
    const completedClass = task.completed ? 'completed' : '';
    const categoryLabel = task.category.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    
    // Filter out due date comments from display
    const displayComments = (task.comments || []).filter(c => {
        const text = typeof c === 'string' ? c : c.text;
        return !text.match(/^(due|截止日期)[:：]/i);
    });
    
    // Count subtasks
    const subtaskCount = (task.comments || []).filter(c => {
        const text = typeof c === 'string' ? c : c.text;
        return text.match(/^\[[x ]\]/i);
    }).length;
    
    const completedSubtasks = (task.comments || []).filter(c => {
        const text = typeof c === 'string' ? c : c.text;
        return text.match(/^\[x\]/i);
    }).length;
    
    return `
        <div class="task-card ${priorityClass} ${completedClass}" onclick="event.stopPropagation()">
            <div class="task-header">
                <div class="task-title" 
                     contenteditable="true" 
                     data-task-id="${task.id}"
                     data-original-title="${escapeHtml(task.title)}"
                     onfocus="this.dataset.originalTitle = this.textContent"
                     onblur="updateTaskTitle('${task.id}', this)"
                     onkeydown="handleTitleKeypress(event, '${task.id}', this)"
                     onclick="event.stopPropagation()">${escapeHtml(task.title)}</div>
                <div class="task-actions" onclick="event.stopPropagation()">
                    ${!task.completed ? `
                        <button class="task-action-btn complete-btn" onclick="toggleComplete('${task.id}')" title="Mark Done">
                            <i class="fas fa-check"></i>
                        </button>
                    ` : `
                        <button class="task-action-btn" onclick="toggleComplete('${task.id}')" title="Mark Undone">
                            <i class="fas fa-undo"></i>
                        </button>
                    `}
                    <button class="task-action-btn" onclick="openEditModal('${task.id}')" title="More Options">
                        <i class="fas fa-ellipsis-h"></i>
                    </button>
                </div>
            </div>
            <div class="task-meta">
                <span class="task-tag"><i class="fas fa-folder"></i> ${categoryLabel}</span>
                <span class="task-tag"><i class="fas fa-flag"></i> ${task.priority || 'Low'}</span>
                ${task.dueDate ? `<span class="task-tag"><i class="fas fa-calendar"></i> ${task.dueDate}</span>` : ''}
                ${subtaskCount > 0 ? `
                    <span class="task-tag">
                        <i class="fas fa-check-square"></i>
                        ${completedSubtasks}/${subtaskCount}
                    </span>
                ` : ''}
            </div>
            <div class="task-comments">
                ${displayComments.map((c, idx) => {
                    const commentText = typeof c === 'string' ? c : c.text;
                    const commentTime = typeof c === 'object' && c.createdAt ? formatTime(c.createdAt) : '';
                    const commentId = typeof c === 'object' && c.id ? c.id : idx;
                    const subtaskMatch = commentText.match(/^\[([x ])\]\s*(.+)/i);
                    if (subtaskMatch) {
                        const isCompleted = subtaskMatch[1] === 'x';
                        const text = subtaskMatch[2];
                        return `
                            <div class="task-comment subtask" 
                                 data-task-id="${task.id}"
                                 data-comment-idx="${idx}"
                                 onclick="toggleSubtaskComment('${task.id}', ${idx}, event)">
                                <div class="task-comment-checkbox ${isCompleted ? 'checked' : ''}">
                                    ${isCompleted ? '<i class="fas fa-check" style="font-size: 9px;"></i>' : ''}
                                </div>
                                <div class="task-comment-text ${isCompleted ? 'completed' : ''}" 
                                     contenteditable="true" 
                                     data-task-id="${task.id}"
                                     data-comment-idx="${idx}"
                                     data-original-comment="${escapeHtml(commentText)}"
                                     onfocus="this.dataset.originalComment = this.textContent"
                                     onblur="updateComment('${task.id}', ${idx}, this)"
                                     onkeydown="handleCommentKeypress(event, '${task.id}', ${idx}, this)"
                                     onclick="event.stopPropagation()">${escapeHtml(text)}</div>
                                <button class="task-comment-delete" onclick="deleteComment('${task.id}', ${idx}, event)">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                        `;
                    } else {
                        return `
                            <div class="task-comment" 
                                 data-task-id="${task.id}"
                                 data-comment-idx="${idx}">
                                <div class="task-comment-text" 
                                     contenteditable="true"
                                     data-task-id="${task.id}"
                                     data-comment-idx="${idx}"
                                     data-original-comment="${escapeHtml(commentText)}"
                                     onfocus="this.dataset.originalComment = this.textContent"
                                     onblur="updateComment('${task.id}', ${idx}, this)"
                                     onkeydown="handleCommentKeypress(event, '${task.id}', ${idx}, this)"
                                     onclick="event.stopPropagation()">${escapeHtml(commentText)}</div>
                                ${commentTime ? `<span class="comment-time">${commentTime}</span>` : ''}
                                <button class="task-comment-delete" onclick="deleteComment('${task.id}', ${idx}, event)">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                        `;
                    }
                }).join('')}
                <div class="add-comment">
                    <input type="text" 
                           placeholder="Add comment or [ ] subtask..." 
                           data-task-id="${task.id}"
                           onblur="addComment('${task.id}', this)"
                           onkeydown="handleAddCommentKeypress(event, '${task.id}', this)"
                           onclick="event.stopPropagation()">
                </div>
                ${displayComments.length > 2 ? `<div class="task-comment">+${displayComments.length - 2} more</div>` : ''}
            </div>
        </div>
    `;
}

/**
 * Update statistics display
 */
function updateStats() {
    const tasks = window.tasks;
    const total = tasks.length;
    const completed = tasks.filter(t => t.completed).length;
    const important = tasks.filter(t => t.priority === 'high' && !t.completed).length;

    document.getElementById('total-tasks').textContent = total;
    document.getElementById('completed-tasks').textContent = completed;
    document.getElementById('important-count').textContent = important;
}

/**
 * Open the quick add task input
 */
function openQuickAdd() {
    document.getElementById('quick-add').style.display = 'block';
    document.getElementById('new-task-input').focus();
}

/**
 * Close the quick add task input
 */
function closeQuickAdd() {
    document.getElementById('quick-add').style.display = 'none';
    document.getElementById('new-task-input').value = '';
}

/**
 * Open the task edit modal
 * @param {string} taskId - Task ID to edit
 */
function openEditModal(taskId) {
    const task = window.tasks.find(t => t.id === taskId);
    if (!task) return;

    document.getElementById('edit-task-id').value = taskId;
    document.getElementById('edit-task-category').value = task.category;
    document.getElementById('edit-task-title').value = task.title;
    document.getElementById('edit-task-status').value = task.status;
    document.getElementById('edit-task-priority').value = task.priority;
    document.getElementById('edit-task-due-date').value = task.dueDate || '';
    document.getElementById('edit-task-comments').value = task.comments.map(c => c.text || c).join('\n');

    document.getElementById('task-modal').classList.add('active');
}

/**
 * Close the task edit modal
 */
function closeModal() {
    document.getElementById('task-modal').classList.remove('active');
}

/**
 * Toggle sidebar on mobile
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
}

/**
 * Toggle desktop sidebar visibility
 */
function toggleDesktopSidebar() {
    const container = document.querySelector('.app-container');
    container.classList.toggle('sidebar-hidden');
}

/**
 * Handle title keypress events
 * @param {Event} event - Keyboard event
 * @param {string} taskId - Task ID
 * @param {HTMLElement} element - Input element
 */
function handleTitleKeypress(event, taskId, element) {
    if (event.key === 'Enter') {
        event.preventDefault();
        element.blur();
    } else if (event.key === 'Escape') {
        element.textContent = element.dataset.originalTitle || element.textContent;
        element.blur();
    }
}

/**
 * Handle comment keypress events
 * @param {Event} event - Keyboard event
 * @param {string} taskId - Task ID
 * @param {number} commentIdx - Comment index
 * @param {HTMLElement} element - Input element
 */
function handleCommentKeypress(event, taskId, commentIdx, element) {
    if (event.key === 'Enter') {
        event.preventDefault();
        element.blur();
    } else if (event.key === 'Escape') {
        element.textContent = element.dataset.originalComment || element.textContent;
        element.blur();
    }
}

/**
 * Handle add comment keypress events
 * @param {Event} event - Keyboard event
 * @param {string} taskId - Task ID
 * @param {HTMLElement} element - Input element
 */
function handleAddCommentKeypress(event, taskId, element) {
    if (event.key === 'Enter') {
        event.preventDefault();
        addComment(taskId, element.value.trim());
        element.value = '';
    } else if (event.key === 'Escape') {
        element.value = '';
        element.blur();
    }
}

/**
 * Handle inline task title update
 * @param {string} taskId - Task ID
 * @param {HTMLElement} element - Input element
 */
function updateTaskTitleInline(taskId, element) {
    const newTitle = element.textContent.trim();
    if (!newTitle) {
        element.textContent = element.dataset.originalTitle || '';
        return;
    }
    updateTaskTitle(taskId, newTitle);
}

/**
 * Handle inline comment update
 * @param {string} taskId - Task ID
 * @param {number} commentIdx - Comment index
 * @param {HTMLElement} element - Input element
 */
function updateCommentInline(taskId, commentIdx, element) {
    const newComment = element.textContent.trim();
    updateComment(taskId, commentIdx, newComment);
}

/**
 * Handle add comment from inline input
 * @param {string} taskId - Task ID
 * @param {HTMLElement} element - Input element
 */
function addCommentInline(taskId, element) {
    const newComment = element.value.trim();
    if (!newComment) return;
    addComment(taskId, newComment);
    element.value = '';
}
