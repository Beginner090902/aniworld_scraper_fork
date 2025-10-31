const stopBtn = document.getElementById('stopBtn');
stopBtn.addEventListener('click', async () => {
  stopBtn.disabled = true; // verhindern Doppel-Klicks
  try {
    const resp = await fetch('/stop', { method: 'POST' });
    const json = await resp.json();
    if (resp.ok) {
      console.log('Stopped:', json);
    } else {
      console.warn('Stop failed:', json);
      alert(json.message || 'Stop fehlgeschlagen');
    }
  } catch (err) {
    console.error('Network error while stopping:', err);
    alert('Netzwerkfehler beim Stoppen');
  } finally {
    stopBtn.disabled = false;
  }
});
