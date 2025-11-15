/**
 * Main Application Logic
 */

// State
let currentCompany = null;
let currentStatement = 'income_statement';
let currentPeriod = 'quarterly';
let currentYear = new Date().getFullYear();
let currentQuarter = 4;
let currentStatementData = null;

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const searchResults = document.getElementById('searchResults');
const companySection = document.getElementById('companySection');
const companyName = document.getElementById('companyName');
const companyTicker = document.getElementById('companyTicker');
const companyCIK = document.getElementById('companyCIK');
const companyExchange = document.getElementById('companyExchange');
const quarterlyBtn = document.getElementById('quarterlyBtn');
const annualBtn = document.getElementById('annualBtn');
const yearSelect = document.getElementById('yearSelect');
const quarterSelect = document.getElementById('quarterSelect');
const quarterLabel = document.getElementById('quarterLabel');
const tabButtons = document.querySelectorAll('.tab-button');
const statementTitle = document.getElementById('statementTitle');
const statementTable = document.getElementById('statementTable');
const exportButton = document.getElementById('exportButton');
const loadingIndicator = document.getElementById('loadingIndicator');
const errorMessage = document.getElementById('errorMessage');

// Event Listeners
searchInput.addEventListener('input', debounce(handleSearch, 300));
searchButton.addEventListener('click', handleSearchButtonClick);
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSearchButtonClick();
});

quarterlyBtn.addEventListener('click', () => setPeriod('quarterly'));
annualBtn.addEventListener('click', () => setPeriod('annual'));

yearSelect.addEventListener('change', () => {
    currentYear = parseInt(yearSelect.value);
    loadStatement();
});

quarterSelect.addEventListener('change', () => {
    currentQuarter = parseInt(quarterSelect.value);
    loadStatement();
});

tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        setStatement(btn.dataset.statement);
    });
});

exportButton.addEventListener('click', exportToCSV);

// Initialize year selector
function initYearSelector() {
    const currentYearValue = new Date().getFullYear();
    yearSelect.innerHTML = '';
    for (let year = currentYearValue; year >= currentYearValue - 10; year--) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearSelect.appendChild(option);
    }
}

// Search Functions
async function handleSearch() {
    const query = searchInput.value.trim();

    if (query.length < 1) {
        searchResults.classList.add('hidden');
        return;
    }

    // Check if it's a ticker (short and all caps)
    if (query.length <= 5 && query === query.toUpperCase()) {
        // Direct ticker lookup
        try {
            const company = await api.getCompany(query);
            displayCompany(company);
            searchResults.classList.add('hidden');
        } catch (error) {
            // If not found, search by name
            searchByName(query);
        }
    } else {
        searchByName(query);
    }
}

async function searchByName(query) {
    try {
        const results = await api.searchCompanies(query);
        displaySearchResults(results);
    } catch (error) {
        console.error('Search failed:', error);
        searchResults.classList.add('hidden');
    }
}

function displaySearchResults(results) {
    if (results.length === 0) {
        searchResults.innerHTML = '<div class="search-result-item">No results found</div>';
        searchResults.classList.remove('hidden');
        return;
    }

    searchResults.innerHTML = results.map(company => `
        <div class="search-result-item" onclick="selectCompany('${company.ticker}')">
            <span class="result-ticker">${company.ticker}</span>
            <span class="result-name">${company.company_name || 'N/A'}</span>
        </div>
    `).join('');

    searchResults.classList.remove('hidden');
}

async function handleSearchButtonClick() {
    const query = searchInput.value.trim().toUpperCase();
    if (query) {
        try {
            const company = await api.getCompany(query);
            displayCompany(company);
            searchResults.classList.add('hidden');
        } catch (error) {
            showError(`Company "${query}" not found`);
        }
    }
}

async function selectCompany(ticker) {
    try {
        const company = await api.getCompany(ticker);
        displayCompany(company);
        searchResults.classList.add('hidden');
    } catch (error) {
        showError(`Failed to load company ${ticker}`);
    }
}

// Display Functions
function displayCompany(company) {
    currentCompany = company;

    companyName.textContent = company.company_name || company.ticker;
    companyTicker.textContent = company.ticker;
    companyCIK.textContent = `CIK: ${company.cik}`;
    companyExchange.textContent = company.exchange || '';

    companySection.classList.remove('hidden');

    // Load initial statement
    loadStatement();
}

function setPeriod(period) {
    currentPeriod = period;

    if (period === 'quarterly') {
        quarterlyBtn.classList.add('active');
        annualBtn.classList.remove('active');
        quarterSelect.style.display = 'inline';
        quarterLabel.style.display = 'inline';
    } else {
        annualBtn.classList.add('active');
        quarterlyBtn.classList.remove('active');
        quarterSelect.style.display = 'none';
        quarterLabel.style.display = 'none';
    }

    loadStatement();
}

function setStatement(statement) {
    currentStatement = statement;

    tabButtons.forEach(btn => {
        if (btn.dataset.statement === statement) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    const titles = {
        'income_statement': 'Income Statement',
        'balance_sheet': 'Balance Sheet',
        'cash_flow': 'Cash Flow Statement'
    };

    statementTitle.textContent = titles[statement];

    loadStatement();
}

// Load Statement
async function loadStatement() {
    if (!currentCompany) return;

    showLoading();
    hideError();

    try {
        const quarter = currentPeriod === 'quarterly' ? currentQuarter : null;
        const data = await api.getStatement(
            currentCompany.ticker,
            currentStatement,
            currentYear,
            quarter
        );

        currentStatementData = data;
        displayStatement(data);
    } catch (error) {
        showError(`Failed to load statement: ${error.message}`);
    } finally {
        hideLoading();
    }
}

function displayStatement(data) {
    if (!data.data || data.data.length === 0) {
        statementTable.innerHTML = '<p class="no-data">No data available for this period</p>';
        return;
    }

    const table = `
        <table>
            <thead>
                <tr>
                    <th>Line Item</th>
                    <th>Value</th>
                </tr>
            </thead>
            <tbody>
                ${data.data.map(item => `
                    <tr>
                        <td>${item.line_item_name}</td>
                        <td>${formatNumber(item.value)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    statementTable.innerHTML = table;
}

// Export to CSV
function exportToCSV() {
    if (!currentStatementData || !currentStatementData.data) {
        alert('No data to export');
        return;
    }

    const data = currentStatementData;
    const period = data.period_quarter ? `Q${data.period_quarter} ${data.period_year}` : `FY ${data.period_year}`;

    // Create CSV content
    let csv = `${data.ticker} - ${statementTitle.textContent} - ${period}\n\n`;
    csv += 'Line Item,Value\n';

    data.data.forEach(item => {
        const name = `"${item.line_item_name.replace(/"/g, '""')}"`;
        const value = item.value !== null ? item.value : '';
        csv += `${name},${value}\n`;
    });

    // Download file
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${data.ticker}_${currentStatement}_${period.replace(/\s/g, '_')}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Utility Functions
function formatNumber(value) {
    if (value === null || value === undefined) {
        return '-';
    }

    const num = parseFloat(value);
    if (isNaN(num)) return '-';

    return num.toLocaleString('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
}

function showLoading() {
    loadingIndicator.classList.remove('hidden');
    statementTable.innerHTML = '';
}

function hideLoading() {
    loadingIndicator.classList.add('hidden');
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
}

function hideError() {
    errorMessage.classList.add('hidden');
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize
initYearSelector();
