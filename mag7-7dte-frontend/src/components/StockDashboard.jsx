import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "./ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { ArrowUpCircle, ArrowDownCircle, TrendingUp, TrendingDown, DollarSign, BarChart2, Activity, Calendar, Clock, AlertCircle } from 'lucide-react';

const MAG7_STOCKS = [
  { symbol: 'AAPL', name: 'Apple Inc.', color: '#7cb5ec' },
  { symbol: 'MSFT', name: 'Microsoft Corp.', color: '#90ed7d' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', color: '#f7a35c' },
  { symbol: 'AMZN', name: 'Amazon.com Inc.', color: '#8085e9' },
  { symbol: 'NVDA', name: 'NVIDIA Corp.', color: '#f15c80' },
  { symbol: 'TSLA', name: 'Tesla Inc.', color: '#e4d354' },
  { symbol: 'META', name: 'Meta Platforms Inc.', color: '#2b908f' },
];

const StockDashboard = () => {
  const [selectedStock, setSelectedStock] = useState(MAG7_STOCKS[0]);
  const [stockData, setStockData] = useState({});
  const [loading, setLoading] = useState(true);
  const [timeframe, setTimeframe] = useState('1d');

  useEffect(() => {
    // Fetch data for all Mag7 stocks
    const fetchAllStockData = async () => {
      setLoading(true);
      try {
        const data = {};
        for (const stock of MAG7_STOCKS) {
          // In a real implementation, this would be an API call
          // For now, we'll use mock data
          data[stock.symbol] = generateMockData(stock.symbol);
        }
        setStockData(data);
      } catch (error) {
        console.error('Error fetching stock data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAllStockData();
    
    // Set up polling for real-time updates
    const interval = setInterval(() => {
      fetchAllStockData();
    }, 60000); // Update every minute
    
    return () => clearInterval(interval);
  }, []);

  // Generate mock data for demonstration
  const generateMockData = (symbol) => {
    const basePrice = {
      'AAPL': 175.25,
      'MSFT': 325.50,
      'GOOGL': 142.75,
      'AMZN': 132.30,
      'NVDA': 425.80,
      'TSLA': 245.60,
      'META': 315.40,
    }[symbol] || 100;
    
    const priceChange = (Math.random() * 10 - 5).toFixed(2);
    const percentChange = (priceChange / basePrice * 100).toFixed(2);
    const isPositive = parseFloat(priceChange) >= 0;
    
    // Generate price history
    const priceHistory = Array.from({ length: 30 }, (_, i) => {
      const date = new Date();
      date.setDate(date.getDate() - (29 - i));
      const randomChange = (Math.random() * 10 - 5);
      return {
        date: date.toISOString().split('T')[0],
        price: (basePrice + randomChange).toFixed(2),
        volume: Math.floor(Math.random() * 10000000) + 5000000,
      };
    });
    
    // Generate options data
    const optionsData = {
      callIV: (Math.random() * 0.3 + 0.2).toFixed(2),
      putIV: (Math.random() * 0.3 + 0.2).toFixed(2),
      skew: (Math.random() * 0.2 - 0.1).toFixed(2),
      atmStrike: Math.round(basePrice / 5) * 5,
      expirationDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      daysToExpiration: 7,
    };
    
    // Generate signals
    const signals = [
      {
        id: 1,
        type: Math.random() > 0.5 ? 'LONG_CALL' : 'LONG_PUT',
        source: ['TECHNICAL', 'FUNDAMENTAL', 'VOLATILITY', 'ENSEMBLE'][Math.floor(Math.random() * 4)],
        confidence: (Math.random() * 0.4 + 0.6).toFixed(2),
        timestamp: new Date().toISOString(),
        strike: Math.round(basePrice / 5) * 5 + (Math.random() > 0.5 ? 5 : -5),
        expiration: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      },
      {
        id: 2,
        type: Math.random() > 0.5 ? 'LONG_CALL' : 'LONG_PUT',
        source: ['TECHNICAL', 'FUNDAMENTAL', 'VOLATILITY', 'ENSEMBLE'][Math.floor(Math.random() * 4)],
        confidence: (Math.random() * 0.4 + 0.6).toFixed(2),
        timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
        strike: Math.round(basePrice / 5) * 5 + (Math.random() > 0.5 ? 10 : -10),
        expiration: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      },
    ];
    
    return {
      symbol,
      price: basePrice,
      priceChange,
      percentChange,
      isPositive,
      priceHistory,
      optionsData,
      signals,
      volume: Math.floor(Math.random() * 10000000) + 5000000,
      marketCap: (basePrice * (Math.random() * 5 + 1) * 1000000000).toFixed(2),
      pe: (Math.random() * 30 + 10).toFixed(2),
      beta: (Math.random() * 1.5 + 0.5).toFixed(2),
    };
  };

  const renderPriceChart = () => {
    if (!stockData[selectedStock.symbol]) return null;
    
    const data = stockData[selectedStock.symbol].priceHistory;
    
    return (
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={selectedStock.color} stopOpacity={0.8}/>
              <stop offset="95%" stopColor={selectedStock.color} stopOpacity={0.1}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis domain={['auto', 'auto']} />
          <Tooltip />
          <Area type="monotone" dataKey="price" stroke={selectedStock.color} fillOpacity={1} fill="url(#colorPrice)" />
        </AreaChart>
      </ResponsiveContainer>
    );
  };

  const renderVolumeChart = () => {
    if (!stockData[selectedStock.symbol]) return null;
    
    const data = stockData[selectedStock.symbol].priceHistory;
    
    return (
      <ResponsiveContainer width="100%" height={150}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="volume" fill="#8884d8" />
        </BarChart>
      </ResponsiveContainer>
    );
  };

  const renderOptionsData = () => {
    if (!stockData[selectedStock.symbol]) return null;
    
    const { optionsData } = stockData[selectedStock.symbol];
    
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Call IV</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{optionsData.callIV}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Put IV</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{optionsData.putIV}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">IV Skew</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{optionsData.skew}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">ATM Strike</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${optionsData.atmStrike}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Expiration</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{optionsData.expirationDate}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">DTE</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{optionsData.daysToExpiration}</div>
          </CardContent>
        </Card>
      </div>
    );
  };

  const renderSignals = () => {
    if (!stockData[selectedStock.symbol]) return null;
    
    const { signals } = stockData[selectedStock.symbol];
    
    return (
      <div className="space-y-4 mt-4">
        {signals.map(signal => (
          <Card key={signal.id}>
            <CardHeader className="pb-2">
              <div className="flex justify-between items-center">
                <CardTitle className="text-lg font-medium">
                  {signal.type === 'LONG_CALL' ? (
                    <span className="flex items-center text-green-500"><ArrowUpCircle className="mr-2" size={20} /> Long Call</span>
                  ) : (
                    <span className="flex items-center text-red-500"><ArrowDownCircle className="mr-2" size={20} /> Long Put</span>
                  )}
                </CardTitle>
                <Badge variant={signal.confidence > 0.75 ? "default" : "outline"}>
                  {(signal.confidence * 100).toFixed(0)}% Confidence
                </Badge>
              </div>
              <CardDescription>
                <div className="flex items-center space-x-2">
                  <span className="flex items-center"><Calendar className="mr-1" size={14} /> {signal.expiration}</span>
                  <span className="flex items-center"><DollarSign className="mr-1" size={14} /> Strike: ${signal.strike}</span>
                </div>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Source: {signal.source}</span>
                <span className="text-sm text-muted-foreground">
                  <Clock className="inline mr-1" size={14} />
                  {new Date(signal.timestamp).toLocaleString()}
                </span>
              </div>
            </CardContent>
            <CardFooter>
              <Button variant="outline" className="w-full">View Details</Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    );
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">Magnificent 7 Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-7 gap-4 mb-6">
        {MAG7_STOCKS.map(stock => {
          const data = stockData[stock.symbol];
          return (
            <Card 
              key={stock.symbol}
              className={`cursor-pointer hover:shadow-md transition-shadow ${selectedStock.symbol === stock.symbol ? 'ring-2 ring-primary' : ''}`}
              onClick={() => setSelectedStock(stock)}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-bold">{stock.symbol}</CardTitle>
                <CardDescription>{stock.name}</CardDescription>
              </CardHeader>
              <CardContent>
                {data ? (
                  <>
                    <div className="text-2xl font-bold">${data.price}</div>
                    <div className={`flex items-center ${data.isPositive ? 'text-green-500' : 'text-red-500'}`}>
                      {data.isPositive ? <TrendingUp className="mr-1" size={16} /> : <TrendingDown className="mr-1" size={16} />}
                      <span>{data.isPositive ? '+' : ''}{data.priceChange} ({data.isPositive ? '+' : ''}{data.percentChange}%)</span>
                    </div>
                  </>
                ) : (
                  <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>{selectedStock.name} ({selectedStock.symbol})</CardTitle>
              <div className="flex space-x-2">
                <Button variant={timeframe === '1d' ? 'default' : 'outline'} size="sm" onClick={() => setTimeframe('1d')}>1D</Button>
                <Button variant={timeframe === '1w' ? 'default' : 'outline'} size="sm" onClick={() => setTimeframe('1w')}>1W</Button>
                <Button variant={timeframe === '1m' ? 'default' : 'outline'} size="sm" onClick={() => setTimeframe('1m')}>1M</Button>
                <Button variant={timeframe === '3m' ? 'default' : 'outline'} size="sm" onClick={() => setTimeframe('3m')}>3M</Button>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="animate-pulse h-80 bg-gray-200 rounded"></div>
              ) : (
                <>
                  {renderPriceChart()}
                  {renderVolumeChart()}
                </>
              )}
            </CardContent>
          </Card>
          
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>7-DTE Options Data</CardTitle>
              <CardDescription>Options expiring in approximately 7 days</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="animate-pulse h-40 bg-gray-200 rounded"></div>
              ) : (
                renderOptionsData()
              )}
            </CardContent>
          </Card>
        </div>
        
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Trading Signals</CardTitle>
              <CardDescription>Recent signals for {selectedStock.symbol}</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="animate-pulse h-80 bg-gray-200 rounded"></div>
              ) : (
                renderSignals()
              )}
            </CardContent>
            <CardFooter>
              <Button className="w-full">View All Signals</Button>
            </CardFooter>
          </Card>
          
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Key Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="animate-pulse h-40 bg-gray-200 rounded"></div>
              ) : (
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Market Cap</span>
                    <span className="font-medium">${(parseFloat(stockData[selectedStock.symbol].marketCap) / 1000000000).toFixed(2)}B</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Volume</span>
                    <span className="font-medium">{(stockData[selectedStock.symbol].volume / 1000000).toFixed(2)}M</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">P/E Ratio</span>
                    <span className="font-medium">{stockData[selectedStock.symbol].pe}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Beta</span>
                    <span className="font-medium">{stockData[selectedStock.symbol].beta}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default StockDashboard;

