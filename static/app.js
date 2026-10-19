const form = document.querySelector('#form');
const status = document.querySelector('#status');
const submit = document.querySelector('#submit');
const result = document.querySelector('#result');
const text = document.querySelector('#text');
let filename = 'transcription.txt';
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = document.querySelector('#audio').files[0];
  if (!file) return;
  result.hidden = true;
  if (file.size >= 25000000 || file.size === 0) {
    status.textContent = 'Choisissez un MP3 ou OGG non vide de moins de 25 Mo.';
    return;
  }
  submit.disabled = true;
  form.setAttribute('aria-busy', 'true');
  status.textContent = 'Envoi et transcription en cours… Cela peut prendre quelques minutes.';
  try {
    const response = await fetch('/transcribe', {
      method: 'POST', body: new FormData(form),
      headers: {'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content}
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'La transcription a échoué.');
    text.value = data.text;
    filename = data.filename;
    result.hidden = false;
    status.textContent = 'Transcription terminée.';
    text.focus();
  } catch (error) {
    status.textContent = error instanceof SyntaxError ? 'Réponse serveur invalide. Réessayez.' : error.message;
  } finally {
    submit.disabled = false;
    form.removeAttribute('aria-busy');
  }
});
document.querySelector('#download').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([text.value], {type: 'text/plain;charset=utf-8'}));
  const link = document.createElement('a');
  link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
