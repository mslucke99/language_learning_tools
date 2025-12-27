/**
 * Simplified Popup Script
 * Just checks API status and shows basic information
 */

const API_URL = 'http://localhost:5000/api';

document.addEventListener('DOMContentLoaded', () => {
  checkApiStatus();
  // Check status every 10 seconds
  setInterval(checkApiStatus, 10000);
});

// Check API status
async function checkApiStatus() {
  try {
    const response = await fetch(`${API_URL}/health`);
    const data = await response.json();

    const statusIndicator = document.getElementById('api-status');
    const statusText = document.getElementById('api-status-text');

    if (response.ok && data.status === 'ok') {
      statusIndicator.className = 'status-indicator online';
      statusText.textContent = '✓ API Connected';
    } else {
      statusIndicator.className = 'status-indicator offline';
      statusText.textContent = '✗ API Offline';
    }
  } catch (error) {
    const statusIndicator = document.getElementById('api-status');
    const statusText = document.getElementById('api-status-text');
    statusIndicator.className = 'status-indicator offline';
    statusText.textContent = '✗ API Offline';
  }
}
