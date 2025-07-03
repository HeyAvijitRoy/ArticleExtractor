// The URL of your local Python server
const SERVER_URL = 'http://127.0.0.1:5000/extract';

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "extractText") {
    // Get the currently active tab
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const activeTab = tabs[0];
      if (!activeTab || !activeTab.url) {
        // Send a status update back to the popup
        chrome.runtime.sendMessage({ action: "updateStatus", status: "Error: Could not get tab URL." });
        return;
      }

      const articleUrl = activeTab.url;
      console.log(`Sending URL to server: ${articleUrl}`);

      // Use the fetch API to send the URL to the Python server
      fetch(SERVER_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: articleUrl }),
      })
      .then(response => {
        // Check if the server responded successfully
        if (!response.ok) {
          throw new Error(`Server responded with status: ${response.status}`);
        }
        return response.json(); // Parse the JSON from the response
      })
      .then(data => {
        // The server's response is in 'data'
        if (data.error) {
          console.error("Server returned an error:", data.error);
          chrome.runtime.sendMessage({ action: "updateStatus", status: `Server Error: ${data.error}` });
          return;
        }

        console.log("Received text from server.");
        // Split the text into sentences using a robust regex
        let sentences = data.text.match(/(.+?[.!?])(?=\s+|$)/g) || [];
        if (sentences) {
            sentences = sentences.map(sentence => sentence.trim());
        }

        const jsonContent = JSON.stringify(sentences, null, 2);
        const url = 'data:application/json;charset=utf-8,' + encodeURIComponent(jsonContent);

        // Use the article title from the server for the filename
        const pageTitle = data.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
        
        chrome.downloads.download({
          url: url,
          filename: `${pageTitle || 'article'}_export.json`,
          saveAs: true
        });

        sendResponse({ status: "Download initiated." });
      })
      .catch(error => {
        console.error('Failed to fetch from server:', error);
        sendResponse({ status: "Error: Could not connect to the local server. Is it running?" });
      });
    });

    // Return true to indicate that we will send a response asynchronously
    return true;
  }
});
