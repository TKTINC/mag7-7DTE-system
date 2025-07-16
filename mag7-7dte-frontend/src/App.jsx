import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, NavLink } from 'react-router-dom';
import { Button } from './components/ui/button';
import { Tabs, TabsList, TabsTrigger } from './components/ui/tabs';
import { Avatar, AvatarFallback, AvatarImage } from './components/ui/avatar';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from './components/ui/dropdown-menu';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from './components/ui/sheet';
import { Switch } from './components/ui/switch';
import { Label } from './components/ui/label';
import { Separator } from './components/ui/separator';
import { BarChart2, Activity, Briefcase, LineChart, MessageSquare, Settings, Menu, Sun, Moon, LogOut, ChevronRight, Home, Bell, Search } from 'lucide-react';

import StockDashboard from './components/StockDashboard';
import SignalExplorer from './components/SignalExplorer';
import PortfolioManager from './components/PortfolioManager';
import ConversationalAI from './components/ConversationalAI';

function App() {
  const [theme, setTheme] = useState('light');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.documentElement.classList.toggle('dark', newTheme === 'dark');
  };

  return (
    <Router>
      <div className="min-h-screen bg-background">
        {/* Mobile Header */}
        <header className="lg:hidden sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="container flex h-14 items-center">
            <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="mr-2">
                  <Menu className="h-5 w-5" />
                  <span className="sr-only">Toggle menu</span>
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="pr-0">
                <SheetHeader>
                  <SheetTitle>Mag7-7DTE-System</SheetTitle>
                  <SheetDescription>
                    Options trading for Magnificent 7 stocks
                  </SheetDescription>
                </SheetHeader>
                <div className="grid gap-2 py-6">
                  <Link 
                    to="/" 
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md hover:bg-accent hover:text-accent-foreground"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <Home className="h-5 w-5" />
                    Dashboard
                  </Link>
                  <Link 
                    to="/signals" 
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md hover:bg-accent hover:text-accent-foreground"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <Activity className="h-5 w-5" />
                    Signals
                  </Link>
                  <Link 
                    to="/portfolio" 
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md hover:bg-accent hover:text-accent-foreground"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <Briefcase className="h-5 w-5" />
                    Portfolio
                  </Link>
                  <Link 
                    to="/assistant" 
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md hover:bg-accent hover:text-accent-foreground"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <MessageSquare className="h-5 w-5" />
                    AI Assistant
                  </Link>
                </div>
                <Separator />
                <div className="mt-4 px-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Switch id="mobile-theme-toggle" checked={theme === 'dark'} onCheckedChange={toggleTheme} />
                      <Label htmlFor="mobile-theme-toggle">Dark Mode</Label>
                    </div>
                  </div>
                </div>
              </SheetContent>
            </Sheet>
            <Link to="/" className="flex items-center gap-2 font-semibold">
              <BarChart2 className="h-6 w-6" />
              <span>Mag7-7DTE</span>
            </Link>
            <div className="flex-1"></div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon">
                <Bell className="h-5 w-5" />
                <span className="sr-only">Notifications</span>
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="rounded-full">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src="" />
                      <AvatarFallback>U</AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>My Account</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>
                    <Settings className="mr-2 h-4 w-4" />
                    <span>Settings</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>Log out</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>

        <div className="flex min-h-screen">
          {/* Desktop Sidebar */}
          <aside className="hidden lg:flex h-screen w-64 flex-col fixed inset-y-0 z-50 border-r bg-background">
            <div className="flex h-14 items-center border-b px-4">
              <Link to="/" className="flex items-center gap-2 font-semibold">
                <BarChart2 className="h-6 w-6" />
                <span>Mag7-7DTE-System</span>
              </Link>
            </div>
            <div className="flex-1 overflow-auto py-2">
              <nav className="grid items-start px-2 text-sm font-medium">
                <NavLink 
                  to="/" 
                  className={({ isActive }) => 
                    `flex items-center gap-3 rounded-lg px-3 py-2 transition-all ${
                      isActive 
                        ? 'bg-accent text-accent-foreground' 
                        : 'hover:bg-accent hover:text-accent-foreground'
                    }`
                  }
                >
                  <Home className="h-4 w-4" />
                  Dashboard
                </NavLink>
                <NavLink 
                  to="/signals" 
                  className={({ isActive }) => 
                    `flex items-center gap-3 rounded-lg px-3 py-2 transition-all ${
                      isActive 
                        ? 'bg-accent text-accent-foreground' 
                        : 'hover:bg-accent hover:text-accent-foreground'
                    }`
                  }
                >
                  <Activity className="h-4 w-4" />
                  Signal Explorer
                </NavLink>
                <NavLink 
                  to="/portfolio" 
                  className={({ isActive }) => 
                    `flex items-center gap-3 rounded-lg px-3 py-2 transition-all ${
                      isActive 
                        ? 'bg-accent text-accent-foreground' 
                        : 'hover:bg-accent hover:text-accent-foreground'
                    }`
                  }
                >
                  <Briefcase className="h-4 w-4" />
                  Portfolio Manager
                </NavLink>
                <NavLink 
                  to="/assistant" 
                  className={({ isActive }) => 
                    `flex items-center gap-3 rounded-lg px-3 py-2 transition-all ${
                      isActive 
                        ? 'bg-accent text-accent-foreground' 
                        : 'hover:bg-accent hover:text-accent-foreground'
                    }`
                  }
                >
                  <MessageSquare className="h-4 w-4" />
                  AI Assistant
                </NavLink>
              </nav>
            </div>
            <div className="mt-auto p-4 border-t">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Avatar>
                    <AvatarImage src="" />
                    <AvatarFallback>U</AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="text-sm font-medium">User</p>
                    <p className="text-xs text-muted-foreground">user@example.com</p>
                  </div>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem>
                      <Settings className="mr-2 h-4 w-4" />
                      <span>Settings</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      {theme === 'light' ? (
                        <Moon className="mr-2 h-4 w-4" />
                      ) : (
                        <Sun className="mr-2 h-4 w-4" />
                      )}
                      <span onClick={toggleTheme}>
                        {theme === 'light' ? 'Dark Mode' : 'Light Mode'}
                      </span>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem>
                      <LogOut className="mr-2 h-4 w-4" />
                      <span>Log out</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <main className="flex-1 lg:pl-64">
            <Routes>
              <Route path="/" element={<StockDashboard />} />
              <Route path="/signals" element={<SignalExplorer />} />
              <Route path="/portfolio" element={<PortfolioManager />} />
              <Route path="/assistant" element={<ConversationalAI />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
}

export default App;

