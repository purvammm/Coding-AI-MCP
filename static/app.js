// WebSocket connections
let chatSocket = null;
let terminalSocket = null;

// Current model
let currentModel = null;

// Attachments
let attachments = [];
let selectedAttachments = [];

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

async function initializeApp() {
    // Connect WebSockets
    connectWebSockets();
    
    // Load models
    await loadModels();
    
    // Load project summary
    await loadProjectSummary();
    
    // Load file explorer
    await loadFileExplorer();
    
    // Update status
    updateStatus();
    
    // Load attachments
    await loadAttachments();

    // Set up event listeners
    document.getElementById('model-select').addEventListener('change', selectModel);
    document.getElementById('refresh-files').addEventListener('click', loadFileExplorer);
    document.getElementById('clear-chat').addEventListener('click', clearChat);
    document.getElementById('search-button').addEventListener('click', searchCode);

    // Attachment event listeners
    setupAttachmentHandlers();

    // Web search event listeners
    setupWebSearchHandlers();
}

// WebSocket connections
function connectWebSockets() {
    // Chat WebSocket
    const chatWsUrl = `ws://${window.location.host}/ws/chat`;
    chatSocket = new WebSocket(chatWsUrl);
    
    chatSocket.onopen = function(e) {
        updateConnectionStatus(true);
        console.log('Chat WebSocket connected');
    };
    
    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        
        if (data.type === 'chat_chunk') {
            appendAssistantMessage(data.content, true);
        } else if (data.type === 'chat_end') {
            // Finish the message
            finishAssistantMessage();
        }
    };
    
    chatSocket.onclose = function(e) {
        updateConnectionStatus(false);
        console.log('Chat WebSocket disconnected');
        // Try to reconnect after 2 seconds
        setTimeout(connectWebSockets, 2000);
    };
    
    // Terminal WebSocket
    const terminalWsUrl = `ws://${window.location.host}/ws/terminal`;
    terminalSocket = new WebSocket(terminalWsUrl);
    
    terminalSocket.onopen = function(e) {
        console.log('Terminal WebSocket connected');
    };
    
    terminalSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        
        if (data.type === 'terminal_output') {
            appendTerminalOutput(data.content);
        } else if (data.type === 'terminal_end') {
            // Terminal command completed
            appendTerminalOutput('\n$ ');
        }
    };
    
    terminalSocket.onclose = function(e) {
        console.log('Terminal WebSocket disconnected');
    };
}

// Update connection status indicator
function updateConnectionStatus(connected) {
    const statusIndicator = document.getElementById('connection-status');
    const statusText = document.getElementById('connection-text');
    
    if (connected) {
        statusIndicator.className = 'status-indicator status-online';
        statusText.textContent = 'Connected';
    } else {
        statusIndicator.className = 'status-indicator status-offline';
        statusText.textContent = 'Disconnected';
    }
}

// Load available models
async function loadModels() {
    try {
        const response = await fetch('/api/models');
        const data = await response.json();
        
        const modelSelect = document.getElementById('model-select');
        modelSelect.innerHTML = '';
        
        if (data.models && data.models.length > 0) {
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.name;
                option.textContent = `${model.name} (${model.provider})`;
                modelSelect.appendChild(option);
            });
            
            // Get current model
            await getCurrentModel();
        } else {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No models available';
            modelSelect.appendChild(option);
        }
    } catch (error) {
        console.error('Error loading models:', error);
    }
}

// Get current model
async function getCurrentModel() {
    try {
        const response = await fetch('/api/current-model');
        const data = await response.json();
        
        if (data.model) {
            currentModel = data.model;
            document.getElementById('model-select').value = currentModel.name;
            
            // Update model info
            document.getElementById('model-description').textContent = currentModel.description;
            document.getElementById('current-model-info').style.display = 'block';
        }
    } catch (error) {
        console.error('Error getting current model:', error);
    }
}

// Select model
async function selectModel() {
    const modelName = document.getElementById('model-select').value;
    
    try {
        const response = await fetch('/api/select-model', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ model_name: modelName })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentModel = data.model;
            
            // Update model info
            document.getElementById('model-description').textContent = currentModel.description;
            document.getElementById('current-model-info').style.display = 'block';
            
            // Show success message
            appendSystemMessage(`Model changed to ${currentModel.name}`);
        }
    } catch (error) {
        console.error('Error selecting model:', error);
        appendSystemMessage('Error selecting model');
    }
}

// Load project summary
async function loadProjectSummary() {
    try {
        const response = await fetch('/api/project-summary');
        const data = await response.json();
        
        const summaryContainer = document.getElementById('project-summary');
        
        let languagesHtml = '';
        if (data.languages) {
            languagesHtml = '<ul class="list-unstyled mb-0">';
            for (const [lang, count] of Object.entries(data.languages)) {
                languagesHtml += `<li><small>${lang}: ${count} files</small></li>`;
            }
            languagesHtml += '</ul>';
        }
        
        summaryContainer.innerHTML = `
            <div class="small">
                <div><strong>Files:</strong> ${data.total_files || 0}</div>
                <div><strong>Lines:</strong> ${data.total_lines || 0}</div>
                <div><strong>Symbols:</strong> ${data.symbol_count || 0}</div>
                <div><strong>Languages:</strong></div>
                ${languagesHtml}
                <div class="mt-2 text-muted">
                    <small>Last updated: ${data.last_updated ? new Date(data.last_updated).toLocaleString() : 'Never'}</small>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error loading project summary:', error);
    }
}

// Load file explorer
async function loadFileExplorer() {
    try {
        const response = await fetch('/api/file-operation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                operation: 'list',
                path: '.',
                include_hidden: false
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.files) {
            const fileExplorer = document.getElementById('file-explorer');
            fileExplorer.innerHTML = '';
            
            const fileList = document.createElement('ul');
            fileList.className = 'list-group list-group-flush';
            
            data.files.forEach(file => {
                const item = document.createElement('li');
                item.className = 'list-group-item py-2';
                
                const icon = file.is_directory ? 
                    '<i class="fas fa-folder text-warning"></i>' : 
                    '<i class="fas fa-file text-primary"></i>';
                
                item.innerHTML = `
                    <div class="d-flex align-items-center">
                        <div class="me-2">${icon}</div>
                        <div class="flex-grow-1 text-truncate">${file.name}</div>
                        <div class="small text-muted">${file.is_directory ? '' : formatFileSize(file.size)}</div>
                    </div>
                `;
                
                item.addEventListener('click', () => {
                    if (file.is_directory) {
                        // Navigate to directory
                        loadDirectory(file.path);
                    } else {
                        // View file
                        viewFile(file.path);
                    }
                });
                
                fileList.appendChild(item);
            });
            
            fileExplorer.appendChild(fileList);
        }
    } catch (error) {
        console.error('Error loading file explorer:', error);
    }
}

// Load directory
async function loadDirectory(path) {
    try {
        const response = await fetch('/api/file-operation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                operation: 'list',
                path: path,
                include_hidden: false
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.files) {
            const fileExplorer = document.getElementById('file-explorer');
            fileExplorer.innerHTML = '';
            
            // Add back button
            const backButton = document.createElement('button');
            backButton.className = 'btn btn-sm btn-light w-100 text-start mb-2';
            backButton.innerHTML = '<i class="fas fa-arrow-left"></i> Back';
            backButton.addEventListener('click', () => {
                // Go up one directory
                const parentPath = path.split('/').slice(0, -1).join('/');
                if (parentPath === '') {
                    loadFileExplorer();
                } else {
                    loadDirectory(parentPath);
                }
            });
            fileExplorer.appendChild(backButton);
            
            // Current path
            const pathElement = document.createElement('div');
            pathElement.className = 'alert alert-light py-1 mb-2';
            pathElement.textContent = path;
            fileExplorer.appendChild(pathElement);
            
            const fileList = document.createElement('ul');
            fileList.className = 'list-group list-group-flush';
            
            data.files.forEach(file => {
                const item = document.createElement('li');
                item.className = 'list-group-item py-2';
                
                const icon = file.is_directory ? 
                    '<i class="fas fa-folder text-warning"></i>' : 
                    '<i class="fas fa-file text-primary"></i>';
                
                item.innerHTML = `
                    <div class="d-flex align-items-center">
                        <div class="me-2">${icon}</div>
                        <div class="flex-grow-1 text-truncate">${file.name}</div>
                        <div class="small text-muted">${file.is_directory ? '' : formatFileSize(file.size)}</div>
                    </div>
                `;
                
                item.addEventListener('click', () => {
                    if (file.is_directory) {
                        // Navigate to directory
                        loadDirectory(file.path);
                    } else {
                        // View file
                        viewFile(file.path);
                    }
                });
                
                fileList.appendChild(item);
            });
            
            fileExplorer.appendChild(fileList);
        }
    } catch (error) {
        console.error('Error loading directory:', error);
    }
}

// View file
async function viewFile(path) {
    try {
        const response = await fetch('/api/file-operation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                operation: 'read',
                path: path
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.content !== undefined) {
            // Create a message with the file content
            const message = `File: ${path}\n\n\`\`\`\n${data.content}\n\`\`\``;
            appendSystemMessage(message);
        }
    } catch (error) {
        console.error('Error viewing file:', error);
    }
}

// Format file size
function formatFileSize(bytes) {
    if (bytes < 1024) {
        return bytes + ' B';
    } else if (bytes < 1024 * 1024) {
        return (bytes / 1024).toFixed(1) + ' KB';
    } else {
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
}

// Update status
function updateStatus() {
    const statusInfo = document.getElementById('status-info');
    
    statusInfo.innerHTML = `
        <div class="small">
            <div><strong>Server:</strong> <span id="server-status">Online</span></div>
            <div><strong>Model:</strong> <span id="model-status">${currentModel ? currentModel.name : 'None'}</span></div>
            <div><strong>WebSocket:</strong> <span id="ws-status">Connected</span></div>
            <div class="mt-2 text-muted">
                <small>Last updated: ${new Date().toLocaleString()}</small>
            </div>
        </div>
    `;
}

// Chat functions
function handleChatKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function sendMessage() {
    const chatInput = document.getElementById('chat-input');
    const message = chatInput.value.trim();

    if (message === '') return;

    // Add user message to chat
    appendUserMessage(message);

    // Clear input
    chatInput.value = '';

    // Get selected attachment IDs
    const attachmentIds = selectedAttachments.map(att => att.id);

    // Clear selected attachments
    selectedAttachments = [];
    updateSelectedAttachmentsDisplay();

    // Send message to server
    if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        chatSocket.send(JSON.stringify({
            type: 'chat',
            message: message,
            attachment_ids: attachmentIds
        }));

        // Start a new assistant message (will be filled by streaming)
        startAssistantMessage();
    } else {
        appendSystemMessage('WebSocket not connected. Please refresh the page.');
    }
}

function appendUserMessage(message) {
    const chatContainer = document.getElementById('chat-container');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    messageDiv.textContent = message;
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function startAssistantMessage() {
    const chatContainer = document.getElementById('chat-container');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message';
    messageDiv.id = 'current-assistant-message';
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function appendAssistantMessage(content, isStreaming = false) {
    const chatContainer = document.getElementById('chat-container');
    let messageDiv;
    
    if (isStreaming) {
        messageDiv = document.getElementById('current-assistant-message');
        if (!messageDiv) {
            messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant-message';
            messageDiv.id = 'current-assistant-message';
            chatContainer.appendChild(messageDiv);
        }
        
        // Append content
        const currentContent = messageDiv.innerHTML;
        messageDiv.innerHTML = currentContent + content;
    } else {
        messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message';
        messageDiv.innerHTML = content;
        chatContainer.appendChild(messageDiv);
    }
    
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function finishAssistantMessage() {
    const messageDiv = document.getElementById('current-assistant-message');
    if (messageDiv) {
        // Convert markdown to HTML
        const content = messageDiv.innerHTML;
        messageDiv.innerHTML = marked.parse(content);
        
        // Remove the ID
        messageDiv.removeAttribute('id');
        
        // Highlight code blocks
        Prism.highlightAllUnder(messageDiv);
    }
}

function appendSystemMessage(message) {
    const chatContainer = document.getElementById('chat-container');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.style.backgroundColor = '#f0f0f0';
    messageDiv.style.color = '#666';
    messageDiv.style.textAlign = 'center';
    messageDiv.style.padding = '5px';
    messageDiv.style.margin = '10px 0';
    messageDiv.style.borderRadius = '4px';
    
    // Convert markdown to HTML
    messageDiv.innerHTML = marked.parse(message);
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    // Highlight code blocks
    Prism.highlightAllUnder(messageDiv);
}

function clearChat() {
    document.getElementById('chat-container').innerHTML = '';
    
    // Clear conversation on server
    fetch('/api/clear-conversation', {
        method: 'POST'
    });
}

// Terminal functions
function handleTerminalKeyPress(event) {
    if (event.key === 'Enter') {
        executeCommand();
    }
}

function executeCommand() {
    const terminalInput = document.getElementById('terminal-input');
    const command = terminalInput.value.trim();
    
    if (command === '') return;
    
    // Clear input
    terminalInput.value = '';
    
    // Get auto-approve setting
    const autoApprove = document.getElementById('auto-approve').checked;
    
    // Append command to terminal
    appendTerminalOutput(`$ ${command}\n`);
    
    // Send command to server
    if (terminalSocket && terminalSocket.readyState === WebSocket.OPEN) {
        terminalSocket.send(JSON.stringify({
            type: 'command',
            command: command,
            auto_approve: autoApprove
        }));
    } else {
        appendTerminalOutput('WebSocket not connected. Please refresh the page.\n$ ');
    }
}

function appendTerminalOutput(output) {
    const terminalOutput = document.getElementById('terminal-output');
    terminalOutput.textContent += output;
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

// Code search
async function searchCode() {
    const query = document.getElementById('search-input').value.trim();
    const symbolType = document.getElementById('symbol-type').value;
    
    if (query === '') return;
    
    try {
        const response = await fetch('/api/search-code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                symbol_type: symbolType || null
            })
        });
        
        const data = await response.json();
        
        const resultsContainer = document.getElementById('search-results');
        resultsContainer.innerHTML = '';
        
        if (data.results && data.results.length > 0) {
            const resultsList = document.createElement('ul');
            resultsList.className = 'list-group';
            
            data.results.forEach(result => {
                const item = document.createElement('li');
                item.className = 'list-group-item py-2';
                
                let icon = '';
                if (result.type === 'function' || result.type === 'method') {
                    icon = '<i class="fas fa-code text-primary"></i>';
                } else if (result.type === 'class') {
                    icon = '<i class="fas fa-cube text-success"></i>';
                } else if (result.type === 'variable') {
                    icon = '<i class="fas fa-dollar-sign text-warning"></i>';
                }
                
                item.innerHTML = `
                    <div>
                        <div class="d-flex align-items-center">
                            <div class="me-2">${icon}</div>
                            <div class="flex-grow-1">
                                <strong>${result.name}</strong>
                                <span class="badge bg-secondary ms-1">${result.type}</span>
                            </div>
                        </div>
                        <div class="small text-muted mt-1">
                            ${result.file_path}:${result.line_number}
                            ${result.parent ? `<span class="ms-2">(in ${result.parent})</span>` : ''}
                        </div>
                    </div>
                `;
                
                item.addEventListener('click', () => {
                    viewFile(result.file_path);
                });
                
                resultsList.appendChild(item);
            });
            
            resultsContainer.appendChild(resultsList);
        } else {
            resultsContainer.innerHTML = '<div class="alert alert-light py-2">No results found</div>';
        }
    } catch (error) {
        console.error('Error searching code:', error);
    }
}

// Rebuild index
async function rebuildIndex() {
    try {
        const statusInfo = document.getElementById('status-info');
        statusInfo.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> Rebuilding index...</div>';
        
        const response = await fetch('/api/rebuild-index', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update project summary
            await loadProjectSummary();
            
            // Update status
            updateStatus();
            
            // Show success message
            appendSystemMessage('Project index rebuilt successfully');
        }
    } catch (error) {
        console.error('Error rebuilding index:', error);
        appendSystemMessage('Error rebuilding index');
    }
}

// Show command history
async function showHistory() {
    try {
        const response = await fetch('/api/terminal-history');
        const data = await response.json();
        
        let historyHtml = '<div class="list-group">';
        
        if (data.history && data.history.length > 0) {
            data.history.forEach(cmd => {
                const statusClass = cmd.exit_code === 0 ? 'text-success' : 'text-danger';
                const statusIcon = cmd.exit_code === 0 ? 
                    '<i class="fas fa-check-circle"></i>' : 
                    '<i class="fas fa-times-circle"></i>';
                
                historyHtml += `
                    <div class="list-group-item py-2">
                        <div class="d-flex justify-content-between">
                            <div class="text-truncate">${cmd.command}</div>
                            <div class="${statusClass}">${statusIcon}</div>
                        </div>
                        <div class="small text-muted">
                            ${new Date(cmd.timestamp).toLocaleString()} 
                            (${cmd.execution_time.toFixed(2)}s)
                        </div>
                    </div>
                `;
            });
        } else {
            historyHtml += '<div class="list-group-item">No command history</div>';
        }
        
        historyHtml += '</div>';
        
        appendSystemMessage('## Command History\n\n' + historyHtml);
    } catch (error) {
        console.error('Error showing history:', error);
    }
}

// Show running processes
async function showProcesses() {
    try {
        const response = await fetch('/api/running-processes');
        const data = await response.json();
        
        let processesHtml = '<div class="list-group">';
        
        if (data.processes && data.processes.length > 0) {
            data.processes.forEach(proc => {
                processesHtml += `
                    <div class="list-group-item py-2">
                        <div class="d-flex justify-content-between">
                            <div class="text-truncate">${proc.command}</div>
                            <div>
                                <span class="badge bg-primary">PID: ${proc.pid}</span>
                                <button class="btn btn-sm btn-danger ms-2" onclick="killProcess(${proc.pid})">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                        </div>
                        <div class="small text-muted">
                            Started: ${new Date(proc.start_time).toLocaleString()} 
                            (${proc.duration.toFixed(2)}s ago)
                        </div>
                    </div>
                `;
            });
        } else {
            processesHtml += '<div class="list-group-item">No running processes</div>';
        }
        
        processesHtml += '</div>';
        
        appendSystemMessage('## Running Processes\n\n' + processesHtml);
    } catch (error) {
        console.error('Error showing processes:', error);
    }
}

// Kill process
async function killProcess(pid) {
    try {
        const response = await fetch(`/api/kill-process/${pid}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            appendSystemMessage(`Process ${pid} killed successfully`);
            // Refresh process list
            showProcesses();
        } else {
            appendSystemMessage(`Failed to kill process ${pid}`);
        }
    } catch (error) {
        console.error('Error killing process:', error);
    }
}

// Attachment functions
function setupAttachmentHandlers() {
    const fileInput = document.getElementById('file-input');
    const uploadButton = document.getElementById('upload-button');
    const dropZone = document.getElementById('drop-zone');

    // Upload button click
    uploadButton.addEventListener('click', () => {
        fileInput.click();
    });

    // Drop zone click
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', handleFileSelection);

    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.backgroundColor = '#f8f9fa';
    });

    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.style.backgroundColor = '';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.backgroundColor = '';

        const files = Array.from(e.dataTransfer.files);
        uploadFiles(files);
    });
}

async function handleFileSelection(event) {
    const files = Array.from(event.target.files);
    await uploadFiles(files);

    // Clear the input
    event.target.value = '';
}

async function uploadFiles(files) {
    for (const file of files) {
        await uploadFile(file);
    }

    // Refresh attachments list
    await loadAttachments();
}

async function uploadFile(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);

        // Show upload progress
        appendSystemMessage(`Uploading ${file.name}...`);

        const response = await fetch('/api/upload-attachment', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            appendSystemMessage(`✓ Uploaded ${file.name} successfully`);
        } else {
            appendSystemMessage(`✗ Failed to upload ${file.name}: ${data.error}`);
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        appendSystemMessage(`✗ Error uploading ${file.name}`);
    }
}

async function loadAttachments() {
    try {
        const response = await fetch('/api/attachments');
        const data = await response.json();

        attachments = data.attachments || [];
        updateAttachmentsList();
    } catch (error) {
        console.error('Error loading attachments:', error);
    }
}

function updateAttachmentsList() {
    const attachmentsList = document.getElementById('attachments-list');
    attachmentsList.innerHTML = '';

    if (attachments.length === 0) {
        attachmentsList.innerHTML = '<div class="text-muted text-center py-2">No attachments</div>';
        return;
    }

    attachments.forEach(attachment => {
        const item = document.createElement('div');
        item.className = 'attachment-item d-flex align-items-center justify-content-between p-2 border-bottom';

        const icon = getFileIcon(attachment.file_type);
        const size = formatFileSize(attachment.size);

        item.innerHTML = `
            <div class="d-flex align-items-center flex-grow-1">
                <div class="me-2">${icon}</div>
                <div class="flex-grow-1">
                    <div class="text-truncate" style="max-width: 150px;" title="${attachment.filename}">
                        ${attachment.filename}
                    </div>
                    <small class="text-muted">${size} • ${attachment.file_type}</small>
                </div>
            </div>
            <div class="btn-group btn-group-sm">
                <button class="btn btn-outline-primary btn-sm" onclick="selectAttachment('${attachment.id}')" title="Select for chat">
                    <i class="fas fa-plus"></i>
                </button>
                <button class="btn btn-outline-info btn-sm" onclick="viewAttachment('${attachment.id}')" title="View content">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-outline-danger btn-sm" onclick="deleteAttachment('${attachment.id}')" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;

        attachmentsList.appendChild(item);
    });
}

function getFileIcon(fileType) {
    const icons = {
        'image': '<i class="fas fa-image text-info"></i>',
        'document': '<i class="fas fa-file-alt text-primary"></i>',
        'spreadsheet': '<i class="fas fa-file-excel text-success"></i>',
        'code': '<i class="fas fa-code text-warning"></i>',
        'archive': '<i class="fas fa-file-archive text-secondary"></i>',
        'other': '<i class="fas fa-file text-muted"></i>'
    };

    return icons[fileType] || icons['other'];
}

function selectAttachment(attachmentId) {
    const attachment = attachments.find(att => att.id === attachmentId);
    if (!attachment) return;

    // Check if already selected
    if (selectedAttachments.find(att => att.id === attachmentId)) {
        return;
    }

    selectedAttachments.push(attachment);
    updateSelectedAttachmentsDisplay();
}

function unselectAttachment(attachmentId) {
    selectedAttachments = selectedAttachments.filter(att => att.id !== attachmentId);
    updateSelectedAttachmentsDisplay();
}

function updateSelectedAttachmentsDisplay() {
    const container = document.getElementById('selected-attachments');
    const list = document.getElementById('selected-attachments-list');

    if (selectedAttachments.length === 0) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';
    list.innerHTML = '';

    selectedAttachments.forEach(attachment => {
        const item = document.createElement('span');
        item.className = 'badge bg-primary me-1 mb-1';
        item.innerHTML = `
            ${attachment.filename}
            <button type="button" class="btn-close btn-close-white ms-1"
                    onclick="unselectAttachment('${attachment.id}')" style="font-size: 0.7em;"></button>
        `;
        list.appendChild(item);
    });
}

function toggleAttachmentSelection() {
    // Simple toggle - could be enhanced with a modal
    if (attachments.length === 0) {
        appendSystemMessage('No attachments available. Upload some files first.');
        return;
    }

    // For now, just show a message about how to select attachments
    appendSystemMessage('Click the + button next to any attachment to include it in your next message.');
}

async function viewAttachment(attachmentId) {
    try {
        const response = await fetch(`/api/attachment/${attachmentId}`);
        const data = await response.json();

        if (data.success) {
            const attachment = data.attachment;
            let content = `## ${attachment.filename}\n\n`;
            content += `**Type:** ${attachment.file_type}\n`;
            content += `**Size:** ${formatFileSize(attachment.size)}\n`;
            content += `**Uploaded:** ${new Date(attachment.upload_time).toLocaleString()}\n\n`;

            if (attachment.extracted_text) {
                content += `**Extracted Content:**\n\`\`\`\n${attachment.extracted_text.substring(0, 1000)}`;
                if (attachment.extracted_text.length > 1000) {
                    content += '\n... (truncated)';
                }
                content += '\n\`\`\`';
            } else {
                content += '*No text content extracted*';
            }

            appendSystemMessage(content);
        }
    } catch (error) {
        console.error('Error viewing attachment:', error);
        appendSystemMessage('Error loading attachment content');
    }
}

async function deleteAttachment(attachmentId) {
    if (!confirm('Are you sure you want to delete this attachment?')) {
        return;
    }

    try {
        const response = await fetch(`/api/attachment/${attachmentId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            appendSystemMessage('Attachment deleted successfully');

            // Remove from selected attachments if present
            selectedAttachments = selectedAttachments.filter(att => att.id !== attachmentId);
            updateSelectedAttachmentsDisplay();

            // Refresh attachments list
            await loadAttachments();
        } else {
            appendSystemMessage('Failed to delete attachment');
        }
    } catch (error) {
        console.error('Error deleting attachment:', error);
        appendSystemMessage('Error deleting attachment');
    }
}

// Show conversation statistics
async function showConversationStats() {
    try {
        const response = await fetch('/api/conversation-stats');
        const data = await response.json();

        let statsHtml = '<div class="list-group">';

        if (data && Object.keys(data).length > 0) {
            statsHtml += `
                <div class="list-group-item">
                    <strong>Conversation Statistics</strong>
                </div>
                <div class="list-group-item">
                    <div class="d-flex justify-content-between">
                        <span>Total Turns:</span>
                        <span>${data.total_turns || 0}</span>
                    </div>
                </div>
                <div class="list-group-item">
                    <div class="d-flex justify-content-between">
                        <span>Total Tokens:</span>
                        <span>${data.total_tokens || 0}</span>
                    </div>
                </div>
                <div class="list-group-item">
                    <div class="d-flex justify-content-between">
                        <span>Average Importance:</span>
                        <span>${data.average_importance || 0}</span>
                    </div>
                </div>
                <div class="list-group-item">
                    <div class="d-flex justify-content-between">
                        <span>Turns with Code:</span>
                        <span>${data.turns_with_code || 0}</span>
                    </div>
                </div>
                <div class="list-group-item">
                    <div class="d-flex justify-content-between">
                        <span>Turns with Attachments:</span>
                        <span>${data.turns_with_attachments || 0}</span>
                    </div>
                </div>
                <div class="list-group-item">
                    <div class="d-flex justify-content-between">
                        <span>Summaries Created:</span>
                        <span>${data.summaries_created || 0}</span>
                    </div>
                </div>
                <div class="list-group-item">
                    <div class="d-flex justify-content-between">
                        <span>Tokens Saved:</span>
                        <span>${data.tokens_saved_by_summaries || 0}</span>
                    </div>
                </div>
            `;
        } else {
            statsHtml += '<div class="list-group-item">No conversation data available</div>';
        }

        statsHtml += '</div>';

        appendSystemMessage('## Conversation Statistics\n\n' + statsHtml);
    } catch (error) {
        console.error('Error showing conversation stats:', error);
        appendSystemMessage('Error loading conversation statistics');
    }
}

// Web search functions
function setupWebSearchHandlers() {
    const webSearchInput = document.getElementById('web-search-input');
    const urlScrapeInput = document.getElementById('url-scrape-input');

    // Enter key handlers
    webSearchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performWebSearch();
        }
    });

    urlScrapeInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            scrapeUrl();
        }
    });
}

async function performWebSearch() {
    const query = document.getElementById('web-search-input').value.trim();
    const provider = document.getElementById('search-provider').value;
    const numResults = parseInt(document.getElementById('search-results-count').value) || 5;

    if (!query) return;

    try {
        appendSystemMessage(`🔍 Searching the web for: "${query}"...`);

        const response = await fetch('/api/web-search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                provider: provider,
                num_results: numResults,
                include_content: false
            })
        });

        const data = await response.json();

        if (data.success) {
            displayWebSearchResults(data);

            // Also add to chat as context
            let searchSummary = `Web search results for "${query}":\n\n`;
            data.results.forEach((result, index) => {
                searchSummary += `${index + 1}. **${result.title}**\n`;
                searchSummary += `   ${result.url}\n`;
                searchSummary += `   ${result.snippet}\n\n`;
            });

            appendSystemMessage(searchSummary);
        } else {
            appendSystemMessage(`❌ Search failed: ${data.error}`);
        }
    } catch (error) {
        console.error('Web search error:', error);
        appendSystemMessage('❌ Error performing web search');
    }
}

async function scrapeUrl() {
    const url = document.getElementById('url-scrape-input').value.trim();

    if (!url) return;

    try {
        appendSystemMessage(`🔗 Scraping content from: ${url}...`);

        const response = await fetch('/api/scrape-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                use_cache: true
            })
        });

        const data = await response.json();

        if (data.success) {
            let content = `## Scraped Content: ${data.title}\n\n`;
            content += `**URL:** ${data.url}\n`;
            content += `**Word Count:** ${data.word_count}\n`;
            content += `**Scraped:** ${new Date(data.scraped_at).toLocaleString()}\n\n`;
            content += `**Summary:**\n${data.summary}\n\n`;

            if (data.content && data.content.length > 2000) {
                content += `**Content Preview:**\n\`\`\`\n${data.content.substring(0, 2000)}...\n\`\`\``;
            } else if (data.content) {
                content += `**Full Content:**\n\`\`\`\n${data.content}\n\`\`\``;
            }

            appendSystemMessage(content);
        } else {
            appendSystemMessage(`❌ Scraping failed: ${data.error}`);
        }
    } catch (error) {
        console.error('URL scraping error:', error);
        appendSystemMessage('❌ Error scraping URL');
    }
}

function displayWebSearchResults(data) {
    const resultsContainer = document.getElementById('web-search-results');
    resultsContainer.innerHTML = '';

    if (!data.results || data.results.length === 0) {
        resultsContainer.innerHTML = '<div class="alert alert-light py-2">No results found</div>';
        return;
    }

    const resultsList = document.createElement('div');
    resultsList.className = 'list-group';

    data.results.forEach((result, index) => {
        const item = document.createElement('div');
        item.className = 'list-group-item py-2';

        item.innerHTML = `
            <div>
                <div class="d-flex align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1 text-truncate" title="${result.title}">
                            ${result.title}
                        </h6>
                        <p class="mb-1 small text-muted">${result.snippet}</p>
                        <small class="text-primary">${result.url}</small>
                    </div>
                    <div class="ms-2">
                        <button class="btn btn-outline-primary btn-sm" onclick="scrapeSpecificUrl('${result.url}')" title="Scrape this URL">
                            <i class="fas fa-download"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

        resultsList.appendChild(item);
    });

    resultsContainer.appendChild(resultsList);
}

async function scrapeSpecificUrl(url) {
    document.getElementById('url-scrape-input').value = url;
    await scrapeUrl();
}

async function showWebCacheStats() {
    try {
        const response = await fetch('/api/web-cache-stats');
        const data = await response.json();

        let statsHtml = '<div class="list-group">';

        if (data && Object.keys(data).length > 0) {
            statsHtml += `
                <div class="list-group-item">
                    <strong>Web Cache Statistics</strong>
                </div>
                <div class="list-group-item">
                    <div class="d-flex justify-content-between">
                        <span>Cached Items:</span>
                        <span>${data.cached_items || 0}</span>
                    </div>
                </div>
                <div class="list-group-item">
                    <div class="d-flex justify-content-between">
                        <span>Cache Duration:</span>
                        <span>${data.cache_duration_hours || 0} hours</span>
                    </div>
                </div>
            `;

            if (data.oldest_item) {
                statsHtml += `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between">
                            <span>Oldest Item:</span>
                            <span>${new Date(data.oldest_item).toLocaleString()}</span>
                        </div>
                    </div>
                `;
            }

            if (data.newest_item) {
                statsHtml += `
                    <div class="list-group-item">
                        <div class="d-flex justify-content-between">
                            <span>Newest Item:</span>
                            <span>${new Date(data.newest_item).toLocaleString()}</span>
                        </div>
                    </div>
                `;
            }
        } else {
            statsHtml += '<div class="list-group-item">No cache data available</div>';
        }

        statsHtml += '</div>';

        appendSystemMessage('## Web Cache Statistics\n\n' + statsHtml);
    } catch (error) {
        console.error('Error showing web cache stats:', error);
        appendSystemMessage('Error loading web cache statistics');
    }
}

// Enhanced chat with web search integration
async function performWebSearchAndChat(query) {
    try {
        // First perform web search
        const searchResponse = await fetch('/api/search-and-summarize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                num_results: 5,
                provider: document.getElementById('search-provider').value
            })
        });

        const searchData = await searchResponse.json();

        if (searchData.success) {
            // Add search results as context to the chat
            const contextMessage = `Based on web search results for "${query}":\n\n${searchData.summary}`;

            // Send to chat with web context
            if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
                chatSocket.send(JSON.stringify({
                    type: 'chat',
                    message: `${query}\n\nWeb search context:\n${contextMessage}`,
                    attachment_ids: []
                }));

                startAssistantMessage();
            }
        }
    } catch (error) {
        console.error('Error in web search and chat:', error);
        appendSystemMessage('Error performing web search for chat context');
    }
}
