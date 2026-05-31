/**
 * SLB GSAP Animations — Safe version
 * Uses gsap.to() with gsap.set() instead of gsap.from() to avoid FOUC
 * Falls back to visible if anything goes wrong
 */
(function() {
  'use strict';

  // Safety timeout: if GSAP doesn't init in 2s, show everything
  var safetyTimer = setTimeout(function() {
    document.querySelectorAll('.gsap-hidden').forEach(function(el) {
      el.classList.remove('gsap-hidden');
    });
  }, 2000);

  if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') {
    clearTimeout(safetyTimer);
    return;
  }

  gsap.registerPlugin(ScrollTrigger);

  var mm = gsap.matchMedia();

  mm.add(
    {
      isDesktop: '(min-width: 769px)',
      isMobile: '(max-width: 768px)',
      reduceMotion: '(prefers-reduced-motion: reduce)'
    },
    function(context) {
      var reduceMotion = context.conditions.reduceMotion;
      var isDesktop = context.conditions.isDesktop;

      clearTimeout(safetyTimer);

      if (reduceMotion) return;

      // ========================================
      // 1. Scroll reveal — use gsap.to() (safe)
      // ========================================
      gsap.utils.toArray('.reveal').forEach(function(el) {
        gsap.set(el, { y: 30, autoAlpha: 0 });
        ScrollTrigger.create({
          trigger: el,
          start: 'top 90%',
          once: true,
          onEnter: function() {
            gsap.to(el, { y: 0, autoAlpha: 1, duration: 0.7, ease: 'power2.out' });
          }
        });
      });

      // Stagger children
      gsap.utils.toArray('.reveal-stagger').forEach(function(container) {
        var children = gsap.utils.toArray(container.children);
        if (!children.length) return;

        gsap.set(children, { y: 40, autoAlpha: 0 });
        ScrollTrigger.create({
          trigger: container,
          start: 'top 88%',
          once: true,
          onEnter: function() {
            gsap.to(children, { y: 0, autoAlpha: 1, duration: 0.6, stagger: 0.1, ease: 'power2.out' });
          }
        });
      });

      // ========================================
      // 2. Hero entrance
      // ========================================
      var hero = document.querySelector('.hero');
      if (hero) {
        var heroItems = hero.querySelectorAll('h1, p, .btn, [style*="inline-block"]');
        if (heroItems.length) {
          gsap.set(heroItems, { y: 30, autoAlpha: 0 });
          var heroTl = gsap.timeline({ delay: 0.2 });
          heroTl.to(heroItems, {
            y: 0,
            autoAlpha: 1,
            duration: 0.7,
            stagger: 0.12,
            ease: 'power3.out'
          });
        }
      }

      // ========================================
      // 3. Stat counter
      // ========================================
      gsap.utils.toArray('[style*="tabular-nums"]').forEach(function(el) {
        var target = parseInt(el.textContent);
        if (isNaN(target) || target === 0) return;

        var obj = { val: 0 };
        ScrollTrigger.create({
          trigger: el,
          start: 'top 92%',
          once: true,
          onEnter: function() {
            gsap.to(obj, {
              val: target,
              duration: 1.5,
              ease: 'power2.out',
              onUpdate: function() { el.textContent = Math.round(obj.val); }
            });
          }
        });
      });

      // ========================================
      // 4. Card hover (desktop)
      // ========================================
      if (isDesktop) {
        document.addEventListener('mouseenter', function(e) {
          var card = e.target.closest('.card');
          if (card) gsap.to(card, { y: -4, duration: 0.3, ease: 'power2.out' });
        }, true);
        document.addEventListener('mouseleave', function(e) {
          var card = e.target.closest('.card');
          if (card) gsap.to(card, { y: 0, duration: 0.4, ease: 'power2.out' });
        }, true);
      }

      // ========================================
      // 5. Score counter
      // ========================================
      var scoreEl = document.querySelector('.score-circle, [style*="font-size: 64px"]');
      if (scoreEl) {
        var scoreVal = parseInt(scoreEl.textContent);
        if (!isNaN(scoreVal) && scoreVal > 0) {
          scoreEl.textContent = '0';
          var scoreObj = { val: 0 };
          gsap.to(scoreObj, {
            val: scoreVal,
            duration: 2,
            ease: 'power2.out',
            delay: 0.5,
            onUpdate: function() { scoreEl.textContent = Math.round(scoreObj.val); },
            onComplete: function() {
              gsap.fromTo(scoreEl, { scale: 1 }, { scale: 1.1, duration: 0.15, yoyo: true, repeat: 1 });
            }
          });
        }
      }

      // ========================================
      // 6. Dimension bars
      // ========================================
      gsap.utils.toArray('.dim-fill').forEach(function(bar) {
        var w = bar.style.width;
        if (!w || w === '0%') return;
        bar.style.width = '0%';
        ScrollTrigger.create({
          trigger: bar,
          start: 'top 92%',
          once: true,
          onEnter: function() {
            gsap.to(bar, { width: w, duration: 1, ease: 'power2.out' });
          }
        });
      });

      // ========================================
      // 7. Navbar shadow
      // ========================================
      var navbar = document.querySelector('.navbar');
      if (navbar) {
        ScrollTrigger.create({
          start: 'top -80',
          onUpdate: function(self) {
            if (self.progress > 0) {
              navbar.style.boxShadow = '0 1px 8px rgba(0,0,0,0.08)';
            } else {
              navbar.style.boxShadow = '';
            }
          }
        });
      }

      // ========================================
      // 8. Button click feedback
      // ========================================
      document.addEventListener('click', function(e) {
        var btn = e.target.closest('.btn');
        if (btn) gsap.fromTo(btn, { scale: 0.97 }, { scale: 1, duration: 0.3, ease: 'back.out(2)' });
      });

      ScrollTrigger.refresh();
    }
  );
})();
