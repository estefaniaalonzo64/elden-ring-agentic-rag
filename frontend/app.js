(function () {
  'use strict';

  // Session-only state (PRD §25.4): lives in memory, never persisted to
  // localStorage — a page reload or logout wipes it and returns to Login.
  var state = { token: null, sessionId: null, pending: false };

  function qs(id) { return document.getElementById(id); }

  function showScreen(id) {
    document.querySelectorAll('.screen').forEach(function (el) { el.hidden = true; });
    qs(id).hidden = false;
  }

  function apiFetch(path, options) {
    options = options || {};
    var headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
    if (state.token) headers.Authorization = 'Bearer ' + state.token;

    return fetch(path, Object.assign({}, options, { headers: headers }))
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (data) {
          if (!response.ok) throw new Error(data.detail || 'Request failed (' + response.status + ')');
          return data;
        });
      });
  }

  function resetChat() {
    qs('messages').innerHTML = '';
  }

  function renderMarkdown(text) {
    if (window.marked && window.DOMPurify) {
      return window.DOMPurify.sanitize(window.marked.parse(text, { breaks: true, gfm: true }));
    }
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function appendMessage(role, text, sources) {
    var container = qs('messages');

    var bubble = document.createElement('div');
    bubble.className = 'message ' + role;
    bubble.innerHTML = renderMarkdown(text);
    container.appendChild(bubble);

    if (sources && sources.length) {
      var sourcesEl = document.createElement('div');
      sourcesEl.className = 'sources';
      sourcesEl.textContent = 'Fuentes: ' + sources.map(function (s) {
        return s.entity_type + ' · ' + s.name;
      }).join(', ');
      container.appendChild(sourcesEl);
    }

    container.scrollTop = container.scrollHeight;
  }

  function setPending(pending, thinkingText) {
    state.pending = pending;
    qs('thinking-indicator').textContent = thinkingText || 'Pensando...';
    qs('thinking-indicator').hidden = !pending;
    qs('chat-submit').disabled = pending;
  }

  function formatDate(isoString) {
    try {
      return new Date(isoString).toLocaleString();
    } catch (e) {
      return isoString;
    }
  }

  function loadConversations() {
    apiFetch('/sessions')
      .then(function (data) { renderConversations(data.sessions || []); })
      .catch(function () { renderConversations([]); });
  }

  function renderConversations(sessions) {
    var list = qs('conversations-list');
    list.innerHTML = '';

    if (!sessions.length) {
      var empty = document.createElement('li');
      empty.className = 'conversations-empty';
      empty.textContent = 'Todavía no hay conversaciones.';
      list.appendChild(empty);
      return;
    }

    sessions.forEach(function (session) {
      var item = document.createElement('li');
      item.className = 'conversation-item';
      if (session.session_id === state.sessionId) item.className += ' active';

      var preview = document.createElement('div');
      preview.className = 'conversation-preview';
      preview.textContent = session.preview || '(sin mensajes)';

      var date = document.createElement('div');
      date.className = 'conversation-date';
      date.textContent = formatDate(session.created_at);

      item.appendChild(preview);
      item.appendChild(date);
      item.addEventListener('click', function () { openConversation(session.session_id); });
      list.appendChild(item);
    });
  }

  function openConversation(sessionId) {
    apiFetch('/sessions/' + sessionId + '/messages')
      .then(function (data) {
        state.sessionId = sessionId;
        resetChat();
        (data.messages || []).forEach(function (msg) {
          appendMessage(msg.role, msg.content, msg.sources);
        });
        loadConversations();
      })
      .catch(function (err) { appendMessage('assistant', 'Error: ' + err.message); });
  }

  qs('new-conversation-button').addEventListener('click', function () {
    apiFetch('/sessions', { method: 'POST' })
      .then(function (data) {
        state.sessionId = data.session_id;
        resetChat();
        loadConversations();
      })
      .catch(function (err) { appendMessage('assistant', 'Error: ' + err.message); });
  });

  qs('login-form').addEventListener('submit', function (event) {
    event.preventDefault();
    qs('login-error').textContent = '';

    var username = qs('login-username').value.trim();
    var password = qs('login-password').value;

    apiFetch('/login', {
      method: 'POST',
      body: JSON.stringify({ username: username, password: password })
    })
      .then(function (data) {
        state.token = data.access_token;
        state.sessionId = data.session_id;
        resetChat();
        showScreen('screen-chat');
        loadConversations();
      })
      .catch(function (err) { qs('login-error').textContent = err.message; });
  });

  qs('logout-button').addEventListener('click', function () {
    // §25.4: logout borra token y session_id; el próximo login pide uno nuevo al backend.
    state.token = null;
    state.sessionId = null;
    setPending(false);
    resetChat();
    renderConversations([]);
    qs('login-password').value = '';
    showScreen('screen-login');
  });

  qs('chat-form').addEventListener('submit', function (event) {
    event.preventDefault();
    if (state.pending) return;

    var input = qs('chat-input');
    var message = input.value.trim();
    if (!message) return;

    appendMessage('user', message);
    input.value = '';
    setPending(true, 'Buscando información...');

    apiFetch('/chat', {
      method: 'POST',
      body: JSON.stringify({ session_id: state.sessionId, message: message })
    })
      .then(function (data) {
        appendMessage('assistant', data.message, data.sources);
        loadConversations();
      })
      .catch(function (err) { appendMessage('assistant', 'Error: ' + err.message); })
      .then(function () { setPending(false); });
  });
})();
