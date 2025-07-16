import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "./ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Progress } from "./ui/progress";
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { ArrowUpCircle, ArrowDownCircle, TrendingUp, TrendingDown, DollarSign, BarChart2, Activity, Calendar, Clock, AlertCircle, Briefcase, PieChart as PieChartIcon, BarChart as BarChartIcon, Percent, Target, Award, Trash2, Edit, Plus, X, Check, RefreshCw } from 'lucide-react';

const MAG7_STOCKS = [
  { symbol: 'AAPL', name: 'Apple Inc.', color: '#7cb5ec' },
  { symbol: 'MSFT', name: 'Microsoft Corp.', color: '#90ed7d' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', color: '#f7a35c' },
  { symbol: 'AMZN', name: 'Amazon.com Inc.', color: '#8085e9' },
  { symbol: 'NVDA', name: 'NVIDIA Corp.', color: '#f15c80' },
  { symbol: 'TSLA', name: 'Tesla Inc.', color: '#e4d354' },
  { symbol: 'META', name: 'Meta Platforms Inc.', color: '#2b908f' },
];

const PortfolioManager = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [portfolio, setPortfolio] = useState(null);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [showAddPosition, setShowAddPosition] = useState(false);
  const [newPosition, setNewPosition] = useState({
    symbol: 'AAPL',
    type: 'LONG_CALL',
    strike: '',
    expiration: '',
    contracts: 1,
    entryPrice: '',
    entryDate: new Date().toISOString().split('T')[0]
  });

  useEffect(() => {
    fetchPortfolioData();
  }, []);

  const fetchPortfolioData = async () => {
    setLoading(true);
    try {
      // In a real implementation, this would be API calls
      // For now, we'll use mock data
      const mockPortfolio = generateMockPortfolio();
      const mockPositions = generateMockPositions();
      const mockTrades = generateMockTrades();
      
      setPortfolio(mockPortfolio);
      setPositions(mockPositions);
      setTrades(mockTrades);
    } catch (error) {
      console.error('Error fetching portfolio data:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateMockPortfolio = () => {
    return {
      totalValue: 25750.42,
      cashBalance: 12500.00,
      investedValue: 13250.42,
      totalPnL: 3250.42,
      totalPnLPercent: 14.5,
      dailyPnL: 450.25,
      dailyPnLPercent: 1.8,
      weeklyPnL: 1250.75,
      weeklyPnLPercent: 5.2,
      winRate: 0.68,
      avgWinAmount: 425.50,
      avgLossAmount: 215.25,
      profitFactor: 2.1,
      sharpeRatio: 1.8,
      maxDrawdown: 2150.00,
      maxDrawdownPercent: 8.5,
      allocation: {
        AAPL: 15,
        MSFT: 20,
        GOOGL: 10,
        AMZN: 12,
        NVDA: 25,
        TSLA: 8,
        META: 10
      },
      strategyAllocation: {
        'LONG_CALL': 65,
        'LONG_PUT': 35
      },
      performance: [
        { date: '2023-01-01', value: 20000 },
        { date: '2023-01-08', value: 20500 },
        { date: '2023-01-15', value: 21200 },
        { date: '2023-01-22', value: 20800 },
        { date: '2023-01-29', value: 21500 },
        { date: '2023-02-05', value: 22100 },
        { date: '2023-02-12', value: 22800 },
        { date: '2023-02-19', value: 23500 },
        { date: '2023-02-26', value: 24200 },
        { date: '2023-03-05', value: 23800 },
        { date: '2023-03-12', value: 24500 },
        { date: '2023-03-19', value: 25200 },
        { date: '2023-03-26', value: 25750 }
      ],
      dailyReturns: [
        { date: '2023-03-20', return: 0.8 },
        { date: '2023-03-21', return: -0.5 },
        { date: '2023-03-22', return: 1.2 },
        { date: '2023-03-23', return: 0.3 },
        { date: '2023-03-24', return: -0.2 },
        { date: '2023-03-25', return: 0.9 },
        { date: '2023-03-26', return: 1.8 }
      ]
    };
  };

  const generateMockPositions = () => {
    const positions = [];
    
    // Generate 10 mock positions
    for (let i = 1; i <= 10; i++) {
      const stock = MAG7_STOCKS[Math.floor(Math.random() * MAG7_STOCKS.length)];
      const isCall = Math.random() > 0.4;
      const basePrice = {
        'AAPL': 175.25,
        'MSFT': 325.50,
        'GOOGL': 142.75,
        'AMZN': 132.30,
        'NVDA': 425.80,
        'TSLA': 245.60,
        'META': 315.40,
      }[stock.symbol] || 100;
      
      // Random entry date within the last 7 days
      const entryDate = new Date();
      entryDate.setDate(entryDate.getDate() - Math.floor(Math.random() * 7));
      
      // Random expiration date 7 days from entry date
      const expiration = new Date(entryDate);
      expiration.setDate(expiration.getDate() + 7);
      
      const strike = Math.round(basePrice / 5) * 5 + (isCall ? 5 : -5);
      const entryPrice = (Math.random() * 5 + 1).toFixed(2);
      const currentPrice = (parseFloat(entryPrice) * (1 + (Math.random() * 0.6 - 0.3))).toFixed(2);
      const contracts = Math.floor(Math.random() * 5) + 1;
      const cost = (parseFloat(entryPrice) * contracts * 100).toFixed(2);
      const value = (parseFloat(currentPrice) * contracts * 100).toFixed(2);
      const pnl = (parseFloat(value) - parseFloat(cost)).toFixed(2);
      const pnlPercent = ((parseFloat(pnl) / parseFloat(cost)) * 100).toFixed(2);
      
      positions.push({
        id: i,
        symbol: stock.symbol,
        stockName: stock.name,
        type: isCall ? 'LONG_CALL' : 'LONG_PUT',
        strike,
        expiration: expiration.toISOString().split('T')[0],
        entryDate: entryDate.toISOString().split('T')[0],
        entryPrice,
        currentPrice,
        contracts,
        cost,
        value,
        pnl,
        pnlPercent,
        daysToExpiration: Math.floor((expiration - new Date()) / (1000 * 60 * 60 * 24)),
        status: 'ACTIVE'
      });
    }
    
    return positions;
  };

  const generateMockTrades = () => {
    const trades = [];
    
    // Generate 20 mock trades
    for (let i = 1; i <= 20; i++) {
      const stock = MAG7_STOCKS[Math.floor(Math.random() * MAG7_STOCKS.length)];
      const isCall = Math.random() > 0.4;
      const basePrice = {
        'AAPL': 175.25,
        'MSFT': 325.50,
        'GOOGL': 142.75,
        'AMZN': 132.30,
        'NVDA': 425.80,
        'TSLA': 245.60,
        'META': 315.40,
      }[stock.symbol] || 100;
      
      // Random entry date within the last 30 days
      const entryDate = new Date();
      entryDate.setDate(entryDate.getDate() - Math.floor(Math.random() * 30));
      
      // Random exit date after entry date
      const exitDate = new Date(entryDate);
      exitDate.setDate(exitDate.getDate() + Math.floor(Math.random() * 7) + 1);
      
      const strike = Math.round(basePrice / 5) * 5 + (isCall ? 5 : -5);
      const entryPrice = (Math.random() * 5 + 1).toFixed(2);
      const exitPrice = (parseFloat(entryPrice) * (1 + (Math.random() * 0.6 - 0.3))).toFixed(2);
      const contracts = Math.floor(Math.random() * 5) + 1;
      const cost = (parseFloat(entryPrice) * contracts * 100).toFixed(2);
      const proceeds = (parseFloat(exitPrice) * contracts * 100).toFixed(2);
      const pnl = (parseFloat(proceeds) - parseFloat(cost)).toFixed(2);
      const pnlPercent = ((parseFloat(pnl) / parseFloat(cost)) * 100).toFixed(2);
      
      trades.push({
        id: i,
        symbol: stock.symbol,
        stockName: stock.name,
        type: isCall ? 'LONG_CALL' : 'LONG_PUT',
        strike,
        expiration: new Date(entryDate.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        entryDate: entryDate.toISOString().split('T')[0],
        exitDate: exitDate.toISOString().split('T')[0],
        entryPrice,
        exitPrice,
        contracts,
        cost,
        proceeds,
        pnl,
        pnlPercent,
        holdingPeriod: Math.floor((exitDate - entryDate) / (1000 * 60 * 60 * 24)),
        result: parseFloat(pnl) >= 0 ? 'WIN' : 'LOSS'
      });
    }
    
    return trades;
  };

  const handleAddPosition = () => {
    // Validate form
    if (!newPosition.strike || !newPosition.expiration || !newPosition.entryPrice) {
      alert('Please fill in all required fields');
      return;
    }
    
    // In a real app, this would be an API call
    const stock = MAG7_STOCKS.find(s => s.symbol === newPosition.symbol);
    const cost = (parseFloat(newPosition.entryPrice) * newPosition.contracts * 100).toFixed(2);
    
    const position = {
      id: positions.length + 1,
      symbol: newPosition.symbol,
      stockName: stock.name,
      type: newPosition.type,
      strike: parseFloat(newPosition.strike),
      expiration: newPosition.expiration,
      entryDate: newPosition.entryDate,
      entryPrice: newPosition.entryPrice,
      currentPrice: newPosition.entryPrice, // Initially the same
      contracts: newPosition.contracts,
      cost,
      value: cost, // Initially the same
      pnl: '0.00',
      pnlPercent: '0.00',
      daysToExpiration: Math.floor((new Date(newPosition.expiration) - new Date()) / (1000 * 60 * 60 * 24)),
      status: 'ACTIVE'
    };
    
    setPositions([position, ...positions]);
    setShowAddPosition(false);
    setNewPosition({
      symbol: 'AAPL',
      type: 'LONG_CALL',
      strike: '',
      expiration: '',
      contracts: 1,
      entryPrice: '',
      entryDate: new Date().toISOString().split('T')[0]
    });
  };

  const handleClosePosition = (position) => {
    // In a real app, this would be an API call
    const exitPrice = (parseFloat(position.currentPrice)).toFixed(2);
    const proceeds = (parseFloat(exitPrice) * position.contracts * 100).toFixed(2);
    const pnl = (parseFloat(proceeds) - parseFloat(position.cost)).toFixed(2);
    const pnlPercent = ((parseFloat(pnl) / parseFloat(position.cost)) * 100).toFixed(2);
    
    const trade = {
      id: trades.length + 1,
      symbol: position.symbol,
      stockName: position.stockName,
      type: position.type,
      strike: position.strike,
      expiration: position.expiration,
      entryDate: position.entryDate,
      exitDate: new Date().toISOString().split('T')[0],
      entryPrice: position.entryPrice,
      exitPrice,
      contracts: position.contracts,
      cost: position.cost,
      proceeds,
      pnl,
      pnlPercent,
      holdingPeriod: Math.floor((new Date() - new Date(position.entryDate)) / (1000 * 60 * 60 * 24)),
      result: parseFloat(pnl) >= 0 ? 'WIN' : 'LOSS'
    };
    
    setTrades([trade, ...trades]);
    setPositions(positions.filter(p => p.id !== position.id));
    setSelectedPosition(null);
  };

  const renderOverview = () => {
    if (!portfolio) return null;
    
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Portfolio Value</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${portfolio.totalValue.toLocaleString()}</div>
              <div className={`flex items-center ${portfolio.totalPnL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {portfolio.totalPnL >= 0 ? <TrendingUp className="mr-1" size={16} /> : <TrendingDown className="mr-1" size={16} />}
                <span>{portfolio.totalPnL >= 0 ? '+' : ''}{portfolio.totalPnL.toLocaleString()} ({portfolio.totalPnLPercent}%)</span>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Today's P&L</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${portfolio.dailyPnL.toLocaleString()}</div>
              <div className={`flex items-center ${portfolio.dailyPnL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {portfolio.dailyPnL >= 0 ? <TrendingUp className="mr-1" size={16} /> : <TrendingDown className="mr-1" size={16} />}
                <span>{portfolio.dailyPnLPercent}%</span>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(portfolio.winRate * 100).toFixed(1)}%</div>
              <div className="text-muted-foreground">
                {Math.round(portfolio.winRate * trades.length)}/{trades.length} trades
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Profit Factor</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{portfolio.profitFactor.toFixed(2)}</div>
              <div className="text-muted-foreground">
                Avg Win: ${portfolio.avgWinAmount.toFixed(2)} / Avg Loss: ${portfolio.avgLossAmount.toFixed(2)}
              </div>
            </CardContent>
          </Card>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Portfolio Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={portfolio.performance}>
                  <defs>
                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip formatter={(value) => ['$' + value.toLocaleString(), 'Portfolio Value']} />
                  <Area type="monotone" dataKey="value" stroke="#3b82f6" fillOpacity={1} fill="url(#colorValue)" />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Stock Allocation</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={Object.entries(portfolio.allocation).map(([symbol, value]) => ({
                      name: symbol,
                      value,
                      color: MAG7_STOCKS.find(s => s.symbol === symbol)?.color || '#000000'
                    }))}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                    label={({name, percent}) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {Object.entries(portfolio.allocation).map(([symbol, value], index) => (
                      <Cell key={`cell-${index}`} fill={MAG7_STOCKS.find(s => s.symbol === symbol)?.color || '#000000'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${value}%`, 'Allocation']} />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Daily Returns</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={portfolio.dailyReturns}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis tickFormatter={(value) => `${value}%`} />
                  <Tooltip formatter={(value) => [`${value}%`, 'Return']} />
                  <Bar dataKey="return" fill={(value) => value >= 0 ? '#22c55e' : '#ef4444'}>
                    {portfolio.dailyReturns.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.return >= 0 ? '#22c55e' : '#ef4444'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Strategy Allocation</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Long Calls', value: portfolio.strategyAllocation['LONG_CALL'], color: '#22c55e' },
                      { name: 'Long Puts', value: portfolio.strategyAllocation['LONG_PUT'], color: '#ef4444' }
                    ]}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                    label={({name, percent}) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    <Cell fill="#22c55e" />
                    <Cell fill="#ef4444" />
                  </Pie>
                  <Tooltip formatter={(value) => [`${value}%`, 'Allocation']} />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Key Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Cash Balance</span>
                    <span>${portfolio.cashBalance.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Invested Value</span>
                    <span>${portfolio.investedValue.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Weekly P&L</span>
                    <span className={portfolio.weeklyPnL >= 0 ? 'text-green-500' : 'text-red-500'}>
                      ${portfolio.weeklyPnL.toLocaleString()} ({portfolio.weeklyPnLPercent}%)
                    </span>
                  </div>
                </div>
                
                <div className="pt-2 border-t">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Sharpe Ratio</span>
                    <span>{portfolio.sharpeRatio.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Max Drawdown</span>
                    <span className="text-red-500">
                      ${portfolio.maxDrawdown.toLocaleString()} ({portfolio.maxDrawdownPercent}%)
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  };

  const renderPositions = () => {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold">Open Positions</h2>
            <p className="text-muted-foreground">Currently holding {positions.length} positions</p>
          </div>
          <Button onClick={() => setShowAddPosition(true)}>
            <Plus className="mr-2" size={16} />
            Add Position
          </Button>
        </div>
        
        {showAddPosition && (
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Add New Position</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setShowAddPosition(false)}>
                  <X size={16} />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="symbol">Stock</Label>
                  <Select value={newPosition.symbol} onValueChange={(value) => setNewPosition({...newPosition, symbol: value})}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select stock" />
                    </SelectTrigger>
                    <SelectContent>
                      {MAG7_STOCKS.map(stock => (
                        <SelectItem key={stock.symbol} value={stock.symbol}>{stock.symbol} - {stock.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="type">Option Type</Label>
                  <Select value={newPosition.type} onValueChange={(value) => setNewPosition({...newPosition, type: value})}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select option type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="LONG_CALL">Long Call</SelectItem>
                      <SelectItem value="LONG_PUT">Long Put</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="strike">Strike Price</Label>
                  <Input
                    id="strike"
                    type="number"
                    placeholder="e.g. 150"
                    value={newPosition.strike}
                    onChange={(e) => setNewPosition({...newPosition, strike: e.target.value})}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="expiration">Expiration Date</Label>
                  <Input
                    id="expiration"
                    type="date"
                    value={newPosition.expiration}
                    onChange={(e) => setNewPosition({...newPosition, expiration: e.target.value})}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="contracts">Number of Contracts</Label>
                  <Input
                    id="contracts"
                    type="number"
                    min="1"
                    placeholder="e.g. 1"
                    value={newPosition.contracts}
                    onChange={(e) => setNewPosition({...newPosition, contracts: parseInt(e.target.value) || 1})}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="entryPrice">Entry Price per Contract</Label>
                  <Input
                    id="entryPrice"
                    type="number"
                    step="0.01"
                    placeholder="e.g. 3.50"
                    value={newPosition.entryPrice}
                    onChange={(e) => setNewPosition({...newPosition, entryPrice: e.target.value})}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="entryDate">Entry Date</Label>
                  <Input
                    id="entryDate"
                    type="date"
                    value={newPosition.entryDate}
                    onChange={(e) => setNewPosition({...newPosition, entryDate: e.target.value})}
                  />
                </div>
              </div>
            </CardContent>
            <CardFooter className="flex justify-end space-x-2">
              <Button variant="outline" onClick={() => setShowAddPosition(false)}>Cancel</Button>
              <Button onClick={handleAddPosition}>Add Position</Button>
            </CardFooter>
          </Card>
        )}
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className={`${selectedPosition ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
            <Card>
              <CardHeader>
                <CardTitle>Current Positions</CardTitle>
              </CardHeader>
              <CardContent>
                {positions.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No open positions. Add a position to get started.
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Symbol</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Strike</TableHead>
                        <TableHead>Expiration</TableHead>
                        <TableHead>DTE</TableHead>
                        <TableHead>Contracts</TableHead>
                        <TableHead>Current Value</TableHead>
                        <TableHead>P&L</TableHead>
                        <TableHead></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {positions.map(position => (
                        <TableRow key={position.id} className="cursor-pointer hover:bg-muted/50" onClick={() => setSelectedPosition(position)}>
                          <TableCell className="font-medium">{position.symbol}</TableCell>
                          <TableCell>
                            <div className="flex items-center">
                              {position.type === 'LONG_CALL' ? (
                                <ArrowUpCircle className="mr-1 text-green-500" size={16} />
                              ) : (
                                <ArrowDownCircle className="mr-1 text-red-500" size={16} />
                              )}
                              {position.type === 'LONG_CALL' ? 'Call' : 'Put'}
                            </div>
                          </TableCell>
                          <TableCell>${position.strike}</TableCell>
                          <TableCell>{position.expiration}</TableCell>
                          <TableCell>{position.daysToExpiration}</TableCell>
                          <TableCell>{position.contracts}</TableCell>
                          <TableCell>${position.value}</TableCell>
                          <TableCell>
                            <div className={`flex items-center ${parseFloat(position.pnl) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                              {parseFloat(position.pnl) >= 0 ? (
                                <TrendingUp className="mr-1" size={16} />
                              ) : (
                                <TrendingDown className="mr-1" size={16} />
                              )}
                              ${position.pnl} ({position.pnlPercent}%)
                            </div>
                          </TableCell>
                          <TableCell>
                            <Button variant="ghost" size="sm">View</Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>
          
          {selectedPosition && (
            <div className="lg:col-span-1">
              <Card>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <CardTitle>Position Details</CardTitle>
                    <Button variant="ghost" size="sm" onClick={() => setSelectedPosition(null)}>
                      <X size={16} />
                    </Button>
                  </div>
                  <CardDescription>
                    {selectedPosition.symbol} - {selectedPosition.type === 'LONG_CALL' ? 'Call' : 'Put'} @ ${selectedPosition.strike}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <h3 className="text-sm font-medium text-muted-foreground mb-1">Entry Date</h3>
                        <div className="text-lg font-semibold">{selectedPosition.entryDate}</div>
                      </div>
                      <div>
                        <h3 className="text-sm font-medium text-muted-foreground mb-1">Expiration Date</h3>
                        <div className="text-lg font-semibold">{selectedPosition.expiration}</div>
                      </div>
                      <div>
                        <h3 className="text-sm font-medium text-muted-foreground mb-1">Days to Expiration</h3>
                        <div className="text-lg font-semibold">{selectedPosition.daysToExpiration}</div>
                      </div>
                      <div>
                        <h3 className="text-sm font-medium text-muted-foreground mb-1">Contracts</h3>
                        <div className="text-lg font-semibold">{selectedPosition.contracts}</div>
                      </div>
                    </div>
                    
                    <div>
                      <h3 className="text-sm font-medium text-muted-foreground mb-2">Performance</h3>
                      <div className="grid grid-cols-2 gap-4">
                        <Card>
                          <CardHeader className="py-2">
                            <CardTitle className="text-xs">Entry Price</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-lg font-bold">${selectedPosition.entryPrice}</div>
                            <div className="text-xs text-muted-foreground">Total: ${selectedPosition.cost}</div>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardHeader className="py-2">
                            <CardTitle className="text-xs">Current Price</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-lg font-bold">${selectedPosition.currentPrice}</div>
                            <div className="text-xs text-muted-foreground">Total: ${selectedPosition.value}</div>
                          </CardContent>
                        </Card>
                      </div>
                      
                      <div className="mt-4">
                        <Card>
                          <CardHeader className="py-2">
                            <CardTitle className="text-xs">Profit/Loss</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className={`text-lg font-bold ${parseFloat(selectedPosition.pnl) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                              ${selectedPosition.pnl} ({selectedPosition.pnlPercent}%)
                            </div>
                            <Progress 
                              value={Math.min(Math.max(parseFloat(selectedPosition.pnlPercent) + 100, 0), 200) / 2} 
                              className="h-2 mt-2"
                              indicatorClassName={parseFloat(selectedPosition.pnl) >= 0 ? 'bg-green-500' : 'bg-red-500'}
                            />
                          </CardContent>
                        </Card>
                      </div>
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="flex justify-between">
                  <Button variant="outline">Edit Position</Button>
                  <Button variant="default" onClick={() => handleClosePosition(selectedPosition)}>Close Position</Button>
                </CardFooter>
              </Card>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderTrades = () => {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold">Trade History</h2>
          <p className="text-muted-foreground">Showing {trades.length} completed trades</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total Trades</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{trades.length}</div>
              <div className="text-muted-foreground">
                {trades.filter(t => t.result === 'WIN').length} wins / {trades.filter(t => t.result === 'LOSS').length} losses
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{((trades.filter(t => t.result === 'WIN').length / trades.length) * 100).toFixed(1)}%</div>
              <Progress 
                value={(trades.filter(t => t.result === 'WIN').length / trades.length) * 100} 
                className="h-2 mt-2"
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Average P&L</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                ${(trades.reduce((sum, trade) => sum + parseFloat(trade.pnl), 0) / trades.length).toFixed(2)}
              </div>
              <div className="text-muted-foreground">
                Per trade average
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Average Holding</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(trades.reduce((sum, trade) => sum + trade.holdingPeriod, 0) / trades.length).toFixed(1)} days
              </div>
              <div className="text-muted-foreground">
                Per trade average
              </div>
            </CardContent>
          </Card>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle>Trade History</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Strike</TableHead>
                  <TableHead>Entry Date</TableHead>
                  <TableHead>Exit Date</TableHead>
                  <TableHead>Holding</TableHead>
                  <TableHead>P&L</TableHead>
                  <TableHead>Result</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {trades.map(trade => (
                  <TableRow key={trade.id}>
                    <TableCell className="font-medium">{trade.symbol}</TableCell>
                    <TableCell>
                      <div className="flex items-center">
                        {trade.type === 'LONG_CALL' ? (
                          <ArrowUpCircle className="mr-1 text-green-500" size={16} />
                        ) : (
                          <ArrowDownCircle className="mr-1 text-red-500" size={16} />
                        )}
                        {trade.type === 'LONG_CALL' ? 'Call' : 'Put'}
                      </div>
                    </TableCell>
                    <TableCell>${trade.strike}</TableCell>
                    <TableCell>{trade.entryDate}</TableCell>
                    <TableCell>{trade.exitDate}</TableCell>
                    <TableCell>{trade.holdingPeriod} days</TableCell>
                    <TableCell>
                      <div className={`flex items-center ${parseFloat(trade.pnl) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {parseFloat(trade.pnl) >= 0 ? (
                          <TrendingUp className="mr-1" size={16} />
                        ) : (
                          <TrendingDown className="mr-1" size={16} />
                        )}
                        ${trade.pnl} ({trade.pnlPercent}%)
                      </div>
                    </TableCell>
                    <TableCell>
                      {trade.result === 'WIN' ? (
                        <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Win</Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-800 hover:bg-red-100">Loss</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <div className="container mx-auto p-4">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Portfolio Manager</h1>
          <p className="text-muted-foreground">Manage your 7DTE options portfolio for Magnificent 7 stocks</p>
        </div>
        <div className="flex space-x-2 mt-4 md:mt-0">
          <Button variant="outline" onClick={fetchPortfolioData} className="flex items-center">
            <RefreshCw className="mr-2" size={16} />
            Refresh
          </Button>
        </div>
      </div>
      
      <Tabs defaultValue="overview" value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview" className="flex items-center">
            <BarChart2 className="mr-2" size={16} />
            Overview
          </TabsTrigger>
          <TabsTrigger value="positions" className="flex items-center">
            <Activity className="mr-2" size={16} />
            Positions
          </TabsTrigger>
          <TabsTrigger value="trades" className="flex items-center">
            <Briefcase className="mr-2" size={16} />
            Trade History
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="space-y-4">
          {loading ? (
            <div className="animate-pulse space-y-4">
              <div className="h-20 bg-gray-200 rounded"></div>
              <div className="h-80 bg-gray-200 rounded"></div>
              <div className="h-40 bg-gray-200 rounded"></div>
            </div>
          ) : (
            renderOverview()
          )}
        </TabsContent>
        
        <TabsContent value="positions" className="space-y-4">
          {loading ? (
            <div className="animate-pulse space-y-4">
              <div className="h-20 bg-gray-200 rounded"></div>
              <div className="h-80 bg-gray-200 rounded"></div>
            </div>
          ) : (
            renderPositions()
          )}
        </TabsContent>
        
        <TabsContent value="trades" className="space-y-4">
          {loading ? (
            <div className="animate-pulse space-y-4">
              <div className="h-20 bg-gray-200 rounded"></div>
              <div className="h-80 bg-gray-200 rounded"></div>
            </div>
          ) : (
            renderTrades()
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default PortfolioManager;

