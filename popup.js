// Author: Avijit Roy
const extractBtn = document.getElementById('extractBtn');
const statusDiv = document.getElementById('status');
const formatSel = document.getElementById('format');

extractBtn.addEventListener('click', () => {
  statusDiv.textContent = 'Contacting server...';
  const format = formatSel.value || 'json';

  chrome.runtime.sendMessage({ action: "extractText", format }, (response) => {
    if (chrome.runtime.lastError) {
      statusDiv.textContent = 'Error: ' + chrome.runtime.lastError.message;
    } else if (response && response.status) {
      statusDiv.textContent = response.status;
    } else {
      statusDiv.textContent = 'An unexpected error occurred.';
    }
  });
});
