import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "./ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Slider } from "./ui/slider";
import { Switch } from "./ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { ArrowUpCircle, ArrowDownCircle, Filter, RefreshCw, Check, X, AlertCircle, Clock, Calendar, DollarSign, Percent, BarChart2, TrendingUp, TrendingDown } from 'lucide-react';

const MAG7_STOCKS = [
  { symbol: 'AAPL', name: 'Apple Inc.' },
  { symbol: 'MSFT', name: 'Microsoft Corp.' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.' },
  { symbol: 'AMZN', name: 'Amazon.com Inc.' },
  { symbol: 'NVDA', name: 'NVIDIA Corp.' },
  { symbol: 'TSLA', name: 'Tesla Inc.' },
  { symbol: 'META', name: 'Meta Platforms Inc.' },
];

const SIGNAL_SOURCES = [
  { id: 'TECHNICAL', name: 'Technical Analysis' },
  { id: 'FUNDAMENTAL', name: 'Fundamental Analysis' },
  { id: 'VOLATILITY', name: 'Volatility Analysis' },
  { id: 'ENSEMBLE', name: 'Ensemble Strategy' },
];

const SIGNAL_TYPES = [
  { id: 'LONG_CALL', name: 'Long Call', icon: <ArrowUpCircle className="text-green-500" size={16} /> },
  { id: 'LONG_PUT', name: 'Long Put', icon: <ArrowDownCircle className="text-red-500" size={16} /> },
];

const SignalExplorer = () => {
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    stocks: MAG7_STOCKS.map(s => s.symbol),
    sources: SIGNAL_SOURCES.map(s => s.id),
    types: SIGNAL_TYPES.map(t => t.id),
    minConfidence: 60,
    onlyActive: false,
    dateRange: '7d',
  });
  const [filteredSignals, setFilteredSignals] = useState([]);
  const [selectedSignal, setSelectedSignal] = useState(null);
  const [view, setView] = useState('table');

  useEffect(() => {
    fetchSignals();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [signals, filters]);

  const fetchSignals = async () => {
    setLoading(true);
    try {
      // In a real implementation, this would be an API call
      // For now, we'll use mock data
      const mockSignals = generateMockSignals();
      setSignals(mockSignals);
    } catch (error) {
      console.error('Error fetching signals:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateMockSignals = () => {
    const mockSignals = [];
    
    // Generate 50 mock signals
    for (let i = 1; i <= 50; i++) {
      const stock = MAG7_STOCKS[Math.floor(Math.random() * MAG7_STOCKS.length)];
      const source = SIGNAL_SOURCES[Math.floor(Math.random() * SIGNAL_SOURCES.length)];
      const type = SIGNAL_TYPES[Math.floor(Math.random() * SIGNAL_TYPES.length)];
      const basePrice = {
        'AAPL': 175.25,
        'MSFT': 325.50,
        'GOOGL': 142.75,
        'AMZN': 132.30,
        'NVDA': 425.80,
        'TSLA': 245.60,
        'META': 315.40,
      }[stock.symbol] || 100;
      
      // Random date within the last 30 days
      const date = new Date();
      date.setDate(date.getDate() - Math.floor(Math.random() * 30));
      
      // Random expiration date 7 days from signal date
      const expiration = new Date(date);
      expiration.setDate(expiration.getDate() + 7);
      
      mockSignals.push({
        id: i,
        symbol: stock.symbol,
        stockName: stock.name,
        type: type.id,
        source: source.id,
        confidence: (Math.random() * 0.4 + 0.6).toFixed(2), // 0.6 to 1.0
        timestamp: date.toISOString(),
        strike: Math.round(basePrice / 5) * 5 + (Math.random() > 0.5 ? 5 : -5),
        expiration: expiration.toISOString().split('T')[0],
        status: ['PENDING', 'ACTIVE', 'EXECUTED', 'EXPIRED', 'CANCELLED'][Math.floor(Math.random() * 5)],
        entryPrice: Math.random() > 0.3 ? (Math.random() * 5 + 1).toFixed(2) : null,
        currentPrice: Math.random() > 0.3 ? (Math.random() * 10 + 1).toFixed(2) : null,
        pnl: Math.random() > 0.3 ? (Math.random() * 200 - 100).toFixed(2) : null,
        pnlPercent: Math.random() > 0.3 ? (Math.random() * 200 - 100).toFixed(2) : null,
        factors: [
          {
            name: 'RSI',
            value: (Math.random() * 100).toFixed(2),
            weight: (Math.random() * 0.5 + 0.5).toFixed(2),
            category: 'technical'
          },
          {
            name: 'IV Percentile',
            value: (Math.random() * 100).toFixed(2),
            weight: (Math.random() * 0.5 + 0.5).toFixed(2),
            category: 'volatility'
          },
          {
            name: 'Earnings',
            value: (Math.random() * 10 - 5).toFixed(2),
            weight: (Math.random() * 0.5 + 0.5).toFixed(2),
            category: 'fundamental'
          }
        ]
      });
    }
    
    return mockSignals;
  };

  const applyFilters = () => {
    const filtered = signals.filter(signal => {
      // Filter by stock
      if (!filters.stocks.includes(signal.symbol)) return false;
      
      // Filter by source
      if (!filters.sources.includes(signal.source)) return false;
      
      // Filter by type
      if (!filters.types.includes(signal.type)) return false;
      
      // Filter by confidence
      if (parseFloat(signal.confidence) * 100 < filters.minConfidence) return false;
      
      // Filter by active status
      if (filters.onlyActive && signal.status !== 'ACTIVE') return false;
      
      // Filter by date range
      const signalDate = new Date(signal.timestamp);
      const now = new Date();
      let cutoffDate;
      
      switch (filters.dateRange) {
        case '1d':
          cutoffDate = new Date(now.setDate(now.getDate() - 1));
          break;
        case '7d':
          cutoffDate = new Date(now.setDate(now.getDate() - 7));
          break;
        case '30d':
          cutoffDate = new Date(now.setDate(now.getDate() - 30));
          break;
        case 'all':
        default:
          cutoffDate = new Date(0); // Beginning of time
          break;
      }
      
      if (signalDate < cutoffDate) return false;
      
      return true;
    });
    
    setFilteredSignals(filtered);
  };

  const toggleStockFilter = (symbol) => {
    if (filters.stocks.includes(symbol)) {
      setFilters({
        ...filters,
        stocks: filters.stocks.filter(s => s !== symbol)
      });
    } else {
      setFilters({
        ...filters,
        stocks: [...filters.stocks, symbol]
      });
    }
  };

  const toggleSourceFilter = (source) => {
    if (filters.sources.includes(source)) {
      setFilters({
        ...filters,
        sources: filters.sources.filter(s => s !== source)
      });
    } else {
      setFilters({
        ...filters,
        sources: [...filters.sources, source]
      });
    }
  };

  const toggleTypeFilter = (type) => {
    if (filters.types.includes(type)) {
      setFilters({
        ...filters,
        types: filters.types.filter(t => t !== type)
      });
    } else {
      setFilters({
        ...filters,
        types: [...filters.types, type]
      });
    }
  };

  const handleConfidenceChange = (value) => {
    setFilters({
      ...filters,
      minConfidence: value[0]
    });
  };

  const handleActiveToggle = (checked) => {
    setFilters({
      ...filters,
      onlyActive: checked
    });
  };

  const handleDateRangeChange = (value) => {
    setFilters({
      ...filters,
      dateRange: value
    });
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'PENDING':
        return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">Pending</Badge>;
      case 'ACTIVE':
        return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Active</Badge>;
      case 'EXECUTED':
        return <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">Executed</Badge>;
      case 'EXPIRED':
        return <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">Expired</Badge>;
      case 'CANCELLED':
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">Cancelled</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const renderSignalTable = () => {
    return (
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Symbol</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Strike</TableHead>
              <TableHead>Expiration</TableHead>
              <TableHead>Confidence</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>P&L</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredSignals.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-4">
                  No signals match your filters
                </TableCell>
              </TableRow>
            ) : (
              filteredSignals.map(signal => (
                <TableRow key={signal.id} className="cursor-pointer hover:bg-muted/50" onClick={() => setSelectedSignal(signal)}>
                  <TableCell className="font-medium">{signal.symbol}</TableCell>
                  <TableCell>
                    <div className="flex items-center">
                      {signal.type === 'LONG_CALL' ? (
                        <ArrowUpCircle className="mr-1 text-green-500" size={16} />
                      ) : (
                        <ArrowDownCircle className="mr-1 text-red-500" size={16} />
                      )}
                      {signal.type === 'LONG_CALL' ? 'Call' : 'Put'}
                    </div>
                  </TableCell>
                  <TableCell>${signal.strike}</TableCell>
                  <TableCell>{signal.expiration}</TableCell>
                  <TableCell>{(parseFloat(signal.confidence) * 100).toFixed(0)}%</TableCell>
                  <TableCell>{signal.source}</TableCell>
                  <TableCell>{getStatusBadge(signal.status)}</TableCell>
                  <TableCell>
                    {signal.pnl !== null ? (
                      <div className={`flex items-center ${parseFloat(signal.pnl) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {parseFloat(signal.pnl) >= 0 ? (
                          <TrendingUp className="mr-1" size={16} />
                        ) : (
                          <TrendingDown className="mr-1" size={16} />
                        )}
                        ${signal.pnl} ({signal.pnlPercent}%)
                      </div>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm">View</Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    );
  };

  const renderSignalCards = () => {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredSignals.length === 0 ? (
          <div className="col-span-full text-center py-8 text-muted-foreground">
            No signals match your filters
          </div>
        ) : (
          filteredSignals.map(signal => (
            <Card key={signal.id} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setSelectedSignal(signal)}>
              <CardHeader className="pb-2">
                <div className="flex justify-between items-center">
                  <CardTitle className="text-lg font-medium">
                    {signal.symbol} - {signal.type === 'LONG_CALL' ? (
                      <span className="inline-flex items-center text-green-500"><ArrowUpCircle className="mr-1" size={16} /> Call</span>
                    ) : (
                      <span className="inline-flex items-center text-red-500"><ArrowDownCircle className="mr-1" size={16} /> Put</span>
                    )}
                  </CardTitle>
                  {getStatusBadge(signal.status)}
                </div>
                <CardDescription>
                  <div className="flex items-center space-x-2">
                    <span className="flex items-center"><Calendar className="mr-1" size={14} /> {signal.expiration}</span>
                    <span className="flex items-center"><DollarSign className="mr-1" size={14} /> Strike: ${signal.strike}</span>
                  </div>
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Confidence:</span>
                    <Badge variant={parseFloat(signal.confidence) > 0.75 ? "default" : "outline"}>
                      {(parseFloat(signal.confidence) * 100).toFixed(0)}%
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Source:</span>
                    <span>{signal.source}</span>
                  </div>
                  {signal.pnl !== null && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">P&L:</span>
                      <span className={parseFloat(signal.pnl) >= 0 ? 'text-green-500' : 'text-red-500'}>
                        ${signal.pnl} ({signal.pnlPercent}%)
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
              <CardFooter>
                <div className="w-full text-right">
                  <span className="text-xs text-muted-foreground">
                    <Clock className="inline mr-1" size={12} />
                    {new Date(signal.timestamp).toLocaleString()}
                  </span>
                </div>
              </CardFooter>
            </Card>
          ))
        )}
      </div>
    );
  };

  const renderSignalDetail = () => {
    if (!selectedSignal) return null;
    
    return (
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>Signal Details</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setSelectedSignal(null)}>
              <X size={16} />
            </Button>
          </div>
          <CardDescription>
            {selectedSignal.symbol} - {selectedSignal.stockName}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Signal Type</h3>
                <div className="text-lg font-semibold">
                  {selectedSignal.type === 'LONG_CALL' ? (
                    <span className="flex items-center text-green-500"><ArrowUpCircle className="mr-2" size={20} /> Long Call</span>
                  ) : (
                    <span className="flex items-center text-red-500"><ArrowDownCircle className="mr-2" size={20} /> Long Put</span>
                  )}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Status</h3>
                <div>{getStatusBadge(selectedSignal.status)}</div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Strike Price</h3>
                <div className="text-lg font-semibold">${selectedSignal.strike}</div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Expiration Date</h3>
                <div className="text-lg font-semibold">{selectedSignal.expiration}</div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Confidence Score</h3>
                <div className="text-lg font-semibold">{(parseFloat(selectedSignal.confidence) * 100).toFixed(0)}%</div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-1">Signal Source</h3>
                <div className="text-lg font-semibold">{selectedSignal.source}</div>
              </div>
            </div>
            
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-2">Performance</h3>
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <CardHeader className="py-2">
                    <CardTitle className="text-xs">Entry Price</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-lg font-bold">
                      {selectedSignal.entryPrice !== null ? `$${selectedSignal.entryPrice}` : '-'}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="py-2">
                    <CardTitle className="text-xs">Current Price</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-lg font-bold">
                      {selectedSignal.currentPrice !== null ? `$${selectedSignal.currentPrice}` : '-'}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="py-2">
                    <CardTitle className="text-xs">P&L</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className={`text-lg font-bold ${selectedSignal.pnl !== null && parseFloat(selectedSignal.pnl) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {selectedSignal.pnl !== null ? (
                        <>
                          ${selectedSignal.pnl}
                          <span className="text-xs ml-1">({selectedSignal.pnlPercent}%)</span>
                        </>
                      ) : '-'}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
            
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-2">Signal Factors</h3>
              <div className="space-y-3">
                {selectedSignal.factors.map((factor, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div>
                      <span className="font-medium">{factor.name}</span>
                      <span className="text-xs text-muted-foreground ml-2">({factor.category})</span>
                    </div>
                    <div className="flex items-center">
                      <span className="mr-2">{factor.value}</span>
                      <Badge variant="outline">Weight: {factor.weight}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-1">Signal Generated</h3>
              <div className="text-sm">
                {new Date(selectedSignal.timestamp).toLocaleString()}
              </div>
            </div>
          </div>
        </CardContent>
        <CardFooter className="flex justify-between">
          <Button variant="outline">Execute Trade</Button>
          <Button variant="default">View Similar Signals</Button>
        </CardFooter>
      </Card>
    );
  };

  return (
    <div className="container mx-auto p-4">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Signal Explorer</h1>
          <p className="text-muted-foreground">Explore and filter trading signals for Magnificent 7 stocks</p>
        </div>
        <div className="flex space-x-2 mt-4 md:mt-0">
          <Button variant="outline" onClick={fetchSignals} className="flex items-center">
            <RefreshCw className="mr-2" size={16} />
            Refresh
          </Button>
          <Button variant="outline" onClick={() => setView(view === 'table' ? 'cards' : 'table')} className="flex items-center">
            {view === 'table' ? 'Card View' : 'Table View'}
          </Button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Filter className="mr-2" size={18} />
                Filters
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <Label className="text-base">Stocks</Label>
                <div className="grid grid-cols-2 gap-2 mt-2">
                  {MAG7_STOCKS.map(stock => (
                    <Button
                      key={stock.symbol}
                      variant={filters.stocks.includes(stock.symbol) ? "default" : "outline"}
                      size="sm"
                      onClick={() => toggleStockFilter(stock.symbol)}
                      className="justify-start"
                    >
                      {filters.stocks.includes(stock.symbol) && <Check className="mr-1" size={14} />}
                      {stock.symbol}
                    </Button>
                  ))}
                </div>
              </div>
              
              <div>
                <Label className="text-base">Signal Sources</Label>
                <div className="grid grid-cols-1 gap-2 mt-2">
                  {SIGNAL_SOURCES.map(source => (
                    <Button
                      key={source.id}
                      variant={filters.sources.includes(source.id) ? "default" : "outline"}
                      size="sm"
                      onClick={() => toggleSourceFilter(source.id)}
                      className="justify-start"
                    >
                      {filters.sources.includes(source.id) && <Check className="mr-1" size={14} />}
                      {source.name}
                    </Button>
                  ))}
                </div>
              </div>
              
              <div>
                <Label className="text-base">Signal Types</Label>
                <div className="grid grid-cols-2 gap-2 mt-2">
                  {SIGNAL_TYPES.map(type => (
                    <Button
                      key={type.id}
                      variant={filters.types.includes(type.id) ? "default" : "outline"}
                      size="sm"
                      onClick={() => toggleTypeFilter(type.id)}
                      className="justify-start"
                    >
                      {filters.types.includes(type.id) && <Check className="mr-1" size={14} />}
                      <span className="flex items-center">
                        {type.icon}
                        <span className="ml-1">{type.name.split('_')[1]}</span>
                      </span>
                    </Button>
                  ))}
                </div>
              </div>
              
              <div>
                <div className="flex justify-between items-center">
                  <Label className="text-base">Min Confidence</Label>
                  <span className="text-sm font-medium">{filters.minConfidence}%</span>
                </div>
                <Slider
                  defaultValue={[filters.minConfidence]}
                  min={0}
                  max={100}
                  step={5}
                  onValueChange={handleConfidenceChange}
                  className="mt-2"
                />
              </div>
              
              <div className="flex items-center space-x-2">
                <Switch
                  id="active-only"
                  checked={filters.onlyActive}
                  onCheckedChange={handleActiveToggle}
                />
                <Label htmlFor="active-only">Active Signals Only</Label>
              </div>
              
              <div>
                <Label className="text-base">Date Range</Label>
                <Select defaultValue={filters.dateRange} onValueChange={handleDateRangeChange}>
                  <SelectTrigger className="mt-2">
                    <SelectValue placeholder="Select date range" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1d">Last 24 Hours</SelectItem>
                    <SelectItem value="7d">Last 7 Days</SelectItem>
                    <SelectItem value="30d">Last 30 Days</SelectItem>
                    <SelectItem value="all">All Time</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <Button className="w-full" variant="outline" onClick={() => {
                setFilters({
                  stocks: MAG7_STOCKS.map(s => s.symbol),
                  sources: SIGNAL_SOURCES.map(s => s.id),
                  types: SIGNAL_TYPES.map(t => t.id),
                  minConfidence: 60,
                  onlyActive: false,
                  dateRange: '7d',
                });
              }}>
                Reset Filters
              </Button>
            </CardContent>
          </Card>
        </div>
        
        <div className={`${selectedSignal ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Trading Signals</CardTitle>
                <Badge variant="outline">{filteredSignals.length} signals</Badge>
              </div>
              <CardDescription>
                Showing {filteredSignals.length} of {signals.length} signals based on your filters
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="animate-pulse space-y-4">
                  <div className="h-10 bg-gray-200 rounded"></div>
                  <div className="h-10 bg-gray-200 rounded"></div>
                  <div className="h-10 bg-gray-200 rounded"></div>
                  <div className="h-10 bg-gray-200 rounded"></div>
                  <div className="h-10 bg-gray-200 rounded"></div>
                </div>
              ) : (
                view === 'table' ? renderSignalTable() : renderSignalCards()
              )}
            </CardContent>
          </Card>
        </div>
        
        {selectedSignal && (
          <div className="lg:col-span-1">
            {renderSignalDetail()}
          </div>
        )}
      </div>
    </div>
  );
};

export default SignalExplorer;

