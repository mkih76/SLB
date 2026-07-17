/**
 * SLB GSAP Animations — Modular Engine
 * Uses gsap.set() + ScrollTrigger.onEnter to avoid FOUC
 * Supports: prefers-reduced-motion, matchMedia (desktop/mobile)
 */
(function() {
  'use strict';

  // Safety timeout: if GSAP doesn't init in 3s, remove all gsap-hidden
  var safetyTimer = setTimeout(function() {
    var els = document.querySelectorAll('[data-gsap-init]');
    for (var i = 0; i < els.length; i++) els[i].removeAttribute('data-gsap-init');
  }, 3000);

  if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') {
    clearTimeout(safetyTimer);
    return;
  }

  gsap.registerPlugin(ScrollTrigger);

  // Public API
  window.SLB = window.SLB || {};
  window.SLB.gsap = {
    refresh: function() { ScrollTrigger.refresh(); },
    version: '2.0.0'
  };

  var mm = gsap.matchMedia();

  mm.add(
    {
      desktop: '(min-width: 769px)',
      mobile: '(max-width: 768px)',
      reduceMotion: '(prefers-reduced-motion: reduce)'
    },
    function(ctx) {
      var reduce = ctx.conditions.reduceMotion;
      var isDesktop = ctx.conditions.desktop;
      clearTimeout(safetyTimer);
      if (reduce) return;

      var $ = gsap.utils.toArray;

      // ========================================
      // 1. SCROLL REVEAL SYSTEM
      // ========================================

      // Single element fade-up
      $('.reveal').forEach(function(el) {
        gsap.set(el, { y: 30, autoAlpha: 0 });
        ScrollTrigger.create({
          trigger: el, start: 'top 92%', once: true,
          onEnter: function() { gsap.to(el, { y: 0, autoAlpha: 1, duration: 0.6, ease: 'power2.out' }); }
        });
      });

      // Scale in
      $('.reveal-scale').forEach(function(el) {
        gsap.set(el, { scale: 0.9, autoAlpha: 0 });
        ScrollTrigger.create({
          trigger: el, start: 'top 92%', once: true,
          onEnter: function() { gsap.to(el, { scale: 1, autoAlpha: 1, duration: 0.6, ease: 'back.out(1.4)' }); }
        });
      });

      // Slide left
      $('.reveal-left').forEach(function(el) {
        gsap.set(el, { x: -40, autoAlpha: 0 });
        ScrollTrigger.create({
          trigger: el, start: 'top 92%', once: true,
          onEnter: function() { gsap.to(el, { x: 0, autoAlpha: 1, duration: 0.6, ease: 'power2.out' }); }
        });
      });

      // Slide right
      $('.reveal-right').forEach(function(el) {
        gsap.set(el, { x: 40, autoAlpha: 0 });
        ScrollTrigger.create({
          trigger: el, start: 'top 92%', once: true,
          onEnter: function() { gsap.to(el, { x: 0, autoAlpha: 1, duration: 0.6, ease: 'power2.out' }); }
        });
      });

      // Stagger children
      $('.reveal-stagger').forEach(function(container) {
        var kids = $(container.children);
        if (!kids.length) return;
        gsap.set(kids, { y: 35, autoAlpha: 0 });
        ScrollTrigger.create({
          trigger: container, start: 'top 90%', once: true,
          onEnter: function() {
            gsap.to(kids, { y: 0, autoAlpha: 1, duration: 0.5, stagger: 0.08, ease: 'power2.out' });
          }
        });
      });

      // ========================================
      // 2. HERO ENTRANCE (index page)
      // ========================================
      var hero = document.querySelector('.hero');
      if (hero) {
        var tag = hero.querySelector('[style*="inline-block"]');
        var h1 = hero.querySelector('h1');
        var desc = hero.querySelector('p');
        var btns = hero.querySelectorAll('.btn, a.btn');
        var items = [tag, h1, desc].concat(Array.from(btns)).filter(Boolean);

        gsap.set(items, { y: 30, autoAlpha: 0 });
        var heroTl = gsap.timeline({ delay: 0.3 });
        heroTl.to(items[0], { y: 0, autoAlpha: 1, duration: 0.5, ease: 'power3.out' });
        if (items[1]) heroTl.to(items[1], { y: 0, autoAlpha: 1, duration: 0.6, ease: 'power3.out' }, '-=0.2');
        if (items[2]) heroTl.to(items[2], { y: 0, autoAlpha: 1, duration: 0.5, ease: 'power3.out' }, '-=0.3');
        for (var bi = 3; bi < items.length; bi++) {
          heroTl.to(items[bi], { y: 0, autoAlpha: 1, duration: 0.4, ease: 'power2.out' }, '-=0.2');
        }

        // Parallax gradient orbs (desktop)
        if (isDesktop) {
          var orbs = hero.querySelectorAll('[style*="radial-gradient"]');
          orbs.forEach(function(orb) {
            gsap.to(orb, {
              y: -50,
              scrollTrigger: { trigger: hero, start: 'top top', end: 'bottom top', scrub: 1 }
            });
          });
        }
      }

      // ========================================
      // 3. COUNTER ANIMATION
      // ========================================
      $('[data-gsap="counter"]').forEach(function(el) {
        var target = parseInt(el.getAttribute('data-target') || el.textContent);
        if (isNaN(target) || target <= 0) return;
        var obj = { v: 0 };
        ScrollTrigger.create({
          trigger: el, start: 'top 92%', once: true,
          onEnter: function() {
            gsap.to(obj, {
              v: target, duration: 1.5, ease: 'power2.out',
              onUpdate: function() { el.textContent = Math.round(obj.v); }
            });
          }
        });
      });

      // Stat numbers (tabular-nums)
      $('[style*="tabular-nums"]').forEach(function(el) {
        var target = parseInt(el.textContent);
        if (isNaN(target) || target <= 0) return;
        var obj = { v: 0 };
        ScrollTrigger.create({
          trigger: el, start: 'top 92%', once: true,
          onEnter: function() {
            gsap.to(obj, {
              v: target, duration: 1.5, ease: 'power2.out',
              onUpdate: function() { el.textContent = Math.round(obj.v); }
            });
          }
        });
      });

      // Score circle
      var scoreEl = document.querySelector('.score-circle, #total-score, [style*="font-size: 72px"]');
      if (scoreEl) {
        var sv = parseInt(scoreEl.textContent);
        if (!isNaN(sv) && sv > 0) {
          scoreEl.textContent = '0';
          var sObj = { v: 0 };
          gsap.to(sObj, {
            v: sv, duration: 2, ease: 'power2.out', delay: 0.5,
            onUpdate: function() { scoreEl.textContent = Math.round(sObj.v); },
            onComplete: function() {
              gsap.fromTo(scoreEl, { scale: 1 }, { scale: 1.08, duration: 0.15, yoyo: true, repeat: 1, ease: 'power2.inOut' });
            }
          });
        }
      }

      // ========================================
      // 4. PROGRESS BARS
      // ========================================
      $('.dim-fill, [data-gsap="progress-bar"]').forEach(function(bar) {
        var w = bar.style.width || bar.getAttribute('data-width');
        if (!w || w === '0%') return;
        bar.style.width = '0%';
        ScrollTrigger.create({
          trigger: bar, start: 'top 92%', once: true,
          onEnter: function() { gsap.to(bar, { width: w, duration: 1, ease: 'power2.out' }); }
        });
      });

      // ========================================
      // 5. CARD SYSTEM
      // ========================================

      // Hover lift (desktop)
      if (isDesktop) {
        document.addEventListener('mouseenter', function(e) {
          var card = e.target.closest('.card');
          if (card && !card.closest('.modal')) {
            gsap.to(card, { y: -4, boxShadow: '0 8px 25px rgba(0,0,0,0.1)', duration: 0.3, ease: 'power2.out' });
          }
        }, true);
        document.addEventListener('mouseleave', function(e) {
          var card = e.target.closest('.card');
          if (card) {
            gsap.to(card, { y: 0, boxShadow: '', duration: 0.4, ease: 'power2.out' });
          }
        }, true);
      }

      // ========================================
      // 6. NAVBAR SCROLL EFFECT
      // ========================================
      var navbar = document.querySelector('.navbar');
      if (navbar) {
        ScrollTrigger.create({
          start: 'top -80',
          onUpdate: function(self) {
            if (self.progress > 0) {
              gsap.to(navbar, { boxShadow: '0 2px 12px rgba(0,0,0,0.08)', duration: 0.3 });
            } else {
              gsap.to(navbar, { boxShadow: 'none', duration: 0.3 });
            }
          }
        });
      }

      // ========================================
      // 7. BUTTON FEEDBACK
      // ========================================
      document.addEventListener('click', function(e) {
        var btn = e.target.closest('.btn');
        if (btn) gsap.fromTo(btn, { scale: 0.97 }, { scale: 1, duration: 0.3, ease: 'back.out(2)' });
      });

      // ========================================
      // 8. MODAL ANIMATION
      // ========================================
      var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(m) {
          if (m.target.classList.contains('modal')) {
            var content = m.target.querySelector('.modal-content');
            if (!content) return;
            if (m.target.classList.contains('active')) {
              gsap.fromTo(content, { scale: 0.92, autoAlpha: 0 }, { scale: 1, autoAlpha: 1, duration: 0.35, ease: 'back.out(1.2)' });
            }
          }
        });
      });
      document.querySelectorAll('.modal').forEach(function(modal) {
        observer.observe(modal, { attributes: true, attributeFilter: ['class'] });
      });

      // ========================================
      // 9. TOAST NOTIFICATION
      // ========================================
      var toastObserver = new MutationObserver(function(mutations) {
        mutations.forEach(function(m) {
          m.addedNodes.forEach(function(node) {
            if (node.classList && node.classList.contains('toast')) {
              gsap.fromTo(node, { x: 80, autoAlpha: 0 }, { x: 0, autoAlpha: 1, duration: 0.4, ease: 'power3.out' });
              gsap.to(node, { x: 80, autoAlpha: 0, duration: 0.3, ease: 'power2.in', delay: 2.7 });
            }
          });
        });
      });
      var toastContainer = document.getElementById('toast-container');
      if (toastContainer) {
        toastObserver.observe(toastContainer, { childList: true });
      }

      // ========================================
      // 10. TEXT REVEAL
      // ========================================
      $('[data-gsap="text-reveal"]').forEach(function(el) {
        var text = el.textContent;
        el.innerHTML = '';
        text.split('').forEach(function(char) {
          var span = document.createElement('span');
          span.textContent = char === ' ' ? '\u00a0' : char;
          span.style.display = 'inline-block';
          span.style.opacity = '0';
          el.appendChild(span);
        });
        var spans = el.querySelectorAll('span');
        ScrollTrigger.create({
          trigger: el, start: 'top 92%', once: true,
          onEnter: function() {
            gsap.to(spans, { autoAlpha: 1, y: 0, duration: 0.05, stagger: 0.03, ease: 'none' });
          }
        });
        gsap.set(spans, { y: 10, autoAlpha: 0 });
      });

      // ========================================
      // 11. PAGE ENTRANCE
      // ========================================
      var main = document.querySelector('main');
      if (main) {
        gsap.fromTo(main, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.4, ease: 'power1.out' });
      }

      // ========================================
      // 12. BACK TO TOP
      // ========================================
      var btt = document.querySelector('.back-to-top');
      if (btt) {
        gsap.set(btt, { autoAlpha: 0, y: 20 });
        ScrollTrigger.create({
          start: 'top -300',
          onUpdate: function(self) {
            if (self.progress > 0.05) {
              gsap.to(btt, { autoAlpha: 1, y: 0, duration: 0.3, pointerEvents: 'auto' });
            } else {
              gsap.to(btt, { autoAlpha: 0, y: 20, duration: 0.3, pointerEvents: 'none' });
            }
          }
        });
        btt.addEventListener('click', function() {
          window.scrollTo({ top: 0, behavior: 'smooth' });
        });
      }

      // Final refresh
      ScrollTrigger.refresh();
    }
  );
})();
