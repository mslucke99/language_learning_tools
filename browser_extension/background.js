/**
 * Background Service Worker
 * Handles context menu and API communication for importing words/sentences
 */

const API_URL = 'http://localhost:5000/api';

// Create context menu items
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

  // Initialize storage with defaults
  chrome.storage.local.get(['apiUrl'], (result) => {
    if (!result.apiUrl) {
      chrome.storage.local.set({ apiUrl: API_URL });
    }
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  const selectedText = info.selectionText.trim();
  console.log('[BG] Context menu:', info.menuItemId, 'Text:', selectedText);
  
  if (!selectedText) return;

  let contentType = 'word';
  if (info.menuItemId === 'import-sentence') {
    contentType = 'sentence';
  }

  importContent(selectedText, contentType, tab);
});

// Import content via API
function importContent(text, type, tab) {
  console.log('[BG] Importing:', { text: text.substring(0, 30), type, url: tab.url });
  // Verify API is available
  fetch(`${API_URL}/health`)
    .then(response => {
      if (!response.ok) throw new Error('API not available');

      // Send to API
      return fetch(`${API_URL}/imported`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content_type: type,
          content: text,
          url: tab.url,
          title: tab.title || ''
        })
      });
    })
    .then(res => res.json())
    .then(data => {
      console.log('[BG] API success:', data);
      if (data.success) {
        // Notify user in content script
        chrome.tabs.sendMessage(tab.id, {
          action: 'showNotification',
          message: `✓ Added ${type}: "${text.substring(0, 40)}..."`,
          error: false
        }).catch(() => {
          // Content script might not be loaded, that's OK
        });
      } else {
        throw new Error(data.error || 'Unknown error');
      }
    })
    .catch(error => {
      console.error('[BG] Error:', error.message);
      // Try to notify the tab
      chrome.tabs.sendMessage(tab.id, {
        action: 'showNotification',
        message: `✗ Failed: ${error.message}`,
        error: true
      }).catch(() => {
        // Content script might not be loaded
      });
    });
}

// Handle messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('[BG] Message from content:', request.action);
  if (request.action === 'importContent') {
    const content = request.content;
    console.log('[BG] Importing from content:', content);
    
    // Verify API is available
    fetch(`${API_URL}/health`)
      .then(response => {
        if (!response.ok) throw new Error('API not available');

        // Prepare JSON payload
        const payload = {
          content_type: content.type,
          content: content.text,
          url: content.url,
          title: content.title || ''
        };
        console.log('[BG] Sending payload to API:', payload);
        
        // Send to API
        return fetch(`${API_URL}/imported`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      })
      .then(res => res.json())
      .then(data => {
        console.log('[BG] API response:', data);
        if (data.success) {
          console.log('[BG] Success! Sending response to content script');
          sendResponse({ success: true });
        } else {
          console.log('[BG] API returned error:', data.error);
          sendResponse({ success: false, error: data.error || 'Unknown error' });
        }
      })
      .catch(error => {
        console.error('[BG] Fetch error:', error);
        sendResponse({ success: false, error: error.message });
      });

    return true; // Keep channel open for async response
  }
});
