const categorySelect = document.getElementById('loanCategorySelect');
const amountInput = document.getElementById('loanAmountInput');
const amountSlider = document.getElementById('loanAmountSlider');
const savingsInput = document.getElementById('savingsBalanceInput');
const savingsSlider = document.getElementById('savingsBalanceSlider');
const netSalaryInput = document.getElementById('netSalaryInput');
const tenureChips = document.querySelectorAll('#tenureChipGroup .tenure-chip');

const rateBadgeDisplay = document.getElementById('rateBadgeDisplay');
const maxAmtLabelDisplay = document.getElementById('maxAmtLabelDisplay');
const sliderMaxAmtText = document.getElementById('sliderMaxAmtText');
const tenureLimitDisplay = document.getElementById('tenureLimitDisplay');
const loanAmountValidationMsg = document.getElementById('loanAmountValidationMsg');
const savingsValidationMsg = document.getElementById('savingsValidationMsg');

const summaryMonthlyFigure = document.querySelector('#summaryMonthlyInstallment .figure');
const summaryPrincipal = document.getElementById('summaryPrincipal');
const summaryRateText = document.getElementById('summaryRateText');
const summaryTotalInterest = document.getElementById('summaryTotalInterest');
const summaryTotalPayable = document.getElementById('summaryTotalPayable');

const affordabilityBadge = document.getElementById('affordabilityBadge');
const affordabilityText = document.getElementById('affordabilityText');
const affordabilityIcon = document.getElementById('affordabilityIcon');

const eligibilityBanner = document.getElementById('summaryEligibilityBanner');
const eligibilityTitleText = document.getElementById('eligibilityTitleText');
const eligibilityDescText = document.getElementById('eligibilityDescText');
const eligibilityIconBox = document.getElementById('eligibilityIconBox');

const scheduleTableBody = document.getElementById('scheduleTableBody');
const toggleScheduleBtn = document.getElementById('toggleScheduleBtn');
const scheduleTableWrap = document.getElementById('scheduleTableWrap');
const sendWaCalcBtn = document.getElementById('sendWaCalcBtn');

const toggleSalaryDrawerBtn = document.getElementById('toggleSalaryDrawerBtn');
const optionalSalaryBox = document.getElementById('optionalSalaryBox');
const salaryDrawerIcon = document.getElementById('salaryDrawerIcon');

let currentSelectedMonths = 24;
let isSalaryDrawerOpen = false;

function setValidationMsg(el, text) {
    if (!el) return;
    el.innerHTML = text ? '<span class="material-symbols-outlined">error</span>' + text : '';
}

if (toggleSalaryDrawerBtn && optionalSalaryBox && salaryDrawerIcon) {
    toggleSalaryDrawerBtn.addEventListener('click', () => {
        isSalaryDrawerOpen = !isSalaryDrawerOpen;
        toggleSalaryDrawerBtn.classList.toggle('open', isSalaryDrawerOpen);
        if (isSalaryDrawerOpen) {
            optionalSalaryBox.classList.add('open');
            salaryDrawerIcon.textContent = 'add';
            if (affordabilityBadge) affordabilityBadge.classList.add('open');
        } else {
            optionalSalaryBox.classList.remove('open');
            salaryDrawerIcon.textContent = 'add';
            if (affordabilityBadge) affordabilityBadge.classList.remove('open');
        }
        runFullCalculation();
    });
}


function paintSliderFill(sliderEl) {
    const min = parseFloat(sliderEl.min);
    const max = parseFloat(sliderEl.max);
    const val = parseFloat(sliderEl.value);
    const pct = max > min ? ((val - min) / (max - min)) * 100 : 0;
    sliderEl.style.background = `linear-gradient(to right, var(--primary-green) ${pct}%, var(--border-color) ${pct}%)`;
}

function parseMoneyValue(raw) {
    const digits = String(raw).replace(/[^0-9]/g, '');
    return digits ? parseInt(digits, 10) : 0;
}

function syncSliderAndInput(inputEl, sliderEl, validationEl, labelName) {
    if (!inputEl || !sliderEl) return;
    inputEl.addEventListener('input', () => {
        const val = parseMoneyValue(inputEl.value);
        const min = parseFloat(sliderEl.min);
        const max = parseFloat(sliderEl.max);
        if (val > max) {
            setValidationMsg(validationEl, `Maximum for ${labelName} is GH¢${max.toLocaleString('en-US')}.`);
        } else if (val > 0 && val < min) {
            setValidationMsg(validationEl, `Minimum for ${labelName} is GH¢${min.toLocaleString('en-US')}.`);
        } else {
            setValidationMsg(validationEl, '');
        }
        sliderEl.value = Math.max(min, Math.min(max, val || min));
        paintSliderFill(sliderEl);
        runFullCalculation();
    });
    inputEl.addEventListener('blur', () => {
        const min = parseFloat(sliderEl.min);
        const max = parseFloat(sliderEl.max);
        let val = parseMoneyValue(inputEl.value) || min;
        val = Math.max(min, Math.min(max, val));
        inputEl.value = val.toLocaleString('en-US');
        sliderEl.value = val;
        paintSliderFill(sliderEl);
        setValidationMsg(validationEl, '');
        runFullCalculation();
    });
    sliderEl.addEventListener('input', () => {
        inputEl.value = parseFloat(sliderEl.value).toLocaleString('en-US');
        paintSliderFill(sliderEl);
        setValidationMsg(validationEl, '');
        runFullCalculation();
    });
    paintSliderFill(sliderEl);
}

syncSliderAndInput(amountInput, amountSlider, loanAmountValidationMsg, 'this facility');
syncSliderAndInput(savingsInput, savingsSlider, savingsValidationMsg, 'this estimate');

if (netSalaryInput) {
    netSalaryInput.addEventListener('input', runFullCalculation);
}

if (tenureChips) {
    tenureChips.forEach(chip => {
        chip.addEventListener('click', () => {
            if (chip.disabled) return;
            tenureChips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            currentSelectedMonths = parseInt(chip.getAttribute('data-months')) || 24;
            runFullCalculation();
        });
    });
}

function updateCategoryConstraints() {
    if (!categorySelect) return;
    const opt = categorySelect.options[categorySelect.selectedIndex];
    const rate = parseFloat(opt.getAttribute('data-rate'));
    const maxAmt = parseFloat(opt.getAttribute('data-max-amt'));
    const maxMo = parseInt(opt.getAttribute('data-max-mo'));

    if (rateBadgeDisplay) rateBadgeDisplay.textContent = `${rate}% Flat / Annum`;
    if (maxAmtLabelDisplay) maxAmtLabelDisplay.textContent = `Max: GH¢ ${maxAmt.toLocaleString('en-US')}`;
    if (sliderMaxAmtText) sliderMaxAmtText.textContent = `Max GH¢${maxAmt.toLocaleString('en-US')}`;
    if (tenureLimitDisplay) tenureLimitDisplay.textContent = `Up to ${maxMo} Months`;

    if (amountInput && amountSlider) {
        amountSlider.max = maxAmt;
        if (parseMoneyValue(amountInput.value) > maxAmt) {
            amountInput.value = maxAmt.toLocaleString('en-US');
            amountSlider.value = maxAmt;
        }
        paintSliderFill(amountSlider);
        setValidationMsg(loanAmountValidationMsg, '');
    }

    if (tenureChips) {
        let activeValid = false;
        tenureChips.forEach(chip => {
            const m = parseInt(chip.getAttribute('data-months'));
            if (m > maxMo) {
                chip.disabled = true;
                chip.classList.remove('active');
            } else {
                chip.disabled = false;
                if (m === currentSelectedMonths) activeValid = true;
            }
        });
        if (!activeValid) {
            let highestAvailable = 12;
            tenureChips.forEach(chip => {
                if (!chip.disabled) {
                    chip.classList.remove('active');
                    highestAvailable = parseInt(chip.getAttribute('data-months'));
                }
            });
            currentSelectedMonths = highestAvailable;
            tenureChips.forEach(chip => {
                if (parseInt(chip.getAttribute('data-months')) === currentSelectedMonths) {
                    chip.classList.add('active');
                }
            });
        }
    }

    runFullCalculation();
}

if (categorySelect) {
    categorySelect.addEventListener('change', updateCategoryConstraints);
}

const categoryTrigger = document.getElementById('categoryTrigger');
const categoryTriggerLabel = document.getElementById('categoryTriggerLabel');
const categoryPanel = document.getElementById('categoryPanel');
const categoryOptions = categoryPanel ? Array.from(categoryPanel.querySelectorAll('.custom-select-option')) : [];
let highlightedIndex = 0;

function openCategoryPanel() {
    categoryPanel.classList.add('open');
    categoryTrigger.classList.add('open');
    categoryTrigger.setAttribute('aria-expanded', 'true');
    highlightedIndex = categorySelect.selectedIndex;
    highlightOption(highlightedIndex);
    categoryPanel.focus();
}

function closeCategoryPanel() {
    categoryPanel.classList.remove('open');
    categoryTrigger.classList.remove('open');
    categoryTrigger.setAttribute('aria-expanded', 'false');
}

function highlightOption(index) {
    categoryOptions.forEach((opt, i) => opt.classList.toggle('highlighted', i === index));
    const el = categoryOptions[index];
    if (el) el.scrollIntoView({ block: 'nearest' });
}

function selectCategoryIndex(index) {
    categorySelect.selectedIndex = index;
    categoryOptions.forEach((opt, i) => {
        opt.classList.toggle('active', i === index);
        opt.setAttribute('aria-selected', i === index ? 'true' : 'false');
    });
    categoryTriggerLabel.textContent = categorySelect.options[index].value;
    categorySelect.dispatchEvent(new Event('change'));
    closeCategoryPanel();
    categoryTrigger.focus();
}

if (categoryTrigger && categoryPanel) {
    categoryTrigger.addEventListener('click', () => {
        categoryPanel.classList.contains('open') ? closeCategoryPanel() : openCategoryPanel();
    });

    categoryOptions.forEach((opt, i) => {
        opt.addEventListener('click', () => selectCategoryIndex(i));
        opt.addEventListener('mouseenter', () => { highlightedIndex = i; highlightOption(i); });
    });

    categoryPanel.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            highlightedIndex = Math.min(highlightedIndex + 1, categoryOptions.length - 1);
            highlightOption(highlightedIndex);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            highlightedIndex = Math.max(highlightedIndex - 1, 0);
            highlightOption(highlightedIndex);
        } else if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            selectCategoryIndex(highlightedIndex);
        } else if (e.key === 'Escape') {
            closeCategoryPanel();
            categoryTrigger.focus();
        }
    });

    document.addEventListener('click', (e) => {
        if (!categoryTrigger.contains(e.target) && !categoryPanel.contains(e.target)) {
            closeCategoryPanel();
        }
    });
}

function runFullCalculation() {
    if (!categorySelect || !amountInput || !savingsInput) return;

    const opt = categorySelect.options[categorySelect.selectedIndex];
    const facilityName = opt.value || "Personal & Emergency Fast-Track Loan";
    const annualRatePercent = parseFloat(opt.getAttribute('data-rate')) || 15;
    const categoryMaxAmt = parseFloat(opt.getAttribute('data-max-amt')) || 100000;
    const amount = parseMoneyValue(amountInput.value) || 15000;
    const savings = parseMoneyValue(savingsInput.value) || 6000;
    const salary = parseFloat(netSalaryInput ? netSalaryInput.value : 4500) || 4500;
    const months = currentSelectedMonths || 24;

    const totalInterest = amount * ((annualRatePercent / 100) * (months / 12));
    const totalPayable = amount + totalInterest;
    const monthlyInstallment = totalPayable / months;

    if (summaryMonthlyFigure) summaryMonthlyFigure.textContent = monthlyInstallment.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (summaryPrincipal) summaryPrincipal.textContent = 'GH¢ ' + amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (summaryRateText) summaryRateText.textContent = `${annualRatePercent.toFixed(2)}% / annum`;
    if (summaryTotalInterest) summaryTotalInterest.textContent = 'GH¢ ' + totalInterest.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (summaryTotalPayable) summaryTotalPayable.textContent = 'GH¢ ' + totalPayable.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    if (isSalaryDrawerOpen && affordabilityBadge && affordabilityText && affordabilityIcon) {
        const dtiPct = Math.round((monthlyInstallment / salary) * 100);
        affordabilityBadge.className = 'affordability-badge open';
        if (dtiPct <= 30) {
            affordabilityBadge.classList.add('afford-healthy');
            affordabilityIcon.textContent = 'check_circle';
            affordabilityText.innerHTML = `<strong>Healthy Load Ratio</strong> (${dtiPct}% of take-home pay)`;
        } else if (dtiPct <= 40) {
            affordabilityBadge.classList.add('afford-moderate');
            affordabilityIcon.textContent = 'warning';
            affordabilityText.innerHTML = `<strong>Moderate Load</strong> (${dtiPct}% of pay, consider extending tenure)`;
        } else {
            affordabilityBadge.classList.add('afford-high');
            affordabilityIcon.textContent = 'error';
            affordabilityText.innerHTML = `<strong>High Debt Ratio</strong> (${dtiPct}% of pay, longer duration recommended)`;
        }
    } else if (affordabilityBadge) {
        affordabilityBadge.className = 'affordability-badge';
    }

    // Fast-Track eligibility is capped at the category's own published limit —
    // otherwise a high savings balance could imply an entitlement (e.g. GH¢300,000
    // on a Personal & Emergency Loan) that exceeds what that facility actually allows.
    const maxFastTrackLimit = Math.min(savings * 3, categoryMaxAmt);
    if (eligibilityBanner && eligibilityTitleText && eligibilityDescText && eligibilityIconBox) {
        if (amount <= maxFastTrackLimit) {
            eligibilityBanner.classList.remove('requires-review');
            eligibilityIconBox.style.color = '#34D399';
            eligibilityIconBox.textContent = 'verified';
            eligibilityTitleText.textContent = 'Verified Fast-Track Eligible';
            eligibilityDescText.textContent = `Your GH¢${savings.toLocaleString('en-US')} savings unlocks up to GH¢${maxFastTrackLimit.toLocaleString('en-US')} in Fast-Track credit without external guarantors.`;
        } else {
            eligibilityBanner.classList.add('requires-review');
            eligibilityIconBox.style.color = '#FCD34D';
            eligibilityIconBox.textContent = 'warning';
            eligibilityTitleText.textContent = 'Requires Guarantor or Committee Sign-Off';
            eligibilityDescText.textContent = `Requested amount exceeds your 3x savings limit (GH¢${maxFastTrackLimit.toLocaleString('en-US')}). Application will be routed to the Loans Committee or requires a qualified guarantor.`;
        }
    }

    if (sendWaCalcBtn) {
        sendWaCalcBtn.onclick = () => {
            const textMsg = `Hello GCPCUL! I just used the calculator for a *${facilityName}*:\n\n` +
                `• *Requested Amount:* GH¢ ${amount.toLocaleString('en-US')}\n` +
                `• *Tenure:* ${months} Months (${annualRatePercent}% Flat/Annum)\n` +
                `• *Estimated Installment:* GH¢ ${monthlyInstallment.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/mo\n` +
                `• *Current Regular Savings:* GH¢ ${savings.toLocaleString('en-US')}\n\n` +
                `I would like to initiate my application!`;
            const encoded = encodeURIComponent(textMsg);
            window.open(`https://wa.me/233548685362?text=${encoded}`, '_blank');
        };
    }

    if (scheduleTableBody) {
        scheduleTableBody.innerHTML = '';
        const monthlyPrincipal = amount / months;
        const monthlyInterest = totalInterest / months;
        let remainingBalance = totalPayable;

        for (let m = 1; m <= months; m++) {
            remainingBalance -= (monthlyPrincipal + monthlyInterest);
            if (remainingBalance < 0 || m === months) remainingBalance = 0;

            const row = document.createElement('tr');
            row.innerHTML = `
            <td>Month ${m}</td>
            <td>GH¢ ${monthlyPrincipal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
            <td>GH¢ ${monthlyInterest.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
            <td><strong>GH¢ ${(monthlyPrincipal + monthlyInterest).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong></td>
            <td>GH¢ ${remainingBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
          `;
            scheduleTableBody.appendChild(row);
        }
    }
}

if (toggleScheduleBtn && scheduleTableWrap) {
    toggleScheduleBtn.addEventListener('click', () => {
        if (scheduleTableWrap.style.display === 'none') {
            scheduleTableWrap.style.display = 'block';
            toggleScheduleBtn.innerHTML = '<span>Hide Schedule Table ↑</span>';
        } else {
            scheduleTableWrap.style.display = 'none';
            toggleScheduleBtn.innerHTML = '<span>Show Payment Plan ↓</span>';
        }
    });
}

updateCategoryConstraints();
