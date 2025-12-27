/**
 * Content Script - Simple word and sentence importer
 * Detects text selection and offers quick import options
 */

const API_URL = 'http://localhost:5000/api';

// Store selected content
let selectedContent = {
  text: '',
  type: '', // 'word' or 'sentence'
  title: '',
  url: ''
};

// Detect text selection
document.addEventListener('mouseup', function() {
  const selection = window.getSelection();
  const selectedText = selection.toString().trim();

  if (selectedText && selectedText.length > 0) {
    console.log('[Content] Text selected:', selectedText.substring(0, 50));
    selectedContent = {
      text: selectedText,
      type: '', // Will be determined by user choice
      title: document.title || '',
      url: window.location.href
    };

    showImportOptions();
  }
});

// Show import options (Word or Sentence)
function showImportOptions() {
  // Remove existing buttons
  const existing = document.getElementById('import-options-container');
  if (existing) existing.remove();

  const selection = window.getSelection();
  if (!selection.rangeCount) return;

  const range = selection.getRangeAt(0);
  const rect = range.getBoundingClientRect();

  // Create container
  const container = document.createElement('div');
  container.id = 'import-options-container';
  container.style.cssText = `
    position: fixed;
    top: ${rect.bottom + window.scrollY + 10}px;
    left: ${rect.left + window.scrollX}px;
    z-index: 10000;
    display: flex;
    gap: 8px;
    background: white;
    padding: 8px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  `;

  // Word button
  const wordBtn = document.createElement('button');
  wordBtn.textContent = '📝 Add as Word';
  wordBtn.style.cssText = `
    padding: 8px 12px;
    background: #007AFF;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.2s;
  `;
  wordBtn.onmouseover = () => wordBtn.style.background = '#0056CC';
  wordBtn.onmouseout = () => wordBtn.style.background = '#007AFF';
  wordBtn.onclick = () => importAsType('word');

  // Sentence button
  const sentenceBtn = document.createElement('button');
  sentenceBtn.textContent = '💬 Add as Sentence';
  sentenceBtn.style.cssText = `
    padding: 8px 12px;
    background: #34C759;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.2s;
  `;
  sentenceBtn.onmouseover = () => sentenceBtn.style.background = '#30B24D';
  sentenceBtn.onmouseout = () => sentenceBtn.style.background = '#34C759';
  sentenceBtn.onclick = () => importAsType('sentence');

  container.appendChild(wordBtn);
  container.appendChild(sentenceBtn);
  document.body.appendChild(container);

  // Remove buttons after 10 seconds if not clicked
  setTimeout(() => {
    if (container.parentNode) {
      container.style.opacity = '0';
      container.style.transition = 'opacity 0.2s';
      setTimeout(() => container.remove(), 200);
    }
  }, 10000);
}

// Import content as specific type
function importAsType(type) {
  const container = document.getElementById('import-options-container');
  if (container) container.remove();

  selectedContent.type = type;
  
  if (!selectedContent.text) {
    showNotification('No text selected', true);
    return;
  }

  // Send to background script for API call
  console.log('[Content] Sending import:', selectedContent);
  chrome.runtime.sendMessage({
    action: 'importContent',
    content: selectedContent
  }, (response) => {
    console.log('[Content] Response:', response);
    if (response && response.success) {
      showNotification(`✓ Added ${type}: "${selectedContent.text.substring(0, 40)}..."`);
    } else {
      const error = response?.error || 'Unknown error';
      showNotification(`✗ Failed to add ${type}`, true);
    }
  });

  // Clear selection
  window.getSelection().removeAllRanges();
}

// Simple notification system
function showNotification(message, isError = false) {
  const notification = document.createElement('div');
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 16px;
    background-color: ${isError ? '#FF3B30' : '#34C759'};
    color: white;
    border-radius: 8px;
    z-index: 10001;
    font-weight: 500;
    font-size: 13px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    animation: slideIn 0.3s ease-out;
    max-width: 300px;
    word-wrap: break-word;
  `;

  // Add animation
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideIn {
      from {
        transform: translateX(400px);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }
    @keyframes slideOut {
      from {
        transform: translateX(0);
        opacity: 1;
      }
      to {
        transform: translateX(400px);
        opacity: 0;
      }
    }
  `;
  if (!document.querySelector('style[data-notification]')) {
    style.setAttribute('data-notification', 'true');
    document.head.appendChild(style);
  }

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-in';
    setTimeout(() => notification.remove(), 300);
  }, 4000);
}
