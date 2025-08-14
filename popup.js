// Author: Avijit Roy
const extractBtn = document.getElementById('extractBtn');
const statusDiv = document.getElementById('status');
const formatSel = document.getElementById('format');
const asciiChk = document.getElementById('asciiClean');

extractBtn.addEventListener('click', () => {
  statusDiv.textContent = 'Contacting server...';
  const format = formatSel.value || 'json';
  const ascii_clean = !!asciiChk.checked;

  chrome.runtime.sendMessage({ action: "extractText", format, ascii_clean }, (response) => {
    if (chrome.runtime.lastError) {
      statusDiv.textContent = 'Error: ' + chrome.runtime.lastError.message;
    } else if (response && response.status) {
      statusDiv.textContent = response.status;
    } else {
      statusDiv.textContent = 'An unexpected error occurred.';
    }
  });
});
