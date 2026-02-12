const BASE_PATH = "sites/";
const JS_PATH = "js/";

async function authFetch(url, options = {}) {
  const token = localStorage.getItem('auth_token');
  const opts = { ...options };

  // Token-Header
  const baseHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  // NICHT "application/json" setzen, wenn FormData/Blob gesendet wird
  const isFormData = opts.body instanceof FormData;
  const isBlob = (typeof Blob !== 'undefined') && (opts.body instanceof Blob);

  const defaultHeaders = (!isFormData && !isBlob) ? { 'Content-Type': 'application/json' } : {};

  opts.headers = {
    ...defaultHeaders,
    ...baseHeaders,
    ...(options.headers || {})
  };

  return fetch(url, opts);
}


// === Auth Fetch ===
async function authFetchOld(url, options = {}) {
  const token = localStorage.getItem('auth_token');

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...(options.headers || {})
    }
  });

  // Falls Token ungültig ist, automatisch ausloggen
  if (response.status === 401) {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('first_name');
    localStorage.removeItem('last_name');
    window.location.href = '/static/sites/login.html';
    return;
  }

  return response;
}

async function checkAuth() {
    const res = await authFetch("/auth/check");

    if (!res || res.status === 401) {
      logout(); // Token löschen
      window.location.href = "/static/sites/login.html";
    }
  }


// Hilfsfunktion: HTML in den Main-Container laden
// HTML-Snippet in den Main-Container laden
async function loadPageIntoMain(pagePath) {
  const main = document.getElementById('main-content');
  try {
    const res = await fetch(BASE_PATH + pagePath, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const html = await res.text();
    main.innerHTML = html;

    // Gleichnamige JS-Datei versuchen zu laden (z. B. settings.js)
    const scriptName = pagePath.replace(".html", ".js");
    loadPageScript(JS_PATH + scriptName); // <-- hier liegt der Fix

  } catch (err) {
    main.innerHTML = `<div class="alert alert-danger">Fehler beim Laden (${pagePath}): ${err}</div>`;
  }
}

// Seite-spezifisches Script dynamisch laden (wenn vorhanden)
function loadPageScript(fullSrc) {
  // altes Seitenscript entfernen
  const old = document.querySelector('script[data-page-script]');
  if (old) old.remove();

  const script = document.createElement('script');
  // Cache-Busting, damit Änderungen sofort greifen
  const cacheBuster = (fullSrc.includes('?') ? '&' : '?') + '_=' + Date.now();
  script.src = fullSrc + cacheBuster;
  script.defer = true;
  script.dataset.pageScript = 'true';

  // Wenn du initialisieren willst, NACHDEM das Script geladen ist:
  script.onload = () => { window.pageInit && window.pageInit(); };

  document.body.appendChild(script);
}

// Navigation anklicken → Inhalt laden
function setupNavLinks() {
  const links = document.querySelectorAll('[data-page]');
  links.forEach(link => {
    link.addEventListener('click', async (e) => {
      e.preventDefault();
      const page = link.getAttribute('data-page');

      // Active-Klasse updaten
      document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
      link.classList.add('active');

      // Inhalt laden
      await loadPageIntoMain(page);

      // Offcanvas auf Mobile schließen
      const sidebarEl = document.getElementById('sidebar');
      const sidebar = bootstrap.Offcanvas.getInstance(sidebarEl);
      if (sidebar) sidebar.hide();
    });
  });
}

// Initial: Dashboard laden
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    const token = localStorage.getItem('auth_token');
    const user_name = localStorage.getItem('user_name');

    if (!token && !window.location.pathname.includes('login.html') && !window.location.pathname.includes('register.html')) {
        window.location.href = '/static/sites/login.html';
        return;
    }

    if (token && (window.location.pathname.endsWith('login.html') || window.location.pathname.endsWith('register.html'))) {
        window.location.href = '/index.html';
        return;
    }

     if (document.querySelector('main.content')) {
        const content = document.querySelector('main.content');

        setupNavLinks();
        const defaultLink = document.querySelector('[data-page].active') || document.querySelector('[data-page]');
        if (defaultLink) {
            loadPageIntoMain(defaultLink.getAttribute('data-page'));
        }
     }

     //Setzte Username als User Status
     const logged_in_user = document.getElementById('logged_in_user');
     if (logged_in_user) {
        logged_in_user.textContent = "User: " + user_name;
    }

        
        
});


function logout(){
  localStorage.removeItem('auth_token');
  localStorage.removeItem('user_name');
  location.reload();
}

