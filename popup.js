// Autjhor: Avijit Roy
// Get the extract button and status element from the DOM
const extractBtn = document.getElementById('extractBtn');
const statusDiv = document.getElementById('status');

// Add a click event listener to the extract button
extractBtn.addEventListener('click', () => {
  // Clear any previous status messages and show a new one
  statusDiv.textContent = 'Contacting server...';

  // Send a message to the background script to start the extraction
  chrome.runtime.sendMessage({ action: "extractText" }, (response) => {
    // Handle the response from the background script
    if (chrome.runtime.lastError) {
      // If there was an error, display it
      statusDiv.textContent = 'Error: ' + chrome.runtime.lastError.message;
    } else if (response && response.status) {
      // If the background script sends back a status, display it
      statusDiv.textContent = response.status;
    } else {
      // If the response is unexpected, show a generic error
      statusDiv.textContent = 'An unexpected error occurred.';
    }
  });
});
