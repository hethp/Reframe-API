(function() {
  // toggle sidebar if it already exists
  const existing = document.getElementById('reframe-sidebar');
  if (existing) {
    existing.remove();
    return;
  }

  const div = document.createElement('div');
  div.id = 'reframe-sidebar';
  Object.assign(div.style, {
    position: 'fixed',
    top: '0',
    right: '0',
    width: '320px',
    height: '100vh',
    background: 'rgba(15,23,42,0.8)',
    'backdrop-filter': 'blur(10px)',
    'z-index': '2147483647',
    overflow: 'hidden',
    boxShadow: '-2px 0 12px rgba(0,0,0,0.3)'
  });

  const iframe = document.createElement('iframe');
  iframe.src = chrome.runtime.getURL('sidebar.html');
  iframe.style.border = 'none';
  iframe.style.width = '100%';
  iframe.style.height = '100%';
  iframe.style.background = 'transparent';

  div.appendChild(iframe);
  document.body.appendChild(div);
})();