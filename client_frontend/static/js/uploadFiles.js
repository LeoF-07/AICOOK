document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const status = document.getElementById('status');

    uploadForm.addEventListener('submit', (e) => {
        e.preventDefault();

        status.className = "loading";

        const fileInput = document.getElementById('fileInput');
        const file = fileInput.files[0];

        if (!file) {
            status.innerText = "Per favore, seleziona un file.";
            status.className = "error";
            return;
        }

        const isPDF = file.type === "application/pdf" || file.name.toLowerCase().endsWith('.pdf');

        if (!isPDF) {
            status.innerText = "Errore: puoi caricare solo file in formato PDF.";
            status.className = "error";
            fileInput.value = "";
            return;
        }

        const formData = new FormData(uploadForm);
        formData.append('file', file);

        status.innerText = "Caricamento in corso...";

        fetch('http://127.0.0.1:5000/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.text())
        .then(data => {
            status.innerText = "Caricamento avvenuto con successo!!!";
            status.className = "success";
            console.log('data:', data);
        })
        .catch(error => {
            status.innerText = "Errore durante il caricamento.";
            status.className = "error";
            console.error('Errore:', error);
        });
    });
});