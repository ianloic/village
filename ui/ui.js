console.log('hello world')

import { html, render } from 'https://esm.run/lit-html@1';

function getKey(o) {
    let keys = [];
    for (let key of Object.keys(o)) {
        if (o[key] !== null) {
            keys.push(key);
        }
    }
    if (keys.length === 1) {
        return keys[0];
    } else {
        console.error("expected one key, got: ", keys);
        return keys.join(',');
    }
}

const historyPart = (part) => {
    const key = getKey(part);
    switch (key) {
        case 'text':
            return html`<div class="part text"><b>Text</b><pre>${part.text}</pre></div>`;
        case 'function_call':
            return html`<div class="part function_call"><b>Function Call</b><pre>${JSON.stringify(part.function_call)}</pre></div>`;
        case 'function_response':
            return html`<div class="part function_response"><b>Function Response</b><pre>${JSON.stringify(part.function_response)}</pre></div>`;
        default:
            return html`<div class="part"><b>${key}</b>${JSON.stringify(part)}</div>`;

    }
};
const historyItem = (item) => html`
<div class="entry">
    <div class="role">${item.role}</div>
    <div class="parts">${item.parts.map(historyPart)}</div>
</div>`;
const historyList = (items) => html`<div class="history">${items.map(historyItem)}</div>`;




async function loadHistory() {
    const response = await fetch('/state');
    const state = await response.json();
    console.log(state);
    const history = state.history;
    const historyDiv = document.getElementById('history');
    render(historyList(history), historyDiv)
    // historyDiv.innerHTML = ''; // Clear previous history

    // history.forEach(entry => {
    //     const p = document.createElement('p');
    //     p.className = 'entry'
    //     p.textContent = JSON.stringify(entry);
    //     historyDiv.appendChild(p);
    // });
}

// Initial load of history when the page loads
document.addEventListener('DOMContentLoaded', loadHistory);
