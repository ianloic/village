console.log('hello world')

import { render, html, unsafeHTML } from 'https://cdn.jsdelivr.net/gh/lit/dist@3/all/lit-all.min.js';
import * as commonmark from 'https://esm.run/commonmark';



console.log(commonmark);
const markdownReader = new commonmark.Parser();
const markdownWriter = new commonmark.HtmlRenderer({ safe: true });
const markdown = (text) => unsafeHTML(markdownWriter.render(markdownReader.parse(text)));

let testing = markdown("# Hello World\n\n");
console.log(testing);
console.log(typeof unsafeHTML(testing));

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

const fileContents = (contents) => html`
    <details class="function-arg-value">
        <summary>File Contents (${contents.split('\n').length} lines)</summary>
        <pre>${contents}</pre>
    </details>
`

const textPart = (text) => html`
    <div class="part text">
        <b>Text</b>${markdown(text)}
    </div>`


const functionCallArgs = (name, args) => {
    switch (name) {
        case 'write_file':
            const fewer_args = {};
            fewer_args.path = args.path;
            return html`<pre>${JSON.stringify(fewer_args)}</pre>`
        default:
            return html`<pre>${JSON.stringify(args)}</pre>`

    }

}

const functionArgValue = (function_name, name, value) => {
    switch (`${function_name}.${name}`) {
        case 'write_file.contents':
        case 'read_file.result':
            return fileContents(value);
        // TODO: read_files
        case 'list_directory.result':
            return html`<ul>${value.map(item => html`<li class="filename">${item}</li>`)}</ul>`
        default:
            return html`<p>${value}</p>`;
    }
}

const functionArg = (function_name, name, value) => html`
    <div class="function-arg" data-arg-name="${name}">
        <div class="function-arg-name">${name}</div>
        <div class="function-arg-value">${functionArgValue(function_name, name, value)}</div>
    </div>`;

const functionCallPart = (function_call) => {
    console.assert(function_call.id === null);
    return html`
        <div class="part function_call" data-function-name="${function_call.name}">
            <b>Function Call</b>
            <div class="function-name">${function_call.name}</div>
            <div class="function-args">${Object.entries(function_call.args).map(([name, value]) => functionArg(function_call.name, name, value))}</div>
        </div>`
};

const functionResponsePart = (function_call) => {
    console.assert(function_call.id === null);
    return html`
        <div class="part function_response" data-function-name="${function_call.name}">
            <b>Function Response</b>
            <div class="function-name">${function_call.name}</div>
            <div class="function-args">${Object.entries(function_call.response).map(([name, value]) => functionArg(function_call.name, name, value))}</div>
        </div>`
};


const historyPart = (part) => {
    const key = getKey(part);
    switch (key) {
        case 'text':
            return textPart(part.text);
        case 'function_call':
            return functionCallPart(part.function_call);
        case 'function_response':
            return functionResponsePart(part.function_response);
        default:
            return html`<div class="part"><b>${key}</b>${JSON.stringify(part)}</div>`;

    }
};
const role = (role) => {
    if (role === 'user') {
        return html`<div class="role">User 🠮 Model</div>`;
    } else {
        console.assert(role === 'model');
        return html`<div class="role">Model 🠮 User</div>`;

    }
}
const historyItem = (item) => html`
<div class="entry">
    ${role(item.role)}
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
