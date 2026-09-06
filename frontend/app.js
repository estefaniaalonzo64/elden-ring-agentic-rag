(function () {
  'use strict';

  // Session-only state (PRD §25.4): lives in memory, never persisted to
  // localStorage — a page reload or logout wipes it and returns to Login.
  var state = { token: null, sessionId: null };

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
      })
      .catch(function (err) { qs('login-error').textContent = err.message; });
  });

  qs('logout-button').addEventListener('click', function () {
    // §25.4: logout borra token y session_id; el próximo login pide uno nuevo al backend.
    state.token = null;
    state.sessionId = null;
    resetChat();
    qs('login-password').value = '';
    showScreen('screen-login');
  });

  qs('chat-form').addEventListener('submit', function (event) {
    event.preventDefault();

    var input = qs('chat-input');
    var message = input.value.trim();
    if (!message) return;

    appendMessage('user', message);
    input.value = '';

    apiFetch('/chat', {
      method: 'POST',
      body: JSON.stringify({ session_id: state.sessionId, message: message })
    })
      .then(function (data) { appendMessage('assistant', data.message, data.sources); })
      .catch(function (err) { appendMessage('assistant', 'Error: ' + err.message); });
  });
})();
