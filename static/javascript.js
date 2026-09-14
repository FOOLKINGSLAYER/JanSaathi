document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector("[data-password-toggle]");
    const password = document.querySelector("#password");

    if (toggle && password) {
        toggle.addEventListener("click", () => {
            const isPassword = password.type === "password";
            password.type = isPassword ? "text" : "password";
            toggle.textContent = isPassword ? "Hide" : "Show";
            toggle.setAttribute("aria-label", `${isPassword ? "Hide" : "Show"} password`);
        });
    }

    document.querySelectorAll("[data-filter-input]").forEach((input) => {
        input.addEventListener("input", () => {
            const query = input.value.toLowerCase().trim();
            document.querySelectorAll("[data-filter-item]").forEach((item) => {
                item.hidden = query && !item.dataset.filterItem.toLowerCase().includes(query);
            });
        });
    });

    const menuToggle = document.querySelector(".menu-toggle");
    const publicNav = document.querySelector("#public-nav");
    if (menuToggle && publicNav) {
        menuToggle.addEventListener("click", () => {
            const expanded = menuToggle.getAttribute("aria-expanded") === "true";
            menuToggle.setAttribute("aria-expanded", String(!expanded));
            publicNav.classList.toggle("is-open", !expanded);
        });
    }
});

/**
 * JanSaathi — Master Front-end Controller (SIH 2026)
 * Handles mobile navigation, interactive states, forms, and accessibility.
 */

document.addEventListener('DOMContentLoaded', () => {
  /* ==========================================================================
     1. Mobile Navigation & Utility Menu
     ========================================================================== */
  const menuToggle = document.querySelector('.menu-toggle');
  const publicNav = document.getElementById('public-nav');

  if (menuToggle && publicNav) {
    const toggleNav = (forceState) => {
      const isExpanded = forceState !== undefined 
        ? forceState 
        : menuToggle.getAttribute('aria-expanded') !== 'true';

      menuToggle.setAttribute('aria-expanded', isExpanded);
      publicNav.classList.toggle('is-open', isExpanded);
    };

    menuToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleNav();
    });

    // Close on outside click
    document.addEventListener('click', (event) => {
      if (
        publicNav.classList.contains('is-open') &&
        !publicNav.contains(event.target) &&
        !menuToggle.contains(event.target)
      ) {
        toggleNav(false);
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && publicNav.classList.contains('is-open')) {
        toggleNav(false);
        menuToggle.focus();
      }
    });
  }

  /* ==========================================================================
     2. Interactive Button States & Ripple Simulation
     ========================================================================== */
  const interactiveElements = document.querySelectorAll(
    '.primary-button, .header-cta, .sitemap-grid a, .menu-toggle, .search-link'
  );

  interactiveElements.forEach((btn) => {
    btn.addEventListener('mousedown', () => {
      btn.style.transform = 'scale(0.98)';
    });

    const resetTransform = () => {
      btn.style.transform = '';
    };

    btn.addEventListener('mouseup', resetTransform);
    btn.addEventListener('mouseleave', resetTransform);
  });

  /* ==========================================================================
     3. Flash Notification Stack Auto-Dismiss
     ========================================================================== */
  const flashMessages = document.querySelectorAll('.flash');

  if (flashMessages.length > 0) {
    flashMessages.forEach((flash) => {
      // Add a dismiss button if one doesn't exist
      if (!flash.querySelector('.flash-close')) {
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'flash-close';
        closeBtn.setAttribute('aria-label', 'Close message');
        closeBtn.innerHTML = '&times;';
        closeBtn.style.cssText = `
          float: right;
          background: none;
          border: none;
          font-size: 1.25rem;
          line-height: 1;
          color: inherit;
          opacity: 0.7;
          cursor: pointer;
          margin-left: 12px;
        `;
        
        closeBtn.addEventListener('click', () => dismissFlash(flash));
        flash.prepend(closeBtn);
      }
    });

    // Auto-dismiss after 6 seconds
    setTimeout(() => {
      flashMessages.forEach((flash) => dismissFlash(flash));
    }, 6000);
  }

  function dismissFlash(flashNode) {
    if (!flashNode || flashNode.dataset.dismissing) return;
    flashNode.dataset.dismissing = 'true';
    flashNode.style.transition = 'opacity 0.3s ease, transform 0.3s ease, margin 0.3s ease, height 0.3s ease';
    flashNode.style.opacity = '0';
    flashNode.style.transform = 'translateY(-8px)';
    
    setTimeout(() => {
      flashNode.remove();
    }, 300);
  }

  /* ==========================================================================
     4. Registration Role Selector State Management
     ========================================================================== */
  const roleRadios = document.querySelectorAll('.role-picker input[type="radio"]');

  if (roleRadios.length > 0) {
    const updateActiveTile = () => {
      roleRadios.forEach((radio) => {
        const parentLabel = radio.closest('label');
        if (parentLabel) {
          if (radio.checked) {
            parentLabel.setAttribute('aria-checked', 'true');
          } else {
            parentLabel.setAttribute('aria-checked', 'false');
          }
        }
      });
    };

    roleRadios.forEach((radio) => {
      radio.addEventListener('change', updateActiveTile);
    });

    updateActiveTile();
  }

  /* ==========================================================================
     5. Contact & Feedback Form Handling (Client-side validation/fallback)
     ========================================================================== */
  const contactForm = document.querySelector('.contact-form');

  if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
      // Validate inputs
      const requiredInputs = contactForm.querySelectorAll('[required]');
      let isValid = true;

      requiredInputs.forEach((input) => {
        if (!input.value.trim()) {
          isValid = false;
          input.style.borderColor = '#ef4444';
          input.focus();
        } else {
          input.style.borderColor = '';
        }
      });

      if (!isValid) {
        e.preventDefault();
        return;
      }

      // If purely prototype without backend action, reveal success state
      if (!contactForm.getAttribute('action')) {
        e.preventDefault();
        contactForm.classList.add('submitted');
        
        // Reset inputs after acknowledgement
        requiredInputs.forEach((input) => {
          input.disabled = true;
        });
        const submitBtn = contactForm.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;
      }
    });
  }

  /* ==========================================================================
     6. Accessible FAQ Accordions (Exclusive Auto-Close Option)
     ========================================================================== */
  const faqDetails = document.querySelectorAll('.faq-list details');

  faqDetails.forEach((targetDetail) => {
    targetDetail.addEventListener('toggle', () => {
      if (targetDetail.open) {
        faqDetails.forEach((detail) => {
          if (detail !== targetDetail && detail.open) {
            detail.removeAttribute('open');
          }
        });
      }
    });
  });
});

/* ==========================================================================
   Admin Dashboard & Review Interactions
   ========================================================================== */
const secondaryButtons = document.querySelectorAll('.secondary-button');

secondaryButtons.forEach((btn) => {
  btn.addEventListener('mousedown', () => {
    btn.style.transform = 'scale(0.97)';
  });
  const resetBtn = () => { btn.style.transform = ''; };
  btn.addEventListener('mouseup', resetBtn);
  btn.addEventListener('mouseleave', resetBtn);
});

// Highlight review rows on hover/focus for clearer review navigation
const reviewRows = document.querySelectorAll('.review-row');
reviewRows.forEach((row) => {
  const link = row.querySelector('.secondary-button');
  if (link) {
    row.addEventListener('click', (e) => {
      // Don't trigger twice if clicking the button directly
      if (!e.target.closest('.secondary-button')) {
        link.click();
      }
    });
    row.style.cursor = 'pointer';
  }
});

/* ==========================================================================
   Citizen Workspace: Interactive Filtering & Search
   ========================================================================== */
const filterInput = document.querySelector('[data-filter-input]');
const statusSelect = document.querySelector('[data-filter-status]');
const categorySelect = document.querySelector('[data-filter-category]');
const challengeItems = document.querySelectorAll('.challenge-row[data-filter-item]');

function applyChallengeFilters() {
  const query = filterInput ? filterInput.value.toLowerCase().trim() : '';
  const selectedStatus = statusSelect ? statusSelect.value.toLowerCase().trim() : '';
  const selectedCategory = categorySelect ? categorySelect.value.toLowerCase().trim() : '';

  challengeItems.forEach((item) => {
    const itemText = item.getAttribute('data-filter-item').toLowerCase();
    const itemStatus = (item.getAttribute('data-status') || '').toLowerCase();
    const itemCategory = (item.getAttribute('data-category') || '').toLowerCase();

    const matchesQuery = !query || itemText.includes(query);
    const matchesStatus = !selectedStatus || itemStatus.includes(selectedStatus);
    const matchesCategory = !selectedCategory || itemCategory.includes(selectedCategory);

    if (matchesQuery && matchesStatus && matchesCategory) {
      item.style.display = 'grid';
    } else {
      item.style.display = 'none';
    }
  });
}

if (filterInput) filterInput.addEventListener('input', applyChallengeFilters);
if (statusSelect) statusSelect.addEventListener('change', applyChallengeFilters);
if (categorySelect) categorySelect.addEventListener('change', applyChallengeFilters);

/* ==========================================================================
   Government Portfolio: District & Stage Filtering
   ========================================================================== */
const govSearchInput = document.querySelector('.workspace [data-filter-input]');
const districtSelect = document.querySelector('[data-filter-district]');
const stageSelect = document.querySelector('[data-filter-stage]');
const govChallengeRows = document.querySelectorAll('.challenge-list .challenge-row');

function applyGovFilters() {
  if (!govChallengeRows.length) return;

  const query = govSearchInput ? govSearchInput.value.toLowerCase().trim() : '';
  const selectedDistrict = districtSelect ? districtSelect.value.toLowerCase().trim() : '';
  const selectedStage = stageSelect ? stageSelect.value.toLowerCase().trim() : '';

  govChallengeRows.forEach((row) => {
    const itemText = (row.getAttribute('data-filter-item') || row.innerText).toLowerCase();
    const itemDistrict = (row.getAttribute('data-district') || '').toLowerCase();
    const itemStage = (row.getAttribute('data-stage') || '').toLowerCase();

    const matchesQuery = !query || itemText.includes(query);
    const matchesDistrict = !selectedDistrict || itemDistrict.includes(selectedDistrict);
    const matchesStage = !selectedStage || itemStage.includes(selectedStage);

    if (matchesQuery && matchesDistrict && matchesStage) {
      row.style.display = 'grid';
    } else {
      row.style.display = 'none';
    }
  });
}

if (govSearchInput) govSearchInput.addEventListener('input', applyGovFilters);
if (districtSelect) districtSelect.addEventListener('change', applyGovFilters);
if (stageSelect) stageSelect.addEventListener('change', applyGovFilters);

/* ==========================================================================
   Industry Collaboration Board: Interactive Filtering
   ========================================================================== */
const industrySearchInput = document.querySelector('.workspace [data-filter-input]');
const collabTypeSelect = document.querySelector('[data-filter-type]');
const opportunityCards = document.querySelectorAll('.opportunity-grid .opportunity-card');

function applyIndustryFilters() {
  if (!opportunityCards.length) return;

  const query = industrySearchInput ? industrySearchInput.value.toLowerCase().trim() : '';
  const selectedType = collabTypeSelect ? collabTypeSelect.value.toLowerCase().trim() : '';

  opportunityCards.forEach((card) => {
    const itemText = (card.getAttribute('data-filter-item') || card.innerText).toLowerCase();
    const itemType = (card.getAttribute('data-type') || '').toLowerCase();

    const matchesQuery = !query || itemText.includes(query);
    const matchesType = !selectedType || itemType.includes(selectedType) || itemText.includes(selectedType);

    if (matchesQuery && matchesType) {
      card.style.display = 'flex';
    } else {
      card.style.display = 'none';
    }
  });
}

if (industrySearchInput) industrySearchInput.addEventListener('input', applyIndustryFilters);
if (collabTypeSelect) collabTypeSelect.addEventListener('change', applyIndustryFilters);

/* ==========================================================================
   University Discovery Board: Multi-Criteria Filtering
   ========================================================================== */
const uniSearchInput = document.querySelector('.workspace [data-filter-input]');
const domainSelect = document.querySelector('[data-filter-domain]');
const prioritySelect = document.querySelector('[data-filter-priority]');
const uniChallengeRows = document.querySelectorAll('.challenge-list .challenge-row');

function applyUniFilters() {
  if (!uniChallengeRows.length) return;

  const query = uniSearchInput ? uniSearchInput.value.toLowerCase().trim() : '';
  const selectedDomain = domainSelect ? domainSelect.value.toLowerCase().trim() : '';
  const selectedPriority = prioritySelect ? prioritySelect.value.toLowerCase().trim() : '';

  uniChallengeRows.forEach((row) => {
    const itemText = (row.getAttribute('data-filter-item') || row.innerText).toLowerCase();
    const itemDomain = (row.getAttribute('data-domain') || '').toLowerCase();
    const itemPriority = (row.getAttribute('data-priority') || '').toLowerCase();

    const matchesQuery = !query || itemText.includes(query);
    const matchesDomain = !selectedDomain || itemDomain.includes(selectedDomain);
    const matchesPriority = !selectedPriority || itemPriority.includes(selectedPriority);

    if (matchesQuery && matchesDomain && matchesPriority) {
      row.style.display = 'grid';
    } else {
      row.style.display = 'none';
    }
  });
}

if (uniSearchInput) uniSearchInput.addEventListener('input', applyUniFilters);
if (domainSelect) domainSelect.addEventListener('change', applyUniFilters);
if (prioritySelect) prioritySelect.addEventListener('change', applyUniFilters);

/* ==========================================================================
   University Workspace: Action Handlers & Clarification Request
   ========================================================================== */
const clarificationBtn = document.querySelector('[data-action="request-clarification"]');
if (clarificationBtn) {
  clarificationBtn.addEventListener('click', () => {
    const userPrompt = window.prompt('Specify the clarification or additional context required from the community:');
    if (userPrompt && userPrompt.trim()) {
      alert('Clarification request recorded. The community contributor will be notified.');
    }
  });
}

const addMilestoneBtn = document.querySelector('[data-action="add-milestone"]');
if (addMilestoneBtn) {
  addMilestoneBtn.addEventListener('click', () => {
    const milestoneTitle = window.prompt('Enter new milestone description:');
    if (milestoneTitle && milestoneTitle.trim()) {
      const milestoneList = document.querySelector('.milestone-list');
      if (milestoneList) {
        const nextIndex = milestoneList.querySelectorAll('.milestone').length + 1;
        const newMilestone = document.createElement('div');
        newMilestone.className = 'milestone';
        newMilestone.innerHTML = `
          <span class="milestone-step">${nextIndex}</span>
          <div class="milestone-content">
            <strong>${milestoneTitle.trim()}</strong>
            <small>Planned next</small>
          </div>
          <b class="milestone-status">·</b>
        `;
        milestoneList.appendChild(newMilestone);
      }
    }
  });
}