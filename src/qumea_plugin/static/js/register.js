async function register(data){
  const errorDiv = document.getElementById("register-error");
  try {
      const res = await fetch('/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      if (res.ok) {
        window.location.href = '/static/sites/login.html';
      } else {
        const error = await res.json();
        errorDiv.textContent = error.detail || 'Registrierung fehlgeschlagen';
        errorDiv.style.display = 'block';
      }
    } catch (err) {
      errorDiv.textContent = 'Serverfehler: ' + err.message;
      errorDiv.style.display = 'block';
    }
};

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById("register-form");
  const password = document.getElementById("password");
  const passwordRepeat = document.getElementById("password_repeat");
  const errorText = document.getElementById("password-error");

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

      // Passwortvalidierung
      if (password.value !== passwordRepeat.value) {
        errorText.style.display = "block";
        passwordRepeat.classList.add("is-invalid");
        return;
      } else {
        errorText.style.display = "none";
        passwordRepeat.classList.remove("is-invalid");
      }

      // Beispiel für zusätzliche Passwort-Regel
      const strongPassword = /^(?=.*[A-Z])(?=.*\d).{8,}$/;
      if (!strongPassword.test(password.value)) {
        alert("Passwort muss mindestens 8 Zeichen, eine Zahl und einen Großbuchstaben enthalten!");
        return;
      }

      // Wenn alles passt → registrieren
      console.log("Formular gültig, absenden...");
      const data = {
      username: document.getElementById('username').value.trim(),
      password: document.getElementById('password').value,
    };
    register(data);
    });
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
      window.location.href = "/static/sites/login.html";
      // z. B. Formular anzeigen
    } else if (data === false) {
      console.log('Registrierung ist erlaubt.');
    } else {
      console.warn('Unerwartete Antwort:', data);
    }

  } catch (err) {
    showError('Serverfehler oder keine Verbindung');
    console.error(err);
  }
}

registerCheck();