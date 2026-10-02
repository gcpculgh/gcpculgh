const MIN_LOAN = 500;
const categorySelect = document.getElementById('loanCategory');
const loanAmount = document.getElementById('loanAmount');
const loanMonths = document.getElementById('loanMonths');
const monthlyDisplay = document.getElementById('monthlyDisplay');
const loanValidationMsg = document.getElementById('loanAmountValidationMsg');

function formatGHS(n) {
    return 'GH¢ ' + n.toLocaleString('en-GH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function setLoanValidationMsg(text) {
    if (!loanValidationMsg) return;
    loanValidationMsg.innerHTML = text ? '<span class="material-symbols-outlined">error</span>' + text : '';
}

function calculateEMI(isTyping) {
    if (!categorySelect || !loanMonths) return;
    const opt = categorySelect.options[categorySelect.selectedIndex];
    const annualRate = parseFloat(opt.getAttribute('data-rate')) || 15;
    const maxLoan = parseFloat(opt.getAttribute('data-max-amt')) || 100000;
    const rawValue = parseFloat(loanAmount.value) || 0;

    if (isTyping && rawValue > maxLoan) {
        setLoanValidationMsg(`This facility caps at GH¢${maxLoan.toLocaleString('en-US')}. Speak with a specialist for larger amounts.`);
    } else if (isTyping && rawValue > 0 && rawValue < MIN_LOAN) {
        setLoanValidationMsg('Minimum for this estimate is GH¢500.');
    } else {
        setLoanValidationMsg('');
    }

    const P = Math.max(MIN_LOAN, Math.min(maxLoan, rawValue || 15000));
    if (!isTyping) loanAmount.value = P;
    if (loanAmount.max !== String(maxLoan)) loanAmount.max = maxLoan;

    const n = parseInt(loanMonths.value, 10) || 1;
    const r = (annualRate / 100) / 12;
    const emi = P * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1);
    monthlyDisplay.textContent = formatGHS(emi) + ' / mo';
}

// ---- Select Logic for ALL dropdowns ----
const customSelectWraps = document.querySelectorAll('.custom-select-wrap');

customSelectWraps.forEach(wrap => {
    const trigger = wrap.querySelector('.custom-select-trigger');
    const label = wrap.querySelector('span[id$="TriggerLabel"]');
    const panel = wrap.querySelector('.custom-select-panel');
    const options = Array.from(wrap.querySelectorAll('.custom-select-option'));
    const hiddenSelect = wrap.querySelector('.visually-hidden-select');

    if (!trigger || !hiddenSelect) return;

    let highlightedIndex = hiddenSelect.selectedIndex > -1 ? hiddenSelect.selectedIndex : 0;

    function openPanel() {
        panel.classList.add('open');
        trigger.classList.add('open');
        trigger.setAttribute('aria-expanded', 'true');
        highlightedIndex = hiddenSelect.selectedIndex;
        highlightOption(highlightedIndex);
        panel.focus();
    }

    function closePanel() {
        panel.classList.remove('open');
        trigger.classList.remove('open');
        trigger.setAttribute('aria-expanded', 'false');
    }

    function highlightOption(index) {
        options.forEach((opt, i) => opt.classList.toggle('highlighted', i === index));
        if (options[index]) options[index].scrollIntoView({ block: 'nearest' });
    }

    function selectOption(index) {
        hiddenSelect.selectedIndex = index;
        options.forEach((opt, i) => {
            opt.classList.toggle('active', i === index);
            opt.setAttribute('aria-selected', i === index ? 'true' : 'false');
        });
        if (label && options[index]) {
            label.textContent = options[index].querySelector('.opt-name').textContent;
        }
        hiddenSelect.dispatchEvent(new Event('change'));
        closePanel();
        trigger.focus();
    }

    trigger.addEventListener('click', () => {
        panel.classList.contains('open') ? closePanel() : openPanel();
    });

    options.forEach((opt, i) => {
        opt.addEventListener('click', () => selectOption(i));
        opt.addEventListener('mouseenter', () => { highlightedIndex = i; highlightOption(i); });
    });

    // Keyboard navigation
    panel.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            highlightedIndex = Math.min(highlightedIndex + 1, options.length - 1);
            highlightOption(highlightedIndex);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            highlightedIndex = Math.max(highlightedIndex - 1, 0);
            highlightOption(highlightedIndex);
        } else if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            selectOption(highlightedIndex);
        } else if (e.key === 'Escape') {
            closePanel();
            trigger.focus();
        }
    });

    // Close when clicking outside
    document.addEventListener('click', (e) => {
        if (!wrap.contains(e.target)) closePanel();
    });
});

if (categorySelect) {
    categorySelect.addEventListener('change', () => calculateEMI(false));
}

if (loanAmount && loanMonths) {
    loanAmount.addEventListener('input', () => calculateEMI(true));
    loanAmount.addEventListener('blur', () => calculateEMI(false));
    loanMonths.addEventListener('change', () => calculateEMI(false));
    calculateEMI(false);
}

const track = document.getElementById('tcarousel');
if (track) {
    const cards = track.children;
    const dotsWrap = document.getElementById('tDots');
    const prevBtn = document.getElementById('tPrev');
    const nextBtn = document.getElementById('tNext');
    for (let i = 0; i < cards.length; i++) {
        const dot = document.createElement('button');
        dot.className = 'tdot' + (i === 0 ? ' active' : '');
        dot.addEventListener('click', () => cards[i].scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' }));
        dotsWrap.appendChild(dot);
    }
    const dots = dotsWrap.children;
    function updateActiveDot() {
        const center = track.scrollLeft + track.clientWidth / 2;
        let closest = 0, minDist = Infinity;
        for (let i = 0; i < cards.length; i++) {
            const dist = Math.abs((cards[i].offsetLeft + cards[i].clientWidth / 2) - center);
            if (dist < minDist) { minDist = dist; closest = i; }
        }
        for (let i = 0; i < dots.length; i++) dots[i].classList.toggle('active', i === closest);
    }
    track.addEventListener('scroll', () => requestAnimationFrame(updateActiveDot));
    prevBtn.addEventListener('click', () => track.scrollBy({ left: -track.clientWidth * 0.85, behavior: 'smooth' }));
    nextBtn.addEventListener('click', () => track.scrollBy({ left: track.clientWidth * 0.85, behavior: 'smooth' }));
    updateActiveDot();
}
