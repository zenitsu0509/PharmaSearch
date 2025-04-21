// Wait for the DOM to be fully loaded before running script
document.addEventListener('DOMContentLoaded', () => {

    // Get references to DOM elements
    const medicineInput = document.getElementById('medicine-name');
    const searchButton = document.getElementById('search-button');
    const loadingIndicator = document.getElementById('loading');
    const errorDisplay = document.getElementById('error');
    const resultsContainer = document.getElementById('results');

    // --- Function to perform the search ---
    function searchMedicine() {
        const medicineName = medicineInput.value.trim(); // Get and trim input value

        // Basic validation
        if (!medicineName) {
            showError('Please enter a medicine name.');
            medicineInput.focus(); // Focus the input field
            return;
        }

        // --- UI Updates - Start Search ---
        clearError(); // Clear previous errors
        hideResults(); // Hide previous results
        showLoading(); // Show loading indicator

        // --- API Call ---
        fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ medicine_name: medicineName }),
        })
        .then(response => {
            // Check if the response status is OK (2xx)
            if (!response.ok) {
                 // If not OK, try to parse the error message from JSON
                 return response.json().then(err => {
                     // Throw an error with the message from the server response
                     throw new Error(err.error || `HTTP error! Status: ${response.status}`);
                 }).catch(() => {
                     // If parsing JSON fails, throw a generic HTTP error
                     throw new Error(`HTTP error! Status: ${response.status}`);
                 });
            }
             // If response is OK, parse the JSON data
            return response.json();
        })
        .then(data => {
            // --- UI Updates - Success ---
            hideLoading();
            displayResults(data); // Display the fetched data
        })
        .catch(error => {
            // --- UI Updates - Error ---
            console.error('Search Error:', error); // Log the full error for debugging
            hideLoading();
            showError(error.message || 'An unexpected error occurred.'); // Show user-friendly error
        });
    }

    // --- Function to display results in the HTML ---
    function displayResults(data) {
        // Set basic info
        document.getElementById('medicine-title').textContent = data.name || 'N/A';
        document.getElementById('medicine-id').textContent = data.id || 'N/A';

        // Populate lists (Substitutes, Uses, Side Effects)
        populateList('substitutes', data.substitutes);
        populateList('uses', data.uses);
        populateList('side-effects', data.side_effects);

        // Set classification and other info
        document.getElementById('chemical-class').textContent = data.chemical_class || 'N/A';
        document.getElementById('therapeutic-class').textContent = data.therapeutic_class || 'N/A';
        document.getElementById('action-class').textContent = data.action_class || 'N/A';
        document.getElementById('habit-forming').textContent = data.habit_forming || 'N/A';
        document.getElementById('match-score').textContent = data.match_score || 'N/A';

        // Show the results container
        resultsContainer.style.display = 'block';
    }

    // --- Helper function to populate a <ul> list ---
    function populateList(elementId, items) {
        const ul = document.getElementById(elementId);
        ul.innerHTML = ''; // Clear previous items

        if (items && items.length > 0) {
            items.forEach(item => {
                if (item) { // Ensure item is not null or empty string
                    const li = document.createElement('li');
                    li.textContent = item;
                    ul.appendChild(li);
                }
            });
        } else {
            // Optional: Add a message if the list is empty
            const li = document.createElement('li');
            li.textContent = 'No information available.';
            li.style.fontStyle = 'italic'; // Style the placeholder message
             li.style.color = '#6c757d';
            ul.appendChild(li);
        }
    }

    // --- Helper functions for UI states ---
    function showLoading() {
        loadingIndicator.style.display = 'flex'; // Use flex for spinner alignment
    }

    function hideLoading() {
        loadingIndicator.style.display = 'none';
    }

    function showError(message) {
        errorDisplay.textContent = message;
        errorDisplay.style.display = 'block';
    }

    function clearError() {
        errorDisplay.textContent = '';
        errorDisplay.style.display = 'none';
    }

     function hideResults() {
        resultsContainer.style.display = 'none';
         // Optionally clear old data immediately when hiding
        // document.getElementById('medicine-title').textContent = '';
        // ... clear other fields ...
    }

    // --- Event Listeners ---
    // Search button click
    searchButton.addEventListener('click', searchMedicine);

    // Enter key press in the input field
    medicineInput.addEventListener('keyup', function(event) {
        // Check if the key pressed was 'Enter'
        if (event.key === 'Enter' || event.keyCode === 13) {
             event.preventDefault(); // Prevent default form submission (if it were in a form)
            searchMedicine();
        }
    });

}); // End of DOMContentLoaded