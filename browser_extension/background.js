/**
 * Background Service Worker
 * Handles context menu and API communication for importing words/sentences
 */

const API_URL = 'http://localhost:5000/api';

// Initialize storage with defaults and setup alarms
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'import-word',
    title: 'Add "%s" as Word',
    contexts: ['selection']
  });

  chrome.contextMenus.create({
    id: 'import-sentence',
    title: 'Add "%s" as Sentence',
    contexts: ['selection']
  });

  // Initialize storage
  chrome.storage.local.get(['apiUrl', 'pendingQueue'], (result) => {
    if (!result.apiUrl) {
      chrome.storage.local.set({ apiUrl: API_URL });
    }
    if (!result.pendingQueue) {
      chrome.storage.local.set({ pendingQueue: [] });
    }
  });

  // Setup periodic sync attempt and health check
  chrome.alarms.create('sync-check', { periodInMinutes: 2 });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  const selectedText = info.selectionText.trim();
  console.log('[BG] Context menu:', info.menuItemId, 'Text length:', selectedText.length);

  if (!selectedText) return;

  let contentType = 'word';
  if (info.menuItemId === 'import-sentence') {
    contentType = 'sentence';
  }

  importContent(selectedText, contentType, tab);
});

/**
 * Import content to the API
 * @param {string} text - The content text to import
 * @param {string} type - Type of content: 'word' or 'sentence'
 * @param {chrome.tabs.Tab} tab - The current tab with URL and title
 * @returns {void}
 */
function importContent(text, type, tab) {
  console.log('[BG] Importing: type=' + type + ', length=' + text.length);

  const payload = {
    content_type: type,
    content: text,
    url: tab.url,
    title: tab.title || '',
    timestamp: new Date().toISOString()
  };

  fetch(`${API_URL}/health`)
    .then(response => {
      if (!response.ok) throw new Error('API not available');
      return fetch(`${API_URL}/imported`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        chrome.tabs.sendMessage(tab.id, {
          action: 'showNotification',
          message: `✓ Added ${type} successfully`,
          error: false
        }).catch(() => { });
        // If we just succeeded, try to sync the rest of the queue
        syncQueue();
      } else {
        throw new Error(data.error || 'Unknown error');
      }
    })
    .catch(error => {
      console.log('[BG] API offline or error, adding to local queue:', error.message);
      addToQueue(payload);

      chrome.tabs.sendMessage(tab.id, {
        action: 'showNotification',
        message: `⏳ API offline. Saved to local queue for later.`,
        error: false,
        isWarning: true
      }).catch(() => { });
    });
}

// Handle messages from content scripts or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('[BG] Message action:', request.action);

  if (request.action === 'importContent') {
    const content = request.content;
    const payload = {
      content_type: content.type,
      content: content.text,
      url: content.url,
      title: content.title || '',
      timestamp: new Date().toISOString()
    };

    fetch(`${API_URL}/health`)
      .then(response => {
        if (!response.ok) throw new Error('API not available');
        return fetch(`${API_URL}/imported`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          syncQueue(); // Try to clear queue if we're back online
          sendResponse({ success: true });
        } else {
          sendResponse({ success: false, error: data.error || 'Unknown error' });
        }
      })
      .catch(error => {
        console.log('[BG] Content import failed/offline, queueing:', error.message);
        addToQueue(payload);
        sendResponse({ success: true, queued: true });
      });

    return true;
  }

  if (request.action === 'getQueueCount') {
    chrome.storage.local.get(['pendingQueue'], (result) => {
      sendResponse({ count: result.pendingQueue ? result.pendingQueue.length : 0 });
    });
    return true;
  }

  if (request.action === 'exportQueue') {
    exportQueue();
    sendResponse({ success: true });
    return true;
  }
});

// Helper: Add item to local storage queue
/**
 * Add an item to the pending import queue in local storage
 * @param {Object} item - The item to queue for import
 * @param {string} item.content_type - Type of content ('word' or 'sentence')
 * @param {string} item.content - The actual content text
 * @param {string} item.url - Source URL
 * @param {string} item.title - Source page title
 * @param {string} item.timestamp - ISO timestamp when queued
 * @returns {void}
 */
function addToQueue(item) {
  chrome.storage.local.get(['pendingQueue'], (result) => {
    const queue = result.pendingQueue || [];
    queue.push(item);
    chrome.storage.local.set({ pendingQueue: queue }, () => {
      console.log('[BG] Item added to queue. Total:', queue.length);
      // If queue is getting long and we're offline, maybe auto-export?
      if (queue.length >= 1) {
        checkAndAutoExport(queue);
      }
    });
  });
}

// Helper: Attempt to sync queued items to API
/**
 * Attempt to synchronize queued items with the API
 * Retries items that were previously queued when the API was offline
 * @returns {Promise<void>}
 */
async function syncQueue() {
  const result = await chrome.storage.local.get(['pendingQueue']);
  const queue = result.pendingQueue || [];
  if (queue.length === 0) return;

  console.log('[BG] Attempting to sync queue of', queue.length, 'items');

  try {
    const health = await fetch(`${API_URL}/health`);
    if (!health.ok) return;

    const remainingItems = [];
    for (const item of queue) {
      try {
        const res = await fetch(`${API_URL}/imported`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(item)
        });
        const data = await res.json();
        if (!data.success) remainingItems.push(item);
      } catch (e) {
        remainingItems.push(item);
      }
    }

    chrome.storage.local.set({ pendingQueue: remainingItems });
    console.log('[BG] Sync complete. Remaining in queue:', remainingItems.length);
  } catch (e) {
    console.log('[BG] Sync failed (still offline)');
  }
}

// Helper: Export queue to a JSON file in Downloads
/**
 * Export the pending queue to a JSON file for manual import later
 * @returns {void}
 */
function exportQueue() {
  chrome.storage.local.get(['pendingQueue'], (result) => {
    const queue = result.pendingQueue || [];
    if (queue.length === 0) return;

    const blob = new Blob([JSON.stringify(queue, null, 2)], { type: 'application/json' });
    const reader = new FileReader();
    reader.onload = function () {
      chrome.downloads.download({
        url: reader.result,
        filename: 'proficiency_pending_imports.json',
        saveAs: false,
        conflictAction: 'overwrite'
      }, (downloadId) => {
        console.log('[BG] Exported queue to file. Download ID:', downloadId);
      });
    };
    reader.readAsDataURL(blob);
  });
}

// Helper: Auto-export if offline for a while
/**
 * Check if API is offline and auto-export queue if necessary
 * Prevents multiple exports within 5-minute intervals
 * @param {Array<Object>} queue - The pending queue to export
 * @returns {void}
 */
let lastExportTime = 0;
function checkAndAutoExport(queue) {
  const now = Date.now();
  // Don't export more than once every 5 minutes automatically
  if (now - lastExportTime < 5 * 60 * 1000) return;

  fetch(`${API_URL}/health`)
    .catch(() => {
      // API is offline
      console.log('[BG] API offline during auto-export check. Triggering file export.');
      exportQueue();
      lastExportTime = now;
    });
}

// Listen for periodic sync alarm
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'sync-check') {
    syncQueue();
  }
});
