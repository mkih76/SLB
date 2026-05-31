/**
 * SLB GSAP Animations
 * Replaces CSS-only reveal system with GSAP ScrollTrigger
 * Respects prefers-reduced-motion
 */
(function() {
  'use strict';

  // Bail if GSAP not loaded
  if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') return;

  // Register plugin
  gsap.registerPlugin(ScrollTrigger);

  // Respect reduced motion
  const mm = gsap.matchMedia();
  mm.add(
    {
      isDesktop: '(min-width: 769px)',
      isMobile: '(max-width: 768px)',
      reduceMotion: '(prefers-reduced-motion: reduce)'
    },
    (context) => {
      const { isDesktop, reduceMotion } = context.conditions;

      // If user prefers reduced motion, skip all animations
      if (reduceMotion) {
        gsap.set('.reveal, .reveal-stagger > *, .reveal-left, .reveal-right, .reveal-scale', {
          opacity: 1, y: 0, x: 0, scale: 1
        });
        return;
      }

      // ==========================================
      // 1. Replace CSS reveal with GSAP
      // ==========================================

      // Single reveal elements (fade up)
      gsap.utils.toArray('.reveal').forEach((el, i) => {
        gsap.from(el, {
          y: 30,
          opacity: 0,
          duration: 0.7,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: el,
            start: 'top 88%',
            toggleActions: 'play none none none',
            once: true
          }
        });
      });

      // Stagger reveal (children fade up in sequence)
      gsap.utils.toArray('.reveal-stagger').forEach((container) => {
        const children = container.children;
        if (!children.length) return;

        gsap.from(children, {
          y: 40,
          opacity: 0,
          duration: 0.6,
          stagger: 0.1,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: container,
            start: 'top 85%',
            toggleActions: 'play none none none',
            once: true
          }
        });
      });

      // ==========================================
      // 2. Homepage Hero — cinematic entrance
      // ==========================================
      const hero = document.querySelector('.hero');
      if (hero) {
        const heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });

        heroTl
          .from('.hero [style*="inline-block"]', { y: -20, opacity: 0, duration: 0.6 })
          .from('.hero h1', { y: 40, opacity: 0, duration: 0.8 }, '-=0.3')
          .from('.hero p', { y: 30, opacity: 0, duration: 0.6 }, '-=0.4')
          .from('.hero .btn, .hero a.btn', { y: 20, opacity: 0, duration: 0.5, stagger: 0.15 }, '-=0.3');

        // Subtle parallax on gradient orbs
        if (isDesktop) {
          gsap.to('.hero [style*="radial-gradient"]:first-of-type', {
            y: -60,
            scrollTrigger: {
              trigger: '.hero',
              start: 'top top',
              end: 'bottom top',
              scrub: 1
            }
          });
        }
      }

      // ==========================================
      // 3. Stat counter animation
      // ==========================================
      gsap.utils.toArray('[style*="tabular-nums"]').forEach((el) => {
        const target = parseInt(el.textContent);
        if (isNaN(target) || target === 0) return;

        const obj = { val: 0 };
        gsap.to(obj, {
          val: target,
          duration: 1.5,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: el,
            start: 'top 90%',
            once: true
          },
          onUpdate: () => {
            el.textContent = Math.round(obj.val);
          }
        });
      });

      // ==========================================
      // 4. Cards — hover tilt effect (desktop only)
      // ==========================================
      if (isDesktop) {
        gsap.utils.toArray('.card').forEach((card) => {
          card.addEventListener('mouseenter', () => {
            gsap.to(card, { y: -4, duration: 0.3, ease: 'power2.out' });
          });
          card.addEventListener('mouseleave', () => {
            gsap.to(card, { y: 0, duration: 0.4, ease: 'power2.out' });
          });
        });
      }

      // ==========================================
      // 5. Score reveal animation (result page)
      // ==========================================
      const scoreEl = document.querySelector('.score-circle, [style*="font-size: 64px"]');
      if (scoreEl) {
        const scoreVal = parseInt(scoreEl.textContent);
        if (!isNaN(scoreVal)) {
          scoreEl.textContent = '0';
          const scoreObj = { val: 0 };
          gsap.to(scoreObj, {
            val: scoreVal,
            duration: 2,
            ease: 'power2.out',
            delay: 0.3,
            onUpdate: () => {
              scoreEl.textContent = Math.round(scoreObj.val);
            },
            onComplete: () => {
              // Pulse effect on completion
              gsap.fromTo(scoreEl, { scale: 1 }, { scale: 1.1, duration: 0.15, yoyo: true, repeat: 1, ease: 'power2.inOut' });
            }
          });
        }
      }

      // ==========================================
      // 6. Diagnosis page — dimension bars animate
      // ==========================================
      gsap.utils.toArray('.dim-fill').forEach((bar) => {
        const width = bar.style.width;
        bar.style.width = '0%';
        gsap.to(bar, {
          width: width,
          duration: 1,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: bar,
            start: 'top 90%',
            once: true
          }
        });
      });

      // ==========================================
      // 7. Page transition — smooth content entry
      // ==========================================
      gsap.from('main', {
        opacity: 0,
        duration: 0.4,
        ease: 'power1.out'
      });

      // ==========================================
      // 8. Back to top button animation
      // ==========================================
      const backToTop = document.querySelector('.back-to-top');
      if (backToTop) {
        ScrollTrigger.create({
          start: 'top -300',
          onUpdate: (self) => {
            if (self.direction === 1 && self.progress > 0.1) {
              gsap.to(backToTop, { opacity: 1, y: 0, duration: 0.3, pointerEvents: 'auto' });
            } else if (self.direction === -1 && self.progress < 0.05) {
              gsap.to(backToTop, { opacity: 0, y: 20, duration: 0.3, pointerEvents: 'none' });
            }
          }
        });
      }

      // ==========================================
      // 9. Navbar scroll effect
      // ==========================================
      const navbar = document.querySelector('.navbar');
      if (navbar) {
        ScrollTrigger.create({
          start: 'top -80',
          onUpdate: (self) => {
            if (self.progress > 0) {
              navbar.style.boxShadow = '0 1px 8px rgba(0,0,0,0.08)';
              navbar.style.backdropFilter = 'blur(12px)';
            } else {
              navbar.style.boxShadow = '';
              navbar.style.backdropFilter = '';
            }
          }
        });
      }

      // ==========================================
      // 10. CTA section — scale in
      // ==========================================
      const ctaSection = document.querySelector('[style*="border-radius: var(--radius-2xl)"][style*="brand-dark"]');
      if (ctaSection) {
        gsap.from(ctaSection, {
          scale: 0.95,
          opacity: 0,
          duration: 0.8,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: ctaSection,
            start: 'top 80%',
            once: true
          }
        });
      }

      // Refresh ScrollTrigger after all setup
      ScrollTrigger.refresh();
    }
  );

  // Click feedback — subtle scale on button press
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn');
    if (btn && typeof gsap !== 'undefined') {
      gsap.fromTo(btn, { scale: 0.97 }, { scale: 1, duration: 0.3, ease: 'back.out(2)' });
    }
  });

})();
