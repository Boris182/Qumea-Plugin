// maintenance.js
window.pageInit = function () {
  const btn = document.getElementById('btn-save');
  if (btn) {
    btn.addEventListener('click', () => {
      alert("Einstellungen gespeichert!");
    });
  }
};