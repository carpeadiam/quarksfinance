from jugaad_data.nse import NSELive
from datetime import datetime, date, timedelta
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from statsmodels.tsa.arima.model import ARIMA
import numpy as np
import os
import base64
from typing import List, Dict
from matplotlib import pyplot as plt
import json
import requests
from jugaad_data.nse import bhavcopy_save
from flask import jsonify
import tempfile
from mailing import send_strategy_signal


# Run once at the start of your script

email_global=''

# Add this class just below your imports
class PortfolioEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


# Initialize NSELive for live data
nse = NSELive()


def get_stock_price(symbol, live=True):
    """Fetch live (most recent) or today's stock price for Indian stocks using yfinance"""
    # Ensure symbol ends with '.NS' for NSE stocks
    if not symbol.endswith('.NS'):
        symbol += '.NS'

    try:
        stock = yf.Ticker(symbol)

        if live:
            # Fetch the latest market data
            data = stock.history(period='1d', interval='1m')  # 1-minute intervals for today
            if not data.empty:
                result = data['Close'].iloc[-1]  # Most recent close (live price)
                print(f"get_stock_price result for {symbol} (live=True): {result}")
                return result
        else:
            today = date.today().strftime('%Y-%m-%d')
            data = stock.history(start=today, end=today)
            if not data.empty:
                result = data['Close'].iloc[-1]  # Last close price for the day
                print(f"get_stock_price result for {symbol} (live=False): {result}")
                return result

        print(f"No data found for {symbol}")
        return None  # No data found
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None


def stock_df(symbol, from_date=None, to_date=None, series='EQ'):
    """
    Fetch stock data in the same format as jugaad_data.stock_df() using yfinance.

    Parameters:
    -----------
    symbol : str
        Stock symbol (e.g., 'RELIANCE', 'TCS', 'AAPL').
        If Indian stock, '.NS' is auto-added.
    from_date : datetime.datetime (optional)
        Start date (default: 5 years ago).
    to_date : datetime.datetime (optional)
        End date (default: today).

    Returns:
    --------
    pandas.DataFrame
        Columns: DATE SERIES, SERIES, OPEN, HIGH, LOW, CLOSE, VALUE, NO OF TRADES, SYMBOL
    """
    # Auto-add '.NS' suffix if missing (for Indian stocks)
    if '.' not in symbol:
        symbol = f"{symbol}.NS"

    # Default date handling
    if from_date is None:
        from_date = datetime.now() - pd.DateOffset(years=5)
    if to_date is None:
        to_date = datetime.now()

    # Convert datetime to string for yfinance
    start_str = from_date.strftime('%Y-%m-%d')
    end_str = to_date.strftime('%Y-%m-%d')

    # Download data
    data = yf.download(symbol, start=start_str, end=end_str, progress=False)

    if data is None or data.empty:
        print(f"No data found for {symbol} between {start_str} and {end_str}")
        return pd.DataFrame()

    # Reset index and rename columns
    data = data.reset_index()
    data = data.rename(columns={
        'Date': 'DATE SERIES',
        'Open': 'OPEN',
        'High': 'HIGH',
        'Low': 'LOW',
        'Close': 'CLOSE',
        'Volume': 'NO OF TRADES'
    })

    # Add required columns
    data['SERIES'] = 'EQ'
    data['SYMBOL'] = symbol.split('.')[0]  # Remove .NS suffix
    data['VALUE'] = data['CLOSE'] * data['NO OF TRADES']  # Turnover (Close × Volume)

    # Reorder columns to match jugaad_data
    data = data[[
        'DATE SERIES', 'SERIES', 'OPEN', 'HIGH', 'LOW',
        'CLOSE', 'VALUE', 'NO OF TRADES', 'SYMBOL'
    ]]

    return data
    
    
################ DISCORD DMS ####################



def send_discord_message(discord_user_id, signal, strategy_type, stock_symbol, reason):
    """
    Sends a message to a Discord user via the bot's API endpoint.
    
    Args:
        discord_user_id (int or str): The Discord user ID to send the message to
        signal (str): Buy/Sell signal
        strategy_type (str): Type of trading strategy
        stock_symbol (str): Stock ticker symbol
        reason (str): Reason for the trade signal
        
    Returns:
        dict: The JSON response from the API
    """
    
    # Option 1: Clean structured format with emojis
    message = f"""🚀 **Strategy Executed!**

📊 **Symbol:** `{stock_symbol}`
📈 **Signal:** `{signal.upper()}`
⚙️ **Strategy:** `{strategy_type}`
💡 **Reason:** {reason}

Happy trading! 💰"""


    url = "https://quarksfebot.onrender.com/api/send_message"
    headers = {"Content-Type": "application/json"}
    payload = {
        "discord_user_id": str(discord_user_id),
        "message": message
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def get_discord_id_by_user_id(user_id: int) -> str | None:
    """
    Returns the discord_id associated with a given user_id.
    Returns None if no matching record is found.
    """
    conn = sqlite3.connect('trading_system.db')  # Replace with your DB path
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT discord_id FROM discord_users 
            WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        return result[0] if result else None
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        conn.close()
        
        
def get_user_id_by_discord_id(discord_id: str) -> int | None:
    """
    Returns the user_id associated with a given discord_id.
    Returns None if no matching record is found.
    """
    conn = sqlite3.connect('trading_system.db')  # Replace with your DB path
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT user_id FROM discord_users 
            WHERE discord_id = ?
        ''', (discord_id,))
        
        result = cursor.fetchone()
        return result[0] if result else None
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        conn.close()


#######################################
import pandas as pd
import requests
from datetime import datetime

from flask import jsonify


def get_historical_price(symbol, date_str):
    """Fetch historical stock price using yfinance with fallback to nearest date."""
    try:
        # Parse and validate date
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        if target_date > datetime.now().date():
            return None

        # Convert symbol for NSE (e.g., RELIANCE → RELIANCE.NS)
        if '.' not in symbol:
            symbol_yf = symbol.upper() + ".NS"
        else:
            symbol_yf = symbol.upper()

        # Fetch data 7 days to allow fallback
        start_date = target_date - timedelta(days=7)
        end_date = target_date + timedelta(days=7)

        # Download historical data
        df = yf.download(symbol_yf, start=start_date, end=end_date, auto_adjust=False)

        if df is None or df.empty:
            return None

        # Process DataFrame
        df.reset_index(inplace=True)
        df['Date'] = pd.to_datetime(df['Date']).dt.date

        # Check exact match
        exact_row = df[df['Date'] == target_date]
        if not exact_row.empty:
            # Fix for FutureWarning
            price = round(float(exact_row['Close'].iloc[0]), 2)
            return price

        # Fallback to nearest date
        df['DATE_DIFF'] = abs(pd.to_datetime(df['Date']) - pd.to_datetime(target_date))
        nearest_row = df.sort_values('DATE_DIFF').iloc[0]
        # Fix for FutureWarning
        price = round(float(nearest_row['Close']), 2)

        return price
    except Exception as e:
        print(f"Error fetching data for {symbol} on {date_str}: {str(e)}")
        return None


########################## FIX THIS #############################

def get_historical_price1(symbol, date_str):
    """Fetch historical closing price for a specific date with robust error handling"""
    try:
        print(f"Attempting to fetch data for {symbol} on {date_str}")

        # Convert input date to date object
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Check if date is in future
        if target_date > datetime.now().date():
            print(f"Date {target_date} is in the future")
            return None

        # Fetch data for a range of dates
        from_date = target_date - timedelta(days=7)
        to_date = target_date + timedelta(days=7)

        print(f"Fetching data for {symbol} from {from_date} to {to_date}")

        # Fetch historical data with timeout
        try:
            df = stock_df(symbol, from_date=from_date, to_date=to_date, series="EQ")
        except Exception as e:
            print(f"Error fetching stock_df for {symbol}: {str(e)}")
            if hasattr(e, 'response'):
                print("Raw response:", e.response.text)
            return None

        if df is None:
            print(f"stock_df returned None for {symbol}")
            return None

        if df.empty:
            print(f"No data found for {symbol} between {from_date} and {to_date}")
            return None

        # Debug: Print raw data
        print(f"Raw data sample:\n{df.head()}")

        # Convert CLOSE to float with error handling
        try:
            df['CLOSE'] = pd.to_numeric(df['CLOSE'], errors='coerce')
            df = df.dropna(subset=['CLOSE'])
        except Exception as e:
            print(f"Error processing CLOSE prices: {str(e)}")
            return None

        # Filter for the exact target date
        target_data = df[df['DATE'] == target_date.strftime("%Y-%m-%d")]

        if target_data is None or target_data.empty:
            print(f"No matching data for {symbol} on {target_date}")
            return None

        # Get the price
        price = float(target_data.iloc[-1]['CLOSE'])
        print(f"Successfully retrieved price for {symbol} on {target_date}: {price}")
        return price

    except Exception as e:
        print(f"Unexpected error fetching price for {symbol} on {date_str}: {str(e)}")
        return None


########################## FIX THIS #############################

class Simulation:
    def __init__(self, name, cash):
        self.name = name
        self.timestamp = datetime.now()
        self.logs = []
        self.images = []  # Store image paths
        self.portfolio = {
            'cash': cash,
            'holdings': {},
            'transactions': [],
            'performance_images': []  # Store backtest result images
        }
        # Add db_id attribute to Simulation class
        self.db_id = None

    def buy_stock(self, symbol, quantity, price=None, live=True):
        """Buy a stock and add it to the portfolio"""
        # Ensure symbol ends with '.NS' for NSE stocks
        if not symbol.endswith('.NS'):
            symbol_with_ns = symbol + '.NS'
        else:
            symbol_with_ns = symbol
        
        if price is None:
            price = get_stock_price(symbol, live=live)
            if price is None:
                print(f"Failed to fetch price for {symbol}. Transaction aborted.")
                self.logs.append(f"Failed to fetch price for {symbol}. Transaction aborted.")
                return

        cost = price * quantity

        if self.portfolio['cash'] >= cost:
            self.portfolio['cash'] -= cost

            if symbol_with_ns in self.portfolio['holdings']:
                # Update average price and quantity
                total_qty = self.portfolio['holdings'][symbol_with_ns]['quantity'] + quantity
                total_invested = self.portfolio['holdings'][symbol_with_ns]['avg_price'] * self.portfolio['holdings'][symbol_with_ns][
                    'quantity'] + cost
                self.portfolio['holdings'][symbol_with_ns]['quantity'] = total_qty
                self.portfolio['holdings'][symbol_with_ns]['avg_price'] = total_invested / total_qty
            else:
                self.portfolio['holdings'][symbol_with_ns] = {'quantity': quantity, 'avg_price': price}

            # Record transaction
            self.portfolio['transactions'].append({
                'type': 'BUY',
                'symbol': symbol_with_ns,  # Use the .NS version in transaction
                'quantity': quantity,
                'price': price,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

            print(f"Bought {quantity} shares of {symbol_with_ns} at {price:.2f}")
            self.logs.append(f"Bought {quantity} shares of {symbol_with_ns} at {price:.2f}")
        else:
            print(f"Insufficient cash to buy {quantity} shares of {symbol}.")
            self.logs.append(f"Insufficient cash to buy {quantity} shares of {symbol}.")

    def sell_stock(self, symbol, quantity, price=None, live=True):
        """Sell a stock and update the portfolio"""
        # Ensure symbol ends with '.NS' for NSE stocks
        if not symbol.endswith('.NS'):
            symbol_with_ns = symbol + '.NS'
        else:
            symbol_with_ns = symbol
        
        if symbol_with_ns not in self.portfolio['holdings']:
            print(f"{symbol_with_ns} not in portfolio.")
            self.logs.append(f"{symbol_with_ns} not in portfolio.")
            return

        if self.portfolio['holdings'][symbol_with_ns]['quantity'] < quantity:
            print(f"Not enough {symbol_with_ns} shares to sell.")
            self.logs.append(f"Not enough {symbol_with_ns} shares to sell.")
            return

        if price is None:
            price = get_stock_price(symbol, live)
            if price is None:
                print(f"Failed to fetch price for {symbol}. Transaction aborted.")
                self.logs.append(f"Failed to fetch price for {symbol}. Transaction aborted.")
                return

        # Calculate profit/loss
        pl = (price - self.portfolio['holdings'][symbol_with_ns]['avg_price']) * quantity
        self.portfolio['cash'] += price * quantity
        self.portfolio['holdings'][symbol_with_ns]['quantity'] -= quantity

        # Record transaction
        self.portfolio['transactions'].append({
            'type': 'SELL',
            'symbol': symbol_with_ns,
            'quantity': quantity,
            'price': price,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'pl': pl
        })

        print(f"Sold {quantity} shares of {symbol_with_ns} at {price:.2f}")
        self.logs.append(f"Sold {quantity} shares of {symbol_with_ns} at {price:.2f}")
        print(f"Profit/Loss: {pl:.2f}")
        self.logs.append(f"Profit/Loss: {pl:.2f}")

        # Remove stock if fully sold
        if self.portfolio['holdings'][symbol_with_ns]['quantity'] == 0:
            del self.portfolio['holdings'][symbol_with_ns]

    def add_historical_transaction(self, symbol, quantity, transaction_type, timestamp, price=None):
        """
        Record a historical transaction with improved price handling

        Parameters:
            symbol: Stock symbol
            quantity: Number of shares
            transaction_type: 'BUY' or 'SELL'
            timestamp: Transaction datetime string (YYYY-MM-DD HH:MM:SS)
            price: Optional price (will use price_history if not provided)
        """
        # Ensure symbol ends with '.NS' for NSE stocks
        if not symbol.endswith('.NS'):
            symbol_with_ns = symbol + '.NS'
        else:
            symbol_with_ns = symbol
        
        try:
            # Parse timestamp and get date
            transaction_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").date()
            date_str = transaction_date.strftime("%Y-%m-%d")

            # Get price (prefer provided price, fall back to price_history or API)
            if price is None:
                if date_str in self.portfolio.get('price_history', {}):
                    price = self.portfolio['price_history'][date_str]
                else:
                    price = get_historical_price(symbol, date_str)
                    if price is None:
                        msg = f"No price data for {symbol} on {date_str}"
                        print(msg)
                        self.logs.append(msg)
                        return

            # Ensure all numeric values are properly typed
            try:
                quantity = int(quantity)
                price = float(price)
                cash = float(self.portfolio['cash'])
            except (ValueError, TypeError) as e:
                msg = f"Invalid numeric value: {str(e)}"
                print(msg)
                self.logs.append(msg)
                return

            transaction_type = transaction_type.upper()

            if transaction_type == 'BUY':
                # Check cash availability
                required_cash = price * quantity
                if cash >= required_cash:
                    self.portfolio['cash'] = cash - required_cash

                    if symbol_with_ns in self.portfolio['holdings']:
                        # Update average price and quantity
                        total_qty = self.portfolio['holdings'][symbol_with_ns]['quantity'] + quantity
                        total_invested = (self.portfolio['holdings'][symbol_with_ns]['avg_price'] *
                                          self.portfolio['holdings'][symbol_with_ns]['quantity'] + required_cash)
                        self.portfolio['holdings'][symbol_with_ns]['quantity'] = total_qty
                        self.portfolio['holdings'][symbol_with_ns]['avg_price'] = total_invested / total_qty
                    else:
                        self.portfolio['holdings'][symbol_with_ns] = {
                            'quantity': quantity,
                            'avg_price': price
                        }

                    # Record transaction
                    self.portfolio['transactions'].append({
                        'type': 'BUY',
                        'symbol': symbol_with_ns,
                        'quantity': quantity,
                        'price': price,
                        'timestamp': timestamp,
                        'date': date_str  # Added for easier filtering
                    })

                    msg = f"Bought {quantity} shares of {symbol_with_ns} at {price:.2f} on {date_str}"
                    print(msg)
                    self.logs.append(msg)
                else:
                    msg = f"Insufficient cash for BUY: Need {required_cash:.2f}, have {cash:.2f}"
                    print(msg)
                    self.logs.append(msg)

            elif transaction_type == 'SELL':
                if symbol_with_ns in self.portfolio['holdings']:
                    if self.portfolio['holdings'][symbol_with_ns]['quantity'] >= quantity:
                        # Calculate profit/loss
                        pl = (price - self.portfolio['holdings'][symbol_with_ns]['avg_price']) * quantity
                        self.portfolio['cash'] += price * quantity
                        self.portfolio['holdings'][symbol_with_ns]['quantity'] -= quantity

                        # Record transaction
                        self.portfolio['transactions'].append({
                            'type': 'SELL',
                            'symbol': symbol_with_ns,
                            'quantity': quantity,
                            'price': price,
                            'timestamp': timestamp,
                            'pl': pl,
                            'date': date_str  # Added for easier filtering
                        })

                        msg = (f"Sold {quantity} shares of {symbol_with_ns} at {price:.2f} on {date_str} "
                               f"(P/L: {pl:.2f})")
                        print(msg)
                        self.logs.append(msg)

                        # Remove stock if fully sold
                        if self.portfolio['holdings'][symbol_with_ns]['quantity'] == 0:
                            del self.portfolio['holdings'][symbol_with_ns]
                    else:
                        msg = f"Not enough {symbol_with_ns} shares to sell (have {self.portfolio['holdings'][symbol_with_ns]['quantity']}, need {quantity})"
                        print(msg)
                        self.logs.append(msg)
                else:
                    msg = f"{symbol_with_ns} not in portfolio to sell"
                    print(msg)
                    self.logs.append(msg)
            else:
                msg = "Invalid transaction type. Use 'BUY' or 'SELL'"
                print(msg)
                self.logs.append(msg)

        except Exception as e:
            msg = f"Error processing transaction: {str(e)}"
            print(msg)
            self.logs.append(msg)
            import traceback
            traceback.print_exc()

    def view_portfolio(self):
        """Display portfolio with current valuations"""
        if not self.portfolio['holdings']:
            print("Portfolio is empty.")
            print("LOGS:", self.logs)
            self.logs.append("Portfolio is empty.")
            return

        total_invested = 0
        total_current = 0
        report = []

        for symbol, data in self.portfolio['holdings'].items():
            current_price = get_stock_price(symbol, live=True)
            if current_price is None:
                print(f"Failed to fetch current price for {symbol}.")
                continue

            invested = data['avg_price'] * data['quantity']
            current_value = current_price * data['quantity']
            pl = current_value - invested

            report.append({
                'Symbol': symbol,
                'Quantity': data['quantity'],
                'Avg Price': data['avg_price'],
                'Current Price': current_price,
                'Invested': invested,
                'Current Value': current_value,
                'P/L': pl
            })

            total_invested += invested
            total_current += current_value

        df = pd.DataFrame(report)

        print("\nPortfolio Summary:")
        self.logs.append("\nPortfolio Summary:")
        print(df.to_string(index=False))
        self.logs.append(df.to_string(index=False))

        print(f"\nTotal Invested: {total_invested:.2f}")
        self.logs.append(f"\nTotal Invested: {total_invested:.2f}")
        print(f"Current Value: {total_current:.2f}")
        self.logs.append(f"Current Value: {total_current:.2f}")
        print(f"Net Profit/Loss: {total_current - total_invested:.2f}")
        self.logs.append(f"Net Profit/Loss: {total_current - total_invested:.2f}")
        print(f"Cash Balance: {self.portfolio['cash']:.2f}")
        self.logs.append(f"Cash Balance: {self.portfolio['cash']:.2f}")

        print("\n\nLOGS:", self.logs)

    def buy_and_hold(self, symbol, initial_investment, start_date):
        """Simple buy and hold strategy from a given start date"""
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

        date_str = start_date.strftime("%Y-%m-%d")
        price = get_historical_price(symbol, date_str)

        if price:
            quantity = int(initial_investment // price)
            if quantity > 0:
                self.add_historical_transaction(symbol, quantity, "BUY", f"{date_str} 09:15:00")
            else:
                print(f"Initial investment {initial_investment} is too small to buy {symbol} at {price}")
                self.logs.append(f"Initial investment {initial_investment} is too small to buy {symbol} at {price}")
        else:
            print(f"No price data for {symbol} on {date_str}")
            self.logs.append(f"No price data for {symbol} on {date_str}")

    def momentum_strategy(self, symbol, current_date, df=None, lookback_days=14, threshold=0.05, **kwargs):
        """
        Revised momentum strategy with exact price synchronization
        """
        try:
            if df is None or len(df) < lookback_days + 1:
                return

            # Get prices - using the actual execution price for current_date
            current_price = float(df.iloc[-1]['Close'])
            past_price = float(df.iloc[-lookback_days - 1]['Close'])

            if past_price <= 0:
                return

            price_change = (current_price - past_price) / past_price

            if price_change > threshold:
                quantity = max(1, int(10000 // current_price))
                self.add_historical_transaction(
                    symbol,
                    quantity,
                    "BUY",
                    f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                    price=current_price  # Explicitly set execution price
                )

            elif price_change < -threshold:
                if symbol in self.portfolio['holdings']:
                    self.add_historical_transaction(
                        symbol,
                        self.portfolio['holdings'][symbol]['quantity'],
                        "SELL",
                        f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                        price=current_price  # Explicitly set execution price
                    )

        except Exception as e:
            print(f"Momentum strategy error: {str(e)}")

    def bollinger_bands_strategy(self, symbol, current_date, df=None, window=20, num_std=2, **kwargs):
        """
        Optimized Bollinger Bands strategy using pre-loaded data
        """
        try:
            if df is None:
                raise ValueError("No DataFrame provided")

            if len(df) < window + 1:
                return

            # Calculate indicators
            df['MA'] = df['Close'].rolling(window=window).mean()
            df['STD'] = df['Close'].rolling(window=window).std()
            df['Upper'] = df['MA'] + (df['STD'] * num_std)
            df['Lower'] = df['MA'] - (df['STD'] * num_std)

            # Get latest values
            current_price = float(df['Close'].iloc[-1])
            upper_band = float(df['Upper'].iloc[-1])
            lower_band = float(df['Lower'].iloc[-1])

            if current_price < lower_band:
                quantity = max(1, int(10000 // current_price))
                self.add_historical_transaction(symbol, quantity, "BUY",
                                                f"{current_date.strftime('%Y-%m-%d')} 09:15:00")

            elif current_price > upper_band:
                if symbol in self.portfolio['holdings']:
                    self.add_historical_transaction(
                        symbol,
                        self.portfolio['holdings'][symbol]['quantity'],
                        "SELL",
                        f"{current_date.strftime('%Y-%m-%d')} 09:15:00"
                    )

        except Exception as e:
            print(f"Bollinger Bands error: {str(e)}")


    def moving_average_crossover(self, symbol, current_date, df=None, short_window=50, long_window=200, **kwargs):
        """
        Restored working version with critical fixes
        """
        try:
            # 1. Validate input data
            if df is None or not isinstance(df, pd.DataFrame) or df.empty:
                return

            # 2. Get clean close prices (the working version)
            close_prices = df['Close'].astype(float).values

            # 3. Manual moving average calculation (working version)
            def calculate_ma(prices, window):
                if len(prices) < window:
                    return None
                cumsum = np.cumsum(np.insert(prices, 0, 0))
                return (cumsum[window:] - cumsum[:-window]) / window

            short_ma = calculate_ma(close_prices, int(short_window))
            long_ma = calculate_ma(close_prices, int(long_window))

            # 4. Validate we have enough data
            if short_ma is None or long_ma is None or len(short_ma) < 2:
                return

            # 5. Get current values with PROPER scalar conversion
            current_price = float(df['Close'].iloc[-1])  # Fixed deprecation warning
            current_short = float(short_ma[-1])
            current_long = float(long_ma[-1])
            prev_short = float(short_ma[-2])
            prev_long = float(long_ma[-2])

            # 6. Trading logic (keep the working version)
            if prev_short <= prev_long and current_short > current_long:
                quantity = max(1, int(10000 // current_price))
                self.add_historical_transaction(
                    symbol,
                    quantity,
                    "BUY",
                    f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                    price=current_price
                )
            elif prev_short >= prev_long and current_short < current_long:
                if symbol in self.portfolio['holdings']:
                    self.add_historical_transaction(
                        symbol,
                        self.portfolio['holdings'][symbol]['quantity'],
                        "SELL",
                        f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                        price=current_price
                    )

        except Exception as e:
            print(f"MA Crossover operation completed: {str(e)}")

    ##################NEW ONES#######################

    def rsi_strategy(self, symbol, current_date, df=None, rsi_window=14, overbought=70, oversold=30, **kwargs):
        """Fixed RSI Strategy with proper array handling"""
        try:
            if df is None or len(df) < rsi_window + 1:
                return

            # Convert to proper 1D arrays
            closes = df['Close'].values.flatten()  # Ensure 1D array
            delta = np.diff(closes)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)

            # Calculate RSI properly
            avg_gain = pd.Series(gain).rolling(rsi_window).mean().values
            avg_loss = pd.Series(loss).rolling(rsi_window).mean().values

            with np.errstate(divide='ignore', invalid='ignore'):
                rs = np.divide(avg_gain, avg_loss)
                rs[avg_loss == 0] = 1  # Handle division by zero
                rsi = 100 - (100 / (1 + rs))

            current_rsi = float(rsi[-1])
            prev_rsi = float(rsi[-2])
            current_price = float(closes[-1])

            if prev_rsi > oversold and current_rsi <= oversold:
                quantity = max(1, int(10000 // current_price))
                self.add_historical_transaction(
                    symbol, quantity, "BUY",
                    f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                    price=current_price
                )
            elif prev_rsi < overbought and current_rsi >= overbought:
                if symbol in self.portfolio['holdings']:
                    self.add_historical_transaction(
                        symbol, self.portfolio['holdings'][symbol]['quantity'], "SELL",
                        f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                        price=current_price
                    )

        except Exception as e:
            print(f"RSI strategy error: {str(e)}")

    def macd_strategy(self, symbol, current_date, df=None, fast=12, slow=26, signal=9, **kwargs):
        """Fixed MACD Strategy with proper array handling"""
        try:
            if df is None or len(df) < slow + signal:
                return

            # Convert to proper 1D arrays
            closes = df['Close'].values.flatten()

            # Calculate MACD components
            exp1 = pd.Series(closes).ewm(span=fast, adjust=False).mean().values
            exp2 = pd.Series(closes).ewm(span=slow, adjust=False).mean().values
            macd = exp1 - exp2
            signal_line = pd.Series(macd).ewm(span=signal, adjust=False).mean().values

            current_macd = float(macd[-1])
            current_signal = float(signal_line[-1])
            prev_macd = float(macd[-2])
            prev_signal = float(signal_line[-2])
            current_price = float(closes[-1])

            if prev_macd < prev_signal and current_macd > current_signal:
                quantity = max(1, int(10000 // current_price))
                self.add_historical_transaction(
                    symbol, quantity, "BUY",
                    f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                    price=current_price
                )
            elif prev_macd > prev_signal and current_macd < current_signal:
                if symbol in self.portfolio['holdings']:
                    self.add_historical_transaction(
                        symbol, self.portfolio['holdings'][symbol]['quantity'], "SELL",
                        f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                        price=current_price
                    )

        except Exception as e:
            print(f"MACD strategy error: {str(e)}")

    def mean_reversion_strategy(self, symbol, current_date, df=None, window=20, z_threshold=2, **kwargs):
        """Fixed Mean Reversion Strategy"""
        try:
            if df is None or len(df) < window:
                return

            closes = df['Close'].values.flatten()
            rolling_mean = pd.Series(closes).rolling(window=window).mean().values[-1]
            rolling_std = pd.Series(closes).rolling(window=window).std().values[-1]
            current_price = float(closes[-1])

            z_score = (current_price - rolling_mean) / rolling_std if rolling_std != 0 else 0

            if z_score < -z_threshold:
                quantity = max(1, int(10000 // current_price))
                self.add_historical_transaction(
                    symbol, quantity, "BUY",
                    f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                    price=current_price
                )
            elif z_score > z_threshold:
                if symbol in self.portfolio['holdings']:
                    self.add_historical_transaction(
                        symbol, self.portfolio['holdings'][symbol]['quantity'], "SELL",
                        f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                        price=current_price
                    )

        except Exception as e:
            print(f"Mean reversion strategy error: {str(e)}")

    def breakout_strategy(self, symbol, current_date, df=None, window=20, multiplier=1.01, **kwargs):
        """Completely fixed Breakout strategy"""
        try:
            if df is None or len(df) < window + 1:
                return

            # Convert to proper numpy arrays and ensure 1D
            highs = np.array(df['High'], dtype=np.float64).flatten()
            lows = np.array(df['Low'], dtype=np.float64).flatten()
            closes = np.array(df['Close'], dtype=np.float64).flatten()

            # Calculate recent high/low (excluding current day)
            recent_high = np.max(highs[-window - 1:-1])  # Look back window days, excluding current
            recent_low = np.min(lows[-window - 1:-1])  # Look back window days, excluding current

            # Calculate breakout levels with tighter multiplier
            resistance = recent_high * multiplier
            support = recent_low / multiplier

            current_price = float(closes[-1])
            prev_price = float(closes[-2])

            # Trading logic with confirmation
            if prev_price <= resistance and current_price > resistance:
                quantity = max(1, int(10000 // current_price))
                self.add_historical_transaction(
                    symbol, quantity, "BUY",
                    f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                    price=current_price
                )
            elif prev_price >= support and current_price < support:
                if symbol in self.portfolio['holdings']:
                    self.add_historical_transaction(
                        symbol, self.portfolio['holdings'][symbol]['quantity'], "SELL",
                        f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                        price=current_price
                    )

        except Exception as e:
            print(f"Breakout strategy error on {current_date}: {str(e)}")


    def volume_spike_strategy(self, symbol, current_date, df=None, window=20, multiplier=2.5, **kwargs):
        """Fixed Volume Spike Strategy"""
        try:
            if df is None or len(df) < window:
                return

            volumes = df['Volume'].values.flatten()
            closes = df['Close'].values.flatten()

            avg_volume = float(pd.Series(volumes).rolling(window=window).mean().values[-1])
            current_volume = float(volumes[-1])
            volume_ratio = current_volume / avg_volume if avg_volume != 0 else 0

            current_price = float(closes[-1])
            price_change = (current_price - float(closes[-2])) / float(closes[-2]) if closes[-2] != 0 else 0

            if volume_ratio > multiplier and price_change > 0:
                quantity = max(1, int(10000 // current_price))
                self.add_historical_transaction(
                    symbol, quantity, "BUY",
                    f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                    price=current_price
                )

        except Exception as e:
            print(f"Volume spike strategy error: {str(e)}")

    def keltner_channels_strategy(self, symbol, current_date, df=None, window=20, atr_multiplier=2, **kwargs):
        """Fixed Keltner Channels Strategy"""
        try:
            if df is None or len(df) < window:
                return

            highs = df['High'].values.flatten()
            lows = df['Low'].values.flatten()
            closes = df['Close'].values.flatten()

            # Calculate ATR properly
            tr = np.maximum(
                highs[1:] - lows[1:],
                np.abs(highs[1:] - closes[:-1]),
                np.abs(lows[1:] - closes[:-1])
            )
            atr = float(pd.Series(tr).rolling(window=window).mean().values[-1])

            middle = float(pd.Series(closes).ewm(span=window).mean().values[-1])
            upper = middle + atr_multiplier * atr
            lower = middle - atr_multiplier * atr

            current_price = float(closes[-1])

            if current_price < lower:
                quantity = max(1, int(10000 // current_price))
                self.add_historical_transaction(
                    symbol, quantity, "BUY",
                    f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                    price=current_price
                )
            elif current_price > upper:
                if symbol in self.portfolio['holdings']:
                    self.add_historical_transaction(
                        symbol, self.portfolio['holdings'][symbol]['quantity'], "SELL",
                        f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                        price=current_price
                    )

        except Exception as e:
            print(f"Keltner Channels strategy error: {str(e)}")

    def stochastic_oscillator_strategy(self, symbol, current_date, df=None, k_window=14, d_window=3,
                                       overbought=80, oversold=20, **kwargs):
        """Completely fixed Stochastic Oscillator strategy"""
        try:
            if df is None or len(df) < k_window + d_window + 1:
                return

            # Convert to proper numpy arrays and ensure 1D
            highs = np.array(df['High'], dtype=np.float64).flatten()
            lows = np.array(df['Low'], dtype=np.float64).flatten()
            closes = np.array(df['Close'], dtype=np.float64).flatten()

            # Calculate %K properly
            lowest_lows = pd.Series(lows).rolling(window=k_window).min().values
            highest_highs = pd.Series(highs).rolling(window=k_window).max().values

            # Current values with proper bounds checking
            current_close = closes[-1]
            current_low = lowest_lows[-1] if not np.isnan(lowest_lows[-1]) else lows[-k_window:].min()
            current_high = highest_highs[-1] if not np.isnan(highest_highs[-1]) else highs[-k_window:].max()

            # Calculate %K with proper division handling
            k_current = 100 * ((current_close - current_low) /
                               (current_high - current_low)) if (current_high - current_low) != 0 else 50

            # Calculate %D as SMA of %K
            k_values = []
            for i in range(len(closes) - k_window + 1):
                window_low = lows[i:i + k_window].min()
                window_high = highs[i:i + k_window].max()
                close = closes[i + k_window - 1]
                k = 100 * ((close - window_low) / (window_high - window_low)) if (window_high - window_low) != 0 else 50
                k_values.append(k)

            d_current = pd.Series(k_values).rolling(window=d_window).mean().values[-1]

            # Previous values
            prev_close = closes[-2]
            prev_low = lowest_lows[-2] if len(lowest_lows) > 1 and not np.isnan(lowest_lows[-2]) else lows[
                                                                                                      -k_window - 1:-1].min()
            prev_high = highest_highs[-2] if len(highest_highs) > 1 and not np.isnan(highest_highs[-2]) else highs[
                                                                                                             -k_window - 1:-1].max()
            k_prev = 100 * ((prev_close - prev_low) / (prev_high - prev_low)) if (prev_high - prev_low) != 0 else 50

            # Current price
            current_price = float(current_close)

            # Trading conditions with buffer zones
            buy_condition = (k_prev < oversold + 5 and k_current > oversold + 5)
            sell_condition = (k_prev > overbought - 5 and k_current < overbought - 5)

            if buy_condition:
                quantity = max(1, int(10000 // current_price))
                self.add_historical_transaction(
                    symbol, quantity, "BUY",
                    f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                    price=current_price
                )
            elif sell_condition and symbol in self.portfolio['holdings']:
                self.add_historical_transaction(
                    symbol, self.portfolio['holdings'][symbol]['quantity'], "SELL",
                    f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                    price=current_price
                )

        except Exception as e:
            print(f"Stochastic strategy error on {current_date}: {str(e)}")

    def parabolic_sar_strategy(self, symbol, current_date, df=None, acceleration=0.02, maximum=0.2, **kwargs):
        """
        Parabolic SAR (Stop and Reverse) strategy
        """
        try:
            if df is None or len(df) < 2:
                return

            # Calculate Parabolic SAR
            high = df['High'].values
            low = df['Low'].values
            close = df['Close'].values

            sar = np.zeros(len(close))
            ep = np.zeros(len(close))
            af = acceleration

            # Initial values
            sar[0] = high[0] if close[0] < high[0] else low[0]
            ep[0] = high[0] if close[0] > high[0] else low[0]
            trend = 1 if close[0] > high[0] else -1

            for i in range(1, len(close)):
                sar[i] = sar[i - 1] + af * (ep[i - 1] - sar[i - 1])

                if trend == 1:
                    if low[i] < sar[i]:
                        trend = -1
                        sar[i] = max(high[i - 1], high[i])
                        ep[i] = low[i]
                        af = acceleration
                    else:
                        ep[i] = max(ep[i - 1], high[i])
                        if high[i] > ep[i - 1]:
                            af = min(af + acceleration, maximum)
                else:
                    if high[i] > sar[i]:
                        trend = 1
                        sar[i] = min(low[i - 1], low[i])
                        ep[i] = high[i]
                        af = acceleration
                    else:
                        ep[i] = min(ep[i - 1], low[i])
                        if low[i] < ep[i - 1]:
                            af = min(af + acceleration, maximum)

            current_sar = sar[-1]
            current_price = float(close[-1])
            prev_sar = sar[-2]
            prev_price = float(close[-2])

            # Trading logic
            if prev_price > prev_sar and current_price < current_sar:  # Downtrend reversal
                if symbol in self.portfolio['holdings']:
                    self.add_historical_transaction(
                        symbol,
                        self.portfolio['holdings'][symbol]['quantity'],
                        "SELL",
                        f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                        price=current_price
                    )
            elif prev_price < prev_sar and current_price > current_sar:  # Uptrend reversal
                quantity = max(1, int(10000 // current_price))
                self.add_historical_transaction(
                    symbol,
                    quantity,
                    "BUY",
                    f"{current_date.strftime('%Y-%m-%d')} 09:15:00",
                    price=current_price
                )

        except Exception as e:
            print(f"Parabolic SAR strategy error: {str(e)}")

    #################################################

    def run_backtest(self, strategy, symbol, start_date, end_date, **strategy_params):
        """
        Revised backtest with strict price synchronization
        Ensures signals and executions use the same price data
        """
        try:
            # Convert dates if needed
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

            # Add .NS suffix for Indian stocks if needed
            symbol_yf = f"{symbol}.NS" if '.' not in symbol else symbol

            # Calculate required buffer for the strategy
            buffer_days = max(
                strategy_params.get('lookback_days', 0) * 3,
                strategy_params.get('window', 0) * 3,
                strategy_params.get('long_window', 0) * 3,
                100  # Minimum buffer
            )

            # Download all data once with buffer period
            data_start = start_date - timedelta(days=buffer_days)
            data_end = end_date + timedelta(days=1)  # Include end date

            print(f"Downloading data for {symbol} from {data_start} to {data_end}")
            df = yf.download(symbol_yf, start=data_start, end=data_end, progress=False, auto_adjust=False)

            if df is None or df.empty:
                raise ValueError(f"No data found for {symbol}")

            # Process DataFrame - we'll keep it as datetime index
            df = df.reset_index()
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df = df.sort_values('Date')

            # Initialize portfolio tracking
            self.portfolio['price_history'] = {}
            try:
                initial_cash = float(self.portfolio['cash'])
            except (KeyError, ValueError, TypeError):
                initial_cash = 100000.0  # Default value
                self.portfolio['cash'] = initial_cash

            # Create a list of business days in our test period
            all_dates = pd.date_range(start=start_date, end=end_date, freq='B').date
            date_index = {date: i for i, date in enumerate(df['Date'])}

            # Main backtest loop
            for current_date in all_dates:
                try:
                    # Find the position of this date in our DataFrame
                    idx = date_index[current_date]

                    # Get the slice of data up to and including current date
                    df_slice = df.iloc[:idx + 1].copy()

                    # Get the actual price for this day
                    current_price = float(df_slice.iloc[-1]['Close'])
                    self.portfolio['price_history'][current_date.strftime('%Y-%m-%d')] = current_price

                    # Run strategy with the data slice
                    if strategy == self.momentum_strategy:
                        strategy(symbol, current_date, df=df_slice, **strategy_params)
                    elif strategy == self.bollinger_bands_strategy:
                        strategy(symbol, current_date, df=df_slice, **strategy_params)
                    elif strategy == self.moving_average_crossover:
                        strategy(symbol, current_date, df=df_slice, **strategy_params)
                        # ADD NEW STRATEGIES BELOW
                    elif strategy == self.rsi_strategy:
                        strategy(symbol, current_date, df=df_slice, **strategy_params)
                    elif strategy == self.macd_strategy:
                        strategy(symbol, current_date, df=df_slice, **strategy_params)
                    elif strategy == self.mean_reversion_strategy:
                        strategy(symbol, current_date, df=df_slice, **strategy_params)
                    elif strategy == self.breakout_strategy:
                        strategy(symbol, current_date, df=df_slice, **strategy_params)
                    elif strategy == self.volume_spike_strategy:
                        strategy(symbol, current_date, df=df_slice, **strategy_params)
                    elif strategy == self.keltner_channels_strategy:
                        strategy(symbol, current_date, df=df_slice, **strategy_params)
                    elif strategy == self.stochastic_oscillator_strategy:
                        strategy(symbol, current_date, df=df_slice, **strategy_params)
                    elif strategy == self.parabolic_sar_strategy:
                        strategy(symbol, current_date, df=df_slice, **strategy_params)
                    else:
                        print(f"Warning: Unknown strategy {strategy.__name__}")

                except KeyError:
                    # Date not found in our data (shouldn't happen with business days)
                    continue

            # Calculate final portfolio value using the exact end date price
            final_value = float(self.portfolio['cash'])
            for s, h in self.portfolio['holdings'].items():
                if s == symbol:  # Only calculate for our test symbol
                    try:
                        last_price = float(df[df['Date'] == end_date]['Close'].values[0])
                        final_value += last_price * h['quantity']
                    except (IndexError, KeyError):
                        # If end date isn't a trading day, use last available price
                        last_price = float(df.iloc[-1]['Close'])
                        final_value += last_price * h['quantity']

            # Calculate return
            self.portfolio['return'] = (final_value - initial_cash) / initial_cash if initial_cash > 0 else 0

            # Generate results
            results = {
                'return': self.portfolio['return'],
                'transactions': self.portfolio['transactions'],
                'price_history': self.portfolio['price_history'],
                'initial_cash': initial_cash,
                'final_value': final_value
            }

            # Generate plot - modified to show actual trade prices
            image_path = self.plot_backtest_results(symbol)
            if image_path:
                results['graph_path'] = image_path

            return results

        except Exception as e:
            print(f"Backtest error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def plot_backtest_results(self, symbol):
        """Plot price history with buy/sell signals"""
        if not self.portfolio.get('price_history'):
            print("DEBUG - No price history in portfolio:", self.portfolio.keys())
            return None

        try:
            # Convert string dates to datetime objects for plotting
            dates = [datetime.strptime(d, "%Y-%m-%d").date()
                     for d in sorted(self.portfolio['price_history'].keys())]
            prices = [self.portfolio['price_history'][d]
                      for d in sorted(self.portfolio['price_history'].keys())]

            plt.figure(figsize=(14, 7))
            plt.plot(dates, prices, label='Price', color='royalblue', linewidth=2)

            # Plot transactions if they exist
            if 'transactions' in self.portfolio:
                for t in self.portfolio['transactions']:
                    try:
                        trans_date = datetime.strptime(t['timestamp'], "%Y-%m-%d %H:%M:%S").date()
                        trans_type = t['type']
                        price = t['price']

                        if trans_type == 'BUY':
                            plt.scatter(trans_date, price, color='limegreen', marker='^',
                                        s=150, edgecolors='black', label='Buy')
                        elif trans_type == 'SELL':
                            plt.scatter(trans_date, price, color='crimson', marker='v',
                                        s=150, edgecolors='black', label='Sell')
                    except Exception as e:
                        print(f"Error plotting transaction: {e}")
                        continue

            plt.title(f"{symbol} Trading Performance")
            plt.xlabel('Date')
            plt.ylabel('Price ()')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.legend()

            # Format dates
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gcf().autofmt_xdate()

            # Save image
            os.makedirs('static/graphs', exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = f"static/graphs/{self.name}_{symbol}_{timestamp}.png"
            plt.savefig(image_path)
            plt.close()

            return image_path

        except Exception as e:
            print(f"Error in plot_backtest_results: {e}")
            return None


################################## PART 1 : STRATEGIES; UNCOMMENT THE BELOW PART TO TRY STRATEGIES. SWITCH THE STRATEGY TO ALL AVAILABLE ONES TO CHECK THEM ########################################3


"""

simobject = Simulation("main1",20000)

results = simobject.run_backtest(
    strategy=simobject.bollinger_bands_strategy,
    symbol="TCS",
    start_date="2023-01-01",
    end_date="2023-12-31",
)

print(f"Strategy Return: {results['return']*100:.2f}%")

for transaction in results['transactions']:
    print(transaction)


"""


############################################

class Watchlist:
    def __init__(self, name):
        self.name = name
        self.watchlist = {}  # This will store symbol data
        self.db_id = None  # To track database ID for updates
        self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def add_to_watchlist(self, symbol, notes="added!"):
        """Add a stock to the watchlist with validation."""
        if symbol in self.watchlist:
            print(f"{symbol} is already in the watchlist.")
            return False

        price = get_stock_price(symbol)
        if price is not None:
            self.watchlist[symbol] = {
                'added_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_price': price,
                'notes': notes
            }
            print(f"Added {symbol} to watchlist at {price:.2f}.")
            return True
        else:
            print(f"Failed to add {symbol} to watchlist.")
            return False

    def remove_from_watchlist(self, symbol):
        """Remove a stock from the watchlist."""
        if symbol in self.watchlist:
            del self.watchlist[symbol]
            print(f"Removed {symbol} from watchlist.")
            return True
        else:
            print(f"{symbol} is not in the watchlist.")
            return False


    def view_watchlist(self):
        """Display the current watchlist with updated prices."""
        if not self.watchlist:
            print("Watchlist is empty.")
            return []
    
        report = []
        for symbol, data in self.watchlist.items():
            current_price = get_stock_price(symbol)
            initial_price = data.get('last_price', current_price)
            price_change = current_price - initial_price if current_price else None
    
            report.append({
                'Symbol': symbol,
                'Added On': data.get('added_on', 'N/A'),
                'Initial Price': initial_price,
                'Current Price': current_price if current_price else "N/A",
                'Change': f"{price_change:.2f}" if price_change is not None else "N/A",
                'Notes': data.get('notes', '')
            })
    
        df = pd.DataFrame(report)
        print("\nWatchlist Summary:")
        print(df.to_string(index=False))
        return report


"""
wtl1 = Watchlist("watchlist1")
wtl1.add_to_watchlist("RELIANCE")
wtl1.add_to_watchlist("TCS")
wtl1.view_watchlist()
wtl1.remove_from_watchlist("RELIANCE")
wtl1.view_watchlist()
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from statsmodels.tsa.arima.model import ARIMA

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from statsmodels.tsa.arima.model import ARIMA

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from statsmodels.tsa.arima.model import ARIMA


def generate_advice_sheet(symbol):
    """
    Generate an advice sheet for a given stock and return as JSON-serializable dict.
    """
    # Add .NS suffix if needed
    if isinstance(symbol, str):
        if '.' not in symbol and not (symbol.endswith('.NS') or symbol.endswith('.BO')):
            symbol += '.NS'

    advice_data = {
        'symbol': symbol,
        'current_price': None,
        'one_year_return': None,
        'recommendations': {},
        'predictions': {},
        'final_recommendation': None,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    try:
        # Get current price
        current_data = yf.download(symbol, period="1d", progress=False)
        if len(current_data) == 0:
            return {'error': f"No current data available for {symbol}"}
        advice_data['current_price'] = float(current_data['Close'].iloc[-1])

        # Get 1-year data
        df = yf.download(symbol, period="1y", progress=False)
        if len(df) == 0:
            return {'error': f"No historical data found for {symbol}"}

        # Calculate returns
        initial_price = float(df['Close'].iloc[0])
        final_price = float(df['Close'].iloc[-1])
        one_year_return = ((final_price - initial_price) / initial_price) * 100
        advice_data['one_year_return'] = one_year_return

        # Generate recommendations
        advice_data['recommendations'] = {}

        # Process each recommendation individually to isolate issues
        try:
            advice_data['recommendations']['buy_and_hold'] = evaluate_buy_and_hold(df)
        except Exception as e:
            advice_data['recommendations']['buy_and_hold'] = {'error': str(e), 'signal': 'hold'}

        try:
            advice_data['recommendations']['momentum'] = evaluate_momentum(df)
        except Exception as e:
            advice_data['recommendations']['momentum'] = {'error': str(e), 'signal': 'hold'}

        try:
            advice_data['recommendations']['bollinger'] = evaluate_bollinger_bands(df)
        except Exception as e:
            advice_data['recommendations']['bollinger'] = {'error': str(e), 'signal': 'hold'}

        try:
            advice_data['recommendations']['ma_crossover'] = evaluate_moving_average_crossover(df)
        except Exception as e:
            advice_data['recommendations']['ma_crossover'] = {'error': str(e), 'signal': 'hold'}

        # Add new strategy evaluations
        try:
            advice_data['recommendations']['rsi'] = evaluate_rsi(df)
        except Exception as e:
            advice_data['recommendations']['rsi'] = {'error': str(e), 'signal': 'hold'}

        try:
            advice_data['recommendations']['macd'] = evaluate_macd(df)
        except Exception as e:
            advice_data['recommendations']['macd'] = {'error': str(e), 'signal': 'hold'}

        try:
            advice_data['recommendations']['mean_reversion'] = evaluate_mean_reversion(df)
        except Exception as e:
            advice_data['recommendations']['mean_reversion'] = {'error': str(e), 'signal': 'hold'}

        try:
            advice_data['recommendations']['breakout'] = evaluate_breakout(df)
        except Exception as e:
            advice_data['recommendations']['breakout'] = {'error': str(e), 'signal': 'hold'}

        try:
            advice_data['recommendations']['volume_spike'] = evaluate_volume_spike(df)
        except Exception as e:
            advice_data['recommendations']['volume_spike'] = {'error': str(e), 'signal': 'hold'}

        try:
            advice_data['recommendations']['keltner'] = evaluate_keltner_channels(df)
        except Exception as e:
            advice_data['recommendations']['keltner'] = {'error': str(e), 'signal': 'hold'}

        try:
            advice_data['recommendations']['stochastic'] = evaluate_stochastic_oscillator(df)
        except Exception as e:
            advice_data['recommendations']['stochastic'] = {'error': str(e), 'signal': 'hold'}

        try:
            advice_data['recommendations']['parabolic_sar'] = evaluate_parabolic_sar(df)
        except Exception as e:
            advice_data['recommendations']['parabolic_sar'] = {'error': str(e), 'signal': 'hold'}

        # Generate predictions
        try:
            advice_data['predictions']['arima_7day'] = predict_future_price(symbol)
        except Exception as e:
            advice_data['predictions']['arima_7day'] = None

        # Final recommendation
        try:
            advice_data['final_recommendation'] = generate_final_recommendation(list(advice_data['recommendations'].values()))

        except Exception as e:
            advice_data['final_recommendation'] = {
                'recommendation': 'HOLD',
                'reason': f'Error generating recommendation: {str(e)}',
                'signal': 'hold'
            }

        return advice_data

    except Exception as e:
        import traceback
        print(traceback.format_exc())  # Print the full stack trace
        return {'error': f"Error processing {symbol}: {str(e)}"}



def evaluate_buy_and_hold(df):
    try:
        # Print debug info
        print(f"Buy and hold - DataFrame shape: {df.shape}")

        # Make sure we're working with scalar values
        if len(df) > 0:
            initial = float(df['Close'].iloc[0])
            final = float(df['Close'].iloc[-1])
            ret = ((final - initial) / initial) * 100

            print(f"Buy and hold - Initial: {initial}, Final: {final}, Return: {ret}%")

            # Direct scalar comparison
            recommendation = 'Buy' if ret > 10.0 else 'Hold'
            signal = 'buy' if ret > 10.0 else 'hold'

            return {
                'recommendation': recommendation,
                'reason': f"1-Year Return: {ret:.2f}%",
                'return': ret,
                'signal': signal
            }
        else:
            print("Insufficient data for buy and hold")
            return {
                'recommendation': 'Hold',
                'reason': "Insufficient data",
                'return': 0.0,
                'signal': 'hold'
            }
    except Exception as e:
        import traceback
        print(f"Buy and hold error: {traceback.format_exc()}")
        return {
            'recommendation': 'Hold',
            'reason': f"Error: {str(e)}",
            'return': 0.0,
            'signal': 'hold'
        }


def evaluate_momentum(df, lookback=14, threshold=0.05):
    try:
        # Print detailed debug information
        print(f"DataFrame shape: {df.shape}")
        print(f"DataFrame columns: {df.columns}")
        print(f"Lookback: {lookback}, Threshold: {threshold}")

        # Make sure we're working with a copy
        df_copy = df.copy()

        # Calculate the percentage change column-by-column to avoid Series comparison issues
        close_values = df_copy['Close'].values  # Convert to numpy array
        pct_changes = np.zeros(len(close_values))

        # Manual calculation to avoid pandas Series comparison
        if len(close_values) > lookback:
            for i in range(lookback, len(close_values)):
                if close_values[i - lookback] != 0:  # Avoid division by zero
                    pct_changes[i] = (close_values[i] - close_values[i - lookback]) / close_values[i - lookback]

        # Get the most recent value (if available)
        if len(pct_changes) > 0:
            current_ret = float(pct_changes[-1])
            current_pct = current_ret * 100

            print(f"Current return: {current_ret}, Current percent: {current_pct}")

            # Use direct float comparisons
            if current_ret > float(threshold):
                print("Returning BUY recommendation")
                return {
                    'recommendation': 'Buy',
                    'reason': f"Positive momentum ({current_pct:.2f}%)",
                    'momentum': current_pct,
                    'signal': 'buy'
                }
            elif current_ret < float(-threshold):
                print("Returning SELL recommendation")
                return {
                    'recommendation': 'Sell',
                    'reason': f"Negative momentum ({current_pct:.2f}%)",
                    'momentum': current_pct,
                    'signal': 'sell'
                }
            else:
                print("Returning HOLD recommendation (within threshold)")
                return {
                    'recommendation': 'Hold',
                    'reason': f"Neutral momentum ({current_pct:.2f}%)",
                    'momentum': current_pct,
                    'signal': 'hold'
                }
        else:
            print("Insufficient data for momentum")
            return {
                'recommendation': 'Hold',
                'reason': "Insufficient data for momentum calculation",
                'momentum': 0.0,
                'signal': 'hold'
            }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Momentum error: {error_trace}")
        return {
            'recommendation': 'Hold',
            'reason': f"Error: {str(e)}",
            'momentum': 0.0,
            'signal': 'hold'
        }


def evaluate_bollinger_bands(df, window=20, num_std=2):
    try:
        # Print debug info
        print(f"Bollinger function - DataFrame shape: {df.shape}")

        # Check if DataFrame has enough data
        if len(df) < window:
            return {
                'recommendation': 'Hold',
                'reason': 'Insufficient data for Bollinger bands calculation',
                'signal': 'hold',
                'bands': None
            }

        # Use pandas rolling function for accurate Bollinger Bands calculation
        df_bb = df.copy()
        
        # Calculate rolling mean and standard deviation
        rolling_mean = df_bb['Close'].rolling(window=window).mean()
        rolling_std = df_bb['Close'].rolling(window=window).std()
        
        # Calculate bands
        upper_band = rolling_mean + (rolling_std * num_std)
        lower_band = rolling_mean - (rolling_std * num_std)
        
        # Get the last values
        current_price = float(df_bb['Close'].iloc[-1])
        current_ma = float(rolling_mean.iloc[-1])
        current_upper = float(upper_band.iloc[-1])
        current_lower = float(lower_band.iloc[-1])

        print(f"Bollinger - Price: {current_price}, MA: {current_ma}, Upper: {current_upper}, Lower: {current_lower}")

        # Check if any of the calculated values are NaN
        if any(np.isnan(val) for val in [current_ma, current_upper, current_lower]):
            return {
                'recommendation': 'Hold',
                'reason': 'Invalid Bollinger bands calculation (NaN values)',
                'signal': 'hold',
                'bands': None
            }

        # Determine the signal based on price position
        if current_price < current_lower:
            signal = 'buy'
            reason = 'Below lower band'
        elif current_price > current_upper:
            signal = 'sell'
            reason = 'Above upper band'
        else:
            signal = 'hold'
            reason = 'Within bands'

        return {
            'recommendation': signal.capitalize(),
            'reason': reason,
            'signal': signal,
            'bands': {
                'upper': current_upper,
                'middle': current_ma,
                'lower': current_lower
            },
            'distance_from_ma': ((current_price - current_ma) / current_ma) * 100
        }
    except Exception as e:
        import traceback
        print(f"Bollinger bands error: {traceback.format_exc()}")
        return {
            'recommendation': 'Hold',
            'reason': f"Error: {str(e)}",
            'signal': 'hold',
            'bands': None
        }


def evaluate_moving_average_crossover(df, short=50, long=200):
    # Create a copy to avoid modifying the original dataframe
    df_ma = df.copy()
    df_ma['SMA50'] = df_ma['Close'].rolling(short).mean()
    df_ma['SMA200'] = df_ma['Close'].rolling(long).mean()

    # Check if we have enough data
    if len(df_ma) <= long:
        return {
            'recommendation': 'Hold',
            'reason': f'Insufficient data for MA crossover (need {long} days)',
            'signal': 'hold',
            'moving_averages': None
        }

    # Get the last values
    try:
        sma50 = float(df_ma['SMA50'].iloc[-1])
        sma200 = float(df_ma['SMA200'].iloc[-1])

        if len(df_ma) > 1:
            sma50_prev = float(df_ma['SMA50'].iloc[-2])
            sma200_prev = float(df_ma['SMA200'].iloc[-2])
        else:
            sma50_prev = sma50
            sma200_prev = sma200

    except (IndexError, ValueError):
        return {
            'recommendation': 'Hold',
            'reason': 'Error calculating moving averages',
            'signal': 'hold',
            'moving_averages': None
        }

    if pd.isna(sma50) or pd.isna(sma200) or pd.isna(sma50_prev) or pd.isna(sma200_prev):
        return {
            'recommendation': 'Hold',
            'reason': 'Insufficient data for MA crossover',
            'signal': 'hold',
            'moving_averages': None
        }

    # Use individual boolean comparisons instead of chained comparisons
    prev_condition = sma50_prev < sma200_prev
    current_condition = sma50 > sma200

    if prev_condition and current_condition:
        signal = 'buy'
        reason = 'Golden cross (50 > 200)'
    elif (sma50_prev > sma200_prev) and (sma50 < sma200):
        signal = 'sell'
        reason = 'Death cross (50 < 200)'
    else:
        signal = 'hold'
        reason = 'No crossover'

    return {
        'recommendation': signal.capitalize(),
        'reason': reason,
        'signal': signal,
        'moving_averages': {
            'sma50': sma50,
            'sma200': sma200
        }
    }


###### NEW ONES #################

# New evaluation functions for each strategy
def evaluate_rsi(df, window=14, overbought=70, oversold=30):
    try:
        # Calculate RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window).mean()
        avg_loss = loss.rolling(window).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        current_rsi = float(rsi.iloc[-1])

        if current_rsi < oversold:
            signal = 'buy'
            reason = f'RSI {current_rsi:.1f} (Oversold)'
        elif current_rsi > overbought:
            signal = 'sell'
            reason = f'RSI {current_rsi:.1f} (Overbought)'
        else:
            signal = 'hold'
            reason = f'RSI {current_rsi:.1f} (Neutral)'

        return {
            'recommendation': signal.capitalize(),
            'reason': reason,
            'signal': signal,
            'rsi_value': current_rsi
        }
    except Exception as e:
        return {
            'recommendation': 'Hold',
            'reason': f'Error calculating RSI: {str(e)}',
            'signal': 'hold',
            'rsi_value': None
        }


def evaluate_macd(df, fast=12, slow=26, signal=9):
    try:
        # Check if DataFrame has enough data
        if len(df) < max(fast, slow, signal):
            return {
                'recommendation': 'Hold',
                'reason': 'Error: Insufficient data for MACD calculation',
                'signal': 'hold',
                'macd': None,
                'signal_line': None
            }
        
        # Calculate MACD
        exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()

        current_macd = float(macd.iloc[-1])
        current_signal = float(signal_line.iloc[-1])

        if current_macd > current_signal:
            signal = 'buy'
            reason = 'MACD above Signal'
        else:
            signal = 'sell'
            reason = 'MACD below Signal'

        return {
            'recommendation': signal.capitalize(),
            'reason': reason,
            'signal': signal,
            'macd': current_macd,
            'signal_line': current_signal
        }
    except Exception as e:
        return {
            'recommendation': 'Hold',
            'reason': f'Error calculating MACD: {str(e)}',
            'signal': 'hold',
            'macd': None,
            'signal_line': None
        }


def evaluate_mean_reversion(df, window=20, z_threshold=2):
    try:
        # Calculate mean reversion
        rolling_mean = df['Close'].rolling(window).mean()
        rolling_std = df['Close'].rolling(window).std()
        current_price = float(df['Close'].iloc[-1])
        current_mean = float(rolling_mean.iloc[-1])
        current_std = float(rolling_std.iloc[-1])

        if current_std == 0:
            return {
                'recommendation': 'Hold',
                'reason': 'No price deviation',
                'signal': 'hold',
                'z_score': 0
            }

        z_score = (current_price - current_mean) / current_std

        if z_score < -z_threshold:
            signal = 'buy'
            reason = f'Z-Score {z_score:.2f} (Undervalued)'
        elif z_score > z_threshold:
            signal = 'sell'
            reason = f'Z-Score {z_score:.2f} (Overvalued)'
        else:
            signal = 'hold'
            reason = f'Z-Score {z_score:.2f} (Normal)'

        return {
            'recommendation': signal.capitalize(),
            'reason': reason,
            'signal': signal,
            'z_score': z_score
        }
    except Exception as e:
        return {
            'recommendation': 'Hold',
            'reason': f'Error calculating mean reversion: {str(e)}',
            'signal': 'hold',
            'z_score': None
        }


def evaluate_breakout(df, window=20, multiplier=1.01):
    """Fixed breakout strategy evaluation"""
    try:
        if len(df) < window + 1:
            return {
                'recommendation': 'Hold',
                'reason': f'Insufficient data (need {window+1} days)',
                'signal': 'hold',
                'resistance': None,
                'support': None
            }

        # Convert to numpy arrays to avoid pandas Series comparison issues
        highs = df['High'].values[-window-1:-1]  # Exclude current day
        lows = df['Low'].values[-window-1:-1]    # Exclude current day
        current_close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])

        recent_high = float(np.max(highs))
        recent_low = float(np.min(lows))
        resistance = recent_high * multiplier
        support = recent_low / multiplier

        # Trading logic with confirmation
        if prev_close <= resistance and current_close > resistance:
            signal = 'buy'
            reason = f'Breakout above resistance {resistance:.2f}'
        elif prev_close >= support and current_close < support:
            signal = 'sell'
            reason = f'Breakdown below support {support:.2f}'
        else:
            signal = 'hold'
            reason = 'Price within range'

        return {
            'recommendation': signal.capitalize(),
            'reason': reason,
            'signal': signal,
            'resistance': resistance,
            'support': support
        }
    except Exception as e:
        return {
            'recommendation': 'Hold',
            'reason': f'Error calculating breakout: {str(e)}',
            'signal': 'hold',
            'resistance': None,
            'support': None
        }



def evaluate_volume_spike(df, window=20, multiplier=2.5):
    """Fixed volume spike evaluation"""
    try:
        if len(df) < window + 1:
            return {
                'recommendation': 'Hold',
                'reason': f'Insufficient data (need {window+1} days)',
                'signal': 'hold',
                'volume_ratio': None
            }

        # Convert to numpy arrays to avoid pandas Series comparison issues
        volumes = df['Volume'].values[-window-1:]  # Include current day
        closes = df['Close'].values[-window-1:]    # Include current day

        avg_volume = float(np.mean(volumes[:-1]))  # Average of previous days
        current_volume = float(volumes[-1])
        volume_ratio = current_volume / avg_volume if avg_volume != 0 else 0

        current_price = float(closes[-1])
        prev_price = float(closes[-2]) if len(closes) > 1 else current_price
        price_change = (current_price - prev_price) / prev_price if prev_price != 0 else 0

        if volume_ratio > multiplier and price_change > 0:
            signal = 'buy'
            reason = f'Volume spike ({volume_ratio:.1f}x) with price increase'
        else:
            signal = 'hold'
            reason = 'No significant volume spike'

        return {
            'recommendation': signal.capitalize(),
            'reason': reason,
            'signal': signal,
            'volume_ratio': volume_ratio
        }
    except Exception as e:
        return {
            'recommendation': 'Hold',
            'reason': f'Error calculating volume spike: {str(e)}',
            'signal': 'hold',
            'volume_ratio': None
        }


def evaluate_keltner_channels(df, window=20, atr_multiplier=2):
    try:
        # Calculate Keltner Channels
        atr = (df['High'] - df['Low']).rolling(window).mean()  # Simplified ATR
        middle = df['Close'].ewm(span=window).mean()
        upper = middle + atr_multiplier * atr
        lower = middle - atr_multiplier * atr
        current_price = float(df['Close'].iloc[-1])

        if current_price < float(lower.iloc[-1]):
            signal = 'buy'
            reason = 'Price below lower Keltner band'
        elif current_price > float(upper.iloc[-1]):
            signal = 'sell'
            reason = 'Price above upper Keltner band'
        else:
            signal = 'hold'
            reason = 'Price within Keltner channels'

        return {
            'recommendation': signal.capitalize(),
            'reason': reason,
            'signal': signal,
            'upper_band': float(upper.iloc[-1]),
            'lower_band': float(lower.iloc[-1])
        }
    except Exception as e:
        return {
            'recommendation': 'Hold',
            'reason': f'Error calculating Keltner Channels: {str(e)}',
            'signal': 'hold',
            'upper_band': None,
            'lower_band': None
        }


def evaluate_stochastic_oscillator(df, k_window=14, d_window=3, overbought=80, oversold=20):
    try:
        # Calculate Stochastic Oscillator
        lowest_low = df['Low'].rolling(k_window).min()
        highest_high = df['High'].rolling(k_window).max()
        k_percent = 100 * ((df['Close'] - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(d_window).mean()

        current_k = float(k_percent.iloc[-1])
        current_d = float(d_percent.iloc[-1])

        if current_k < oversold and current_d < oversold:
            signal = 'buy'
            reason = f'Stochastic {current_k:.1f}/{current_d:.1f} (Oversold)'
        elif current_k > overbought and current_d > overbought:
            signal = 'sell'
            reason = f'Stochastic {current_k:.1f}/{current_d:.1f} (Overbought)'
        else:
            signal = 'hold'
            reason = f'Stochastic {current_k:.1f}/{current_d:.1f} (Neutral)'

        return {
            'recommendation': signal.capitalize(),
            'reason': reason,
            'signal': signal,
            'k_percent': current_k,
            'd_percent': current_d
        }
    except Exception as e:
        return {
            'recommendation': 'Hold',
            'reason': f'Error calculating Stochastic: {str(e)}',
            'signal': 'hold',
            'k_percent': None,
            'd_percent': None
        }


def evaluate_parabolic_sar(df, acceleration=0.02, maximum=0.2):
    try:
        # Simplified Parabolic SAR calculation
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values

        sar = np.zeros(len(close))
        trend = 1  # Start with uptrend
        af = acceleration
        ep = high[0] if trend == 1 else low[0]

        for i in range(1, len(close)):
            sar[i] = sar[i - 1] + af * (ep - sar[i - 1])

            if trend == 1:
                if low[i] < sar[i]:
                    trend = -1
                    sar[i] = max(high[i - 1], high[i])
                    ep = low[i]
                    af = acceleration
                else:
                    if high[i] > ep:
                        ep = high[i]
                        af = min(af + acceleration, maximum)
            else:
                if high[i] > sar[i]:
                    trend = 1
                    sar[i] = min(low[i - 1], low[i])
                    ep = high[i]
                    af = acceleration
                else:
                    if low[i] < ep:
                        ep = low[i]
                        af = min(af + acceleration, maximum)

        current_sar = sar[-1]
        current_price = close[-1]

        if current_price > current_sar:
            signal = 'buy'
            reason = 'Price above SAR (Uptrend)'
        else:
            signal = 'sell'
            reason = 'Price below SAR (Downtrend)'

        return {
            'recommendation': signal.capitalize(),
            'reason': reason,
            'signal': signal,
            'sar_value': float(current_sar)
        }
    except Exception as e:
        return {
            'recommendation': 'Hold',
            'reason': f'Error calculating SAR: {str(e)}',
            'signal': 'hold',
            'sar_value': None
        }


#################################


def generate_final_recommendation(recommendations):
    signals = {'buy': 0, 'sell': 0, 'hold': 0}
    details = []

    for rec in recommendations:
        if isinstance(rec, dict) and 'signal' in rec:
            signal = rec['signal']
            signals[signal] = signals.get(signal, 0) + 1
            details.append({
                'strategy': rec.get('recommendation', 'Unknown'),
                'signal': signal,
                'reason': rec.get('reason', '')
            })

    buy_count = signals.get('buy', 0)
    sell_count = signals.get('sell', 0)
    hold_count = signals.get('hold', 0)

    # Use explicit comparisons instead of chained comparisons
    if buy_count > sell_count:
        if buy_count > hold_count:
            final = 'buy'
            reason = f"Majority buy ({buy_count}/{len(recommendations)})"
        else:
            final = 'hold'
            reason = f"Hold wins ({hold_count}/{len(recommendations)})"
    elif sell_count > buy_count:
        if sell_count > hold_count:
            final = 'sell'
            reason = f"Majority sell ({sell_count}/{len(recommendations)})"
        else:
            final = 'hold'
            reason = f"Hold wins ({hold_count}/{len(recommendations)})"
    else:
        final = 'hold'
        reason = f"No consensus (B:{buy_count}, S:{sell_count}, H:{hold_count})"

    return {
        'recommendation': final.upper(),
        'reason': reason,
        'signal': final,
        'signal_counts': signals,
        'strategy_details': details
    }


def predict_future_price(symbol, days=7):
    try:
        df = yf.download(symbol, period="1y", progress=False)
        if len(df) < 30:
            return None

        # Get the closing prices as a numpy array to avoid pandas issues
        close_prices = df['Close'].values

        # Fit ARIMA model
        model = ARIMA(close_prices, order=(5, 1, 0))
        model_fit = model.fit()

        # Generate forecast
        forecast = model_fit.forecast(steps=days)

        # Return the last forecasted value
        if isinstance(forecast, np.ndarray):
            return float(forecast[-1])
        else:
            return float(forecast.iloc[-1])
    except Exception as e:
        print(f"Prediction error: {str(e)}")
        return None

import sqlite3
import json
from datetime import datetime


def save_graph_image(fig, simulation_id, graph_name):
    """Save matplotlib figure and return path"""
    os.makedirs('static/graphs', exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{simulation_id}_{graph_name}_{timestamp}.png"
    path = f"static/graphs/{filename}"
    fig.savefig(path)
    plt.close(fig)
    return path


def serialize_simulation(simulation):
    """Convert simulation to JSON-serializable dict"""
    # Convert price_history dates to strings if they exist
    portfolio_data = simulation.portfolio.copy()
    if 'price_history' in portfolio_data:
        portfolio_data['price_history'] = {
            k.strftime("%Y-%m-%d") if isinstance(k, date) else k: v
            for k, v in portfolio_data['price_history'].items()
        }

    data = {
        'name': simulation.name,
        'timestamp': simulation.timestamp,
        'portfolio': portfolio_data,
        'logs': simulation.logs,
        'images': simulation.images,
        'performance_images': simulation.portfolio.get('performance_images', [])
    }
    return json.loads(json.dumps(data, cls=PortfolioEncoder))


# --- Database Setup ---
def create_database():
    conn = sqlite3.connect('trading_system.db')
    c = conn.cursor()

    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Portfolios Table
    c.execute('''CREATE TABLE IF NOT EXISTS portfolios (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 name TEXT NOT NULL,
                 data TEXT NOT NULL,  
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY(user_id) REFERENCES users(id))''')

    # Watchlists Table
    c.execute('''CREATE TABLE IF NOT EXISTS watchlists (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 name TEXT NOT NULL,
                 symbols TEXT NOT NULL,  
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY(user_id) REFERENCES users(id))''')

    # NEW TABLE for simulation images
    c.execute('''CREATE TABLE IF NOT EXISTS simulation_images (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 simulation_id INTEGER NOT NULL,
                 image_path TEXT NOT NULL,
                 image_type TEXT NOT NULL,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY(simulation_id) REFERENCES portfolios(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                portfolio_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                strategy_type TEXT NOT NULL CHECK(strategy_type IN (
                    'MOMENTUM', 
                    'BOLLINGER', 
                    'MACROSS', 
                    'RSI', 
                    'MACD', 
                    'MEANREVERSION', 
                    'BREAKOUT', 
                    'VOLUMESPIKE', 
                    'KELTNER', 
                    'STOCHASTIC', 
                    'PARABOLICSAR', 
                    'BUYHOLD', 
                    'QUARKS'
                )),
                parameters TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_executed TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(portfolio_id) REFERENCES portfolios(id)
            )''')

    # Execution log table
    c.execute('''CREATE TABLE IF NOT EXISTS strategy_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id INTEGER NOT NULL,
                    execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    action TEXT NOT NULL,
                    quantity INTEGER,
                    price REAL,
                    FOREIGN KEY(strategy_id) REFERENCES strategies(id))''')

    conn.commit()
    conn.close()


create_database()


########## STRATEGIES ###################

class StrategyExecutor:
    def __init__(self):
        self.conn = sqlite3.connect('trading_system.db')
        self.conn.row_factory = sqlite3.Row
        self.email_records = {}

    def execute_all_strategies(self):
        """Execute all active strategies for all users"""
        try:
            strategies = self._get_active_strategies()
            if not strategies:
                print("No active strategies to execute")
                return {}  # Explicit empty dict

            result = {}
            for strategy in strategies:
                self._execute_strategy(strategy)
                # Debug print
                print(f"After strategy {strategy['id']}, emails: {self.email_records}")

            result = self.email_records.copy()  # Take a copy
            return result  # Return BEFORE closing connection

        except Exception as e:
            print(f"\n[MAIN ERROR] in strategy execution: {str(e)}")
            return {}
        finally:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()

    def _get_active_strategies(self):
        """Fetch all active strategies with portfolio info"""
        c = self.get_connection().cursor()
        c.execute('''SELECT s.id, s.user_id, s.portfolio_id, s.symbol,
                     s.strategy_type, s.parameters, p.name as portfolio_name
                   FROM strategies s
                   JOIN portfolios p ON s.portfolio_id = p.id
                   WHERE s.is_active=1''')
        return c.fetchall()

    def _execute_strategy(self, strategy):
        """Execute a single strategy"""
        try:
            print(f"\nExecuting strategy {strategy['id']} for user {strategy['user_id']}")
            print(f"Strategy Type: {strategy['strategy_type']}")
            print(f"Symbol: {strategy['symbol']}")
            print(f"Parameters: {strategy['parameters']}")

            # Load portfolio
            portfolio = load_portfolio(strategy['user_id'], strategy['portfolio_id'])
            if not portfolio:
                print(f"[ERROR] Portfolio {strategy['portfolio_id']} not found")
                return

            # Get current market data
            df = self._get_market_data(strategy['symbol'])
            if df is None or df.empty:
                print(f"[ERROR] Could not fetch data for {strategy['symbol']}")
                return

            # Generate trading signal
            params = json.loads(strategy['parameters'])
            print("\nGenerating signal...")
            signal = self._generate_signal(
                df=df,
                strategy_type=strategy['strategy_type'],
                params=params
            )
            print(f"Signal generated: {signal}")

            # Mail here
            email2 = return_email(strategy['user_id'])
            if email2:
                if email2 not in self.email_records:
                    self.email_records[email2] = []
                print(email2, "email broooooooooooooo")
                
                
            #discord here
            discord_id_to_send=get_discord_id_by_user_id(strategy['user_id'])
                
                
            # Get current price as float
            current_price = float(df['CLOSE'].iloc[-1].item())
            print(f"Current Price: {current_price:.2f}")

            # Execute trade
            if signal['action'] == 'BUY':
                print("\nExecuting BUY order...")
                self._execute_buy(portfolio, strategy, signal, current_price)
                if email2:
                    self.email_records[email2].append("BUY")
                    self.email_records[email2].append(signal['reason'])
                    if '@' in email2:
                        send_strategy_signal(email2, signal, strategy['strategy_type'], strategy['symbol'])
                        
                if discord_id_to_send:
                    send_discord_message(discord_id_to_send, "BUY", strategy['strategy_type'], strategy['symbol'], signal['reason'] )   
                    
            elif signal['action'] == 'SELL':
                print("\nExecuting SELL order...")
                self._execute_sell(portfolio, strategy, signal, current_price)
                
                if discord_id_to_send:
                    send_discord_message(discord_id_to_send, "SELL", strategy['strategy_type'], strategy['symbol'] , signal['reason'])   
                
                if email2:
                    self.email_records[email2].append("SELL")
                    self.email_records[email2].append(signal['reason'])
                    if '@' in email2:
                        send_strategy_signal(email2, signal, strategy['strategy_type'], strategy['symbol'] )
            else:
                if email2:
                    self.email_records[email2].append("HOLD")
                    self.email_records[email2].append(signal['reason'])
                print("\nNo action taken (HOLD)")

            # Save portfolio and update strategy
            save_portfolio(strategy['user_id'], portfolio)
            self._update_strategy_execution(strategy['id'])

        except Exception as e:
            print(f"\n[STRATEGY ERROR] executing strategy {strategy['id']}: {str(e)}", flush=True)
            self._log_execution(
                strategy['id'],
                'ERROR',
                None,
                None)

    def _get_market_data(self, symbol):
        """Fetch required market data for analysis using yfinance"""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=365)

            # Format dates for yfinance (YYYY-MM-DD)
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')

            # Handle Indian stocks by appending .NS for NSE or .BO for BSE if needed
            ticker_symbol = symbol
            if '.' not in symbol:
                # Try with NSE suffix first
                nse_symbol = f"{symbol}.NS"
                try:
                    ticker = yf.Ticker(nse_symbol)
                    # Quick check if the ticker exists by getting info
                    _ = ticker.info
                    ticker_symbol = nse_symbol
                except:
                    # If NSE fails, try BSE
                    try:
                        bse_symbol = f"{symbol}.BO"
                        ticker = yf.Ticker(bse_symbol)
                        _ = ticker.info
                        ticker_symbol = bse_symbol
                    except:
                        # If both fail, use original symbol
                        ticker_symbol = symbol

            print(f"Downloading data for ticker: {ticker_symbol}")
            # Download data using yfinance
            df = yf.download(ticker_symbol, start=start_str, end=end_str)

            if df is None or df.empty:
                raise Exception(f"No data found for {ticker_symbol}")

            # Rename columns to match previous format (optional)
            df.rename(columns={
                'Close': 'CLOSE',
                'Open': 'OPEN',
                'High': 'HIGH',
                'Low': 'LOW',
                'Volume': 'VOLUME',
                'Adj Close': 'ADJ_CLOSE'
            }, inplace=True)

            print(f"Data downloaded successfully ({len(df)} rows)")
            return df
        except Exception as e:
            print(f"[DATA ERROR] fetching data for {symbol}: {str(e)}")
            return None

    def _generate_signal(self, df, strategy_type, params):
        """Generate trading signal based on strategy"""
        try:
            print(f"\nGenerating {strategy_type} signal with params: {params}")

            if strategy_type == 'MOMENTUM':
                return self._momentum_signal(df, params)
            elif strategy_type == 'BOLLINGER':
                return self._bollinger_signal(df, params)
            elif strategy_type == 'MACROSS':
                return self._macross_signal(df, params)
            elif strategy_type == 'RSI':
                return self._rsi(df, params)
            elif strategy_type == 'MACD':
                return self._macd(df, params)
            elif strategy_type == 'MEANREVERSION':
                return self._mean_reversion(df, params)
            elif strategy_type == 'BREAKOUT':
                return self._breakout(df, params)
            elif strategy_type == 'VOLUMESPIKE':
                return self._volume_spike(df, params)
            elif strategy_type == 'KELTNER':
                return self._keltner_channels(df, params)
            elif strategy_type == 'STOCHASTIC':
                return self._stochastic_oscillator(df, params)
            elif strategy_type == 'PARABOLICSAR':
                return self._parabolic_sar(df, params)

            print(f"[WARNING] Unknown strategy type: {strategy_type}")
            return {'action': 'HOLD', 'reason': 'Unknown strategy'}

        except Exception as e:
            print(f"[SIGNAL ERROR] in {strategy_type} strategy: {str(e)}")
            return {'action': 'HOLD', 'reason': f'Error: {str(e)}'}

    def _momentum_signal(self, df, params):
        """Generate momentum signal"""
        lookback = int(params.get('lookback_days', 14))
        threshold = float(params.get('threshold', 0.05))

        df['returns'] = df['CLOSE'].pct_change(lookback)
        current_return = float(df['returns'].iloc[-1].item())
        print(f"Momentum: {current_return:.2%} (Threshold: {threshold:.2%})")

        if current_return > threshold:
            return {'action': 'BUY', 'reason': f'Momentum {current_return:.2%} > {threshold:.2%}'}
        elif current_return < -threshold:
            return {'action': 'SELL', 'reason': f'Momentum {current_return:.2%} < -{threshold:.2%}'}
        return {'action': 'HOLD', 'reason': 'No significant momentum'}

    def _bollinger_signal(self, df, params):
        """Generate Bollinger Bands signal"""
        window = int(params.get('window', 20))
        num_std = float(params.get('num_std', 2))

        df['MA'] = df['CLOSE'].rolling(window=window).mean()
        df['STD'] = df['CLOSE'].rolling(window=window).std()
        df['Upper'] = df['MA'] + (df['STD'] * num_std)
        df['Lower'] = df['MA'] - (df['STD'] * num_std)

        current_price = float(df['CLOSE'].iloc[-1].item())
        lower_band = float(df['Lower'].iloc[-1].item())
        upper_band = float(df['Upper'].iloc[-1].item())
        ma = float(df['MA'].iloc[-1].item())

        print(f"Price: {current_price:.2f}")
        print(f"Bollinger Bands: Lower={lower_band:.2f}, MA={ma:.2f}, Upper={upper_band:.2f}")

        if current_price < lower_band:
            return {'action': 'BUY', 'reason': f'Price {current_price:.2f} < Lower Band {lower_band:.2f}'}
        elif current_price > upper_band:
            return {'action': 'SELL', 'reason': f'Price {current_price:.2f} > Upper Band {upper_band:.2f}'}
        return {'action': 'HOLD', 'reason': f'Price {current_price:.2f} within bands'}

    def _macross_signal(self, df, params):
        """Generate Moving Average Crossover signal"""
        short_window = int(params.get('short_window', 50))
        long_window = int(params.get('long_window', 200))

        df['SMA50'] = df['CLOSE'].rolling(window=short_window).mean()
        df['SMA200'] = df['CLOSE'].rolling(window=long_window).mean()

        if len(df) < 2:
            print("[WARNING] Insufficient data for crossover detection")
            return {'action': 'HOLD', 'reason': 'Insufficient data for crossover detection'}

        # Get explicit values for comparison
        sma50_prev = float(df['SMA50'].iloc[-2].item())
        sma200_prev = float(df['SMA200'].iloc[-2].item())
        sma50_current = float(df['SMA50'].iloc[-1].item())
        sma200_current = float(df['SMA200'].iloc[-1].item())

        print(f"SMA50: Previous={sma50_prev:.2f}, Current={sma50_current:.2f}")
        print(f"SMA200: Previous={sma200_prev:.2f}, Current={sma200_current:.2f}")

        if sma50_prev < sma200_prev and sma50_current > sma200_current:
            return {'action': 'BUY', 'reason': 'Golden Cross (50MA crossed above 200MA)'}
        elif sma50_prev > sma200_prev and sma50_current < sma200_current:
            return {'action': 'SELL', 'reason': 'Death Cross (50MA crossed below 200MA)'}
        return {'action': 'HOLD', 'reason': 'No crossover detected'}

    ###################NEW ONES##################

    def _rsi(self,df, params):

        window = int(params.get('window', 14))
        overbought = int(params.get('overbought', 70))
        oversold = int(params.get('oversold', 30))

        try:
            # Calculate RSI
            delta = df['CLOSE'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            avg_gain = gain.rolling(window).mean()
            avg_loss = loss.rolling(window).mean()

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            current_rsi = float(rsi.iloc[-1])

            if current_rsi < oversold:
                signal = 'buy'
                reason = f'RSI {current_rsi:.1f} (Oversold)'
            elif current_rsi > overbought:
                signal = 'sell'
                reason = f'RSI {current_rsi:.1f} (Overbought)'
            else:
                signal = 'hold'
                reason = f'RSI {current_rsi:.1f} (Neutral)'

            return {
                'action': signal.upper(),
                'reason': reason
            }
        except Exception as e:
            return {
                'action': 'HOLD',
                'reason': f'Error calculating RSI: {str(e)}',

            }

    def _macd(self, df, params):
        fast = int(params.get('fast', 12))
        slow = int(params.get('slow', 26))
        signal = int(params.get('signal', 9))
        try:
            # Calculate MACD
            exp1 = df['CLOSE'].ewm(span=fast, adjust=False).mean()
            exp2 = df['CLOSE'].ewm(span=slow, adjust=False).mean()
            macd = exp1 - exp2
            signal_line = macd.ewm(span=signal, adjust=False).mean()

            current_macd = float(macd.iloc[-1])
            current_signal = float(signal_line.iloc[-1])

            if current_macd > current_signal:
                signal = 'buy'
                reason = 'MACD above Signal'
            else:
                signal = 'sell'
                reason = 'MACD below Signal'

            return {
                'action': signal.upper(),
                'reason': reason
            }
        except Exception as e:
            return {
                'action': 'HOLD',
                'reason': f'Error calculating MACD: {str(e)}'
            }

    def _mean_reversion(self, df, params):
        window = int(params.get('window', 20))
        z_threshold = int(params.get('z_threshold', 2))
        try:
            # Calculate mean reversion
            rolling_mean = df['CLOSE'].rolling(window).mean()
            rolling_std = df['CLOSE'].rolling(window).std()
            current_price = float(df['CLOSE'].iloc[-1])
            current_mean = float(rolling_mean.iloc[-1])
            current_std = float(rolling_std.iloc[-1])

            if current_std == 0:
                return {
                    'action': 'HOLD',
                    'reason': 'No price deviation'
                }

            z_score = (current_price - current_mean) / current_std

            if z_score < -z_threshold:
                signal = 'buy'
                reason = f'Z-Score {z_score:.2f} (Undervalued)'
            elif z_score > z_threshold:
                signal = 'sell'
                reason = f'Z-Score {z_score:.2f} (Overvalued)'
            else:
                signal = 'hold'
                reason = f'Z-Score {z_score:.2f} (Normal)'

            return {
                'action': signal.upper(),
                'reason': reason,

            }
        except Exception as e:
            return {
                'action': 'HOLD',
                'reason': f'Error calculating mean reversion: {str(e)}',

            }

    def _breakout(self, df,params):
        """Fixed breakout strategy evaluation"""

        window = int(params.get('window', 20))
        multiplier = int(params.get('multiplier', 1.01))

        try:
            if len(df) < window + 1:
                return {
                    'recommendation': 'Hold',
                    'reason': f'Insufficient data (need {window + 1} days)',
                    'signal': 'hold',
                    'resistance': None,
                    'support': None
                }

            # Convert to numpy arrays to avoid pandas Series comparison issues
            highs = df['HIGH'].values[-window - 1:-1]  # Exclude current day
            lows = df['LOW'].values[-window - 1:-1]  # Exclude current day
            current_close = float(df['CLOSE'].iloc[-1])
            prev_close = float(df['CLOSE'].iloc[-2])

            recent_high = float(np.max(highs))
            recent_low = float(np.min(lows))
            resistance = recent_high * multiplier
            support = recent_low / multiplier

            # Trading logic with confirmation
            if prev_close <= resistance and current_close > resistance:
                signal = 'buy'
                reason = f'Breakout above resistance {resistance:.2f}'
            elif prev_close >= support and current_close < support:
                signal = 'sell'
                reason = f'Breakdown below support {support:.2f}'
            else:
                signal = 'hold'
                reason = 'Price within range'

            return {
                'action': signal.upper(),
                'reason': reason
            }
        except Exception as e:
            return {
                'action': 'HOLD',
                'reason': f'Error calculating breakout: {str(e)}'

            }

    def _volume_spike(self,df,params):
        """Fixed volume spike evaluation"""

        window = int(params.get('window', 20))
        multiplier = int(params.get('multiplier', 2.5))

        try:
            if len(df) < window + 1:
                return {
                    'recommendation': 'Hold',
                    'reason': f'Insufficient data (need {window + 1} days)',
                    'signal': 'hold',
                    'volume_ratio': None
                }

            # Convert to numpy arrays to avoid pandas Series comparison issues
            volumes = df['VOLUME'].values[-window - 1:]  # Include current day
            closes = df['CLOSE'].values[-window - 1:]  # Include current day

            avg_volume = float(np.mean(volumes[:-1]))  # Average of previous days
            current_volume = float(volumes[-1])
            volume_ratio = current_volume / avg_volume if avg_volume != 0 else 0

            current_price = float(closes[-1])
            prev_price = float(closes[-2]) if len(closes) > 1 else current_price
            price_change = (current_price - prev_price) / prev_price if prev_price != 0 else 0

            if volume_ratio > multiplier and price_change > 0:
                signal = 'buy'
                reason = f'Volume spike ({volume_ratio:.1f}x) with price increase'
            else:
                signal = 'hold'
                reason = 'No significant volume spike'

            return {
                'action': signal.upper(),
                'reason': reason
            }
        except Exception as e:
            return {
                'action': 'HOLD',
                'reason': f'Error calculating volume spike: {str(e)}'
            }

    def _keltner_channels(self, df, params):
        window = int(params.get('window', 20))
        atr_multiplier = int(params.get('atr_multiplier', 2))
        try:
            # Calculate Keltner Channels
            atr = (df['HIGH'] - df['LOW']).rolling(window).mean()  # Simplified ATR
            middle = df['CLOSE'].ewm(span=window).mean()
            upper = middle + atr_multiplier * atr
            lower = middle - atr_multiplier * atr
            current_price = float(df['CLOSE'].iloc[-1])

            if current_price < float(lower.iloc[-1]):
                signal = 'buy'
                reason = 'Price below lower Keltner band'
            elif current_price > float(upper.iloc[-1]):
                signal = 'sell'
                reason = 'Price above upper Keltner band'
            else:
                signal = 'hold'
                reason = 'Price within Keltner channels'

            return {
                'action': signal.upper(),
                'reason': reason
            }
        except Exception as e:
            return {
                'action': 'HOLD',
                'reason': f'Error calculating Keltner Channels: {str(e)}'

            }

    def _stochastic_oscillator(self, df, params):
        k_window = int(params.get('k_window', 14))
        d_window = int(params.get('d_window', 3))
        overbought = int(params.get('overbought', 80))
        oversold = int(params.get('oversold', 20))
        try:
            # Calculate Stochastic Oscillator
            lowest_low = df['LOW'].rolling(k_window).min()
            highest_high = df['HIGH'].rolling(k_window).max()
            k_percent = 100 * ((df['CLOSE'] - lowest_low) / (highest_high - lowest_low))
            d_percent = k_percent.rolling(d_window).mean()

            current_k = float(k_percent.iloc[-1])
            current_d = float(d_percent.iloc[-1])

            if current_k < oversold and current_d < oversold:
                signal = 'buy'
                reason = f'Stochastic {current_k:.1f}/{current_d:.1f} (Oversold)'
            elif current_k > overbought and current_d > overbought:
                signal = 'sell'
                reason = f'Stochastic {current_k:.1f}/{current_d:.1f} (Overbought)'
            else:
                signal = 'hold'
                reason = f'Stochastic {current_k:.1f}/{current_d:.1f} (Neutral)'

            return {
                'action': signal.upper(),
                'reason': reason
            }
        except Exception as e:
            return {
                'action': 'HOLD',
                'reason': f'Error calculating Stochastic: {str(e)}'
            }

    def _parabolic_sar(self ,df , params):
        acceleration = int(params.get('acceleration', 0.02))
        maximum = int(params.get('maximum', 0.2))
        try:
            # Simplified Parabolic SAR calculation
            high = df['HIGH'].values
            low = df['LOW'].values
            close = df['CLOSE'].values

            sar = np.zeros(len(close))
            trend = 1  # Start with uptrend
            af = acceleration
            ep = high[0] if trend == 1 else low[0]

            for i in range(1, len(close)):
                sar[i] = sar[i - 1] + af * (ep - sar[i - 1])

                if trend == 1:
                    if low[i] < sar[i]:
                        trend = -1
                        sar[i] = max(high[i - 1], high[i])
                        ep = low[i]
                        af = acceleration
                    else:
                        if high[i] > ep:
                            ep = high[i]
                            af = min(af + acceleration, maximum)
                else:
                    if high[i] > sar[i]:
                        trend = 1
                        sar[i] = min(low[i - 1], low[i])
                        ep = high[i]
                        af = acceleration
                    else:
                        if low[i] < ep:
                            ep = low[i]
                            af = min(af + acceleration, maximum)

            current_sar = sar[-1]
            current_price = close[-1]

            if current_price > current_sar:
                signal = 'buy'
                reason = 'Price above SAR (Uptrend)'
            else:
                signal = 'sell'
                reason = 'Price below SAR (Downtrend)'

            return {
                'action': signal.upper(),
                'reason': reason

            }
        except Exception as e:
            return {
                'action': 'HOLD',
                'reason': f'Error calculating SAR: {str(e)}'
            }

    #############################################

    def _execute_buy(self, portfolio, strategy, signal, current_price):
        """Execute buy order"""
        try:
            params = json.loads(strategy['parameters'])
            print(f"Buy parameters: {params}")

            # Calculate quantity based on available cash or fixed amount
            if 'quantity' in params:
                quantity = int(params['quantity'])
                print(f"Using fixed quantity: {quantity}")
            else:
                # Default to using 10% of available cash
                cash_available = float(portfolio.portfolio['cash'])
                max_investment = cash_available * 0.1
                quantity = int(max_investment // current_price)
                print(f"Calculated quantity: {quantity} (Cash: {cash_available:.2f}, Price: {current_price:.2f})")

            if quantity <= 0:
                print("[WARNING] Insufficient cash to buy")
                return

            print(f"Executing BUY: {quantity} shares @ {current_price:.2f}")
            portfolio.buy_stock(strategy['symbol'], quantity, price=current_price)
            self._log_execution(
                strategy['id'],
                'BUY',
                quantity,
                current_price)

            print(f"Successfully bought {quantity} shares of {strategy['symbol']} at {current_price:.2f}")

        except Exception as e:
            print(f"[BUY ERROR] executing buy: {str(e)}")
            raise

    def _execute_sell(self, portfolio, strategy, signal, current_price):
        """Execute sell order"""
        try:
            if strategy['symbol'] not in portfolio.portfolio['holdings']:
                print(f"[WARNING] No holdings of {strategy['symbol']} to sell")
                return

            holding = portfolio.portfolio['holdings'][strategy['symbol']]
            quantity = int(holding['quantity'])
            print(f"Selling {quantity} shares of {strategy['symbol']}")

            portfolio.sell_stock(strategy['symbol'], quantity, price=current_price)
            self._log_execution(
                strategy['id'],
                'SELL',
                quantity,
                current_price)

            print(f"Successfully sold {quantity} shares of {strategy['symbol']} at {current_price:.2f}")

        except Exception as e:
            print(f"[SELL ERROR] executing sell: {str(e)}")
            raise

    def _update_strategy_execution(self, strategy_id):
        """Update last execution time"""
        try:
            c = self.get_connection().cursor()
            c.execute('''UPDATE strategies SET last_executed=CURRENT_TIMESTAMP
                      WHERE id=?''', (strategy_id,))
            self.get_connection().commit()
            print("Strategy execution time updated")
        except Exception as e:
            print(f"[UPDATE ERROR] updating strategy execution time: {str(e)}")
            raise

    def _log_execution(self, strategy_id, action, quantity, price):
        """Log execution details"""
        try:
            c = self.get_connection().cursor()
            c.execute('''INSERT INTO strategy_executions
                      (strategy_id, action, quantity, price, execution_time)
                      VALUES (?, ?, ?, ?, datetime('now'))''',
                      (strategy_id, action, quantity, price))
            self.get_connection().commit()
            print("Execution logged successfully")
        except Exception as e:
            print(f"[LOG ERROR] logging execution: {str(e)}")
            raise


#####################################################

# --- User Authentication ---
def register_user(username, password):
    print(f"[LOCAL DB] Attempting to register user: {username}")
    conn = sqlite3.connect('trading_system.db')
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                     (username, password))
        conn.commit()
        print(f"[LOCAL DB] Successfully registered user: {username}")
        return True
    except sqlite3.IntegrityError:
        print(f"[LOCAL DB] Username already exists: {username}")
        return False
    finally:
        conn.close()


def authenticate_user(username, password):
    print(f"[LOCAL DB] Attempting to authenticate user: {username}")
    conn = sqlite3.connect('trading_system.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()
    if user:
        print(f"[LOCAL DB] Authentication successful for user: {username} (ID: {user[0]})")
        return user[0]
    else:
        print(f"[LOCAL DB] Authentication failed for user: {username}")
        return None

def return_email(user_id):
    conn = sqlite3.connect('trading_system.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id=? ", (user_id,))
    email1 = c.fetchone()
    conn.close()
    return email1[0] if email1 else None



def save_portfolio(user_id, portfolio_obj):
    conn = sqlite3.connect('trading_system.db')
    print("here")
    try:
        # Serialize the portfolio
        json_data = json.dumps(serialize_simulation(portfolio_obj), cls=PortfolioEncoder)

        if hasattr(portfolio_obj, 'db_id') and portfolio_obj.db_id is not None:
            # Update existing portfolio
            conn.execute('''UPDATE portfolios SET name=?, data=? WHERE id=? AND user_id=?''',
                         (portfolio_obj.name, json_data, portfolio_obj.db_id, user_id))
        else:
            # Insert new portfolio
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO portfolios (user_id, name, data) VALUES (?, ?, ?)''',
                           (user_id, portfolio_obj.name, json_data))
            portfolio_obj.db_id = cursor.lastrowid

            # Save images if this is a new portfolio
            for img_path in portfolio_obj.images + portfolio_obj.portfolio.get('performance_images', []):
                img_type = 'performance' if img_path in portfolio_obj.portfolio.get('performance_images',
                                                                                    []) else 'graph'
                conn.execute('''INSERT INTO simulation_images (simulation_id, image_path, image_type)
                              VALUES (?, ?, ?)''', (portfolio_obj.db_id, img_path, img_type))

        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving portfolio: {str(e)}")
        return False
    finally:
        conn.close()


# Update your load_portfolio function
def load_portfolio(user_id, portfolio_id):
    conn = sqlite3.connect('trading_system.db')
    try:
        c = conn.cursor()

        # Load portfolio data
        c.execute('''SELECT id, name, data FROM portfolios 
                   WHERE id=? AND user_id=?''',
                  (portfolio_id, user_id))
        result = c.fetchone()

        if not result:
            return None

        db_id, name, data_str = result
        data = json.loads(data_str)

        # Reconstruct portfolio
        portfolio = Simulation(name, data['portfolio']['cash'])
        portfolio.db_id = db_id
        portfolio.portfolio.update(data['portfolio'])
        portfolio.logs = data.get('logs', [])
        portfolio.images = data.get('images', [])

        # Load associated images
        c.execute('''SELECT image_path, image_type FROM simulation_images
                   WHERE simulation_id=?''', (db_id,))
        images = c.fetchall()

        for img_path, img_type in images:
            if img_type == 'performance':
                if 'performance_images' not in portfolio.portfolio:
                    portfolio.portfolio['performance_images'] = []
                portfolio.portfolio['performance_images'].append(img_path)
            else:
                portfolio.images.append(img_path)

        return portfolio
    except Exception as e:
        print(f"Error loading portfolio: {str(e)}")
        return None
    finally:
        conn.close()
        
        
        
#######################

def delete_portfolio(user_id, portfolio_id):
    """Delete a portfolio and its associated images from the database"""
    conn = sqlite3.connect('trading_system.db')
    try:
        c = conn.cursor()
        
        # First verify the portfolio belongs to the user
        c.execute('''SELECT id FROM portfolios 
                   WHERE id=? AND user_id=?''',
                  (portfolio_id, user_id))
        exists = c.fetchone()
        
        if not exists:
            print(f"No portfolio found with ID {portfolio_id} for user {user_id}")
            return False
        
        # Delete associated images first (foreign key constraint)
        c.execute('''DELETE FROM simulation_images 
                   WHERE simulation_id=?''',
                  (portfolio_id,))
        
        # Delete the portfolio
        c.execute('''DELETE FROM portfolios 
                   WHERE id=? AND user_id=?''',
                  (portfolio_id, user_id))
        
        conn.commit()
        
        if c.rowcount > 0:
            print(f"Successfully deleted portfolio {portfolio_id} and its associated images")
            return True
        else:
            print(f"Failed to delete portfolio {portfolio_id}")
            return False
            
    except sqlite3.Error as e:
        print(f"Database error deleting portfolio: {e}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"Unexpected error deleting portfolio: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()




########################


# --- Watchlist Storage ---
def save_watchlist(user_id, watchlist_obj):
    """Save watchlist to database (CREATE or UPDATE)"""
    conn = sqlite3.connect('trading_system.db')
    try:
        # Prepare complete watchlist data including prices and notes
        watchlist_data = {
            'symbols': list(watchlist_obj.watchlist.keys()),  # Maintain list of symbols
            'details': {  # Store all the detailed information
                symbol: {
                    'added_on': data['added_on'],
                    'last_price': data['last_price'],
                    'notes': data.get('notes', '')
                }
                for symbol, data in watchlist_obj.watchlist.items()
            }
        }

        if watchlist_obj.db_id:
            # UPDATE existing watchlist
            conn.execute('''UPDATE watchlists 
                         SET name=?, symbols=?
                         WHERE id=? AND user_id=?''',
                         (watchlist_obj.name,
                          json.dumps(watchlist_data),  # Serialize complete data
                          watchlist_obj.db_id,
                          user_id))
        else:
            # INSERT new watchlist
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO watchlists 
                           (user_id, name, symbols)
                           VALUES (?, ?, ?)''',
                           (user_id,
                            watchlist_obj.name,
                            json.dumps(watchlist_data)))  # Serialize complete data
            watchlist_obj.db_id = cursor.lastrowid

        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving watchlist: {e}")
        return False
    finally:
        conn.close()


def load_watchlist(user_id, watchlist_id):
    """Load watchlist from database"""
    conn = sqlite3.connect('trading_system.db')
    try:
        c = conn.cursor()
        c.execute('''SELECT id, name, symbols, created_at 
                   FROM watchlists 
                   WHERE id=? AND user_id=?''',
                  (watchlist_id, user_id))
        row = c.fetchone()

        if not row:
            return None

        db_id, name, symbols_str, created_at = row
        watchlist = Watchlist(name)
        watchlist.db_id = db_id
        watchlist.created_at = created_at

        try:
            # Parse the serialized data
            data = json.loads(symbols_str) if symbols_str else {}

            # Handle both old format (just list) and new format (with details)
            if isinstance(data, dict) and 'symbols' in data:
                # New format with details
                symbols = data.get('symbols', [])
                details = data.get('details', {})

                for symbol in symbols:
                    if symbol in details:
                        watchlist.watchlist[symbol] = details[symbol]
                    else:
                        # Fallback for incomplete data
                        watchlist.watchlist[symbol] = {
                            'added_on': created_at,
                            'last_price': get_stock_price(symbol),
                            'notes': ""
                        }
            else:
                # Old format (just list of symbols)
                symbols = data if isinstance(data, list) else []
                for symbol in symbols:
                    watchlist.watchlist[symbol] = {
                        'added_on': created_at,
                        'last_price': get_stock_price(symbol),
                        'notes': ""
                    }

        except json.JSONDecodeError:
            # Handle case where data couldn't be parsed
            print(f"Warning: Could not parse watchlist data for {name}")
            watchlist.watchlist = {}

        return watchlist
    except Exception as e:
        print(f"Error loading watchlist: {e}")
        return None
    finally:
        conn.close()
        
##################     
def delete_watchlist(user_id, watchlist_id):
    """Delete a watchlist from the database with validation"""
    conn = sqlite3.connect('trading_system.db')
    try:
        c = conn.cursor()
        
        # First verify the watchlist belongs to the user
        c.execute('''SELECT id FROM watchlists 
                   WHERE id=? AND user_id=?''',
                  (watchlist_id, user_id))
        exists = c.fetchone()
        
        if not exists:
            print(f"No watchlist found with ID {watchlist_id} for user {user_id}")
            return False
        
        # Delete the watchlist
        c.execute('''DELETE FROM watchlists 
                   WHERE id=? AND user_id=?''',
                  (watchlist_id, user_id))
        conn.commit()
        
        if c.rowcount > 0:
            print(f"Successfully deleted watchlist {watchlist_id}")
            return True
        else:
            print(f"Failed to delete watchlist {watchlist_id}")
            return False
            
    except sqlite3.Error as e:
        print(f"Database error deleting watchlist: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error deleting watchlist: {e}")
        return False
    finally:
        conn.close()

######################


def get_user_portfolios(user_id):
    """Get ALL portfolios for a user in a nested structure"""
    conn = sqlite3.connect('trading_system.db')
    try:
        c = conn.cursor()
        c.execute('''SELECT id, name, data, created_at FROM portfolios
                   WHERE user_id=? ORDER BY created_at DESC''',
                  (user_id,))

        portfolios = []
        for row in c.fetchall():
            try:
                portfolio_data = json.loads(row[2])

                portfolio = {
                    'id': row[0],
                    'name': row[1],
                    'created_at': row[3],
                    'type': 'portfolio',
                    'data': portfolio_data,  # Full portfolio data
                    'cash': portfolio_data.get('portfolio', {}).get('cash', 0),
                    'holdings_count': len(portfolio_data.get('portfolio', {}).get('holdings', {})),
                    'transactions_count': len(portfolio_data.get('portfolio', {}).get('transactions', []))
                }

                portfolios.append(portfolio)

            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error processing portfolio {row[0]}: {str(e)}")
                portfolios.append({
                    'id': row[0],
                    'name': row[1],
                    'created_at': row[3],
                    'type': 'portfolio',
                    'error': f"Could not load portfolio data: {str(e)}"
                })

        return {
            'user_id': user_id,
            'count': len(portfolios),
            'portfolios': portfolios  # Nested under 'portfolios' key
        }
    finally:
        conn.close()


def get_user_watchlists(user_id):
    """Get ALL watchlists for a user with detailed information"""
    conn = sqlite3.connect('trading_system.db')
    try:
        c = conn.cursor()
        c.execute('''SELECT id, name, symbols, created_at 
                   FROM watchlists
                   WHERE user_id=? 
                   ORDER BY created_at DESC''',
                  (user_id,))

        watchlists = []
        for row in c.fetchall():
            try:
                db_id, name, data_str, created_at = row
                data = json.loads(data_str) if data_str else {}

                # Handle both old (array) and new (object with symbols/details) formats
                if isinstance(data, dict) and 'symbols' in data:
                    # New format
                    symbols = data['symbols']
                    details = data.get('details', {})
                else:
                    # Old format (just array of symbols)
                    symbols = data if isinstance(data, list) else []
                    details = {}

                # Create summary for each watchlist
                watchlist_summary = []
                for symbol in symbols:
                    symbol_data = details.get(symbol, {})
                    current_price = get_stock_price(symbol)
                    initial_price = symbol_data.get('last_price', current_price)

                    watchlist_summary.append({
                        'Symbol': symbol,
                        'Added On': symbol_data.get('added_on', created_at),
                        'Initial Price': initial_price,
                        'Current Price': current_price if current_price else "N/A",
                        'Change': current_price - initial_price
                        if current_price and initial_price and isinstance(initial_price, (int, float))
                        else "N/A",
                        'Notes': symbol_data.get('notes', '')
                    })

                watchlists.append({
                    'id': db_id,
                    'name': name,
                    'created_at': created_at,
                    'symbol_count': len(symbols),
                    'watchlist_summary': watchlist_summary
                })

            except Exception as e:
                print(f"Error processing watchlist {row[0]}: {str(e)}")
                watchlists.append({
                    'id': row[0],
                    'name': row[1],
                    'created_at': row[3],
                    'error': str(e)
                })

        return {
            'user_id': user_id,
            'count': len(watchlists),
            'watchlists': watchlists
        }
    finally:
        conn.close()


def get_portfolio_details(portfolio_id):
    """Get full details of a specific portfolio with additional metadata"""
    conn = sqlite3.connect('trading_system.db')
    try:
        c = conn.cursor()

        # Get basic portfolio info
        c.execute('''SELECT id, user_id, name, data, created_at 
                   FROM portfolios WHERE id=?''',
                  (portfolio_id,))
        result = c.fetchone()
        if not result:
            return None

        portfolio_id, user_id, name, data_str, created_at = result
        data = json.loads(data_str)

        # Get associated images
        c.execute('''SELECT image_path, image_type FROM simulation_images
                   WHERE simulation_id=? ORDER BY created_at DESC''',
                  (portfolio_id,))
        images = [{'path': row[0], 'type': row[1]} for row in c.fetchall()]

        # Structure the response
        response = {
            'id': portfolio_id,
            'user_id': user_id,
            'name': name,
            'created_at': created_at,
            'type': 'portfolio',
            'details': {
                'cash': data['portfolio']['cash'],
                'holdings': data['portfolio']['holdings'],
                'transactions': data['portfolio']['transactions'],
                'performance_images': data['portfolio'].get('performance_images', []),
                'logs': data.get('logs', []),
                'return': data['portfolio'].get('return', 0)
            },
            'images': images,
            'raw_data': data  # The complete stored data
        }

        return response
    finally:
        conn.close()


def get_watchlist_details(watchlist_id):
    """Get detailed watchlist information"""
    conn = sqlite3.connect('trading_system.db')
    try:
        c = conn.cursor()
        c.execute('''SELECT id, user_id, name, symbols, created_at 
                   FROM watchlists WHERE id=?''',
                  (watchlist_id,))
        result = c.fetchone()
        if not result:
            return None

        db_id, user_id, name, data_str, created_at = result

        try:
            data = json.loads(data_str) if data_str else {}

            # Handle both old and new formats
            if isinstance(data, dict) and 'symbols' in data:
                # New format
                symbols = data['symbols']
                details = data.get('details', {})
            else:
                # Old format
                symbols = data if isinstance(data, list) else []
                details = {}

            watchlist_data = []
            for symbol in symbols:
                symbol_data = details.get(symbol, {})
                current_price = get_stock_price(symbol)
                initial_price = symbol_data.get('last_price', current_price)

                watchlist_data.append({
                    'Symbol': symbol,
                    'Added On': symbol_data.get('added_on', created_at),
                    'Initial Price': initial_price,
                    'Current Price': current_price if current_price else "N/A",
                    'Change': current_price - initial_price
                    if current_price and initial_price and isinstance(initial_price, (int, float))
                    else "N/A",
                    'Change_Percent': ((current_price - initial_price) / initial_price * 100)
                    if current_price and initial_price and initial_price != 0
                    else "N/A",
                    'Notes': symbol_data.get('notes', ''),
                    'Current_Time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

            return {
                'id': db_id,
                'user_id': user_id,
                'name': name,
                'created_at': created_at,
                'watchlist_summary': watchlist_data,
                'symbol_count': len(symbols),
                'total_change': sum(
                    item['Change'] for item in watchlist_data
                    if isinstance(item['Change'], (int, float))
                ),
                'metadata': {
                    'format': 'enhanced' if isinstance(data, dict) and 'symbols' in data else 'legacy'
                }
            }
        except json.JSONDecodeError as e:
            return {
                'id': db_id,
                'user_id': user_id,
                'name': name,
                'created_at': created_at,
                'error': 'Could not parse watchlist data',
                'raw_data': data_str
            }
    except Exception as e:
        print(f"Error getting watchlist details: {str(e)}")
        return None
    finally:
        conn.close()


def get_portfolio_images(portfolio_id):
    """Get all images associated with a portfolio"""
    conn = sqlite3.connect('trading_system.db')
    try:
        c = conn.cursor()
        c.execute('''SELECT id, image_path, image_type, created_at 
                   FROM simulation_images
                   WHERE simulation_id=? ORDER BY created_at DESC''',
                  (portfolio_id,))
        images = []
        for row in c.fetchall():
            images.append({
                'id': row[0],
                'path': row[1],
                'type': row[2],
                'created_at': row[3]
            })
        return images
    finally:
        conn.close()


class StrategyManager:
    def __init__(self, db_path='trading_system.db', conn=None):
        self.db_path = db_path
        # If a connection is provided (e.g. for testing), use it
        # Otherwise, connect when needed
        self._conn = conn
    
    def get_connection(self):
        """Get database connection, creating it if necessary"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    @property
    def conn(self):
        # If a connection was provided in constructor (e.g. for testing), use it directly
        # Otherwise, create/get connection as needed
        if self._conn is not None:
            return self._conn
        else:
            return self.get_connection()
    
    def close_connection(self):
        if self._conn and hasattr(self._conn, 'close'):
            self._conn.close()
            self._conn = None

    def create_strategy(self, user_id, portfolio_id, name, symbol, strategy_type, parameters):
        """Create a new trading strategy"""
        try:
            # Validate portfolio belongs to user
            c = self.get_connection().cursor()
            c.execute('SELECT id FROM portfolios WHERE id=? AND user_id=?',
                      (portfolio_id, user_id))
            if not c.fetchone():
                return False, "Portfolio not found or access denied"

            # Insert new strategy
            c.execute('''INSERT INTO strategies 
                        (user_id, portfolio_id, name, symbol, strategy_type, parameters)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                      (user_id, portfolio_id, name, symbol.upper(),
                       strategy_type.upper(), json.dumps(parameters)))
            self.get_connection().commit()
            
            return True, "Strategy created successfully"
        except Exception as e:
            print("hehehe",str(e))
            return False, f"Error creating strategy: {str(e)}"
        finally:
            # Only close connection if we opened it for this method
            if hasattr(self, '_conn') and self._conn and hasattr(self._conn, 'close'):
                self._conn.close()
                self._conn = None

    def delete_strategy(self, user_id, strategy_id):
        """Delete a strategy if it belongs to the user"""
        try:
            c = self.get_connection().cursor()
            c.execute('DELETE FROM strategies WHERE id=? AND user_id=?',
                      (strategy_id, user_id))
            self.get_connection().commit()
            return c.rowcount > 0, "Deleted" if c.rowcount else "Strategy not found"
        except Exception as e:
            return False, f"Error deleting strategy: {str(e)}"
        finally:
            # Only close connection if we opened it for this method
            if hasattr(self, '_conn') and self._conn and hasattr(self._conn, 'close'):
                self._conn.close()
                self._conn = None

    def list_strategies(self, user_id):
        """List all strategies for a user with portfolio info"""
        try:
            c = self.get_connection().cursor()
            c.execute('''SELECT s.id, s.name, s.symbol, s.strategy_type, s.is_active,
                         p.name as portfolio_name, s.last_executed
                      FROM strategies s
                      JOIN portfolios p ON s.portfolio_id = p.id
                      WHERE s.user_id=?''', (user_id,))
            return True, [dict(row) for row in c.fetchall()]
        except Exception as e:
            return False, f"Error listing strategies: {str(e)}"
        finally:
            # Only close connection if we opened it for this method
            if hasattr(self, '_conn') and self._conn and hasattr(self._conn, 'close'):
                self._conn.close()
                self._conn = None

    def list_strategies_json(self, user_id):
        """List all strategies for a user with portfolio info"""
        try:
            c = self.get_connection().cursor()
            c.execute('''SELECT s.id, s.name, s.symbol, s.strategy_type, s.is_active,
                         p.name as portfolio_name, s.last_executed
                      FROM strategies s
                      JOIN portfolios p ON s.portfolio_id = p.id
                      WHERE s.user_id=?''', (user_id,))
            return {"hasStrategies":"True","data": [dict(row) for row in c.fetchall()] }
        except Exception as e:
            return {"hasStrategies":'False', "data":[f"Error listing strategies: {str(e)}",]}
        finally:
            # Only close connection if we opened it for this method
            if hasattr(self, '_conn') and self._conn and hasattr(self._conn, 'close'):
                self._conn.close()
                self._conn = None



    def toggle_strategy(self, user_id, strategy_id, active):
        """Enable/disable a strategy"""
        try:
            c = self.get_connection().cursor()
            c.execute('''UPDATE strategies SET is_active=?
                      WHERE id=? AND user_id=?''',
                      (active, strategy_id, user_id))
            self.get_connection().commit()
            return c.rowcount > 0, "Updated" if c.rowcount else "Strategy not found"
        except Exception as e:
            return False, f"Error updating strategy: {str(e)}"
        finally:
            # Only close connection if we opened it for this method
            if hasattr(self, '_conn') and self._conn and hasattr(self._conn, 'close'):
                self._conn.close()
                self._conn = None



# Create user
# register_user("john_doe", "secure123")

# Authenticate
# user_id = authenticate_user("kau", "secure123")

# if user_id:
# Create and save portfolio
"""
my_portfolio = Simulation("Tech Portfolio", 100000)
my_portfolio.buy_stock("TCS", 10)
my_portfolio.buy_stock("INFY", 5)
save_portfolio(user_id, my_portfolio)

# Create and save watchlist
tech_watchlist = Watchlist("Tech Stocks")
tech_watchlist.add_to_watchlist("TCS", "Large cap")
tech_watchlist.add_to_watchlist("INFY", "Mid cap")
save_watchlist(user_id, tech_watchlist)

simobject = Simulation("main1", 20000)

results = simobject.run_backtest(
    strategy=simobject.bollinger_bands_strategy,
    symbol="TCS",
    start_date="2023-01-01",
    end_date="2023-12-31",
)

print(f"Strategy Return: {results['return'] * 100:.2f}%")

for transaction in results['transactions']:
    print(transaction)

    simobject = Simulation("main1", 20000)

results = simobject.run_backtest(
    strategy=simobject.bollinger_bands_strategy,
    symbol="TCS",
    start_date="2023-01-01",
    end_date="2023-12-31",
)

print(f"Strategy Return: {results['return'] * 100:.2f}%")

for transaction in results['transactions']:
    print(transaction)
save_portfolio(user_id, simobject )

results = loaded_portfolio.run_backtest(
    strategy=loaded_portfolio.bollinger_bands_strategy,
    symbol="WIPRO",
    start_date="2023-01-01",
    end_date="2023-12-31",
)

print(f"Strategy Return: {results['return'] * 100:.2f}%")

for transaction in results['transactions']:
    print(transaction)
save_portfolio(user_id, loaded_portfolio)



"""


"""
# Load and display portfolio
loaded_portfolio = load_portfolio(user_id, 3)


if loaded_portfolio:
    loaded_portfolio.view_portfolio()

# Load and display watchlist
loaded_watchlist = load_watchlist(user_id, 1)
if loaded_watchlist:
    loaded_watchlist.view_watchlist()


"""

"""
print(get_portfolio_images(14))
# Get all portfolios
portfolios_response = get_user_portfolios(4)
print(json.dumps(portfolios_response, indent=2))
print(f"User has {portfolios_response['count']} portfolios:")
for portfolio in portfolios_response['portfolios']:
print(f"- {portfolio['name']} (ID: {portfolio['id']}) with {portfolio['holdings_count']} holdings")

# Get all watchlists
watchlists_response = get_user_watchlists(1)
print(json.dumps(watchlists_response, indent=2))
print(f"\nUser has {watchlists_response['count']} watchlists:")
for watchlist in watchlists_response['watchlists']:
print(f"- {watchlist['name']} (ID: {watchlist['id']}) with {watchlist['count']} symbols")



portfolios_response = get_user_portfolios(6)
print(json.dumps(portfolios_response, indent=2))
sm=StrategyManager()
list_strategies1 = sm.list_strategies_json(2)
print(list_strategies1)

"""
# Create a simulation

"""
sim = Simulation("new1", 100000)

# Run a backtest with the Bollinger Bands strategy
results = sim.run_backtest(
sim.momentum_strategy,  # Strategy function
"TITAN",  # Symbol
"2023-01-01",  # Start date
"2023-12-31",  # End date
# lookback_days=14,
# threshold=0.05
)
print(results)
sim.run_backtest(
sim.moving_average_crossover,
"HDFCBANK",
"2023-01-01",
"2023-12-31",
lookback_days=14,
threshold=0.05
)
sim.view_portfolio()

# View final portfolio
print(generate_advice_sheet("SWIGGY"))
"""
# Or try the momentum strategy
















################################ NEW UPDATEE ####################


import yfinance as yf
import json
from typing import Dict, List, Optional, Tuple, Any
import matplotlib
matplotlib.use('Agg')  # Set non-interactive backend to avoid tkinter issues
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
import pandas as pd
import numpy as np

def analyze_sector_performance(json_file_path: str, time_window: int = 180, visualize: bool = False) -> Dict[str, Any]:
    """
    Analyze sector performance by comparing companies within sectors to their respective Nifty indices.
    
    Args:
        json_file_path: Path to the JSON file containing sector and company data
        time_window: Time window in days for analysis (default: 180 days/6 months)
        visualize: Whether to generate visualization plots (default: False)
        
    Returns:
        Dictionary containing sector analysis results
    """
    # Load sector and company data
    with open(json_file_path, 'r') as f:
        sector_data = json.load(f)
    
    # Define sector to Nifty index mapping
    sector_to_index = {
        "Information Technology": "^CNXIT",  # Nifty IT
        "Banking": "^NSEBANK",  # Nifty Bank
        "Pharmaceuticals": "^CNXPHARMA",  # Nifty Pharma
        "Automobile": "^CNXAUTO",  # Nifty Auto
        "Financial Services": "^NSEFIN",  # Nifty Financial Services
        "Metals & Mining": "^CNXMETAL",  # Nifty Metal
        "Energy": "^CNXENERGY",  # Nifty Energy
        "FMCG": "^CNXFMCG",  # Nifty FMCG
        "Construction & Real Estate": "^CNXREALTY"  # Nifty Realty
    }
    
    # Calculate date range for historical data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=time_window)
    
    # Initialize results dictionary
    results = {}
    
    # Process each sector
    for sector, companies in sector_data.items():
        print(f"Analyzing {sector}...")
        
        # Skip if sector doesn't have a mapped index
        if sector not in sector_to_index:
            print(f"No index mapping found for {sector}, skipping.")
            continue
        
        nifty_index = sector_to_index[sector]
        
        # Fetch index data
        try:
            # Note the warning about auto_adjust
            print(" YF.download() has changed argument auto_adjust default to True ")
            index_data = yf.download(nifty_index, start=start_date, end=end_date, progress=False)
            if index_data is None or index_data.empty:
                print(f"No data found for index {nifty_index}, skipping {sector}.")
                continue
                
            # Calculate index return - using scalar values, not Series
            index_start_price = float(index_data['Close'].iloc[0])
            index_end_price = float(index_data['Close'].iloc[-1])
            index_return_pct = round(((index_end_price - index_start_price) / index_start_price) * 100, 2)
        except Exception as e:
            print(f"Error fetching data for index {nifty_index}: {e}")
            continue
        
        # Process companies in the sector
        company_returns = {}
        outperformers = []
        underperformers = []
        company_data_for_viz = []
        
        for company in companies:
            ticker = company['ticker'] + ".NS"  # Add .NS suffix for NSE stocks
            
            try:
                # Fetch company data
                stock_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
                if stock_data is None or stock_data.empty:
                    print(f"No data found for {ticker}, skipping.")
                    continue
                
                # Calculate company return - using scalar values, not Series
                stock_start_price = stock_data['Close'].iloc[0].item() 
                stock_end_price = stock_data['Close'].iloc[-1].item() 
                stock_return_pct = round(((stock_end_price - stock_start_price) / stock_start_price) * 100, 2)
                
                # Store the return value
                company_returns[ticker] = stock_return_pct
                
                # Store data for visualization
                if visualize:
                    company_data_for_viz.append({
                        'ticker': company['ticker'],
                        'data': stock_data
                    })
                
                # Determine if outperforming or underperforming
                # Using scalar comparison, not Series comparison
                if stock_return_pct > index_return_pct:
                    outperformers.append({
                        'ticker': company['ticker'],
                        'return_pct': stock_return_pct,
                        'outperformance': round(stock_return_pct - index_return_pct, 2)
                    })
                else:
                    underperformers.append({
                        'ticker': company['ticker'],
                        'return_pct': stock_return_pct,
                        'underperformance': round(index_return_pct - stock_return_pct, 2)
                    })
                    
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                continue
        
        # Calculate average company return
        if company_returns:
            avg_company_return = round(sum(company_returns.values()) / len(company_returns), 2)
        else:
            avg_company_return = 0
        
        # Store results
        results[sector] = {
            "sector": sector,
            "nifty_index": nifty_index,
            "sector_return_pct": index_return_pct,
            "average_company_return_pct": avg_company_return,
            "company_returns": company_returns,
            "outperformers": outperformers,
            "underperformers": underperformers,
            "analysis_period": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "days": time_window
            }
        }
        
        # Generate visualization if requested
        if visualize and company_data_for_viz:
            generate_sector_visualization(sector, nifty_index, index_data, company_data_for_viz)
    
    return results

def generate_sector_visualization(sector: str, nifty_index: str, index_data: pd.DataFrame, 
                                 company_data: List[Dict]) -> None:
    """
    Generate visualization comparing sector index performance with individual companies.
    
    Args:
        sector: Sector name
        nifty_index: Nifty index symbol
        index_data: DataFrame containing index price data
        company_data: List of dictionaries with company ticker and price data
    """
    plt.figure(figsize=(12, 8))
    
    # Plot index data
    if not index_data.empty:
        # Normalize to 100
        normalized_index = (index_data['Close'] / index_data['Close'].iloc[0]) * 100
        plt.plot(normalized_index.index, normalized_index, 'k-', linewidth=3, label=f"{nifty_index} Index")
    
    # Plot company data (limit to 5 companies for clarity)
    colors = ['b', 'g', 'r', 'c', 'm']
    for i, company in enumerate(company_data[:5]):  # Limit to first 5 companies
        ticker = company['ticker']
        stock_data = company['data']
        
        if not stock_data.empty:
            # Normalize to 100
            normalized_stock = (stock_data['Close'] / stock_data['Close'].iloc[0]) * 100
            plt.plot(normalized_stock.index, normalized_stock, 
                     color=colors[i % len(colors)], 
                     linestyle='-', 
                     label=ticker)
    
    # Add chart elements
    start_date = index_data.index[0].strftime('%Y-%m-%d')
    end_date = index_data.index[-1].strftime('%Y-%m-%d')
    plt.title(f"{sector} Performance: {start_date} to {end_date}")
    plt.xlabel('Date')
    plt.ylabel('Normalized Price (Base 100)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='best')
    
    # Save the figure
    output_dir = "sector_analysis_plots"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{sector.replace(' & ', '_').replace(' ', '_').lower()}_performance.png"
    plt.savefig(filename)
    plt.close('all')  # Close all figures to ensure proper cleanup
    print(f"Visualization saved to {filename}")

def run_sector_analysis(time_window_months: int = 6, visualize: bool = True) -> Dict[str, Any]:
    """
    Run sector analysis with the specified time window and visualization option.
    
    Args:
        time_window_months: Analysis time window in months
        visualize: Whether to generate visualization plots
        
    Returns:
        Dictionary containing sector analysis results
    """
    json_file_path = "sector_company.json"
    time_window_days = time_window_months  * 30
    
    results = analyze_sector_performance(json_file_path, time_window_days, visualize)
    
    # Print summary
    print("\nSector Analysis Summary:")
    for sector, data in results.items():
        print(f"\n{sector}:")
        print(f"  Nifty Index: {data['nifty_index']}")
        print(f"  Sector Return: {data['sector_return_pct']}%")
        print(f"  Avg Company Return: {data['average_company_return_pct']}%")
        print("  Company Returns:")
        for ticker, ret in data['company_returns'].items():
            print(f"    {ticker.replace('.NS', '')}: {ret}%")
        print(f"  Outperformers: {len(data['outperformers'])} stocks")
        for stock in data['outperformers']:
            print(f"    {stock['ticker']}: {stock['return_pct']}% (+{stock['outperformance']}%)")  
        print(f"  Underperformers: {len(data['underperformers'])} stocks")
        for stock in data['underperformers']:
            print(f"    {stock['ticker']}: {stock['return_pct']}% (-{stock['underperformance']}%)")
    return results
def forecast_stock_trends():
    import os
    import json
    import time
    import numpy as np
    import pandas as pd  # Make sure pandas is imported
    from prophet import Prophet
    from sklearn.linear_model import LinearRegression
    
    # Initialize data structures
    trends = {}
    skipped_stocks = []
    
    # Ensure cache directory exists
    os.makedirs('forecast_cache', exist_ok=True)
    
    # Load sector data
    try:
        with open('sector_company.json') as f:
            sector_data = json.load(f)
    except Exception as e:
        print(f"Error loading sector data: {str(e)}")
        return {}, ["Error loading sector data"]
    
    for sector_name, companies in sector_data.items():
        for company in companies:
            symbol = company['ticker']
            ticker = f"{symbol}.NS"
            sect = company['sector']
            cache_file = f"forecast_cache/{symbol}_forecast.json"
            
            # Check cache first
            if os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file)) < 86400:  # 24 hours
                try:
                    with open(cache_file) as f:
                        cached_data = json.load(f)
                        trends[symbol] = {
                            'slope': cached_data['trend_slope'],
                            'expected_return': cached_data.get('expected_return', 0),
                            'trend_strength': cached_data.get('trend_strength', 0)
                        }
                    print(f"Using cached data for {symbol}")
                    continue
                except Exception as e:
                    print(f"Error reading cache for {symbol}: {str(e)}")
                    # Continue to fetch fresh data
            
            print(f"Processing {symbol}...")
            
            # Fetch and validate data
            try:
                # Attempt to fetch data with auto_adjust=True first
                df = yf.download(ticker, period="6mo", progress=False)
                
                # Handle multi-index DataFrame if present
                close_data = None
                if isinstance(df.columns, pd.MultiIndex):
                    # Check if 'Close' is in the first level
                    if 'Close' in df.columns.levels[0]:
                        close_data = df['Close']
                        # If ticker is in the second level, select it
                        if ticker in close_data.columns:
                            close_data = close_data[ticker]
                    # Check if 'Price' is in the first level and contains 'Close'
                    elif 'Price' in df.columns.levels[0]:
                        # Try to find Close in the second level under Price
                        if 'Close' in df['Price'].columns:
                            close_data = df['Price']['Close']
                else:
                    # Standard single-index DataFrame
                    if 'Close' in df.columns:
                        close_data = df['Close']
                
                # If we couldn't find Close data, try to use any available price data
                if close_data is None:
                    for col_level1 in df.columns.levels[0] if isinstance(df.columns, pd.MultiIndex) else df.columns:
                        if isinstance(df.columns, pd.MultiIndex):
                            # For multi-index, try to find any price-related column
                            for col_level2 in df[col_level1].columns:
                                if any(price_term in col_level2.lower() for price_term in ['close', 'price', 'adj']):
                                    close_data = df[col_level1][col_level2]
                                    print(f"Using {col_level1}/{col_level2} as price data for {symbol}")
                                    break
                        elif any(price_term in col_level1.lower() for price_term in ['close', 'price', 'adj']):
                            close_data = df[col_level1]
                            print(f"Using {col_level1} as price data for {symbol}")
                            break
                
                # If we still couldn't find price data, skip this stock
                if close_data is None:
                    print(f"Skipping {symbol}: could not find price data in DataFrame")
                    skipped_stocks.append(f"{symbol} (no price data)")
                    continue
                
                # Data validation checks
                if len(close_data) < 30:
                    print(f"Skipping {symbol}: insufficient data (only {len(close_data)} points)")
                    skipped_stocks.append(f"{symbol} (insufficient data)")
                    continue
                
                # Use .item() to avoid truth value of Series is ambiguous error
                if close_data.isnull().any().item() or np.isclose(close_data.std(), 0):
                    print(f"Skipping {symbol}: invalid price data")
                    skipped_stocks.append(f"{symbol} (invalid data)")
                    continue
                
                # Prepare data for Prophet
                if isinstance(close_data.index, pd.DatetimeIndex):
                    prophet_df = pd.DataFrame({
                        'ds': close_data.index,
                        'y': close_data.values
                    })
                else:
                    # If we don't have a DatetimeIndex, create a DataFrame with reset_index
                    prophet_df = pd.DataFrame({
                        'ds': df.index,
                        'y': close_data.values
                    })
                
                # Initialize and fit model
                model = Prophet(daily_seasonality=False)
                model.fit(prophet_df)
                
                # Make future dataframe and predict
                future = model.make_future_dataframe(periods=30)
                forecast = model.predict(future)
                
                # Calculate trend metrics
                X = np.array(range(len(close_data))).reshape(-1, 1)
                y = close_data.values
                lr = LinearRegression().fit(X, y)
                trend_slope = lr.coef_[0]
                r_squared = lr.score(X, y)
                
                # Calculate expected return
                last_price = close_data.iloc[-1]
                forecast_price = forecast['yhat'].iloc[-1]
                expected_return = (forecast_price - last_price) / last_price * 100
                
                final_score = (trend_slope * 0.25) + (expected_return * 0.4) + (r_squared * 0.35)
                # Validate results
                if np.isnan(expected_return) or np.isinf(expected_return):
                    print(f"Warning: Invalid expected_return for {symbol}, using default")
                    expected_return = 0
                    
                if np.isnan(r_squared) or np.isinf(r_squared):
                    print(f"Warning: Invalid trend_strength for {symbol}, using default")
                    r_squared = 0
                
                # Store results
                trends[symbol] = {
                    'slope': float(trend_slope),  
                    'sector': sect,
                    'expected_return': float(expected_return),
                    'trend_strength': float(r_squared),
                    'score': float(final_score)
                }
                
                
            except YFPricesMissingError as e:
                print(f"Skipping {symbol}: possibly delisted - {str(e)}")
                skipped_stocks.append(f"{symbol} (delisted)")
                continue
            except Exception as e:
                print(f"Error processing {symbol}: {str(e)}")
                skipped_stocks.append(f"{symbol} (processing error: {str(e)})")
                continue
    
    print(f"Processed {len(trends)} stocks successfully. Skipped {len(skipped_stocks)} stocks.")
    trendsjson = json.dumps(trends, indent = 2)
    return trendsjson

