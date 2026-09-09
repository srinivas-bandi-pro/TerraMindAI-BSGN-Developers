(function () {
  'use strict';

  var lastFocusedElement = null;

  function getBackdrop() {
    return document.querySelector('[data-modal-backdrop]');
  }

  function closeModal() {
    var backdrop = getBackdrop();
    if (!backdrop || !backdrop.classList.contains('is-open')) return;
    backdrop.classList.remove('is-open');
    backdrop.setAttribute('aria-hidden', 'true');
    if (lastFocusedElement && document.contains(lastFocusedElement)) {
      lastFocusedElement.focus();
    }
  }

  function trapModalFocus(event) {
    var backdrop = getBackdrop();
    if (event.key !== 'Tab' || !backdrop || !backdrop.classList.contains('is-open')) return;
    var focusable = Array.from(backdrop.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'));
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  window.AgriSmartModal = { close: closeModal };

  document.addEventListener('focusin', function (event) {
    var backdrop = getBackdrop();
    if (!backdrop || !backdrop.classList.contains('is-open') && !backdrop.contains(event.target)) {
      lastFocusedElement = event.target;
    }
  });

  document.addEventListener('DOMContentLoaded', function () {
    var backdrop = getBackdrop();
    document.querySelectorAll('[data-modal-close]').forEach(function (button) {
      button.addEventListener('click', closeModal);
    });
    if (backdrop) {
      backdrop.addEventListener('click', function (event) {
        if (event.target === backdrop) closeModal();
      });
    }
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && getBackdrop()?.classList.contains('is-open')) {
        event.preventDefault();
        closeModal();
      } else {
        trapModalFocus(event);
      }
    });
  });
}());
