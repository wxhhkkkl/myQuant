from backend.src.db.duckdb import db


def init_schema():
    """Initialize all DuckDB tables and indexes."""
    conn = db.write_conn

    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_kline (
            trade_date  DATE NOT NULL,
            stock_code  VARCHAR(10) NOT NULL,
            stock_name  VARCHAR(20),
            open        DOUBLE,
            high        DOUBLE,
            low         DOUBLE,
            close       DOUBLE,
            volume      BIGINT,
            amount      BIGINT,
            adj_factor  DOUBLE DEFAULT 1.0,
            PRIMARY KEY (trade_date, stock_code)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kline_code ON daily_kline(stock_code)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS minute_kline (
            trade_time  TIMESTAMP NOT NULL,
            stock_code  VARCHAR(10) NOT NULL,
            open        DOUBLE,
            high        DOUBLE,
            low         DOUBLE,
            close       DOUBLE,
            volume      BIGINT,
            amount      BIGINT,
            PRIMARY KEY (trade_time, stock_code)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS model_factors (
            trade_date   DATE NOT NULL,
            stock_code   VARCHAR(10) NOT NULL,
            model_name   VARCHAR(30) NOT NULL,
            factor_name  VARCHAR(30) NOT NULL,
            factor_value DOUBLE,
            PRIMARY KEY (trade_date, stock_code, model_name, factor_name)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            run_id         VARCHAR(36) PRIMARY KEY,
            model_name     VARCHAR(30) NOT NULL,
            model_params   VARCHAR(200),
            stock_code     VARCHAR(10) NOT NULL,
            start_date     DATE NOT NULL,
            end_date       DATE NOT NULL,
            initial_capital DOUBLE NOT NULL,
            final_capital  DOUBLE,
            total_return   DOUBLE,
            annual_return  DOUBLE,
            max_drawdown   DOUBLE,
            sharpe_ratio   DOUBLE,
            trade_count    INTEGER,
            win_rate       DOUBLE,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sector_trend (
            sector_name VARCHAR NOT NULL,
            trade_date  DATE NOT NULL,
            open        DOUBLE,
            high        DOUBLE,
            low         DOUBLE,
            close       DOUBLE,
            stock_count INTEGER,
            PRIMARY KEY (sector_name, trade_date)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sector_trend_date ON sector_trend(trade_date)")

    conn.execute("CREATE SEQUENCE IF NOT EXISTS bt_trades_seq")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS backtest_trades (
            id           INTEGER PRIMARY KEY DEFAULT nextval('bt_trades_seq'),
            run_id       VARCHAR(36) NOT NULL,
            trade_date   DATE NOT NULL,
            trade_type   VARCHAR(4) NOT NULL,
            price        DOUBLE NOT NULL,
            quantity     INTEGER NOT NULL,
            profit       DOUBLE
        )
    """)
