(function () {
  // If the sidebar already exists, toggle its visibility
  const existing = document.getElementById('reframe-sidebar');
  if (existing) {
    existing.remove();
    // Also remove the floating toggle bubble
    const bubble = document.getElementById('reframe-bubble');
    if (bubble) bubble.remove();
    return;
  }

  // Create the sidebar container
  const div = document.createElement('div');
  div.id = 'reframe-sidebar';
  Object.assign(div.style, {
    position: 'fixed',
    top: '0',
    right: '0',
    width: '340px',
    height: '100vh',
    background: 'rgba(15,23,42,0.95)',
    backdropFilter: 'blur(12px)',
    zIndex: '2147483647',
    overflow: 'hidden',
    boxShadow: '-4px 0 20px rgba(0,0,0,0.4)',
    transition: 'transform 0.3s ease, opacity 0.3s ease',
    transform: 'translateX(0)'
  });

  const iframe = document.createElement('iframe');
  iframe.src = chrome.runtime.getURL('sidebar.html');
  iframe.style.border = 'none';
  iframe.style.width = '100%';
  iframe.style.height = '100%';
  iframe.style.background = 'transparent';

  div.appendChild(iframe);
  document.body.appendChild(div);

  // Listen for postMessage from the iframe (close / minimize)
  window.addEventListener('message', function handler(event) {
    if (event.data === 'reframe-close') {
      // Fully close sidebar and remove bubble
      const sidebar = document.getElementById('reframe-sidebar');
      if (sidebar) {
        sidebar.style.transform = 'translateX(350px)';
        sidebar.style.opacity = '0';
        setTimeout(() => sidebar.remove(), 300);
      }
      const bubble = document.getElementById('reframe-bubble');
      if (bubble) bubble.remove();
      window.removeEventListener('message', handler);
    }

    if (event.data === 'reframe-minimize') {
      // Hide sidebar, show floating bubble
      const sidebar = document.getElementById('reframe-sidebar');
      if (sidebar) {
        sidebar.style.transform = 'translateX(350px)';
        sidebar.style.opacity = '0';
        sidebar.style.pointerEvents = 'none';
      }
      showBubble();
    }
  });

  function showBubble() {
    // Don't create duplicate bubbles
    if (document.getElementById('reframe-bubble')) return;

    const bubble = document.createElement('div');
    bubble.id = 'reframe-bubble';
    Object.assign(bubble.style, {
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      width: '56px',
      height: '56px',
      borderRadius: '50%',
      background: 'linear-gradient(135deg, #2563eb, #6366f1)',
      boxShadow: '0 4px 20px rgba(99,102,241,0.5), 0 0 0 3px rgba(99,102,241,0.2)',
      cursor: 'pointer',
      zIndex: '2147483647',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '24px',
      transition: 'transform 0.2s ease, box-shadow 0.2s ease',
      animation: 'reframeBubblePop 0.3s ease-out',
      userSelect: 'none'
    });
    bubble.textContent = '🔄';
    bubble.title = 'Reopen Reframe sidebar';

    // Hover effects
    bubble.addEventListener('mouseenter', () => {
      bubble.style.transform = 'scale(1.15)';
      bubble.style.boxShadow = '0 6px 28px rgba(99,102,241,0.6), 0 0 0 5px rgba(99,102,241,0.25)';
    });
    bubble.addEventListener('mouseleave', () => {
      bubble.style.transform = 'scale(1)';
      bubble.style.boxShadow = '0 4px 20px rgba(99,102,241,0.5), 0 0 0 3px rgba(99,102,241,0.2)';
    });

    // Click to reopen sidebar
    bubble.addEventListener('click', () => {
      const sidebar = document.getElementById('reframe-sidebar');
      if (sidebar) {
        sidebar.style.transform = 'translateX(0)';
        sidebar.style.opacity = '1';
        sidebar.style.pointerEvents = 'auto';
      }
      bubble.style.transform = 'scale(0)';
      setTimeout(() => bubble.remove(), 200);
    });

    // Add pop animation
    const style = document.createElement('style');
    style.id = 'reframe-bubble-style';
    style.textContent = `
      @keyframes reframeBubblePop {
        0% { transform: scale(0); opacity: 0; }
        70% { transform: scale(1.15); }
        100% { transform: scale(1); opacity: 1; }
      }
    `;
    if (!document.getElementById('reframe-bubble-style')) {
      document.head.appendChild(style);
    }

    document.body.appendChild(bubble);
  }
})();