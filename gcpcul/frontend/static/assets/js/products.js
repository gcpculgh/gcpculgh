document.addEventListener("DOMContentLoaded", function () {
    if (window.location.hash) {
        const targetId = window.location.hash;
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            setTimeout(() => {
                targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

                targetElement.classList.remove('glow-active');
                void targetElement.offsetWidth;

                setTimeout(() => {
                    targetElement.classList.add('glow-active');
                }, 600);

            }, 300);
        }
    }
});

const q1Buttons = document.querySelectorAll('#q1Group .toggle-opt');
const q2Buttons = document.querySelectorAll('#q2Group .toggle-opt');
const preQualTitle = document.getElementById('preQualTitle');
const preQualDesc = document.getElementById('preQualDesc');
const preQualBadge = document.getElementById('preQualStatusBadge');

let isHealthcare = 'yes';
let savingsHistory = 'yes';

function updatePreQualStatus() {
    if (!preQualTitle || !preQualDesc || !preQualBadge) return;

    if (isHealthcare === 'yes' && savingsHistory === 'yes') {
        preQualBadge.style.color = '#34D399';
        preQualBadge.innerHTML = '<span class="prequal-status-pill"><span class="material-symbols-outlined" style="font-size:1.1rem;">verified</span><span>Verified Eligible Member</span></span><img src="{% static 'assets / images / linda - landing.jpg' %}" alt="Smiling Pharmacist Member" class="prequal-avatar-thumb" onerror="this.src=\'https://images.unsplash.com/photo-1594824476967-48c8b964273f?auto=format&fit=crop&w=160&q=80\';">';
        preQualTitle.textContent = 'GH¢ 100,000.00 Fast-Track Access';
        preQualDesc.textContent = 'You qualify to borrow up to 3x your savings plus share capital immediately without committee delay or external guarantors.';
    } else if (isHealthcare === 'yes' && savingsHistory === 'new') {
        preQualBadge.style.color = '#FBBF24';
        preQualBadge.innerHTML = '<span class="prequal-status-pill"><span class="material-symbols-outlined" style="font-size:1.1rem;">schedule</span><span>New Member Fast-Track</span></span><img src="{% static 'assets / images / linda - landing.jpg' %}" alt="Smiling Pharmacist Member" class="prequal-avatar-thumb" onerror="this.src=\'https://images.unsplash.com/photo-1594824476967-48c8b964273f?auto=format&fit=crop&w=160&q=80\';">';
        preQualTitle.textContent = '90-Day Credit Acceleration Pathway';
        preQualDesc.textContent = 'Start saving GH¢100/month today. You unlock full 3x Fast-Track borrowing eligibility after your first 3 months of consistent savings.';
    } else {
        preQualBadge.style.color = '#38BDF8';
        preQualBadge.innerHTML = '<span class="prequal-status-pill"><span class="material-symbols-outlined" style="font-size:1.1rem;">hourglass_top</span><span>Pre-Qualification Review</span></span><img src="{% static 'assets / images / linda - landing.jpg' %}" alt="Smiling Pharmacist Member" class="prequal-avatar-thumb" onerror="this.src=\'https://images.unsplash.com/photo-1594824476967-48c8b964273f?auto=format&fit=crop&w=160&q=80\';">';
        preQualTitle.textContent = 'Custom Institutional Assessment';
        preQualDesc.textContent = 'Non-pharmacist healthcare institutions and associated workers can qualify through committee review under CUA stabilization guidelines.';
    }
}

if (q1Buttons && q2Buttons) {
    q1Buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            q1Buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            isHealthcare = btn.getAttribute('data-val');
            updatePreQualStatus();
        });
    });

    q2Buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            q2Buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            savingsHistory = btn.getAttribute('data-val');
            updatePreQualStatus();
        });
    });
}

const savingsInput = document.getElementById('savingsAmountInput');
const savingsSlider = document.getElementById('savingsSlider');
const presetChips = document.querySelectorAll('#savingsPresetRow .preset-chip');
const creditPowerDisplay = document.getElementById('creditPowerDisplay');
const creditPowerFigure = creditPowerDisplay ? creditPowerDisplay.querySelector('.figure') : null;
const validationMsg = document.getElementById('savingsValidationMsg');

function syncPresetChips(value) {
    presetChips.forEach(chip => {
        chip.classList.toggle('active', parseInt(chip.dataset.val, 10) === value);
    });
}

// Parses digits out of whatever the person typed (handles commas, GH¢, spaces)
function parseSavingsValue(raw) {
    const digits = String(raw).replace(/[^0-9]/g, '');
    return digits ? parseInt(digits, 10) : 0;
}

function setValidationMsg(text) {
    if (!validationMsg) return;
    if (!text) { validationMsg.innerHTML = ''; return; }
    validationMsg.innerHTML = '<span class="material-symbols-outlined">error</span>' + text;
}

function updateBorrowingPower(sourceValue, isTyping) {
    if (!savingsInput || !savingsSlider || !creditPowerFigure) return;
    const rawValue = parseSavingsValue(sourceValue);

    // While typing, warn without silently rewriting what they typed underneath their cursor.
    if (isTyping) {
        if (rawValue > 0 && rawValue < 500) {
            setValidationMsg('This estimate starts at GH¢500 in savings — we\'ll use GH¢500 until you enter more.');
        } else {
            setValidationMsg('');
        }
    } else {
        setValidationMsg('');
    }

    let savings = rawValue || 5000;
    savings = Math.max(500, Math.min(35000, savings));
    if (!isTyping) {
        savingsInput.value = savings.toLocaleString('en-US');
    }
    savingsSlider.value = savings;
    syncPresetChips(savings);
    let borrowingPower = savings * 3;
    if (borrowingPower > 100000) borrowingPower = 100000;
    creditPowerFigure.textContent = borrowingPower.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

if (savingsInput && savingsSlider) {
    savingsInput.addEventListener('input', () => updateBorrowingPower(savingsInput.value, true));
    savingsInput.addEventListener('blur', () => updateBorrowingPower(savingsInput.value, false));
    savingsSlider.addEventListener('input', () => updateBorrowingPower(savingsSlider.value, false));
    presetChips.forEach(chip => {
        chip.addEventListener('click', () => updateBorrowingPower(chip.dataset.val, false));
    });
    updateBorrowingPower(savingsInput.value, false);
}

const filterBtns = document.querySelectorAll('.filter-tab-btn');
const bentoCards = document.querySelectorAll('.bento-card');
const filterCountDisplay = document.getElementById('filterCountDisplay');

if (filterBtns && bentoCards && filterCountDisplay) {
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const target = btn.getAttribute('data-filter');
            let visibleCount = 0;

            bentoCards.forEach(card => {
                const cardCat = card.getAttribute('data-category');
                if (target === 'all' || cardCat === target) {
                    card.style.display = 'flex';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            filterCountDisplay.textContent = target === 'all'
                ? `Showing all ${visibleCount} cooperative facilities`
                : `Showing ${visibleCount} matching facility tier(s)`;
        });
    });
}
