/* Theme preference: "light", "dark", or absent (follow the system). Loaded in <head>, before
   first paint, so a stored choice never flashes the other theme. Preference only: if storage
   is unavailable the page still renders and follows the system. */
(function () {
  var KEY = 'foliolet-theme', root = document.documentElement;
  function read() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function write(value) { try { value ? localStorage.setItem(KEY, value) : localStorage.removeItem(KEY); } catch (e) {} }
  function apply(value) {
    if (value === 'light' || value === 'dark') root.setAttribute('data-theme', value);
    else root.removeAttribute('data-theme');
  }
  apply(read());
  document.addEventListener('DOMContentLoaded', function () {
    var buttons = document.querySelectorAll('[data-theme-choice]');
    function sync() {
      var current = read() || 'system';
      for (var i = 0; i < buttons.length; i++)
        buttons[i].setAttribute('aria-pressed', String(buttons[i].getAttribute('data-theme-choice') === current));
    }
    for (var i = 0; i < buttons.length; i++) buttons[i].addEventListener('click', function () {
      var choice = this.getAttribute('data-theme-choice');
      root.classList.add('theme-changing');
      write(choice === 'system' ? null : choice);
      apply(choice);
      sync();
      setTimeout(function () { root.classList.remove('theme-changing'); }, 320);
    });
    sync();
  });
})();
