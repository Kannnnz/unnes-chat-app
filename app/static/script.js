// UNNES Document Chat System - Main JavaScript
// Versi: 7.0.2 (Google Sign-In Integration)

// --- GLOBAL STATE & CONFIGURATION ---
const API_BASE_URL = '/api/v1';
// PENTING: Ganti dengan Client ID Anda yang asli dari Google Cloud Console
const GOOGLE_CLIENT_ID = "589754605755-k35ogen4efe92mpfjeddd8eblq6pm0l4.apps.googleusercontent.com"; 

let currentUser = null;
let currentToken = null;
let currentChatSessionId = null; 
let currentChatDocumentIds = []; 
let currentChatMessages = []; 
let selectedUploadFiles = [];
let confirmCallback = null;

// --- DOM ELEMENTS CACHE ---
const elements = {
    loadingOverlay: document.getElementById('loading-overlay'),
    navUserInfo: document.getElementById('nav-user-info'),
    navUsername: document.getElementById('nav-username'),
    navRole: document.getElementById('nav-role'),
    logoutBtn: document.getElementById('logout-btn'),
    authSection: document.getElementById('auth-section'),
    dashboardSection: document.getElementById('dashboard-section'),
    loginFormContainer: document.getElementById('login-form'),
    registerFormContainer: document.getElementById('register-form'),
    loginFormElement: document.getElementById('login-form-element'),
    registerFormElement: document.getElementById('register-form-element'),
    showRegisterLink: document.getElementById('show-register'),
    showLoginLink: document.getElementById('show-login'),
    navLinks: {
        upload: document.getElementById('nav-upload'),
        documents: document.getElementById('nav-documents'),
        chat: document.getElementById('nav-chat'),
        profile: document.getElementById('nav-profile'),
        faq: document.getElementById('nav-faq'),
        admin: document.getElementById('nav-admin'),
    },
    navAdminItem: document.getElementById('nav-admin-item'),
    contentSections: {
        upload: document.getElementById('upload-section'),
        documents: document.getElementById('documents-section'),
        chat: document.getElementById('chat-section'),
        profile: document.getElementById('profile-section'),
        faq: document.getElementById('faq-section'),
        admin: document.getElementById('admin-section'),
    },
    uploadForm: document.getElementById('upload-form'),
    uploadArea: document.getElementById('upload-area'),
    fileInput: document.getElementById('file-input'),
    fileListDisplay: document.getElementById('file-list'),
    uploadBtn: document.getElementById('upload-btn'),
    documentsContainer: document.getElementById('documents-container'),
    chatDocumentList: document.getElementById('chat-document-list'),
    chatMessagesContainer: document.getElementById('chat-messages'),
    chatForm: document.getElementById('chat-form'),
    chatInput: document.getElementById('chat-input'),
    chatSendBtn: document.getElementById('chat-send-btn'),
    predefinedQuestionsContainer: document.getElementById('predefined-questions-container'),
    profileUsernameDisplay: document.getElementById('profile-username-display'),
    profileEmailDisplay: document.getElementById('profile-email-display'),
    profileRoleDisplay: document.getElementById('profile-role-display'),
    systemInfoContent: document.getElementById('system-info-content'),
    faqContainer: document.querySelector('.faq-container'),
    alertContainer: document.getElementById('alert-container'),
    confirmationModal: {
        element: document.getElementById('confirmation-modal'),
        title: document.getElementById('modal-title'),
        message: document.getElementById('modal-message'),
        cancelBtn: document.getElementById('modal-cancel'),
        confirmBtn: document.getElementById('modal-confirm'),
    },
    adminStats: {
        users: document.getElementById('stat-users'),
        documents: document.getElementById('stat-documents'),
        chats: document.getElementById('stat-chats'),
    },
    adminTabsContainer: document.querySelector('.admin-tabs'),
    adminTabContents: {
        users: document.getElementById('admin-users-tab'),
        documents: document.getElementById('admin-documents-tab'),
        activity: document.getElementById('admin-activity-tab'),
    },
    adminUsersList: document.getElementById('admin-users-list'),
    adminDocumentsList: document.getElementById('admin-documents-list'),
    adminActivityList: document.getElementById('admin-activity-list'),
};

// --- UTILITY FUNCTIONS ---
function showLoading(show = true) { elements.loadingOverlay.style.display = show ? 'flex' : 'none'; }
function hideLoading() { elements.loadingOverlay.style.display = 'none'; }
function showAlert(message, type = 'info', duration = 5000) {
    if(!elements.alertContainer) return;
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    elements.alertContainer.appendChild(alertDiv);
    setTimeout(() => {
        alertDiv.style.opacity = '0';
        setTimeout(() => alertDiv.remove(), 400);
    }, duration - 400);
}
function showModal(title, message, onConfirm) {
    const modal = elements.confirmationModal;
    if (!modal.element) return;
    modal.title.textContent = title;
    modal.message.textContent = message;
    modal.element.style.display = 'flex';
    confirmCallback = onConfirm;
}
function closeModal() {
    const modal = elements.confirmationModal;
    if (modal.element) modal.element.style.display = 'none';
    confirmCallback = null;
}
function formatDate(dateString) {
    if (!dateString) return 'Unknown date';
    try {
        return new Date(dateString).toLocaleString('id-ID', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) { return dateString; }
}
function sanitizeText(text) {
    const tempDiv = document.createElement('div');
    tempDiv.textContent = String(text ?? '');
    return tempDiv.innerHTML;
}
function setButtonLoading(button, isLoading, originalText = "Submit") {
    if(!button) return;
    if (isLoading) {
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = `<span class="loading-spinner-btn"></span> Memproses...`;
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalText || originalText;
    }
}
function renderEmptyState(container, message) {
    if(container) container.innerHTML = `<div class="empty-state"><p>${sanitizeText(message)}</p></div>`;
}

// --- API FUNCTIONS ---
async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = { ...options, headers: { ...options.headers } };
    if (currentToken) {
        config.headers['Authorization'] = `Bearer ${currentToken}`;
    }
    if (!(options.body instanceof FormData) && options.body) {
        config.headers['Content-Type'] = 'application/json';
        config.body = JSON.stringify(options.body);
    }

    try {
        const response = await fetch(url, config);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `HTTP error ${response.status}`);
        }
        return response.status === 204 ? null : await response.json();
    } catch (error) {
        console.error('API Call Error:', error.message, `on ${endpoint}`);
        throw error;
    }
}

// --- FUNGSI BARU: Callback setelah login Google berhasil ---
async function handleCredentialResponse(response) {
    showLoading();
    try {
        const payload = { credential: response.credential };
        const data = await apiCall('/auth/google', { method: 'POST', body: payload });
        
        currentToken = data.access_token;
        localStorage.setItem('token', currentToken);
        await loadUserProfile();

        if (currentUser) {
            showDashboard();
            showAlert(`Login via Google berhasil! Selamat datang, ${sanitizeText(currentUser.username)}.`, 'success');
        }
    } catch (error) {
        showAlert(error.message, 'error');
    } finally {
        hideLoading();
    }
}

// --- AUTHENTICATION & NAVIGATION ---
async function login(username, password) {
    const button = elements.loginFormElement.querySelector('button[type="submit"]');
    setButtonLoading(button, true);
    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        const data = await apiCall('/auth/token', { method: 'POST', body: formData });
        currentToken = data.access_token;
        localStorage.setItem('token', currentToken);
        await loadUserProfile();
        if (currentUser) {
            showDashboard();
            showAlert(`Login berhasil! Selamat datang, ${sanitizeText(currentUser.username)}.`, 'success');
        }
    } catch (error) {
        showAlert(error.message, 'error');
    } finally {
        setButtonLoading(button, false);
    }
}

async function register(username, email, password) {
    const button = elements.registerFormElement.querySelector('button[type="submit"]');
    setButtonLoading(button, true);
    try {
        await apiCall('/auth/register', { method: 'POST', body: { username, email, password } });
        showAlert('Registrasi berhasil! Silakan login.', 'success');
        showLoginForm();
    } catch(error) {
        showAlert(error.message, 'error');
    } finally {
        setButtonLoading(button, false);
    }
}

async function loadUserProfile() {
    const data = await apiCall('/auth/profile');
    currentUser = data;
    elements.navUsername.textContent = sanitizeText(currentUser.username);
    elements.navRole.textContent = sanitizeText(currentUser.role);
    elements.profileUsernameDisplay.textContent = sanitizeText(currentUser.username);
    elements.profileEmailDisplay.textContent = sanitizeText(currentUser.email);
    elements.profileRoleDisplay.textContent = sanitizeText(currentUser.role);
    elements.navUserInfo.style.display = 'flex';
    elements.navAdminItem.style.display = currentUser.role === 'admin' ? 'list-item' : 'none';
}

function logout() {
    localStorage.removeItem('token');
    currentToken = null;
    currentUser = null;
    window.location.reload();
}

function showAuthSection() {
    elements.authSection.style.display = 'flex';
    elements.dashboardSection.style.display = 'none';
    showLoginForm();
}

function showDashboard() {
    elements.authSection.style.display = 'none';
    elements.dashboardSection.style.display = 'flex';
    navigateToSection('chat');
}

function showLoginForm() {
    elements.loginFormContainer.classList.add('active');
    elements.registerFormContainer.classList.remove('active');
}

function showRegisterForm() {
    elements.loginFormContainer.classList.remove('active');
    elements.registerFormContainer.classList.add('active');
}

function navigateToSection(sectionName) {
    Object.values(elements.contentSections).forEach(s => s?.classList.remove('active'));
    Object.values(elements.navLinks).forEach(l => l?.classList.remove('active'));
    elements.contentSections[sectionName]?.classList.add('active');
    elements.navLinks[sectionName]?.classList.add('active');

    showLoading();
    let promise;
    switch(sectionName) {
        case 'documents': promise = loadUserDocuments(); break;
        case 'chat': promise = loadDocumentsForChat(); break;
        case 'profile': promise = loadSystemInfoForProfile(); break;
        case 'admin': promise = loadAdminDashboardData(); break;
        default: promise = Promise.resolve(); break;
    }
    promise.catch(err => showAlert(err.message, 'error')).finally(hideLoading);
}

// --- UPLOAD LOGIC ---
function handleFileSelection(eventFiles) {
    const newFiles = Array.from(eventFiles).slice(0, 5 - selectedUploadFiles.length);
    selectedUploadFiles.push(...newFiles);
    updateSelectedFilesUI();
}

function updateSelectedFilesUI() {
    if (!elements.fileListDisplay) return;
    elements.fileListDisplay.innerHTML = '';
    if (selectedUploadFiles.length === 0) {
        elements.uploadBtn.disabled = true;
        return;
    }
    selectedUploadFiles.forEach((file, index) => {
        const fileSizeMB = (file.size / 1024 / 1024).toFixed(2);
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-info">
                <span class="file-icon" aria-hidden="true">📄</span>
                <span class="file-name">${sanitizeText(file.name)}</span>
                <span class="file-size">(${fileSizeMB} MB)</span>
            </div>
            <button type="button" class="file-remove" data-index="${index}" aria-label="Hapus file ${sanitizeText(file.name)}">×</button>
        `;
        elements.fileListDisplay.appendChild(fileItem);
    });
    elements.uploadBtn.disabled = false;
}

function removeFileFromSelection(indexToRemove) {
    selectedUploadFiles.splice(indexToRemove, 1);
    updateSelectedFilesUI();
}

async function performUploadDocuments() {
    if (selectedUploadFiles.length === 0) return;
    setButtonLoading(elements.uploadBtn, true, "Upload Dokumen");
    const formData = new FormData();
    selectedUploadFiles.forEach(file => formData.append('files', file));
    try {
        const data = await apiCall('/documents/upload', { method: 'POST', body: formData });
        showAlert(`${data.uploaded_documents.length} dokumen berhasil diupload!`, 'success');
        selectedUploadFiles = [];
        updateSelectedFilesUI();
        elements.fileInput.value = '';
    } catch (error) {
        showAlert(`Error Upload: ${error.message}`, 'error');
    } finally {
        setButtonLoading(elements.uploadBtn, false, "Upload Dokumen");
    }
}


// --- DOCUMENT & CHAT LOGIC ---
async function loadUserDocuments() {
    try {
        const data = await apiCall('/documents/documents');
        renderDocumentList(data.documents || [], elements.documentsContainer, true);
    } catch (error) {
        showAlert(`Gagal memuat dokumen: ${error.message}`, 'error');
        renderEmptyState(elements.documentsContainer, 'Gagal memuat dokumen Anda.');
    }
}

function renderDocumentList(documents, containerElement, isUserView = true) {
    if (!containerElement) return;
    containerElement.innerHTML = ''; 

    if (!documents || documents.length === 0) {
        renderEmptyState(containerElement, 'Tidak ada dokumen.');
        return;
    }

    documents.forEach(doc => {
        const docCard = document.createElement('div');
        docCard.className = 'document-card';
        docCard.innerHTML = `
            <div class="document-header">
                <h3 class="document-title" id="doc-title-${doc.id}">${sanitizeText(doc.filename)}</h3>
                <p class="document-meta">Diupload: ${formatDate(doc.upload_date)}</p>
                ${!isUserView ? `<p class="document-meta">Oleh: ${sanitizeText(doc.username)}</p>` : ''}
            </div>
            <div class="document-actions">
                ${isUserView ? `<button class="btn btn-primary btn-small action-chat" data-doc-id="${doc.id}">Chat</button>` : ''}
                ${currentUser.role === 'admin' ? `<button class="btn btn-danger btn-small action-delete-doc" data-doc-id="${doc.id}" data-filename="${sanitizeText(doc.filename)}">Hapus</button>` : ''}
            </div>
        `;
        containerElement.appendChild(docCard);
    });
}

function createSessionId(docIds) {
    if (!docIds || docIds.length === 0) return null;
    return [...docIds].sort().join('_');
}

async function loadDocumentsForChat() {
    try {
        const data = await apiCall('/documents/documents');
        renderChatDocumentSelectionList(data.documents || []);
        resetChatUI();
    } catch (error) {
        showAlert(`Gagal memuat dokumen untuk chat: ${error.message}`, 'error');
    }
}

function renderChatDocumentSelectionList(documents) {
    const listContainer = elements.chatDocumentList;
    listContainer.innerHTML = '';
    document.getElementById('start-chat-session-btn')?.remove();

    if (!documents || documents.length === 0) {
        listContainer.innerHTML = `<div class="empty-state-small"><p>Anda belum mengupload dokumen.</p></div>`;
        return;
    }

    documents.forEach(doc => {
        const item = document.createElement('label');
        item.className = 'chat-document-item';
        item.innerHTML = `
            <input type="checkbox" class="doc-select-checkbox" data-doc-id="${doc.id}">
            <div class="chat-document-item-details">
                <div class="document-title">${sanitizeText(doc.filename)}</div>
                <div class="document-meta">${formatDate(doc.upload_date)}</div>
            </div>
        `;
        listContainer.appendChild(item);
    });

    const button = document.createElement('button');
    button.id = 'start-chat-session-btn';
    button.className = 'btn btn-primary';
    button.textContent = 'Mulai Sesi Chat';
    button.disabled = true;
    listContainer.parentElement.appendChild(button);

    button.addEventListener('click', handleStartChatSession);

    listContainer.addEventListener('change', () => {
        const selectedCount = listContainer.querySelectorAll('.doc-select-checkbox:checked').length;
        button.disabled = selectedCount === 0;
    });
}

async function handleStartChatSession() {
    const checkedBoxes = elements.chatDocumentList.querySelectorAll('.doc-select-checkbox:checked');
    const selectedDocIds = Array.from(checkedBoxes).map(cb => cb.dataset.docId);

    if (selectedDocIds.length === 0) {
        showAlert('Pilih setidaknya satu dokumen untuk memulai chat.', 'info');
        return;
    }
    
    const sessionId = createSessionId(selectedDocIds);
    await activateChatSession(sessionId, selectedDocIds);
}

async function activateChatSession(sessionId, docIds) {
    showLoading();
    try {
        currentChatSessionId = sessionId;
        currentChatDocumentIds = docIds;
        const data = await apiCall(`/chat/history/${sessionId}`);
        currentChatMessages = data || [];
        renderChatMessageHistoryUI();
        renderPredefinedQuestions(); 
        elements.chatInput.disabled = false;
        elements.chatSendBtn.disabled = false;
        const placeholderText = docIds.length > 1 ? `Bertanya tentang ${docIds.length} dokumen...` : `Bertanya tentang dokumen terpilih...`;
        elements.chatInput.placeholder = placeholderText;
        elements.chatInput.focus();
    } catch (error) {
        showAlert(`Gagal memulai sesi chat: ${error.message}`, 'error');
        resetChatUI();
    } finally {
        hideLoading();
    }
}

function renderChatMessageHistoryUI() {
    const container = elements.chatMessagesContainer;
    container.innerHTML = '';
    if (!currentChatSessionId) {
        container.innerHTML = `<div class="chat-welcome"><p>Pilih satu atau lebih dokumen dan klik "Mulai Sesi Chat".</p></div>`;
        return;
    }
    if (currentChatMessages.length === 0) {
        container.innerHTML = `<div class="chat-welcome"><p>Sesi chat dimulai. Silakan ajukan pertanyaan Anda.</p></div>`;
        return;
    }
    currentChatMessages.forEach(msg => {
        addMessageToChatUI(msg.content, msg.sender, msg.timestamp, false);
    });
}

function addMessageToChatUI(content, sender, timestamp, isNew = true) {
    const container = elements.chatMessagesContainer;
    container.querySelector('.chat-welcome')?.remove();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.innerHTML = `
        <div class="message-content">${sanitizeText(content)}</div>
        <div class="message-meta">${formatDate(timestamp)}</div>
    `;
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
    if (isNew) {
        currentChatMessages.push({ content, sender, timestamp });
    }
}

async function submitChatMessage(predefinedMessage = null) {
    const messageContent = predefinedMessage || elements.chatInput.value.trim();
    if (!messageContent || !currentChatSessionId) return;

    addMessageToChatUI(messageContent, 'user', new Date().toISOString(), true);
    
    if (!predefinedMessage) {
       elements.chatInput.value = '';
    }
    
    setButtonLoading(elements.chatSendBtn, true, "Kirim");
    elements.chatInput.disabled = true;

    try {
        const payload = {
            session_id: currentChatSessionId,
            message: messageContent,
            document_ids: currentChatDocumentIds
        };
        const responseData = await apiCall('/chat', { method: 'POST', body: payload });
        addMessageToChatUI(responseData.response, 'assistant', new Date().toISOString(), true);
    } catch (error) {
        showAlert(`Error Chat: ${error.message}`, 'error');
        if (!predefinedMessage) elements.chatInput.value = messageContent;
    } finally {
        setButtonLoading(elements.chatSendBtn, false, "Kirim");
        elements.chatInput.disabled = false;
        elements.chatInput.focus();
    }
}

function resetChatUI() {
    currentChatSessionId = null;
    currentChatDocumentIds = [];
    currentChatMessages = [];
    renderChatMessageHistoryUI();
    elements.predefinedQuestionsContainer.classList.remove('visible');
    elements.predefinedQuestionsContainer.innerHTML = '';

    elements.chatInput.disabled = true;
    elements.chatSendBtn.disabled = true;
    elements.chatInput.placeholder = 'Pilih dokumen dan mulai sesi...';
    document.querySelectorAll('.doc-select-checkbox').forEach(cb => cb.checked = false);
    const startBtn = document.getElementById('start-chat-session-btn');
    if (startBtn) startBtn.disabled = true;
}

function renderPredefinedQuestions() {
    const container = elements.predefinedQuestionsContainer;
    if (!container) return;

    const questions = [
        "Buat ringkasan dari dokumen ini.",
        "Apa saja poin-poin utama yang dibahas?",
        "Jelaskan metodologi penelitian yang digunakan.",
        "Apa kesimpulan dari dokumen ini?"
    ];

    container.innerHTML = `
        <h4>Saran Pertanyaan:</h4>
        <div class="predefined-questions-list">
            ${questions.map(q => `<button class="predefined-question-btn">${sanitizeText(q)}</button>`).join('')}
        </div>
    `;
    container.classList.add('visible');

    container.querySelectorAll('.predefined-question-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const questionText = btn.textContent;
            elements.chatInput.value = questionText;
            submitChatMessage(questionText);
        });
    });
}

async function loadSystemInfoForProfile() {
    try {
        const response = await fetch('/health');
        if (!response.ok) {
             const errorData = await response.json().catch(() => ({ detail: response.statusText }));
             throw new Error(errorData.detail || `HTTP error ${response.status}`);
        }
        const data = await response.json();

        const renderStatus = (label, status) => {
            const color = status === 'connected' ? 'var(--color-success)' : 'var(--color-error)';
            const text = status.charAt(0).toUpperCase() + status.slice(1);
            return `<p><strong>${label}:</strong> <span style="color: ${color};">${sanitizeText(text)}</span></p>`;
        };
        elements.systemInfoContent.innerHTML = `
            ${renderStatus('Status Server Backend', data.status || 'unknown')}
            ${renderStatus('Koneksi Database', data.database || 'unknown')}
            ${renderStatus('Koneksi Ollama', data.llm_ollama || 'unknown')}
        `;
    } catch (error) {
        elements.systemInfoContent.innerHTML = '<p>Gagal memuat informasi sistem.</p>';
        showAlert(`Gagal memuat info sistem: ${error.message}`, 'error');
    }
}


// --- ADMIN PANEL LOGIC ---
async function loadAdminDashboardData() {
    if (!currentUser || currentUser.role !== 'admin') return;
    try {
        const statsData = await apiCall('/admin/stats');
        elements.adminStats.users.textContent = statsData.total_users;
        elements.adminStats.documents.textContent = statsData.total_documents;
        elements.adminStats.chats.textContent = statsData.total_chats;
        await switchAdminTab('users', true); 
    } catch (error) {
        showAlert(`Gagal memuat panel admin: ${error.message}`, 'error');
    }
}

async function switchAdminTab(tabName, forceLoad = false) {
    document.querySelectorAll('.admin-tab-content').forEach(content => content.classList.remove('active'));
    document.querySelectorAll('.admin-tab-btn').forEach(btn => btn.classList.remove('active'));
    elements.adminTabContents[tabName]?.classList.add('active');
    elements.adminTabsContainer.querySelector(`[data-tab='${tabName}']`)?.classList.add('active');

    if (forceLoad) {
        showLoading();
        let promise;
        if (tabName === 'users') promise = loadAdminAllUsers();
        else if (tabName === 'documents') promise = loadAdminAllDocuments();
        else if (tabName === 'activity') promise = loadAdminSystemActivity();
        else promise = Promise.resolve();
        promise.catch(err => showAlert(err.message, 'error')).finally(hideLoading);
    }
}

async function loadAdminAllUsers() {
    const users = await apiCall('/admin/users');
    renderAdminUserList(users || []);
}

function renderAdminUserList(users) {
    const container = elements.adminUsersList;
    container.innerHTML = '';
    if (!users || users.length === 0) {
        return renderEmptyState(container, 'Tidak ada pengguna terdaftar.');
    }
    users.forEach(user => {
        const item = document.createElement('div');
        item.className = 'admin-item';
        item.innerHTML = `
            <div class="admin-item-info">
                <strong>${sanitizeText(user.username)}</strong>
                <span class="item-email">${sanitizeText(user.email)}</span>
                <small class="item-meta">Dibuat: ${formatDate(user.created_at)}</small>
            </div>
            <div class="admin-item-actions">
                <span class="role-badge">${sanitizeText(user.role)}</span>
                ${user.username !== currentUser.username ? `<button class="btn btn-danger btn-small action-delete-user" data-username="${sanitizeText(user.username)}">Hapus</button>` : ''}
            </div>
        `;
        container.appendChild(item);
    });
}

async function loadAdminAllDocuments() {
    const data = await apiCall('/admin/documents');
    renderDocumentList(data || [], elements.adminDocumentsList, false);
}

async function loadAdminSystemActivity() {
    const data = await apiCall('/admin/activity');
    renderAdminActivityList(data.activity || []);
}

function renderAdminActivityList(activities) {
    const container = elements.adminActivityList;
    container.innerHTML = '';
    if (!activities || activities.length === 0) {
        return renderEmptyState(container, 'Tidak ada aktivitas terbaru.');
    }
    activities.forEach(item => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'admin-item';
        const docIds = JSON.parse(item.document_ids || '[]');
        itemDiv.innerHTML = `
           <div class="admin-item-info">
                <strong>${sanitizeText(item.username)}:</strong> ${sanitizeText(item.message)}
                <div class="item-email">Jawaban: ${sanitizeText(item.response)}</div>
                <div class="item-meta">
                    <span>Dok. ID: ${docIds.join(', ') || 'N/A'}</span> | 
                    <span>${formatDate(item.timestamp)}</span>
                </div>
            </div>
        `;
        container.appendChild(itemDiv);
    });
}

async function handleDeleteUser(username) {
    showModal(
        'Hapus Pengguna',
        `Anda yakin ingin menghapus pengguna '${username}'? Semua data milik pengguna ini akan dihapus secara permanen.`,
        async () => {
            showLoading();
            try {
                await apiCall(`/admin/users/${username}`, { method: 'DELETE' });
                showAlert(`Pengguna '${username}' berhasil dihapus.`, 'success');
                await loadAdminAllUsers(); 
                await loadAdminDashboardData(); 
            } catch (error) {
                showAlert(`Gagal menghapus pengguna: ${error.message}`, 'error');
            } finally {
                hideLoading();
            }
        }
    );
}

async function handleDeleteDocument(docId, filename) {
    showModal(
        'Hapus Dokumen',
        `Anda yakin ingin menghapus dokumen '${filename}'?`,
        async () => {
            showLoading();
            try {
                await apiCall(`/admin/documents/${docId}`, { method: 'DELETE' });
                showAlert(`Dokumen '${filename}' berhasil dihapus.`, 'success');
                await loadAdminAllDocuments(); 
                await loadAdminDashboardData(); 
            } catch (error) {
                showAlert(`Gagal menghapus dokumen: ${error.message}`, 'error');
            } finally {
                hideLoading();
            }
        }
    );
}

// --- EVENT LISTENERS & INITIALIZATION ---
function initializeEventListeners() {
    elements.showRegisterLink?.addEventListener('click', (e) => { e.preventDefault(); showRegisterForm(); });
    elements.showLoginLink?.addEventListener('click', (e) => { e.preventDefault(); showLoginForm(); });
    elements.loginFormElement?.addEventListener('submit', (e) => { e.preventDefault(); login(e.target.username.value, e.target.password.value); });
    elements.registerFormElement?.addEventListener('submit', (e) => { e.preventDefault(); register(e.target.username.value, e.target.email.value, e.target.password.value); });
    elements.logoutBtn?.addEventListener('click', logout);

    Object.entries(elements.navLinks).forEach(([name, link]) => {
        link?.addEventListener('click', (e) => { e.preventDefault(); if (!link.classList.contains('active')) navigateToSection(name); });
    });

    elements.uploadArea?.addEventListener('click', () => elements.fileInput?.click());
    elements.uploadArea?.addEventListener('dragover', (e) => { e.preventDefault(); e.stopPropagation(); e.currentTarget.classList.add('dragover'); });
    elements.uploadArea?.addEventListener('dragleave', (e) => { e.preventDefault(); e.stopPropagation(); e.currentTarget.classList.remove('dragover'); });
    elements.uploadArea?.addEventListener('drop', (e) => { e.preventDefault(); e.stopPropagation(); e.currentTarget.classList.remove('dragover'); handleFileSelection(e.dataTransfer.files); });
    elements.fileInput?.addEventListener('change', (e) => handleFileSelection(e.target.files));
    elements.uploadForm?.addEventListener('submit', (e) => { e.preventDefault(); performUploadDocuments(); });
    elements.fileListDisplay?.addEventListener('click', (e) => { if (e.target.classList.contains('file-remove')) removeFileFromSelection(parseInt(e.target.dataset.index, 10)); });

    elements.documentsContainer?.addEventListener('click', (e) => {
        const chatButton = e.target.closest('.action-chat');
        if (chatButton) {
            navigateToSection('chat');
            setTimeout(() => {
                const checkbox = document.querySelector(`.doc-select-checkbox[data-doc-id="${chatButton.dataset.docId}"]`);
                if (checkbox) {
                    checkbox.checked = true;
                    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }, 100);
        }
    });

    elements.chatForm?.addEventListener('submit', (e) => { e.preventDefault(); submitChatMessage(); });
    
    elements.faqContainer?.addEventListener('click', (e) => {
        const qButton = e.target.closest('.faq-question');
        if (qButton) {
            const isActive = qButton.classList.toggle('active');
            qButton.nextElementSibling.style.maxHeight = isActive ? qButton.nextElementSibling.scrollHeight + "px" : null;
        }
    });

    elements.adminTabsContainer?.addEventListener('click', (e) => {
        const tabButton = e.target.closest('.admin-tab-btn');
        if (tabButton && !tabButton.classList.contains('active')) {
            switchAdminTab(tabButton.dataset.tab, true);
        }
    });
    
    elements.adminUsersList?.addEventListener('click', (e) => {
        const deleteBtn = e.target.closest('.action-delete-user');
        if (deleteBtn) {
            handleDeleteUser(deleteBtn.dataset.username);
        }
    });
    
    elements.adminDocumentsList?.addEventListener('click', (e) => {
        const deleteBtn = e.target.closest('.action-delete-doc');
        if (deleteBtn) {
            handleDeleteDocument(deleteBtn.dataset.docId, deleteBtn.dataset.filename);
        }
    });

    elements.confirmationModal.confirmBtn?.addEventListener('click', () => { if (typeof confirmCallback === 'function') confirmCallback(); closeModal(); });
    elements.confirmationModal.cancelBtn?.addEventListener('click', closeModal);
}

async function initializeApp() {
    console.log("Initializing application v7.0.2...");
    initializeEventListeners();

    // Inisialisasi Google Sign-In
    window.onload = function () {
      try {
        if (typeof google === 'undefined') {
            console.error("Pustaka Google GSI tidak termuat.");
            return;
        }
        google.accounts.id.initialize({
            client_id: GOOGLE_CLIENT_ID, 
            callback: handleCredentialResponse
        });
        google.accounts.id.renderButton(
            document.getElementById("google-btn-container"),
            { theme: "outline", size: "large", type: "standard", text: "signin_with", shape: "rectangular" } 
        );
      } catch (e) {
        console.error("Inisialisasi Google Sign-In gagal:", e);
        const googleBtnContainer = document.getElementById("google-btn-container");
        if(googleBtnContainer) googleBtnContainer.innerHTML = '<p style="color:red;font-size:0.8rem;">Gagal memuat Login Google.</p>';
      }
    };

    // Alur pengecekan token yang sudah ada
    showLoading();
    try {
        const storedToken = localStorage.getItem('token');
        if (storedToken) {
            currentToken = storedToken;
            await loadUserProfile();
        }
        if (currentUser) {
            showDashboard();
        } else {
            showAuthSection();
        }
    } catch (error) {
        console.error("Initialization failed:", error);
        localStorage.removeItem('token');
        showAuthSection();
        showAlert("Sesi Anda tidak valid atau telah berakhir. Silakan login kembali.", "error");
    } finally {
        hideLoading();
    }
}

document.addEventListener('DOMContentLoaded', initializeApp);
