-- US Financial Statement Database Schema
-- Version: 1.0
-- Database: PostgreSQL 15+

-- Drop tables if exists (for clean reinstall)
DROP TABLE IF EXISTS financial_data CASCADE;
DROP TABLE IF EXISTS filing CASCADE;
DROP TABLE IF EXISTS company CASCADE;

-- Company Table: Stores information about each unique company
CREATE TABLE company (
    company_id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) UNIQUE NOT NULL,
    cik VARCHAR(20) NOT NULL,
    company_name VARCHAR(255),
    exchange VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_ticker UNIQUE (ticker),
    CONSTRAINT unique_cik UNIQUE (cik)
);

-- Create index on ticker for fast lookups
CREATE INDEX idx_company_ticker ON company(ticker);
CREATE INDEX idx_company_cik ON company(cik);
CREATE INDEX idx_company_active ON company(is_active);

-- Filing Table: Stores information about each unique filing
CREATE TABLE filing (
    filing_id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    filing_type VARCHAR(10) NOT NULL,  -- '10-K' or '10-Q'
    filing_date DATE NOT NULL,
    period_end_date DATE NOT NULL,
    period_year INTEGER NOT NULL,
    period_quarter INTEGER,  -- 1, 2, 3, 4 - NULL for annual 10-K
    accession_number VARCHAR(50) UNIQUE,  -- SEC accession number (unique identifier)
    document_url TEXT,
    is_restatement BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES company(company_id) ON DELETE CASCADE,
    CONSTRAINT valid_filing_type CHECK (filing_type IN ('10-K', '10-Q')),
    CONSTRAINT valid_quarter CHECK (period_quarter IS NULL OR period_quarter BETWEEN 1 AND 4),
    CONSTRAINT unique_filing UNIQUE (company_id, period_year, period_quarter, filing_date)
);

-- Create indexes for common queries
CREATE INDEX idx_filing_company ON filing(company_id);
CREATE INDEX idx_filing_date ON filing(filing_date);
CREATE INDEX idx_filing_period ON filing(company_id, period_year, period_quarter);
CREATE INDEX idx_filing_type ON filing(filing_type);
CREATE INDEX idx_filing_accession ON filing(accession_number);

-- FinancialData Table: Stores each individual line item from financial statements
CREATE TABLE financial_data (
    data_id BIGSERIAL PRIMARY KEY,
    filing_id INTEGER NOT NULL,
    statement_type VARCHAR(5) NOT NULL,  -- 'IS' (Income Statement), 'BS' (Balance Sheet), 'CF' (Cash Flow)
    line_item_name VARCHAR(500) NOT NULL,  -- As-reported name from the filing
    value NUMERIC(19, 4),  -- Handles large financial numbers with 4 decimal precision
    display_order INTEGER,  -- Preserves the original order on the statement
    unit VARCHAR(20) DEFAULT 'USD',  -- Currency unit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (filing_id) REFERENCES filing(filing_id) ON DELETE CASCADE,
    CONSTRAINT valid_statement_type CHECK (statement_type IN ('IS', 'BS', 'CF')),
    CONSTRAINT unique_line_item UNIQUE (filing_id, statement_type, line_item_name)
);

-- Create indexes for fast queries
CREATE INDEX idx_financial_filing ON financial_data(filing_id);
CREATE INDEX idx_financial_statement_type ON financial_data(statement_type);
CREATE INDEX idx_financial_line_item ON financial_data(line_item_name);
CREATE INDEX idx_financial_composite ON financial_data(filing_id, statement_type);

-- Create a materialized view for fast time-series queries
CREATE MATERIALIZED VIEW mv_company_metrics AS
SELECT
    c.ticker,
    c.company_name,
    f.period_year,
    f.period_quarter,
    f.filing_type,
    fd.statement_type,
    fd.line_item_name,
    fd.value,
    fd.display_order
FROM company c
JOIN filing f ON c.company_id = f.company_id
JOIN financial_data fd ON f.filing_id = fd.filing_id
ORDER BY c.ticker, f.period_year DESC, f.period_quarter DESC NULLS LAST;

-- Create index on materialized view
CREATE INDEX idx_mv_ticker_line_item ON mv_company_metrics(ticker, line_item_name);
CREATE INDEX idx_mv_ticker_period ON mv_company_metrics(ticker, period_year, period_quarter);

-- Function to refresh materialized view (call periodically)
CREATE OR REPLACE FUNCTION refresh_company_metrics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_company_metrics;
END;
$$ LANGUAGE plpgsql;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_company_modtime
    BEFORE UPDATE ON company
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_filing_modtime
    BEFORE UPDATE ON filing
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- Comments for documentation
COMMENT ON TABLE company IS 'Stores metadata for all publicly traded companies';
COMMENT ON TABLE filing IS 'Stores metadata for each 10-K and 10-Q filing';
COMMENT ON TABLE financial_data IS 'Stores as-reported financial statement line items';
COMMENT ON COLUMN financial_data.line_item_name IS 'Exact as-reported line item name (no normalization)';
COMMENT ON COLUMN filing.is_restatement IS 'True if this filing restates a previous period';
