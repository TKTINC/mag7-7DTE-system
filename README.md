# Mag7-7DTE-System

A sophisticated algorithmic trading platform focused on the Magnificent 7 stocks (AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, META) with 7-day-to-expiration options strategies.

## Overview

The Mag7-7DTE-System is a modular, high-performance trading platform designed specifically for systematic options trading on the world's most liquid individual stock options. The system leverages advanced machine learning, real-time market data, and sophisticated risk management to identify and execute high-probability trading opportunities in the 7-day-to-expiration timeframe.

### Key Features

- **Focused Strategy**: Specialized for the Magnificent 7 technology stocks (AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, META)
- **Optimal Timeframe**: 7-day-to-expiration (7DTE) options strategies balancing time decay and fundamental analysis
- **Comprehensive Analysis**: Integration of technical, fundamental, and sentiment analysis for superior signal generation
- **Conversational AI**: Natural language interface for market analysis, strategy explanation, and performance insights
- **Advanced Risk Management**: Sophisticated position sizing, correlation analysis, and event risk management
- **Institutional-Grade Infrastructure**: High-performance, scalable architecture with real-time data processing

## System Architecture

The Mag7-7DTE-System implements a modern microservices architecture with the following components:

- **Backend**: FastAPI-based Python services for data processing, signal generation, and risk management
- **Frontend**: React-based user interface with advanced visualization and portfolio management
- **Databases**: PostgreSQL for relational data, InfluxDB for time-series data, Redis for caching
- **Data Feeds**: Real-time market data, fundamental data, and news/sentiment integration

## Development Status

The Mag7-7DTE-System is currently under active development following a phased implementation approach:

1. ✅ **Phase 1**: Repository setup and initial project structure
2. 🔄 **Phase 2**: Core infrastructure adaptations (database schema, data models)
3. 📅 **Phase 3**: Data feed integration enhancements
4. 📅 **Phase 4**: Signal generation framework extensions
5. 📅 **Phase 5**: User interface enhancements
6. 📅 **Phase 6**: Risk management system updates
7. 📅 **Phase 7**: Integration and testing
8. 📅 **Phase 8**: Documentation and deployment

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 20+
- PostgreSQL 14+
- InfluxDB 2.0+
- Redis 6.0+

### Local Development Setup

1. Clone the repository:
   ```
   git clone https://github.com/TKTINC/mag7-7DTE-system.git
   cd mag7-7DTE-system
   ```

2. Start the development environment:
   ```
   docker-compose up -d
   ```

3. Initialize the database:
   ```
   cd backend
   python -m app.scripts.init_db
   ```

4. Start the frontend development server:
   ```
   cd mag7-7dte-frontend
   npm install
   npm run dev
   ```

5. Access the application at http://localhost:3000

## Documentation

Comprehensive documentation is available in the `/docs` directory:

- [System Architecture Analysis](docs/MAG7-7DTE-SYSTEM-ANALYSIS.md)
- [Implementation Guide](docs/MAG7-7DTE-IMPLEMENTATION-GUIDE.md)
- [Local Development Guide](docs/LOCAL-DEVELOPMENT-GUIDE.md)
- [AWS Cloud Provisioning Guide](docs/AWS-CLOUD-PROVISIONING-GUIDE.md)
- [Production Implementation Guide](docs/PRODUCTION-IMPLEMENTATION-GUIDE.md)

## License

Proprietary - All rights reserved

## Contact

For inquiries, please contact [support@tktinc.com](mailto:support@tktinc.com)

