// Helper for elements
function $(id) { return document.getElementById(id); }
const input = $('medicine-name'),
      btn = $('search-button'),
      statusArea = $('status-area'),
      results = $('results');

// Focus input on load, for better UX
window.onload = () => {
  input.focus();
};

function setStatus({type, message, showSpinner=false}) {
  statusArea.innerHTML = '';
  if (!message) return;
  const div = document.createElement('div');
  div.className = 'status-message ' + type;
  if (showSpinner) {
    const spin = document.createElement('span');
    spin.className = 'spinner';
    div.appendChild(spin);
  }
  div.appendChild(document.createTextNode(message));
  statusArea.appendChild(div);
}

function clearStatus() {
  statusArea.innerHTML = '';
}

function showResults(data) {
  // Fill values
  $('medicine-title').textContent = data.name ?? 'N/A';
  $('medicine-id').textContent = data.id ?? 'N/A';
  fillList('substitutes', data.substitutes);
  fillList('uses', data.uses);
  fillList('side-effects', data.side_effects);
  $('chemical-class').textContent = data.chemical_class ?? 'N/A';
  $('therapeutic-class').textContent = data.therapeutic_class ?? 'N/A';
  $('action-class').textContent = data.action_class ?? 'N/A';
  $('habit-forming').textContent = data.habit_forming ?? 'N/A';
  $('match-score').textContent = data.match_score != null ? data.match_score : 'N/A';
  results.style.display = 'block';
  results.scrollIntoView({behavior: 'smooth'});
}

function hideResults() {
  results.style.display = 'none';
}

function fillList(elId, arr) {
  const ul = $(elId);
  ul.innerHTML = '';
  if (Array.isArray(arr) && arr.length) {
    arr.forEach(val => {
      if (val && (typeof val === 'string' && val.trim())) {
        const li = document.createElement('li');
        li.textContent = val;
        ul.appendChild(li);
      }
    });
  }
  if (!ul.children.length) {
    const li = document.createElement('li');
    li.textContent = 'No information available.';
    li.className = 'empty';
    ul.appendChild(li);
  }
}

function runSearch() {
  const q = input.value.trim();
  if (!q) {
    hideResults();
    setStatus({type: 'error', message: 'Please enter a medicine name.'});
    input.focus();
    return;
  }
  hideResults();
  setStatus({type: 'loading', message: 'Searching...', showSpinner:true});

  // ---- Replace the URL below with your real backend API endpoint! ----
  fetch('/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({medicine_name: q})
  })
  // ---------------------------------------------------------------------
    .then(response => {
      if (!response.ok)
        return response.json().then(err =>{
          throw new Error(err.error || `HTTP error! Status: ${response.status}`);
        });
      return response.json();
    })
    .then(data => {
      clearStatus();
      showResults(data);
    })
    .catch(err => {
      hideResults();
      setStatus({type:'error', message: err.message ?? 'An unexpected error occurred.'});
    });
}

// Button click
btn.addEventListener('click', runSearch);

// 'Enter' in input triggers search
input.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    e.preventDefault();
    runSearch();
  }
});

// Optionally: highlight input when typing clears error
input.addEventListener('input', () => {
  clearStatus();
});
