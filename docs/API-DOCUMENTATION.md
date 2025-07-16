# Mag7-7DTE-System: API Documentation

This document provides comprehensive documentation for the Mag7-7DTE-System API endpoints, request/response formats, and authentication.

## Table of Contents

1. [Authentication](#authentication)
2. [Market Data API](#market-data-api)
3. [Signal API](#signal-api)
4. [Portfolio API](#portfolio-api)
5. [Risk Management API](#risk-management-api)
6. [User API](#user-api)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)

## Authentication

The API uses JWT (JSON Web Token) for authentication.

### Obtain Access Token

```
POST /api/v1/auth/login
```

**Request Body:**

```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the Token

Include the token in the Authorization header for all authenticated requests:

```
Authorization: Bearer {access_token}
```

### Refresh Token

```
POST /api/v1/auth/refresh
```

**Request Headers:**

```
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## Market Data API

### Get All Instruments

```
GET /api/v1/market-data/instruments
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| type | string | Filter by instrument type (STOCK) |
| is_active | boolean | Filter by active status |

**Response:**

```json
[
  {
    "id": 1,
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "type": "STOCK",
    "sector": "Technology",
    "is_active": true,
    "description": "Apple Inc. stock"
  },
  ...
]
```

### Get Instrument by ID

```
GET /api/v1/market-data/instruments/{instrument_id}
```

**Response:**

```json
{
  "id": 1,
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "type": "STOCK",
  "sector": "Technology",
  "is_active": true,
  "description": "Apple Inc. stock"
}
```

### Get Stock Prices

```
GET /api/v1/market-data/prices/{instrument_id}
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| start_date | string | Start date (YYYY-MM-DD) |
| end_date | string | End date (YYYY-MM-DD) |
| limit | integer | Maximum number of records to return |

**Response:**

```json
[
  {
    "id": 1,
    "instrument_id": 1,
    "date": "2023-01-01",
    "open_price": 150.0,
    "high_price": 152.0,
    "low_price": 148.0,
    "close_price": 151.0,
    "volume": 1000000
  },
  ...
]
```

### Get Option Chains

```
GET /api/v1/market-data/option-chains/{instrument_id}
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| date | string | Date (YYYY-MM-DD) |
| expiration_date | string | Expiration date (YYYY-MM-DD) |

**Response:**

```json
[
  {
    "id": 1,
    "instrument_id": 1,
    "date": "2023-01-01",
    "expiration_date": "2023-01-08",
    "is_complete": true
  },
  ...
]
```

### Get Option Contracts

```
GET /api/v1/market-data/option-contracts/{option_chain_id}
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| contract_type | string | Filter by contract type (CALL, PUT) |
| min_strike | number | Minimum strike price |
| max_strike | number | Maximum strike price |

**Response:**

```json
[
  {
    "id": 1,
    "option_chain_id": 1,
    "contract_type": "CALL",
    "strike_price": 150.0,
    "bid_price": 2.0,
    "ask_price": 2.2,
    "last_price": 2.1,
    "volume": 1000,
    "open_interest": 5000,
    "implied_volatility": 0.3
  },
  ...
]
```

## Signal API

### Get All Signals

```
GET /api/v1/signals
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| instrument_id | integer | Filter by instrument ID |
| signal_type | string | Filter by signal type (LONG_CALL, LONG_PUT) |
| min_confidence | number | Minimum confidence score |
| status | string | Filter by status (ACTIVE, EXPIRED, EXECUTED) |
| start_date | string | Start date (YYYY-MM-DD) |
| end_date | string | End date (YYYY-MM-DD) |

**Response:**

```json
[
  {
    "id": 1,
    "instrument_id": 1,
    "signal_date": "2023-01-01",
    "signal_type": "LONG_CALL",
    "expiration_date": "2023-01-08",
    "strike_price": 150.0,
    "option_price": 2.1,
    "confidence": 0.8,
    "factors": {
      "technical": {
        "rsi": 65,
        "macd": 0.5
      },
      "fundamental": {
        "pe_ratio": 25
      },
      "volatility": {
        "iv_percentile": 60
      }
    },
    "status": "ACTIVE",
    "source": "ENSEMBLE"
  },
  ...
]
```

### Get Signal by ID

```
GET /api/v1/signals/{signal_id}
```

**Response:**

```json
{
  "id": 1,
  "instrument_id": 1,
  "signal_date": "2023-01-01",
  "signal_type": "LONG_CALL",
  "expiration_date": "2023-01-08",
  "strike_price": 150.0,
  "option_price": 2.1,
  "confidence": 0.8,
  "factors": {
    "technical": {
      "rsi": 65,
      "macd": 0.5
    },
    "fundamental": {
      "pe_ratio": 25
    },
    "volatility": {
      "iv_percentile": 60
    }
  },
  "status": "ACTIVE",
  "source": "ENSEMBLE"
}
```

### Create Signal

```
POST /api/v1/signals
```

**Request Body:**

```json
{
  "instrument_id": 1,
  "signal_type": "LONG_CALL",
  "expiration_date": "2023-01-08",
  "strike_price": 150.0,
  "option_price": 2.1,
  "confidence": 0.8,
  "factors": {
    "technical": {
      "rsi": 65,
      "macd": 0.5
    },
    "fundamental": {
      "pe_ratio": 25
    },
    "volatility": {
      "iv_percentile": 60
    }
  },
  "source": "ENSEMBLE"
}
```

**Response:**

```json
{
  "id": 1,
  "instrument_id": 1,
  "signal_date": "2023-01-01",
  "signal_type": "LONG_CALL",
  "expiration_date": "2023-01-08",
  "strike_price": 150.0,
  "option_price": 2.1,
  "confidence": 0.8,
  "factors": {
    "technical": {
      "rsi": 65,
      "macd": 0.5
    },
    "fundamental": {
      "pe_ratio": 25
    },
    "volatility": {
      "iv_percentile": 60
    }
  },
  "status": "ACTIVE",
  "source": "ENSEMBLE"
}
```

### Update Signal Status

```
PATCH /api/v1/signals/{signal_id}
```

**Request Body:**

```json
{
  "status": "EXECUTED"
}
```

**Response:**

```json
{
  "id": 1,
  "status": "EXECUTED",
  "updated_at": "2023-01-01T12:00:00Z"
}
```

## Portfolio API

### Get All Portfolios

```
GET /api/v1/portfolios
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | integer | Filter by user ID |

**Response:**

```json
[
  {
    "id": 1,
    "user_id": 1,
    "name": "My Portfolio",
    "description": "Magnificent 7 stocks with 7DTE options",
    "initial_capital": 100000.0,
    "cash_balance": 50000.0,
    "total_value": 100000.0,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T12:00:00Z"
  },
  ...
]
```

### Get Portfolio by ID

```
GET /api/v1/portfolios/{portfolio_id}
```

**Response:**

```json
{
  "id": 1,
  "user_id": 1,
  "name": "My Portfolio",
  "description": "Magnificent 7 stocks with 7DTE options",
  "initial_capital": 100000.0,
  "cash_balance": 50000.0,
  "total_value": 100000.0,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T12:00:00Z"
}
```

### Get Portfolio Positions

```
GET /api/v1/portfolios/{portfolio_id}/positions
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| instrument_id | integer | Filter by instrument ID |
| position_type | string | Filter by position type (LONG_CALL, LONG_PUT) |
| status | string | Filter by status (ACTIVE, CLOSED) |

**Response:**

```json
[
  {
    "id": 1,
    "portfolio_id": 1,
    "instrument_id": 1,
    "position_type": "LONG_CALL",
    "entry_date": "2023-01-01",
    "expiration_date": "2023-01-08",
    "strike_price": 150.0,
    "contracts": 2,
    "entry_price": 2.0,
    "current_price": 2.5,
    "cost": 400.0,
    "current_value": 500.0,
    "pnl": 100.0,
    "pnl_percentage": 25.0,
    "status": "ACTIVE"
  },
  ...
]
```

### Create Position

```
POST /api/v1/portfolios/{portfolio_id}/positions
```

**Request Body:**

```json
{
  "instrument_id": 1,
  "position_type": "LONG_CALL",
  "expiration_date": "2023-01-08",
  "strike_price": 150.0,
  "contracts": 2,
  "entry_price": 2.0
}
```

**Response:**

```json
{
  "id": 1,
  "portfolio_id": 1,
  "instrument_id": 1,
  "position_type": "LONG_CALL",
  "entry_date": "2023-01-01",
  "expiration_date": "2023-01-08",
  "strike_price": 150.0,
  "contracts": 2,
  "entry_price": 2.0,
  "current_price": 2.0,
  "cost": 400.0,
  "current_value": 400.0,
  "pnl": 0.0,
  "pnl_percentage": 0.0,
  "status": "ACTIVE"
}
```

### Close Position

```
POST /api/v1/portfolios/{portfolio_id}/positions/{position_id}/close
```

**Request Body:**

```json
{
  "exit_price": 2.5,
  "exit_reason": "TARGET"
}
```

**Response:**

```json
{
  "id": 1,
  "portfolio_id": 1,
  "instrument_id": 1,
  "position_type": "LONG_CALL",
  "entry_date": "2023-01-01",
  "exit_date": "2023-01-03",
  "expiration_date": "2023-01-08",
  "strike_price": 150.0,
  "contracts": 2,
  "entry_price": 2.0,
  "exit_price": 2.5,
  "cost": 400.0,
  "proceeds": 500.0,
  "pnl": 100.0,
  "pnl_percentage": 25.0,
  "status": "CLOSED",
  "exit_reason": "TARGET"
}
```

### Get Portfolio Trades

```
GET /api/v1/portfolios/{portfolio_id}/trades
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| instrument_id | integer | Filter by instrument ID |
| position_type | string | Filter by position type (LONG_CALL, LONG_PUT) |
| start_date | string | Start date (YYYY-MM-DD) |
| end_date | string | End date (YYYY-MM-DD) |
| min_pnl | number | Minimum P&L |

**Response:**

```json
[
  {
    "id": 1,
    "portfolio_id": 1,
    "instrument_id": 1,
    "position_type": "LONG_CALL",
    "entry_date": "2023-01-01",
    "exit_date": "2023-01-03",
    "expiration_date": "2023-01-08",
    "strike_price": 150.0,
    "contracts": 2,
    "entry_price": 2.0,
    "exit_price": 2.5,
    "cost": 400.0,
    "proceeds": 500.0,
    "pnl": 100.0,
    "pnl_percentage": 25.0,
    "status": "CLOSED",
    "exit_reason": "TARGET"
  },
  ...
]
```

## Risk Management API

### Calculate Position Size

```
POST /api/v1/risk-management/position-size
```

**Request Body:**

```json
{
  "user_id": 1,
  "instrument_id": 1,
  "signal_confidence": 0.8,
  "option_price": 2.1
}
```

**Response:**

```json
{
  "contracts": 5,
  "max_capital": 1050.0,
  "risk_per_trade": 1000.0,
  "contract_value": 210.0,
  "portfolio_value": 100000.0,
  "current_allocation": 0.0,
  "available_allocation": 10000.0,
  "confidence_multiplier": 1.3
}
```

### Check Portfolio Exposure

```
GET /api/v1/risk-management/portfolio-exposure/{user_id}
```

**Response:**

```json
{
  "status": "ok",
  "total_exposure": 5000.0,
  "max_exposure": 50000.0,
  "exposure_percentage": 5.0,
  "stock_exposures": {
    "AAPL": {
      "value": 3000.0,
      "percentage": 3.0
    },
    "MSFT": {
      "value": 2000.0,
      "percentage": 2.0
    }
  },
  "alerts": []
}
```

### Calculate Stop-Loss and Take-Profit

```
POST /api/v1/risk-management/stop-loss-take-profit
```

**Request Body:**

```json
{
  "position_id": 1,
  "risk_reward_ratio": 2.0
}
```

**Response:**

```json
{
  "status": "ok",
  "position_id": 1,
  "symbol": "AAPL",
  "position_type": "LONG_CALL",
  "entry_price": 2.0,
  "current_price": 2.5,
  "stop_loss_price": 1.5,
  "take_profit_price": 3.0,
  "risk_reward_ratio": 2.0,
  "current_risk_reward": 1.0,
  "max_loss_percentage": 25.0,
  "pct_to_stop_loss": -40.0,
  "pct_to_take_profit": 20.0,
  "days_to_expiration": 5
}
```

### Check Stop-Loss and Take-Profit

```
GET /api/v1/risk-management/stop-loss-take-profit/check/{position_id}
```

**Response:**

```json
{
  "status": "ok",
  "position_id": 1,
  "symbol": "AAPL",
  "position_type": "LONG_CALL",
  "entry_price": 2.0,
  "current_price": 2.5,
  "stop_loss_price": 1.5,
  "take_profit_price": 3.0,
  "stop_loss_hit": false,
  "take_profit_hit": false,
  "pct_to_stop_loss": -40.0,
  "pct_to_take_profit": 20.0,
  "message": "Position is within acceptable range."
}
```

### Get Portfolio Metrics

```
GET /api/v1/risk-management/portfolio-metrics/{user_id}
```

**Response:**

```json
{
  "status": "ok",
  "metrics": {
    "win_rate": 0.65,
    "profit_factor": 2.1,
    "average_win": 150.0,
    "average_loss": 75.0,
    "largest_win": 300.0,
    "largest_loss": 150.0,
    "average_holding_period": 3.5,
    "sharpe_ratio": 1.8,
    "max_drawdown": 2000.0,
    "max_drawdown_percentage": 2.0
  },
  "equity_curve": [
    {
      "date": "2023-01-01",
      "equity": 100000.0
    },
    {
      "date": "2023-01-05",
      "equity": 101000.0
    },
    ...
  ]
}
```

### Get Risk Profile Recommendations

```
GET /api/v1/risk-management/risk-profile-recommendations/{user_id}
```

**Response:**

```json
{
  "status": "ok",
  "current_profile": {
    "max_portfolio_risk": 2.0,
    "max_portfolio_exposure": 50.0,
    "max_stock_allocation": 10.0,
    "max_loss_per_trade": 25.0,
    "risk_reward_ratio": 2.0
  },
  "recommendations": {
    "max_portfolio_risk": 2.5,
    "max_portfolio_exposure": 60.0,
    "max_stock_allocation": 12.0,
    "max_loss_per_trade": 20.0,
    "risk_reward_ratio": 2.0
  },
  "metrics_summary": {
    "win_rate": 0.65,
    "profit_factor": 2.1,
    "average_holding_period": 3.5,
    "sharpe_ratio": 1.8,
    "max_drawdown_percentage": 2.0
  }
}
```

### Get Correlation Matrix

```
GET /api/v1/risk-management/correlation-matrix
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| lookback_days | integer | Number of days to look back (default: 30) |

**Response:**

```json
{
  "AAPL": {
    "AAPL": 1.0,
    "MSFT": 0.8,
    "GOOGL": 0.7,
    ...
  },
  "MSFT": {
    "AAPL": 0.8,
    "MSFT": 1.0,
    "GOOGL": 0.75,
    ...
  },
  ...
}
```

## User API

### Get Current User

```
GET /api/v1/users/me
```

**Response:**

```json
{
  "id": 1,
  "username": "user",
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2023-01-01T00:00:00Z"
}
```

### Get User Risk Profile

```
GET /api/v1/users/{user_id}/risk-profile
```

**Response:**

```json
{
  "user_id": 1,
  "max_portfolio_risk": 2.0,
  "max_portfolio_exposure": 50.0,
  "max_stock_allocation": 10.0,
  "max_loss_per_trade": 25.0,
  "risk_reward_ratio": 2.0,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T12:00:00Z"
}
```

### Update User Risk Profile

```
PUT /api/v1/users/{user_id}/risk-profile
```

**Request Body:**

```json
{
  "max_portfolio_risk": 2.5,
  "max_portfolio_exposure": 60.0,
  "max_stock_allocation": 12.0,
  "max_loss_per_trade": 20.0,
  "risk_reward_ratio": 2.0
}
```

**Response:**

```json
{
  "user_id": 1,
  "max_portfolio_risk": 2.5,
  "max_portfolio_exposure": 60.0,
  "max_stock_allocation": 12.0,
  "max_loss_per_trade": 20.0,
  "risk_reward_ratio": 2.0,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-02T12:00:00Z"
}
```

## Error Handling

All API endpoints return standard HTTP status codes:

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

Error responses follow this format:

```json
{
  "detail": "Error message"
}
```

For validation errors:

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "Error message",
      "type": "value_error"
    }
  ]
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- Authenticated users: 100 requests per minute
- Unauthenticated users: 20 requests per minute

Rate limit headers are included in all responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1609459200
```

When rate limit is exceeded, the API returns `429 Too Many Requests` with a Retry-After header.

