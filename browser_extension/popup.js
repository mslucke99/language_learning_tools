/**
 * Simplified Popup Script
 * Just checks API status and shows basic information
 */

const API_URL = 'http://localhost:5000/api';

document.addEventListener('DOMContentLoaded', () => {
  checkApiStatus();
  updateQueueCount();

  // Set intervals
  setInterval(checkApiStatus, 10000);
  setInterval(updateQueueCount, 2000);

  // Manual Sync Button
  const syncBtn = document.getElementById('manual-sync-btn');
  if (syncBtn) {
    syncBtn.onclick = () => {
      chrome.runtime.sendMessage({ action: 'exportQueue' }, (response) => {
        if (response && response.success) {
          syncBtn.textContent = '✓ Exported';
          setTimeout(() => { syncBtn.textContent = '💾 Sync to File'; }, 3000);
        }
      });
    };
  }
});

// Check API status
/**
 * Check if the API is online and update status indicator
 * @returns {Promise<void>}
 */
async function checkApiStatus() {
  const statusIndicator = document.getElementById('api-status');
  const statusText = document.getElementById('api-status-text');

  try {
    const response = await fetch(`${API_URL}/health`);
    const data = await response.json();

    if (response.ok && data.status === 'ok') {
      statusIndicator.className = 'status-indicator online';
      statusText.textContent = '✓ API Connected';
    } else {
      statusIndicator.className = 'status-indicator offline';
      statusText.textContent = '✗ API Offline';
    }
  } catch (error) {
    statusIndicator.className = 'status-indicator offline';
    statusText.textContent = '✗ API Offline';
  }
}

// Update Queue Count from background
/**
 * Fetch pending queue count from background script and update UI
 * @returns {void}
 */
function updateQueueCount() {
  chrome.runtime.sendMessage({ action: 'getQueueCount' }, (response) => {
    const countSpan = document.getElementById('queue-count');
    const syncBtn = document.getElementById('manual-sync-btn');

    if (response && response.count > 0) {
      countSpan.textContent = `${response.count} pending`;
      syncBtn.style.display = 'block';
    } else {
      countSpan.textContent = '';
      syncBtn.style.display = 'none';
    }
  });
}
