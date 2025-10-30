  const logWindow = document.getElementById('logWindow');
  const es = new EventSource('/log_stream');
  es.onopen = () => console.log('SSE verbunden');
  es.onmessage = ev => {
    logWindow.textContent += ev.data + "\n";
    logWindow.scrollTop = logWindow.scrollHeight;
  };
  es.onerror = err => {
    console.error('SSE error', err);
  };