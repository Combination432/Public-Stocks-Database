/**
 * API Client for US Financial Statement Database
 */

class FinancialAPI {
    constructor(baseURL, apiKey) {
        this.baseURL = baseURL || 'http://localhost:8000/api/v1';
        this.apiKey = apiKey || 'demo-key-12345';
    }

    /**
     * Make an API request
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;

        const headers = {
            'Content-Type': 'application/json',
            'X-API-Key': this.apiKey,
            ...options.headers,
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers,
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    /**
     * Get company metadata by ticker
     */
    async getCompany(ticker) {
        return this.request(`/company/${ticker}`);
    }

    /**
     * Search companies by name
     */
    async searchCompanies(query, limit = 10) {
        return this.request(`/company/search/name?q=${encodeURIComponent(query)}&limit=${limit}`);
    }

    /**
     * Get filings for a company
     */
    async getFilings(ticker, filingType = null, limit = 100) {
        let endpoint = `/filings/${ticker}?limit=${limit}`;
        if (filingType) {
            endpoint += `&filing_type=${filingType}`;
        }
        return this.request(endpoint);
    }

    /**
     * Get a financial statement
     */
    async getStatement(ticker, statementType, year, quarter = null) {
        let endpoint = `/statement/${ticker}/${statementType}?year=${year}`;
        if (quarter !== null) {
            endpoint += `&quarter=${quarter}`;
        }
        return this.request(endpoint);
    }

    /**
     * Get time series data for a line item
     */
    async getDataPoint(ticker, lineItemName, period = 'quarterly', statementType = 'income_statement', limit = 40) {
        const encodedName = encodeURIComponent(lineItemName);
        return this.request(
            `/data_point/${ticker}/${encodedName}?period=${period}&statement_type=${statementType}&limit=${limit}`
        );
    }
}

// Create global API instance
const api = new FinancialAPI();
