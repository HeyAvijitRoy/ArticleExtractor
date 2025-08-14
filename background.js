// Author: Avijit Roy
const SERVER_URL = 'http://127.0.0.1:5000/extract';

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "extractText") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const activeTab = tabs[0];
      if (!activeTab || !activeTab.url) {
        chrome.runtime.sendMessage({ action: "updateStatus", status: "Error: Could not get tab URL." });
        return;
      }

      const articleUrl = activeTab.url;
      console.log(`Sending URL to server: ${articleUrl} as ${request.format || 'json'} (ascii_clean=${!!request.ascii_clean})`);

      fetch(SERVER_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: articleUrl,
          format: request.format || 'json',
          ascii_clean: !!request.ascii_clean
        }),
      })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Server responded with status: ${response.status}`);
        const contentType = (response.headers.get('content-type') || '').toLowerCase();

        if (contentType.includes('application/json')) {
          const data = await response.json();
          if (data.error) {
            console.error("Server returned an error:", data.error);
            chrome.runtime.sendMessage({ action: "updateStatus", status: `Server Error: ${data.error}` });
            sendResponse({ status: "Error." });
            return;
          }

          const sentences = data.sentences || [];
          const jsonContent = JSON.stringify(sentences, null, 2);
          const url = 'data:application/json;charset=utf-8,' + encodeURIComponent(jsonContent);

          const pageTitle = (data.title || 'article').replace(/[^a-z0-9]/gi, '_').toLowerCase();
          chrome.downloads.download({
            url,
            filename: `${pageTitle}_export.json`,
            saveAs: true
          });
          sendResponse({ status: "Download initiated." });
          return;
        }

        // CSV/XLSX
        const blob = await response.blob();
        const xFileName = response.headers.get('X-File-Name') ||
                          ((request.format === 'xlsx') ? 'article.xlsx' : 'article.csv');

        const reader = new FileReader();
        reader.onloadend = () => {
          const dataUrl = reader.result;
          chrome.downloads.download({
            url: dataUrl,
            filename: xFileName,
            saveAs: true
          });
          sendResponse({ status: "Download initiated." });
        };
        reader.readAsDataURL(blob);
      })
      .catch(error => {
        console.error('Failed to fetch from server:', error);
        sendResponse({ status: "Error: Could not connect to the local server. Is it running?" });
      });
    });

    return true; // keep channel open for async sendResponse
  }
});
