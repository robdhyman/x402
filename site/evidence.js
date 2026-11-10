// Filters the quote list in place. The page is complete without this script: every quote is in the HTML.
(function () {
  var items = Array.prototype.slice.call(document.querySelectorAll('#quotes .q'));
  var q = document.getElementById('f-q'), m = document.getElementById('f-m'), s = document.getElementById('f-s'),
      sec = document.getElementById('f-sec'), b = document.getElementById('f-b'),
      shown = document.getElementById('shown'), none = document.getElementById('none');
  var text = items.map(function (li) { return li.textContent.toLowerCase(); });

  function apply() {
    var words = q.value.toLowerCase().split(/\s+/).filter(Boolean), n = 0;
    items.forEach(function (li, i) {
      var ok = (!m.value || li.dataset.m === m.value) && (!s.value || li.dataset.s === s.value) &&
               (!sec.value || li.dataset.sec === sec.value) && (!b.checked || li.dataset.b === '1') &&
               words.every(function (w) { return text[i].indexOf(w) >= 0; });
      li.hidden = !ok;
      if (ok) n++;
    });
    shown.textContent = n;
    none.hidden = n > 0;
    var p = new URLSearchParams();
    if (q.value) p.set('q', q.value);
    if (m.value) p.set('m', m.value);
    if (s.value) p.set('s', s.value);
    if (sec.value) p.set('sec', sec.value);
    if (b.checked) p.set('b', '1');
    var qs = p.toString();
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : '') + location.hash);
  }

  var p = new URLSearchParams(location.search);
  q.value = p.get('q') || ''; m.value = p.get('m') || ''; s.value = p.get('s') || '';
  sec.value = p.get('sec') || ''; b.checked = p.get('b') === '1';
  [q, m, s, sec, b].forEach(function (el) { el.addEventListener('input', apply); });
  if (location.search) apply();
})();
