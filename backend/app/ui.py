"""Embedded web interface for Document Management and RAG-based Q&A Application."""

UI_HTML = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>Document Management &amp; RAG Q&amp;A</title>
  <style>
    :root {
      --primary: #2563eb;
      --primary-hover: #1d4ed8;
      --bg: #0f172a;
      --surface: #1e293b;
      --surface-border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #10b981;
      --danger: #ef4444;
      --radius: 10px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    body { background-color: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }
    header { background-color: var(--surface); border-bottom: 1px solid var(--surface-border); padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
    header h1 { font-size: 1.25rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem; }
    .badge { background-color: rgba(16, 185, 129, 0.2); color: var(--accent); padding: 0.2rem 0.6rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
    .nav-links { display: flex; gap: 1rem; align-items: center; }
    .nav-links a { color: var(--text-muted); text-decoration: none; font-size: 0.9rem; }
    .nav-links a:hover { color: var(--text); }
    main { flex: 1; max-width: 1200px; width: 100%; margin: 0 auto; padding: 2rem 1rem; display: grid; grid-template-columns: 350px 1fr; gap: 1.5rem; }
    @media (max-width: 850px) { main { grid-template-columns: 1fr; } }
    .card { background-color: var(--surface); border: 1px solid var(--surface-border); border-radius: var(--radius); padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }
    .card-title { font-size: 1.1rem; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
    input, button { border-radius: 6px; font-size: 0.95rem; }
    input[type=\"email\"], input[type=\"password\"], input[type=\"text\"], input[type=\"file\"] {
      width: 100%; background: #0f172a; border: 1px solid var(--surface-border); color: var(--text); padding: 0.6rem 0.8rem; outline: none;
    }
    input:focus { border-color: var(--primary); }
    button { cursor: pointer; border: none; padding: 0.6rem 1rem; font-weight: 600; transition: 0.2s; }
    .btn-primary { background-color: var(--primary); color: white; }
    .btn-primary:hover { background-color: var(--primary-hover); }
    .btn-danger { background-color: var(--danger); color: white; }
    .btn-secondary { background-color: var(--surface-border); color: var(--text); }
    .btn-secondary:hover { background-color: #475569; }
    .auth-toggle { font-size: 0.85rem; color: var(--text-muted); cursor: pointer; text-decoration: underline; }
    .doc-list { list-style: none; display: flex; flex-direction: column; gap: 0.5rem; max-height: 250px; overflow-y: auto; }
    .doc-item { background: #0f172a; border: 1px solid var(--surface-border); border-radius: 6px; padding: 0.6rem; display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; }
    .doc-title { font-weight: 500; word-break: break-all; }
    .chat-box { flex: 1; display: flex; flex-direction: column; min-height: 500px; max-height: 70vh; }
    .chat-messages { flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: 1rem; background: #0f172a; border: 1px solid var(--surface-border); border-radius: 8px; }
    .message { max-width: 85%; padding: 0.8rem 1rem; border-radius: 8px; line-height: 1.4; font-size: 0.95rem; white-space: pre-wrap; }
    .message.user { align-self: flex-end; background-color: var(--primary); color: white; border-bottom-right-radius: 2px; }
    .message.assistant { align-self: flex-start; background-color: #1e293b; border: 1px solid var(--surface-border); color: var(--text); border-bottom-left-radius: 2px; }
    .chat-input-bar { display: flex; gap: 0.5rem; margin-top: 1rem; }
    .chat-input-bar input { flex: 1; }
    .alert { padding: 0.6rem 0.8rem; border-radius: 6px; font-size: 0.85rem; display: none; }
    .alert-error { background-color: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid var(--danger); }
    .alert-success { background-color: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid var(--accent); }
  </style>
</head>
<body>
  <header>
    <h1><span>📄</span> Document RAG Q&amp;A <span class=\"badge\">Live 🟢</span></h1>
    <div class=\"nav-links\">
      <a href=\"/docs\" target=\"_blank\">Swagger API Docs ↗</a>
      <a href=\"/redoc\" target=\"_blank\">ReDoc ↗</a>
      <span id=\"user-display\" style=\"font-weight:600; color: var(--accent);\">Not Logged In</span>
      <button id=\"logout-btn\" class=\"btn-secondary\" style=\"display:none; padding: 0.3rem 0.6rem; font-size: 0.8rem;\">Logout</button>
    </div>
  </header>

  <main>
    <div style=\"display:flex; flex-direction:column; gap:1.5rem;\">
      <div class=\"card\" id=\"auth-card\">
        <div class=\"card-title\">
          <span id=\"auth-title\">Login</span>
          <span class=\"auth-toggle\" id=\"auth-toggle\" onclick=\"toggleAuthMode()\">Need an account? Register</span>
        </div>
        <div id=\"auth-alert\" class=\"alert alert-error\"></div>
        <input type=\"email\" id=\"auth-email\" placeholder=\"Email (e.g. user@example.com)\" value=\"user@example.com\" />
        <input type=\"password\" id=\"auth-password\" placeholder=\"Password (min 8 chars)\" value=\"Password123!\" />
        <button class=\"btn-primary\" id=\"auth-submit\" onclick=\"handleAuth()\">Login</button>
      </div>

      <div class=\"card\" id=\"doc-card\" style=\"display:none;\">
        <div class=\"card-title\">Upload Documents</div>
        <div id=\"upload-alert\" class=\"alert\"></div>
        <input type=\"file\" id=\"pdf-file-input\" accept=\"application/pdf\" />
        <button class=\"btn-primary\" onclick=\"handleUpload()\">Upload &amp; Index PDF</button>

        <div style=\"border-top:1px solid var(--surface-border); padding-top:0.8rem; margin-top:0.4rem;\">
          <div style=\"font-size:0.85rem; font-weight:600; margin-bottom:0.5rem; display:flex; justify-content:space-between;\">
            <span>Your Documents</span>
            <span style=\"cursor:pointer; color:var(--primary);\" onclick=\"loadDocuments()\">↻ Refresh</span>
          </div>
          <ul class=\"doc-list\" id=\"doc-list-container\">
            <li style=\"color:var(--text-muted); font-size:0.85rem;\">No documents uploaded yet.</li>
          </ul>
        </div>
      </div>
    </div>

    <div class=\"card chat-box\">
      <div class=\"card-title\">
        <span>💬 RAG Q&amp;A Assistant</span>
        <button class=\"btn-secondary\" style=\"font-size:0.8rem; padding:0.3rem 0.6rem;\" onclick=\"clearChat()\">Clear History</button>
      </div>
      <div class=\"chat-messages\" id=\"chat-messages\">
        <div class=\"message assistant\">
          Hello! Log in or register on the left, upload a PDF document, and ask questions here. I will search the document and generate answers with citations.
        </div>
      </div>
      <div class=\"chat-input-bar\">
        <input type=\"text\" id=\"chat-input\" placeholder=\"Ask a question about your uploaded documents...\" onkeydown=\"if(event.key==='Enter') sendQuestion()\" />
        <button class=\"btn-primary\" id=\"send-btn\" onclick=\"sendQuestion()\">Send</button>
      </div>
    </div>
  </main>

  <script>
    let isRegisterMode = false;
    let token = localStorage.getItem('rag_token') || null;

    function toggleAuthMode() {
      isRegisterMode = !isRegisterMode;
      document.getElementById('auth-title').innerText = isRegisterMode ? 'Register New Account' : 'Login';
      document.getElementById('auth-submit').innerText = isRegisterMode ? 'Create Account' : 'Login';
      document.getElementById('auth-toggle').innerText = isRegisterMode ? 'Already have an account? Login' : 'Need an account? Register';
      hideAlert('auth-alert');
    }

    function showAlert(id, text, isSuccess=false) {
      const el = document.getElementById(id);
      el.className = 'alert ' + (isSuccess ? 'alert-success' : 'alert-error');
      el.innerText = text;
      el.style.display = 'block';
    }

    function hideAlert(id) {
      document.getElementById(id).style.display = 'none';
    }

    async function handleAuth() {
      const email = document.getElementById('auth-email').value.trim();
      const password = document.getElementById('auth-password').value;
      if (!email || !password) { showAlert('auth-alert', 'Please enter email and password.'); return; }

      const endpoint = isRegisterMode ? '/api/v1/register' : '/api/v1/login';
      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) {
          const errMsg = typeof data.detail === 'string' ? data.detail : (Array.isArray(data.detail) ? data.detail.map(d => d.msg).join(', ') : 'Authentication failed.');
          showAlert('auth-alert', errMsg);
          return;
        }

        if (isRegisterMode) {
          showAlert('auth-alert', 'Account created! Logging in...', true);
          const loginRes = await fetch('/api/v1/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
          });
          const loginData = await loginRes.json();
          if (loginRes.ok) {
            token = loginData.access_token;
            localStorage.setItem('rag_token', token);
            initAuthenticatedUI(email);
            return;
          }
        }

        token = data.access_token;
        localStorage.setItem('rag_token', token);
        initAuthenticatedUI(email);
      } catch (err) {
        showAlert('auth-alert', 'Error connecting to server: ' + err.message);
      }
    }

    function initAuthenticatedUI(email) {
      document.getElementById('auth-card').style.display = 'none';
      document.getElementById('doc-card').style.display = 'flex';
      document.getElementById('user-display').innerText = '👤 ' + (email || 'Logged In');
      document.getElementById('logout-btn').style.display = 'inline-block';
      loadDocuments();
    }

    document.getElementById('logout-btn').onclick = () => {
      localStorage.removeItem('rag_token');
      token = null;
      document.getElementById('auth-card').style.display = 'flex';
      document.getElementById('doc-card').style.display = 'none';
      document.getElementById('user-display').innerText = 'Not Logged In';
      document.getElementById('logout-btn').style.display = 'none';
    };

    async function checkExistingAuth() {
      if (!token) return;
      try {
        const res = await fetch('/api/v1/me', { headers: { 'Authorization': 'Bearer ' + token } });
        if (res.ok) {
          const user = await res.json();
          initAuthenticatedUI(user.email);
        } else {
          localStorage.removeItem('rag_token');
          token = null;
        }
      } catch (e) {}
    }

    async function loadDocuments() {
      if (!token) return;
      try {
        const res = await fetch('/api/v1/documents/', { headers: { 'Authorization': 'Bearer ' + token } });
        if (res.ok) {
          const data = await res.json();
          const docs = Array.isArray(data) ? data : (data.documents || []);
          const list = document.getElementById('doc-list-container');
          list.innerHTML = '';
          if (!docs || docs.length === 0) {
            list.innerHTML = '<li style="color:var(--text-muted); font-size:0.85rem;">No documents uploaded yet.</li>';
            return;
          }
          docs.forEach(doc => {
            const li = document.createElement('li');
            li.className = 'doc-item';
            const displayName = doc.title || doc.original_filename || 'Untitled Document';
            const pageInfo = doc.page_count ? ` | ${doc.page_count} pages` : '';
            li.innerHTML = `
              <div style="display:flex; align-items:center; gap:0.6rem; flex:1; min-width:0;">
                <input type="checkbox" class="doc-select-checkbox" value="${doc.id}" checked title="Select for Q&A" />
                <div style="overflow:hidden; text-overflow:ellipsis;">
                  <div class="doc-title" title="${displayName}">${displayName}</div>
                  <div style="color:var(--text-muted); font-size:0.75rem;">Status: ${doc.status}${pageInfo}</div>
                </div>
              </div>
              <button class="btn-danger" style="padding:0.2rem 0.5rem; font-size:0.75rem; margin-left:0.5rem;" onclick="deleteDocument('${doc.id}')" title="Delete document">✕</button>
            `;
            list.appendChild(li);
          });
        }
      } catch (err) {
        console.error('Failed to load documents:', err);
      }
    }

    async function handleUpload() {
      if (!token) { alert('Please log in first.'); return; }
      const input = document.getElementById('pdf-file-input');
      if (!input.files || input.files.length === 0) {
        showAlert('upload-alert', 'Please select a PDF file.');
        return;
      }
      const file = input.files[0];
      const formData = new FormData();
      formData.append('file', file);

      showAlert('upload-alert', 'Uploading and indexing...', true);
      try {
        const res = await fetch('/api/v1/documents/upload', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + token },
          body: formData
        });
        const data = await res.json();
        if (res.ok) {
          showAlert('upload-alert', `Uploaded \"${data.title || file.name}\". Background indexing started!`, true);
          input.value = '';
          setTimeout(loadDocuments, 1000);
        } else {
          showAlert('upload-alert', data.detail || 'Upload failed.');
        }
      } catch (err) {
        showAlert('upload-alert', 'Network error: ' + err.message);
      }
    }

    async function deleteDocument(docId) {
      if (!confirm('Are you sure you want to delete this document?')) return;
      try {
        const res = await fetch(`/api/v1/documents/${docId}`, {
          method: 'DELETE',
          headers: { 'Authorization': 'Bearer ' + token }
        });
        if (res.ok) loadDocuments();
      } catch (e) {
        alert('Failed to delete document.');
      }
    }

    async function sendQuestion() {
      const input = document.getElementById('chat-input');
      const query = input.value.trim();
      if (!query) return;
      if (!token) { alert('Please log in first on the left panel.'); return; }

      input.value = '';
      const chatMessages = document.getElementById('chat-messages');

      const userMsg = document.createElement('div');
      userMsg.className = 'message user';
      userMsg.innerText = query;
      chatMessages.appendChild(userMsg);

      const botMsg = document.createElement('div');
      botMsg.className = 'message assistant';
      botMsg.innerHTML = '<span style=\"color:var(--text-muted);\">Searching document embeddings and generating answer...</span>';
      chatMessages.appendChild(botMsg);
      chatMessages.scrollTop = chatMessages.scrollHeight;

      const checkedBoxes = Array.from(document.querySelectorAll('.doc-select-checkbox:checked'));
      const totalBoxes = document.querySelectorAll('.doc-select-checkbox');
      let document_ids = null;
      if (checkedBoxes.length > 0 && checkedBoxes.length < totalBoxes.length) {
        document_ids = checkedBoxes.map(cb => cb.value);
      }

      try {
        const res = await fetch('/api/v1/chat/stream', {
          method: 'POST',
          headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ question: query, query: query, document_ids })
        });

        if (!res.ok) {
          botMsg.innerText = 'Error from server: ' + res.statusText;
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let fullAnswer = '';
        botMsg.innerText = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const text = decoder.decode(value);
          const lines = text.split('\\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const payload = line.slice(6).trim();
              if (payload === '[DONE]') break;
              try {
                const parsed = JSON.parse(payload);
                if (parsed.chunk) {
                  fullAnswer += parsed.chunk;
                  botMsg.innerText = fullAnswer;
                  chatMessages.scrollTop = chatMessages.scrollHeight;
                }
              } catch (e) {}
            }
          }
        }
        if (!fullAnswer) {
          botMsg.innerText = 'No answer generated. Ensure a document has been uploaded and indexed.';
        }
      } catch (err) {
        botMsg.innerText = 'Failed to connect: ' + err.message;
      }
    }

    async function clearChat() {
      if (!token) return;
      if (!confirm('Clear chat history?')) return;
      try {
        await fetch('/api/v1/chat/history', { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + token } });
        document.getElementById('chat-messages').innerHTML = `
          <div class=\"message assistant\">
            Chat history cleared. What would you like to ask?
          </div>
        `;
      } catch (e) {}
    }

    checkExistingAuth();
  </script>
</body>
</html>
"""
