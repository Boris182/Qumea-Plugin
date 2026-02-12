document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('login-form');
  const errorDiv = document.getElementById('login-error');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const user_name = document.getElementById('user_name').value.trim();
    const password = document.getElementById('password').value;

    try {
      const res = await fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_name, password })
      });

      if (!res.ok) {
        const err = await res.json();
        showError(err.detail || 'Login fehlgeschlagen');
        return;
      }

      const data = await res.json();
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user_name', data.user_name);
      localStorage.setItem('role', data.role);

      window.location.href = '/static/index.html';

    } catch (err) {
      showError('Serverfehler oder keine Verbindung');
      console.error(err);
    }
  });

  function showError(msg) {
    errorDiv.textContent = msg;
    errorDiv.style.display = 'block';
  }
});

async function registerCheck() {
  try {
    const res = await fetch('/registerCheck', {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!res.ok) {
      const err = await res.json();
      showError(err.detail || 'Abfrage fehlgeschlagen');
      return;
    }

    const data = await res.json(); // z. B. true oder false
    console.log('Antwort:', data);

    if (data === true) {
      console.log('Registrierung ist nicht erlaubt!');
      // z. B. Formular anzeigen
    } else if (data === false) {
      console.log('Registrierung ist erlaubt.');
      window.location.href = "/static/sites/register.html";
    } else {
      console.warn('Unerwartete Antwort:', data);
    }

  } catch (err) {
    showError('Serverfehler oder keine Verbindung');
    console.error(err);
  }
}

registerCheck();