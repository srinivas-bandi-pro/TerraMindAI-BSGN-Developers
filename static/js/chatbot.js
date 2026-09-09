/* LLM chat client: keeps the user's conversation context in browser storage. */
(function () {
  'use strict';
  var STORAGE_KEY = 'terramind-chat-v2';
  function now() { return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
  function loadState() { try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || { messages: [], memory: {} }; } catch (_) { return { messages: [], memory: {} }; } }
  document.addEventListener('DOMContentLoaded', function () {
    var root = document.querySelector('[data-chatbot]'); if (!root) return;
    var panel = root.querySelector('.tm-chat__panel'), input = root.querySelector('[data-chat-input]'), messages = root.querySelector('[data-chat-messages]'), language = root.querySelector('[data-chat-language]'), speak = false, state = loadState();
    function save() { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
    function add(text, who, stamp, recommendation) {
      var item = document.createElement('article'); item.className = 'tm-chat__message tm-chat__message--' + who;
      item.innerHTML = (who === 'bot' ? '<span class="tm-chat__mini-avatar">🌱</span>' : '') + '<div class="tm-chat__bubble"><p></p><time></time></div>';
      item.querySelector('p').textContent = text;
      if (recommendation) { var result = document.createElement('strong'); result.className = 'tm-chat__recommendation'; result.textContent = '🌾 ML recommendation: ' + recommendation.crop + ' (' + recommendation.confidence + '% confidence)'; item.querySelector('.tm-chat__bubble').appendChild(result); }
      item.querySelector('time').textContent = stamp || now(); messages.appendChild(item); messages.scrollTop = messages.scrollHeight;
      if (who === 'bot' && speak && window.speechSynthesis) { var utterance = new SpeechSynthesisUtterance(text); utterance.lang = language.value === 'te' ? 'te-IN' : language.value === 'hi' ? 'hi-IN' : 'en-IN'; window.speechSynthesis.cancel(); window.speechSynthesis.speak(utterance); }
    }
    function restore() { state.messages.forEach(function (item) { add(item.content, item.role === 'assistant' ? 'bot' : 'user', item.time, item.recommendation); }); }
    function remember(role, content, recommendation) { state.messages.push({ role: role, content: content, time: now(), recommendation: recommendation }); state.messages = state.messages.slice(-12); save(); }
    function welcome() { send('Hello', true); }
    function toggle() { var open = panel.hidden; panel.hidden = !open; root.querySelector('.tm-chat__launcher').setAttribute('aria-expanded', String(open)); if (open) { input.focus(); if (!state.messages.length) welcome(); } }
    root.querySelectorAll('[data-chat-toggle]').forEach(function (button) { button.addEventListener('click', toggle); });
    function send(text, silent) {
      text = text.trim(); if (!text) return;
      var history = state.messages.map(function (item) { return { role: item.role, content: item.content }; });
      if (!silent) { add(text, 'user'); remember('user', text); }
      input.value = '';
      var typing = document.createElement('div'); typing.className = 'tm-chat__message tm-chat__message--bot'; typing.innerHTML = '<span class="tm-chat__mini-avatar">🌱</span><div class="tm-chat__bubble">Thinking…</div>'; messages.appendChild(typing); messages.scrollTop = messages.scrollHeight;
      fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, history: history, memory: state.memory }) })
        .then(function (response) { return response.json().then(function (data) { if (!response.ok) throw new Error(data.error && data.error.message || 'Unable to reach the AI assistant.'); return data; }); })
        .then(function (data) { typing.remove(); state.memory = data.memory || state.memory; add(data.reply, 'bot', null, data.recommendation); remember('assistant', data.reply, data.recommendation); })
        .catch(function (error) { typing.remove(); add(error.message || 'Unable to reach the AI assistant. Please try again.', 'bot'); });
    }
    restore();
    root.querySelector('[data-chat-form]').addEventListener('submit', function (event) { event.preventDefault(); send(input.value); });
    root.querySelector('[data-chat-speak]').addEventListener('click', function (event) { speak = !speak; event.currentTarget.setAttribute('aria-pressed', String(speak)); event.currentTarget.setAttribute('aria-label', speak ? 'Disable voice output' : 'Enable voice output'); event.currentTarget.textContent = speak ? '🔊' : '🔈'; });
    root.querySelectorAll('[data-chat-suggestions] button').forEach(function (button) { button.addEventListener('click', function () { send(button.textContent); }); });
    root.querySelector('[data-chat-voice]').addEventListener('click', function () { var Recognition = window.SpeechRecognition || window.webkitSpeechRecognition; if (!Recognition) { add('Voice input is not supported by this browser. Please type your question.', 'bot'); return; } var recognition = new Recognition(); recognition.lang = language.value === 'te' ? 'te-IN' : language.value === 'hi' ? 'hi-IN' : 'en-IN'; recognition.onresult = function (event) { input.value = event.results[0][0].transcript; }; recognition.start(); });
  });
}());
