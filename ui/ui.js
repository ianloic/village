console.log('hello world')


async function loadHistory() {
    const response = await fetch('/history');
    const history = await response.json();
    const historyDiv = document.getElementById('history');
    historyDiv.innerHTML = ''; // Clear previous history

    history.forEach(entry => {
        const p = document.createElement('p');
        p.className = 'entry'
        p.textContent = JSON.stringify(entry);
        historyDiv.appendChild(p);
    });
}

// Initial load of history when the page loads
document.addEventListener('DOMContentLoaded', loadHistory);
