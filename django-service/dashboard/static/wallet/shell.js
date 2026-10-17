/* Private app shell: collapsible sidebar on wide screens, navigation drawer on narrow ones.
   Presentation only. Navigation stays ordinary links and forms; nothing here routes or fetches. */
(function () {
  'use strict';
  var KEY = 'foliolet-sidebar';
  var root = document.documentElement;
  var sidebar = document.getElementById('sidebar');
  if (!sidebar) return;
  var toggle = document.getElementById('sidebar-toggle');
  var toggleLabel = toggle.querySelector('.sidebar-label');
  var openButton = document.getElementById('sidebar-open');
  var closeButton = document.getElementById('sidebar-close');
  var scrim = document.getElementById('sidebar-scrim');
  var main = document.querySelector('.app-main');
  var narrow = window.matchMedia('(max-width: 899px)');

  function collapsed() { return root.getAttribute('data-sidebar') === 'collapsed'; }
  function syncToggle() {
    var isCollapsed = collapsed();
    toggle.setAttribute('aria-expanded', String(!isCollapsed));
    toggleLabel.textContent = isCollapsed ? 'Expand sidebar' : 'Collapse sidebar';
    toggle.setAttribute('data-tip', isCollapsed ? 'Expand sidebar' : 'Collapse sidebar');
  }
  toggle.addEventListener('click', function () {
    var next = !collapsed();
    if (next) root.setAttribute('data-sidebar', 'collapsed'); else root.removeAttribute('data-sidebar');
    try { next ? localStorage.setItem(KEY, 'collapsed') : localStorage.removeItem(KEY); } catch (e) {}
    syncToggle();
  });
  syncToggle();

  // Narrow screens: the sidebar is a drawer over the page.
  function setInert(value) { if (main) { if (value) main.setAttribute('inert', ''); else main.removeAttribute('inert'); } }
  function openDrawer() {
    root.classList.add('drawer-open');
    scrim.hidden = false;
    openButton.setAttribute('aria-expanded', 'true');
    setInert(true);
    var current = sidebar.querySelector('[aria-current="page"]') || sidebar.querySelector('.nav-link');
    if (current) current.focus();
  }
  function closeDrawer(restoreFocus) {
    if (!root.classList.contains('drawer-open')) return;
    root.classList.remove('drawer-open');
    openButton.setAttribute('aria-expanded', 'false');
    setInert(false);
    window.setTimeout(function () { if (!root.classList.contains('drawer-open')) scrim.hidden = true; }, 260);
    if (restoreFocus) openButton.focus();
  }
  openButton.addEventListener('click', openDrawer);
  closeButton.addEventListener('click', function () { closeDrawer(true); });
  scrim.addEventListener('click', function () { closeDrawer(true); });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && root.classList.contains('drawer-open')) closeDrawer(true);
  });
  sidebar.addEventListener('click', function (event) {
    if (event.target.closest('a.nav-link')) closeDrawer(false);
  });
  var onChange = function () { if (!narrow.matches) closeDrawer(false); };
  if (narrow.addEventListener) narrow.addEventListener('change', onChange); else narrow.addListener(onChange);

  // The home route also holds the document list: "Documents" is current while #documents is in view.
  var home = sidebar.querySelector('[data-nav="home"]');
  var documents = sidebar.querySelector('[data-nav="documents"]');
  var section = document.getElementById('documents');
  if (home && documents && section && home.hasAttribute('aria-current')) {
    var mark = function (onDocuments) {
      if (onDocuments) { documents.setAttribute('aria-current', 'page'); home.removeAttribute('aria-current'); }
      else { home.setAttribute('aria-current', 'page'); documents.removeAttribute('aria-current'); }
    };
    if ('IntersectionObserver' in window) {
      // The section counts as "in view" once it reaches the upper part of the viewport.
      new IntersectionObserver(function (entries) { mark(entries[0].isIntersecting); },
        { rootMargin: '0px 0px -55% 0px' }).observe(section);
    }
    if (location.hash === '#documents') mark(true);
  }
})();
