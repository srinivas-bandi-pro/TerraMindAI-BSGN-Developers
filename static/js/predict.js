(function () {
  const fieldAliases = { N: 'nitrogen', P: 'phosphorus', K: 'potassium' };

  function fieldId(name) { return fieldAliases[name] || name; }

  function messageFor(input) {
    const label = document.querySelector('label[for="' + input.id + '"]')?.textContent.replace('*', '').trim() || input.name;
    if (input.value.trim() === '') return label + ' is required.';
    if (!Number.isFinite(Number(input.value))) return label + ' must be a number.';
    if (input.min !== '' && Number(input.value) < Number(input.min)) return label + ' must be at least ' + input.min + '.';
    if (input.max !== '' && Number(input.value) > Number(input.max)) return label + ' must be no more than ' + input.max + '.';
    return '';
  }

  function setFieldError(input, message) {
    const error = document.getElementById(input.id + '-error');
    input.setAttribute('aria-invalid', message ? 'true' : 'false');
    if (error) error.textContent = message || '';
  }

  function showFormAlert(message) {
    const alert = document.querySelector('[data-form-alert]');
    if (!alert) return;
    alert.textContent = message;
    alert.classList.remove('hidden');
  }

  function clearFormAlert() {
    const alert = document.querySelector('[data-form-alert]');
    if (!alert) return;
    alert.textContent = '';
    alert.classList.add('hidden');
  }

  function setLoading(isLoading) {
    const button = document.querySelector('[data-submit]');
    const text = document.querySelector('[data-submit-text]');
    const spinner = document.querySelector('[data-submit-spinner]');
    if (!button) return;
    button.disabled = isLoading;
    text.textContent = isLoading ? 'Analyzing field data…' : 'Predict crop';
    spinner.classList.toggle('hidden', !isLoading);
  }

  function formatTimestamp(timestamp) {
    if (!timestamp) return '—';
    const date = new Date(timestamp);
    return Number.isNaN(date.getTime()) ? timestamp : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
  }

  function showResult(data) {
    const card = document.querySelector('[data-result-card]');
    const placeholder = document.querySelector('[data-result-placeholder]');
    const confidence = Math.max(0, Math.min(100, Number(data.confidence) || 0));
    document.querySelector('[data-result-crop]').textContent = data.prediction || '—';
    document.querySelector('[data-result-confidence]').textContent = confidence.toFixed(1) + '%';
    document.querySelector('[data-confidence-bar]').style.width = confidence + '%';
    document.querySelector('[data-result-version]').textContent = data.model_version || '—';
    document.querySelector('[data-result-time]').textContent = formatTimestamp(data.prediction_timestamp);
    const list = document.querySelector('[data-recommendations]');
    list.replaceChildren();
    (data.alternative_predictions || []).slice(0, 3).forEach(function (recommendation) {
      const item = document.createElement('li');
      const crop = document.createElement('span');
      const score = document.createElement('strong');
      crop.textContent = recommendation.crop || 'Unknown';
      score.textContent = (Number(recommendation.confidence) || 0).toFixed(1) + '%';
      item.append(crop, score);
      list.appendChild(item);
    });
    if (!list.children.length) list.innerHTML = '<li><span>No alternatives available</span><strong>—</strong></li>';
    const aiBtn = document.querySelector('[data-ask-ai-crop]');
    if (aiBtn) {
      const crop = data.prediction || 'this crop';
      aiBtn.textContent = '🌱 Ask AI Assistant about ' + crop;
      aiBtn.onclick = function () {
        const chatPanel = document.querySelector('.tm-chat__panel');
        const chatInput = document.querySelector('[data-chat-input]');
        const chatLauncher = document.querySelector('.tm-chat__launcher');
        if (chatPanel && chatInput) {
          if (chatPanel.hidden) {
            chatPanel.hidden = false;
            if (chatLauncher) chatLauncher.setAttribute('aria-expanded', 'true');
          }
          chatInput.value = 'How can I best cultivate ' + crop + '? Please give fertilizer, irrigation, and pest advice.';
          chatInput.focus();
        }
      };
    }
    placeholder.classList.add('hidden');
    card.classList.remove('hidden');
    card.focus({ preventScroll: true });
  }

  function applyServerFieldErrors(fields, form) {
    Object.entries(fields || {}).forEach(function ([name, message]) {
      const input = form.elements[name] || document.getElementById(fieldId(name));
      if (input) setFieldError(input, Array.isArray(message) ? message.join(' ') : message);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('prediction-form');
    if (!form) return;
    const inputs = Array.from(form.querySelectorAll('input'));
    inputs.forEach(function (input) {
      input.addEventListener('input', function () { setFieldError(input, messageFor(input)); });
      input.addEventListener('blur', function () { setFieldError(input, messageFor(input)); });
    });
    form.addEventListener('reset', function () {
      window.setTimeout(function () {
        inputs.forEach(function (input) { setFieldError(input, ''); });
        clearFormAlert();
        document.querySelector('[data-result-card]')?.classList.add('hidden');
        document.querySelector('[data-result-placeholder]')?.classList.remove('hidden');
      });
    });
    form.addEventListener('submit', async function (event) {
      event.preventDefault();
      clearFormAlert();
      let valid = true;
      inputs.forEach(function (input) {
        const message = messageFor(input);
        setFieldError(input, message);
        valid = valid && !message;
      });
      if (!valid) {
        showFormAlert('Please correct the highlighted fields and try again.');
        form.querySelector('[aria-invalid="true"]')?.focus();
        return;
      }
      const payload = Object.fromEntries(inputs.map(function (input) { return [input.name, Number(input.value)]; }));
      setLoading(true);
      try {
        const response = await fetch('/api/predict', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }, body: JSON.stringify(payload) });
        let body;
        try { body = await response.json(); } catch (_) { throw new Error('The server returned an unexpected response.'); }
        if (!response.ok || body.success === false) {
          if (response.status === 422) {
            applyServerFieldErrors(body.error?.fields, form);
            showFormAlert(body.error?.message || 'Please review the submitted values and try again.');
          } else if (response.status === 503) {
            showFormAlert('The prediction service is temporarily unavailable. Please try again shortly.');
          } else {
            showFormAlert(body.error?.message || 'We could not complete your prediction. Please try again.');
          }
          return;
        }
        sessionStorage.setItem('agrismart-last-prediction', JSON.stringify({ response: body, inputs: payload, savedAt: Date.now() }));
        showResult(body);
        window.AgriSmartToast?.show('Your crop recommendation is ready.', 'success', 'Prediction complete');
      } catch (error) {
        showFormAlert(error instanceof TypeError ? 'Network connection unavailable. Check your connection and try again.' : error.message || 'Something went wrong while contacting the prediction service.');
      } finally {
        setLoading(false);
      }
    });
  });
}());
