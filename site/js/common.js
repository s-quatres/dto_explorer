/** Shared utilities for all pages. */

async function loadJSON(path) {
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`Failed to load ${path}: ${resp.status}`);
  return resp.json();
}

function formatNumber(n) {
  return n.toLocaleString();
}

function formatDate(iso) {
  if (!iso) return 'N/A';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function setTimestamp(id, isoDate) {
  const el = document.getElementById(id);
  if (el && isoDate) {
    el.textContent = `Last updated: ${formatDate(isoDate)}`;
  }
}

/** Highlight the current page's nav link. */
function initNav() {
  const page = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(a => {
    const href = a.getAttribute('href');
    if (href === page || (page === '' && href === 'index.html')) {
      a.classList.add('active');
    }
  });
}

document.addEventListener('DOMContentLoaded', initNav);
