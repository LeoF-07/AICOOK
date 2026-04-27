document.addEventListener('DOMContentLoaded', () => {
    const backButton = document.getElementById('backButton');
    if (backButton) {
        backButton.addEventListener('click', () => {
            window.location.href = INDEX_URL;
        });
    }

    const uploadPageButton = document.getElementById('uploadPageButton');
    if (uploadPageButton) {
        uploadPageButton.addEventListener('click', () => {
            window.location.href = UPLOAD_RECIPE_BOOK_URL;
        });
    }

    const chatForm = document.getElementById('ChatAIForm');
    const chatInput = document.getElementById('chatInput');
    const chatContainer = document.getElementById('chatContainer');

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();

        const message = chatInput.value.trim();
        if (!message) return;

        appendMessage(message, 'user-message');
        chatInput.value = '';

        fetch('http://127.0.0.1/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prompt: message })
        })
        .then(response => response.json())
        .then(data => {
            appendMessage(data.response, 'ai-message');
        })
        .catch(error => {
            console.error('Errore:', error);
            appendMessage("Scusa mi sento male, ripeti fra un po'!", 'ai-message');
        });
    });

    function appendMessage(text, className) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${className}`;
        messageDiv.innerText = text;
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}); 