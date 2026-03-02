// GTD Desktop - API Functions

/**
 * Load tasks from the GTD API
 * @returns {Promise<void>}
 */
async function loadTasks() {
    try {
        const response = await fetch('/api/gtd/tasks', {
            headers: { 'Accept': 'application/json' }
        });
        window.rawGtdData = await response.json();
        parseGtdData();
        renderBoard();
        updateStats();
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

/**
 * Save GTD data back to the API
 * @returns {Promise<void>}
 */
async function saveGtdData() {
    const rawGtdData = window.rawGtdData;
    
    // Convert rawGtdData back to markdown format
    let markdown = '';
    
    if (rawGtdData.projects) {
        markdown += '# Projects\n';
        rawGtdData.projects.forEach(task => {
            markdown += `- [${task.completed ? 'x' : ' '}] ${task.text}\n`;
            if (task.comments && task.comments.length > 0) {
                task.comments.forEach(comment => {
                    const commentText = typeof comment === 'string' ? comment : comment.text;
                    markdown += `  <!-- Comment: ${commentText} -->\n`;
                });
            }
        });
        markdown += '\n';
    }
    
    if (rawGtdData.next_actions) {
        markdown += '# Next Actions\n';
        rawGtdData.next_actions.forEach(task => {
            markdown += `- [${task.completed ? 'x' : ' '}] ${task.text}\n`;
            if (task.comments && task.comments.length > 0) {
                task.comments.forEach(comment => {
                    const commentText = typeof comment === 'string' ? comment : comment.text;
                    markdown += `  <!-- Comment: ${commentText} -->\n`;
                });
            }
        });
        markdown += '\n';
    }
    
    if (rawGtdData.waiting_for) {
        markdown += '# Waiting For\n';
        rawGtdData.waiting_for.forEach(task => {
            markdown += `- [${task.completed ? 'x' : ' '}] ${task.text}\n`;
            if (task.comments && task.comments.length > 0) {
                task.comments.forEach(comment => {
                    const commentText = typeof comment === 'string' ? comment : comment.text;
                    markdown += `  <!-- Comment: ${commentText} -->\n`;
                });
            }
        });
        markdown += '\n';
    }
    
    if (rawGtdData.someday_maybe) {
        markdown += '# Someday/Maybe\n';
        rawGtdData.someday_maybe.forEach(task => {
            markdown += `- [${task.completed ? 'x' : ' '}] ${task.text}\n`;
            if (task.comments && task.comments.length > 0) {
                task.comments.forEach(comment => {
                    const commentText = typeof comment === 'string' ? comment : comment.text;
                    markdown += `  <!-- Comment: ${commentText} -->\n`;
                });
            }
        });
        markdown += '\n';
    }

    const response = await fetch('/api/gtd/tasks', {
        method: 'PUT',
        headers: { 'Content-Type': 'text/markdown' },
        body: markdown
    });

    if (!response.ok) {
        throw new Error('Failed to save tasks');
    }
}

/**
 * Add a new task to the projects list
 * @param {string} title - Task title
 * @returns {Promise<void>}
 */
async function addTask(title) {
    if (!title) return;

    try {
        const newTask = {
            text: title,
            completed: false,
            comments: []
        };

        if (!window.rawGtdData.projects) window.rawGtdData.projects = [];
        window.rawGtdData.projects.push(newTask);

        await saveGtdData();
        await loadTasks();
    } catch (error) {
        console.error('Error adding task:', error);
    }
}

/**
 * Toggle task completion status
 * @param {string} taskId - Task ID
 * @returns {Promise<void>}
 */
async function toggleComplete(taskId) {
    const task = window.tasks.find(t => t.id === taskId);
    if (!task) return;

    const category = window.rawGtdData[task.category];
    if (category) {
        const idx = parseInt(taskId.split('-')[1]);
        if (category[idx]) {
            category[idx].completed = !category[idx].completed;
            await saveGtdData();
            await loadTasks();
        }
    }
}

/**
 * Update task title
 * @param {string} taskId - Task ID
 * @param {string} newTitle - New title
 * @returns {Promise<void>}
 */
async function updateTaskTitle(taskId, newTitle) {
    if (!newTitle) return;

    const task = window.tasks.find(t => t.id === taskId);
    if (!task || task.title === newTitle) return;

    try {
        const categoryData = window.rawGtdData[task.category];
        const idx = parseInt(taskId.split('-')[1]);
        
        if (categoryData && categoryData[idx]) {
            categoryData[idx].text = newTitle;
            await saveGtdData();
            await loadTasks();
        }
    } catch (error) {
        console.error('Error updating task title:', error);
    }
}

/**
 * Update a task comment
 * @param {string} taskId - Task ID
 * @param {number} commentIdx - Comment index
 * @param {string} newComment - New comment text
 * @returns {Promise<void>}
 */
async function updateComment(taskId, commentIdx, newComment) {
    const task = window.tasks.find(t => t.id === taskId);
    if (!task) return;

    try {
        const categoryData = window.rawGtdData[task.category];
        const idx = parseInt(taskId.split('-')[1]);
        
        if (categoryData && categoryData[idx]) {
            if (!newComment) {
                categoryData[idx].comments.splice(commentIdx, 1);
            } else {
                if (typeof categoryData[idx].comments[commentIdx] === 'object') {
                    categoryData[idx].comments[commentIdx].text = newComment;
                } else {
                    categoryData[idx].comments[commentIdx] = newComment;
                }
            }
            await saveGtdData();
            await loadTasks();
        }
    } catch (error) {
        console.error('Error updating comment:', error);
    }
}

/**
 * Add a new comment to a task
 * @param {string} taskId - Task ID
 * @param {string} newComment - Comment text
 * @returns {Promise<void>}
 */
async function addComment(taskId, newComment) {
    if (!newComment) return;

    const task = window.tasks.find(t => t.id === taskId);
    if (!task) return;

    try {
        const categoryData = window.rawGtdData[task.category];
        const idx = parseInt(taskId.split('-')[1]);
        
        if (categoryData && categoryData[idx]) {
            if (!categoryData[idx].comments) {
                categoryData[idx].comments = [];
            }
            categoryData[idx].comments.push({
                id: `c-${Date.now()}`,
                text: newComment,
                createdAt: new Date().toISOString()
            });
            await saveGtdData();
            await loadTasks();
        }
    } catch (error) {
        console.error('Error adding comment:', error);
    }
}

/**
 * Toggle subtask completion status
 * @param {string} taskId - Task ID
 * @param {number} commentIdx - Comment index
 * @returns {Promise<void>}
 */
async function toggleSubtaskComment(taskId, commentIdx) {
    const task = window.tasks.find(t => t.id === taskId);
    if (!task || !task.comments) return;

    try {
        const categoryData = window.rawGtdData[task.category];
        const idx = parseInt(taskId.split('-')[1]);
        
        if (categoryData && categoryData[idx]) {
            const comment = categoryData[idx].comments[commentIdx];
            const commentText = typeof comment === 'string' ? comment : (comment.text || '');
            const newCommentText = commentText.replace(/^\[ \]/i, '[x]').replace(/^\[x\]/i, '[ ]');
            
            if (typeof comment === 'object') {
                categoryData[idx].comments[commentIdx].text = newCommentText;
            } else {
                categoryData[idx].comments[commentIdx] = newCommentText;
            }
            
            await saveGtdData();
            await loadTasks();
        }
    } catch (error) {
        console.error('Error toggling subtask:', error);
    }
}

/**
 * Delete a task comment
 * @param {string} taskId - Task ID
 * @param {number} commentIdx - Comment index
 * @returns {Promise<void>}
 */
async function deleteComment(taskId, commentIdx) {
    const task = window.tasks.find(t => t.id === taskId);
    if (!task || !task.comments) return;

    try {
        const categoryData = window.rawGtdData[task.category];
        const idx = parseInt(taskId.split('-')[1]);
        
        if (categoryData && categoryData[idx]) {
            categoryData[idx].comments.splice(commentIdx, 1);
            await saveGtdData();
            await loadTasks();
        }
    } catch (error) {
        console.error('Error deleting comment:', error);
    }
}

/**
 * Save task edits from modal
 * @param {Object} taskData - Task data from modal
 * @returns {Promise<void>}
 */
async function saveTask(taskData) {
    const { taskId, category, title, status, priority, dueDate, commentsText } = taskData;
    
    if (!title) return;

    try {
        const categoryData = window.rawGtdData[category];
        const idx = parseInt(taskId.split('-')[1]);
        
        if (categoryData && categoryData[idx]) {
            categoryData[idx].text = title;
            categoryData[idx].completed = (status === 'done');
            categoryData[idx].comments = commentsText ? commentsText.split('\n').filter(c => c.trim()) : [];
            
            if (priority === 'high') {
                if (!categoryData[idx].comments.some(c => c.text && c.text.includes('优先级高'))) {
                    categoryData[idx].comments.push({
                        id: `c-${Date.now()}`,
                        text: '优先级高',
                        createdAt: new Date().toISOString()
                    });
                }
            } else {
                categoryData[idx].comments = categoryData[idx].comments.filter(c => !c.text || !c.text.includes('优先级高'));
            }
            
            categoryData[idx].comments = categoryData[idx].comments.filter(c => !c.text || !c.text.match(/^(due|截止日期)[:：]/i));
            if (dueDate) {
                categoryData[idx].comments.push({
                    id: `c-${Date.now()}`,
                    text: `due: ${dueDate}`,
                    createdAt: new Date().toISOString()
                });
            }
            
            await saveGtdData();
            await loadTasks();
        }
    } catch (error) {
        console.error('Error saving task:', error);
    }
}
