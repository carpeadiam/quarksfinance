from flask import Flask, jsonify, request, make_response, session
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import pytz
import sqlite3
from flask_cors import CORS
from datetime import datetime, timedelta
from functools import wraps
from q9 import (
    Simulation, Watchlist,
    register_user, authenticate_user,
    save_portfolio, load_portfolio,delete_portfolio,
    save_watchlist, load_watchlist,
    get_user_portfolios, get_user_watchlists,delete_watchlist,
    get_portfolio_details, get_watchlist_details,
    get_portfolio_images, StrategyManager,
    get_stock_price, get_historical_price,
    generate_advice_sheet,StrategyExecutor,run_sector_analysis, forecast_stock_trends, return_email, create_database
)
from useralgo import (
    UserAlgorithmManager, CustomAlgorithm, 
    create_rsi_oversold_algorithm, create_multi_strategy_algorithm,
    create_mean_reversion_algorithm, create_momentum_algorithm,
    AlgorithmOptimizer, algorithm_manager
)
import yfinance as yf
import pandas as pd
import json
from qs3 import QuarkScriptInterpreter  
import os
import json
import threading
from typing import Dict, Any, Callable, Literal, Union

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app) 

create_database()
def fetch_market_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch market data for a given symbol and date range using yfinance.
    
    Args:
        symbol (str): Stock symbol
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        pd.DataFrame: DataFrame with market data including OPEN, HIGH, LOW, CLOSE, VOLUME
        
    Raises:
        Exception: If data cannot be fetched or processed
    """
    try:
        # Add .NS extension for NSE stocks if not present
        if not symbol.endswith('.NS'):
            ticker = f"{symbol}.NS"
        else:
            ticker = symbol
            
        # Fetch data using yfinance
        stock_data = yf.download(ticker, start=start_date, end=end_date)
        
        # Check if we got any data
        if stock_data is None or stock_data.empty:
            raise Exception(f"No data found for symbol {symbol} between {start_date} and {end_date}")
        
        # Handle multi-index columns if present
        if isinstance(stock_data.columns, pd.MultiIndex):
            # Flatten multi-index columns
            stock_data.columns = stock_data.columns.droplevel(1)
        
        # Make a copy to avoid modifying the original data
        stock_data = stock_data.copy()
        
        # Rename columns to match expected format
        column_mapping = {
            'Open': 'OPEN',
            'High': 'HIGH',
            'Low': 'LOW',
            'Close': 'CLOSE',
            'Volume': 'VOLUME'
        }
        
        # Apply column mapping for any matching columns
        rename_dict = {old: new for old, new in column_mapping.items() if old in stock_data.columns}
        stock_data = stock_data.rename(columns=rename_dict)
        
        # Ensure all required columns are present
        required_columns = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
        missing_columns = [col for col in required_columns if col not in stock_data.columns]
        if missing_columns:
            raise Exception(f"Missing required columns: {missing_columns}")
        
        # Reset index to make Date a column
        stock_data = stock_data.reset_index()
        
        # Rename Date column if needed
        if 'Date' in stock_data.columns:
            stock_data = stock_data.rename(columns={'Date': 'DATE'})
        
        # Ensure DATE column exists
        if 'DATE' not in stock_data.columns:
            raise Exception("Missing DATE column in data")
        
        # FIX: Convert to datetime but DON'T convert to string
        stock_data['DATE'] = pd.to_datetime(stock_data['DATE'])
        
        # FIX: Remove timezone info if present
        if hasattr(stock_data['DATE'].iloc[0], 'tz') and stock_data['DATE'].iloc[0].tz is not None:
            stock_data['DATE'] = stock_data['DATE'].dt.tz_convert(None)
        
        # Sort by date
        stock_data = stock_data.sort_values('DATE').reset_index(drop=True)
        
        # Fill any NaN values using forward and backward fill
        stock_data = stock_data.ffill().bfill()
        
        # Select only the required columns in the correct order
        stock_data = stock_data[['DATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']]
        
        # Ensure we return a DataFrame
        if not isinstance(stock_data, pd.DataFrame):
            stock_data = pd.DataFrame(stock_data)
        
        return stock_data
        
    except Exception as e:
        raise Exception(f"Failed to fetch market data for {symbol}: {str(e)}")
        
def convert_numpy_types(obj):
    """
    Convert NumPy types to native Python types for JSON serialization.
    
    Args:
        obj: Object to convert
        
    Returns:
        Object with NumPy types converted to native Python types
    """
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif hasattr(obj, 'item'):  # NumPy scalar types have an 'item' method
        return obj.item()
    elif hasattr(obj, 'tolist'):  # NumPy arrays have a 'tolist' method
        return obj.tolist()
    else:
        return obj

# Initialize algorithm manager
algorithm_manager = UserAlgorithmManager() 

def get_algorithm_manager():
    """Get the algorithm manager instance, ensuring it's properly initialized"""
    global algorithm_manager
    if algorithm_manager is None:
        algorithm_manager = UserAlgorithmManager()
    return algorithm_manager

# Helper Functions
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['user_id']
        except:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


def create_quantum_momentum_matrix(macd_fast=12, macd_slow=26, macd_signal=9, 
                                 rsi_period=14, rsi_level=55, adx_period=14, 
                                 adx_level=25, volume_lookback=20, volume_multiplier=1.5,
                                 stop_loss=0.02, take_profit=0.06, position_size=0.12):
    """Create Quantum Momentum Matrix strategy"""
    return {
        "name": f"Quantum Momentum Matrix",
        "description": f"Multi-timeframe momentum with RSI {rsi_level}+ and ADX {adx_level}+ trend strength",
        "buy_rules": [
            {
                "id": "multi_timeframe_momentum",
                "name": "3-Timeframe Momentum Alignment",
                "signal_type": "BUY",
                "conditions": [
                    {
                        "id": "daily_macd_bullish",
                        "indicator_type": "MACD",
                        "indicator_params": {"fast": macd_fast, "slow": macd_slow, "signal": macd_signal, "component": "histogram"},
                        "comparison": ">",
                        "value": 0  # MACD histogram above zero
                    },
                    {
                        "id": "rsi_daily_strong",
                        "indicator_type": "RSI",
                        "indicator_params": {"period": rsi_period},
                        "comparison": ">",
                        "value": rsi_level  # Parameterized RSI level
                    },
                    {
                        "id": "volume_confirmation",
                        "indicator_type": "VOLUME",
                        "indicator_params": {"lookback": volume_lookback},
                        "comparison": ">",
                        "value": volume_multiplier  # Parameterized volume multiplier
                    },
                    {
                        "id": "adx_trend_strength",
                        "indicator_type": "ADX",
                        "indicator_params": {"period": adx_period, "component": "adx"},
                        "comparison": ">",
                        "value": adx_level  # Parameterized ADX level
                    }
                ],
                "logic_operator": "AND"
            }
        ],
        "sell_rules": [
            {
                "id": "momentum_divergence",
                "name": "Momentum Divergence Signal",
                "signal_type": "SELL",
                "conditions": [
                    {
                        "id": "macd_histogram_divergence",
                        "indicator_type": "MACD",
                        "indicator_params": {"fast": macd_fast, "slow": macd_slow, "signal": macd_signal, "component": "histogram"},
                        "comparison": "crosses_below",
                        "value": 0  # MACD histogram crosses below zero
                    }
                ],
                "logic_operator": "OR"
            },
            {
                "id": "rsi_overbought",
                "name": "RSI Overbought Exit",
                "signal_type": "SELL",
                "conditions": [
                    {
                        "id": "rsi_extreme",
                        "indicator_type": "RSI",
                        "indicator_params": {"period": rsi_period},
                        "comparison": ">",
                        "value": 70  # Fixed overbought level (could be parameterized if needed)
                    }
                ],
                "logic_operator": "OR"
            }
        ],
        "risk_management": {
            "stop_loss_pct": stop_loss,
            "take_profit_pct": take_profit,
            "max_position_size": position_size,
            "max_daily_loss": 0.03,
            "max_drawdown": 0.12,
            "position_sizing_method": "volatility"
        }
    }

def create_alpha_convergence_system(bb_period=20, bb_std=2, rsi_period=14, 
                                  oversold_level=32, oversold_bb_level=15,
                                  macd_fast=12, macd_slow=26, macd_signal=9, 
                                  target_level=85, stop_loss=0.015, 
                                  take_profit=0.045, position_size=0.15):
    """Create Alpha Convergence System strategy"""
    return {
        "name": "Alpha Convergence System",
        "description": f"Mean reversion + momentum hybrid. Buys at RSI {oversold_level}-, sells at BB {target_level}+",
        "buy_rules": [
            {
                "id": "mean_reversion_entry",
                "name": "Oversold Bounce Setup",
                "signal_type": "BUY",
                "conditions": [
                    {
                        "id": "bollinger_extreme_oversold",
                        "indicator_type": "BOLLINGER",
                        "indicator_params": {"period": bb_period, "std": bb_std, "component": "bb_percent"},
                        "comparison": "<",
                        "value": oversold_bb_level  # Parameterized BB oversold level
                    },
                    {
                        "id": "rsi_oversold",
                        "indicator_type": "RSI",
                        "indicator_params": {"period": rsi_period},
                        "comparison": "<",
                        "value": oversold_level  # Parameterized RSI oversold level
                    },
                    {
                        "id": "macd_positive",
                        "indicator_type": "MACD",
                        "indicator_params": {"fast": macd_fast, "slow": macd_slow, "signal": macd_signal, "component": "histogram"},
                        "comparison": ">",
                        "value": 0  # MACD histogram above zero
                    }
                ],
                "logic_operator": "AND"
            }
        ],
        "sell_rules": [
            {
                "id": "target_reached",
                "name": "Profit Target Achievement",
                "signal_type": "SELL",
                "conditions": [
                    {
                        "id": "bollinger_upper_band",
                        "indicator_type": "BOLLINGER",
                        "indicator_params": {"period": bb_period, "std": bb_std, "component": "bb_percent"},
                        "comparison": ">",
                        "value": target_level  # Parameterized target level
                    }
                ],
                "logic_operator": "OR"
            }
        ],
        "risk_management": {
            "stop_loss_pct": stop_loss,
            "take_profit_pct": take_profit,
            "max_position_size": position_size,
            "max_daily_loss": 0.025,
            "max_drawdown": 0.1,
            "position_sizing_method": "kelly"
        }
    }

def create_volatility_breakout_system(breakout_period=20, consolidation_level=40,
                                    price_breakout_percent=1.02, volume_multiplier=1.5,
                                    atr_trailing_percent=0.97, stop_loss=0.01, 
                                    take_profit=0.04, position_size=0.18):
    """Create Volatility Breakout System strategy"""
    return {
        "name": "Volatility Breakout System",
        "description": f"Identifies low-volatility consolidation followed by high-volume breakouts",
        "buy_rules": [
            {
                "id": "breakout_confirmation",
                "name": "Volume Breakout Signal",
                "signal_type": "BUY",
                "conditions": [
                    {
                        "id": "price_breakout_high",
                        "indicator_type": "PRICE",
                        "indicator_params": {"lookback": breakout_period},
                        "comparison": ">",
                        "value": price_breakout_percent  # Parameterized breakout percentage
                    },
                    {
                        "id": "volume_surge",
                        "indicator_type": "VOLUME",
                        "indicator_params": {"lookback": breakout_period},
                        "comparison": ">",
                        "value": volume_multiplier  # Parameterized volume multiplier
                    },
                    {
                        "id": "low_volatility_setup",
                        "indicator_type": "BOLLINGER",
                        "indicator_params": {"period": 20, "std": 1.5, "component": "bb_percent"},
                        "comparison": "<",
                        "value": consolidation_level  # Parameterized consolidation level
                    }
                ],
                "logic_operator": "AND"
            }
        ],
        "sell_rules": [
            {
                "id": "atr_trailing_stop",
                "name": "ATR Trailing Stop",
                "signal_type": "SELL",
                "conditions": [
                    {
                        "id": "price_below_atr_stop",
                        "indicator_type": "PRICE",
                        "indicator_params": {"lookback": 20},
                        "comparison": "<",
                        "value": atr_trailing_percent  # Parameterized trailing stop percentage
                    }
                ],
                "logic_operator": "OR"
            }
        ],
        "risk_management": {
            "stop_loss_pct": stop_loss,
            "take_profit_pct": take_profit,
            "max_position_size": position_size,
            "max_daily_loss": 0.02,
            "max_drawdown": 0.08,
            "position_sizing_method": "volatility"
        }
    }

def create_smart_money_flow(mfi_period=14, mfi_level=60, obv_lookback=20,
                          obv_multiplier=1.05, vwap_multiplier=1.01,
                          obv_divergence_level=0.95, stop_loss=0.018, 
                          take_profit=0.055, position_size=0.1):
    """Create Smart Money Flow strategy"""
    return {
        "name": "Smart Money Flow Strategy",
        "description": "Follows institutional money flow using OBV, MFI, and large block trades",
        "buy_rules": [
            {
                "id": "smart_money_accumulation",
                "name": "Institutional Accumulation Signal",
                "signal_type": "BUY",
                "conditions": [
                    {
                        "id": "obv_uptrend",
                        "indicator_type": "OBV",
                        "indicator_params": {"lookback": obv_lookback},
                        "comparison": ">",
                        "value": obv_multiplier  # Parameterized OBV multiplier
                    },
                    {
                        "id": "mfi_strong",
                        "indicator_type": "MFI",
                        "indicator_params": {"period": mfi_period},
                        "comparison": ">",
                        "value": mfi_level  # Parameterized MFI level
                    },
                    {
                        "id": "price_above_vwap",
                        "indicator_type": "PRICE",
                        "indicator_params": {"vwap_period": 20},
                        "comparison": ">",
                        "value": vwap_multiplier  # Parameterized VWAP multiplier
                    }
                ],
                "logic_operator": "AND"
            }
        ],
        "sell_rules": [
            {
                "id": "smart_money_distribution",
                "name": "Institutional Distribution",
                "signal_type": "SELL",
                "conditions": [
                    {
                        "id": "obv_divergence",
                        "indicator_type": "OBV",
                        "indicator_params": {"lookback": obv_lookback},
                        "comparison": "<",
                        "value": obv_divergence_level  # Parameterized OBV divergence level
                    }
                ],
                "logic_operator": "OR"
            }
        ],
        "risk_management": {
            "stop_loss_pct": stop_loss,
            "take_profit_pct": take_profit,
            "max_position_size": position_size,
            "max_daily_loss": 0.022,
            "max_drawdown": 0.09,
            "position_sizing_method": "kelly"
        }
    }
def ensure_numeric_values(config_dict):
    """
    Recursively convert string numbers to numeric values in algorithm configuration
    """
    if isinstance(config_dict, dict):
        for key, value in config_dict.items():
            if key == 'value' and isinstance(value, str):
                # Try to convert string numbers to float
                try:
                    if value.replace('.', '', 1).isdigit() or (value.startswith('-') and value[1:].replace('.', '', 1).isdigit()):
                        config_dict[key] = float(value)
                except:
                    pass  # Leave as string if conversion fails
            elif isinstance(value, (dict, list)):
                ensure_numeric_values(value)
    elif isinstance(config_dict, list):
        for item in config_dict:
            ensure_numeric_values(item)
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
@app.route('/', methods=['GET'])
def health_check():
    """Root health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Trading System API is running',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'environment': 'production'
    })

@app.route('/api', methods=['GET'])
def api_health():
    """API health check endpoint with detailed service status"""
    try:
        # Test database connectivity
        conn = sqlite3.connect('trading_system.db')
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        conn.close()
        db_status = 'healthy'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    # Test market data connectivity (quick check)
    try:
        test_price = get_stock_price('AAPL', live=False)  # Use cached data if available
        market_data_status = 'healthy' if test_price else 'warning: limited functionality'
    except Exception as e:
        market_data_status = f'error: {str(e)}'
    
    health_status = {
        'status': 'healthy',
        'message': 'All API endpoints are operational',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'database': db_status,
            'market_data': market_data_status,
            'authentication': 'healthy',
            'portfolio_management': 'healthy',
            'strategy_execution': 'healthy',
            'custom_algorithms': 'healthy'
        },
        'endpoints': {
            'authentication': ['/api/register', '/api/login'],
            'portfolios': ['/api/portfolios', '/api/portfolios/<id>'],
            'watchlists': ['/api/watchlists', '/api/watchlists/<id>'],
            'strategies': ['/api/strategies', '/api/strategies/<id>'],
            'algorithms': ['/api/algorithms', '/api/algorithms/<id>'],
            'market_data': ['/api/market/price/<symbol>', '/api/market/sector-performance'],
            'analysis': ['/api/advice/<symbol>', '/api/forecast-trends']
        }
    }
    
    # Determine overall status
    service_statuses = list(health_status['services'].values())
    if any('error' in status for status in service_statuses):
        health_status['status'] = 'degraded'
        health_status['message'] = 'Some services are experiencing issues'
    elif any('warning' in status for status in service_statuses):
        health_status['status'] = 'warning'
        health_status['message'] = 'All critical services operational, some warnings present'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code

# Authentication Routes
@app.route('/api/register', methods=['POST'])
def register():
    print('[LOCAL API] /api/register endpoint called')
    data = request.get_json()
    success = register_user(data['username'], data['password'])
    if success:
        return jsonify({'message': 'User created successfully'}), 201
    return jsonify({'message': 'Username already exists'}), 400


@app.route('/api/login', methods=['POST'])
def login():
    print('[LOCAL API] /api/login endpoint called')
    auth = request.get_json()
    try:
        response = requests.get(f'https://api.ipgeolocation.io/v2/ipgeo?apiKey= 33a388920bab464ab20c244c5e04fbcf')
        data = response.json()
        if 'country_name' in data and data['country_name'] != 'India':
            return jsonify({
                'message': 'Access denied: This service is only available in India',
                'location': data.get('country_name', 'Unknown')
            }), 403
    except Exception as e:
        # If geolocation check fails, log the error but continue with login
        print(f"Geolocation check failed: {str(e)}")
    
    # Proceed with normal login if geolocation check passes or fails
    user_id = authenticate_user(auth['username'], auth['password'])

    # If user doesn't exist and this looks like a Google sign-in (UID starts with "google:"), 
    # register them automatically
    if not user_id and str(auth['password']).startswith('google:'):
        # Try to register the Google user
        register_success = register_user(auth['username'], auth['password'])
        if register_success:
            # Now authenticate the newly registered user
            user_id = authenticate_user(auth['username'], auth['password'])
        else:
            # If registration failed, try to authenticate again (might be a race condition)
            user_id = authenticate_user(auth['username'], auth['password'])
    
    # If still no user_id, authentication failed
    if not user_id:
        return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'})
    
    global interpreter
    interpreter = QuarkScriptInterpreter(user_id)
    token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(minutes=30)
    }, app.config['SECRET_KEY'])

    return jsonify({'token': token, 'user_id': user_id})
    
@app.route('/api/login2', methods=['POST'])
def login2():
    print('[LOCAL API] /api/login2 endpoint called')
    auth = request.get_json()
    user_id = authenticate_user(auth['username'], auth['password'])

    # If user doesn't exist and this looks like a Google sign-in (UID starts with "google:"), 
    # register them automatically
    if not user_id and str(auth['password']).startswith('google:'):
        # Try to register the Google user
        register_success = register_user(auth['username'], auth['password'])
        if register_success:
            # Now authenticate the newly registered user
            user_id = authenticate_user(auth['username'], auth['password'])
        else:
            # If registration failed, try to authenticate again (might be a race condition)
            user_id = authenticate_user(auth['username'], auth['password'])
    
    # If still no user_id, authentication failed
    if not user_id:
        return jsonify({'message': 'Could not verify user credentials'}), 401

    token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(minutes=30)
    }, app.config['SECRET_KEY'])

    return jsonify({'token': token, 'user_id': user_id})


# User Routes
@app.route('/api/users/<int:user_id>', methods=['GET'])
@token_required
def get_user(current_user, user_id):
    if current_user != user_id:
        return jsonify({'message': 'Cannot access other user data'}), 403

    # In a real app, you'd have a get_user function in quarks3
    return jsonify({'user_id': user_id})
    
# User Routes
@app.route('/api/user_email/<int:user_id>', methods=['GET'])
def get_user_email2(user_id):
    
    result=return_email(user_id)
    if result:
        if '@' in result:
            isEmail='True'
        else:
            isEmail='False'
        return jsonify({'username': result, 'is_email':isEmail})
    # In a real app, you'd have a get_user function in quarks3
    return jsonify({'username': 'none'})


#############DISCORD METHODS################

@app.route('/api/discord/generate-code', methods=['GET'])
@token_required
def generate_verification_code(current_user):
    try:
        # Create JWT token without expiration
        verification_code = jwt.encode(
            {'user_id': current_user},
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )

        return jsonify({'code': verification_code}), 200
        
    except Exception as e:
        app.logger.error(f"Error generating verification code: {str(e)}")
        return jsonify({'error': 'Failed to generate verification code'}), 500

@app.route('/api/discord/verify', methods=['POST'])
def verify_discord_code():
    data = request.get_json()
    
    if not data or 'code' not in data or 'discord_user_id' not in data:
        return jsonify({'error': 'Missing required fields: code and discord_user_id are required'}), 400

    conn = None
    try:
        # Decode the JWT (no expiration check)
        decoded = jwt.decode(data['code'], app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = decoded['user_id']
        
        # Store in database
        conn = sqlite3.connect('trading_system.db')
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO discord_users (user_id, discord_id)
            VALUES (?, ?)
        ''', (user_id, data['discord_user_id']))
        
        conn.commit()
        return jsonify({'success': True, 'user_id': user_id}), 200
        
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid verification code'}), 401
    except sqlite3.Error as e:
        app.logger.error(f"Database error: {str(e)}")
        return jsonify({'error': 'Failed to update user data'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Verification failed'}), 500
    finally:
        if conn:
            conn.close()
############################################




# Portfolio Routes
@app.route('/api/portfolios', methods=['GET', 'POST'])
@token_required
def portfolios(current_user):
    if request.method == 'GET':
        portfolios_data = get_user_portfolios(current_user)
        return jsonify(portfolios_data)

    elif request.method == 'POST':
        data = request.get_json()
        portfolio = Simulation(data['name'], float(data.get('initial_cash', 100000)))
        success = save_portfolio(current_user, portfolio)
        if success:
            return jsonify({
                'message': 'Portfolio created',
                'portfolio_id': portfolio.db_id
            }), 201
        return jsonify({'message': 'Error creating portfolio'}), 500


@app.route('/api/portfolios/<int:portfolio_id>', methods=['GET', 'PUT', 'DELETE'])
@token_required
def portfolio(current_user, portfolio_id):
    portfolio = load_portfolio(current_user, portfolio_id)
    if not portfolio:
        return jsonify({'message': 'Portfolio not found'}), 404

    if request.method == 'GET':
        details = get_portfolio_details(portfolio_id)
        return jsonify(details)

    elif request.method == 'PUT':
        data = request.get_json()
        # Update portfolio name if provided
        if 'name' in data:
            portfolio.name = data['name']
        # You could add more update logic here
        success = save_portfolio(current_user, portfolio)
        if success:
            return jsonify({'message': 'Portfolio updated'})
        return jsonify({'message': 'Error updating portfolio'}), 500

    elif request.method == 'DELETE':
        # Delete logic would need to be implemented in quarks3
        success=delete_portfolio(current_user,portfolio_id)
        if success:
            return jsonify({'message': 'Portfolio deleted'})
        return jsonify({'message': 'Error '}), 501


# Portfolio Transactions
@app.route('/api/portfolios/<int:portfolio_id>/buy', methods=['POST'])
@token_required
def buy_stock(current_user, portfolio_id):
    portfolio = load_portfolio(current_user, portfolio_id)
    if not portfolio:
        return jsonify({'message': 'Portfolio not found'}), 404

    data = request.get_json()
    try:
        portfolio.buy_stock(
            data['symbol'],
            int(data['quantity']),
            price=float(data.get('price')) if data.get('price') else None,
            live=data.get('live', True)
        )
        save_portfolio(current_user, portfolio)
        return jsonify({'message': 'Buy order executed'})
    except Exception as e:
        return jsonify({'message': str(e)}), 400


@app.route('/api/portfolios/<int:portfolio_id>/sell', methods=['POST'])
@token_required
def sell_stock(current_user, portfolio_id):
    portfolio = load_portfolio(current_user, portfolio_id)
    if not portfolio:
        return jsonify({'message': 'Portfolio not found'}), 404

    data = request.get_json()
    try:
        portfolio.sell_stock(
            data['symbol'],
            int(data['quantity']),
            price=float(data.get('price')) if data.get('price') else None,
            live=data.get('live', True)
        )
        save_portfolio(current_user, portfolio)
        return jsonify({'message': 'Sell order executed'})
    except Exception as e:
        return jsonify({'message': str(e)}), 400


# Portfolio Views
@app.route('/api/portfolios/<int:portfolio_id>/view', methods=['GET'])
@token_required
def view_portfolio(current_user, portfolio_id):
    portfolio = load_portfolio(current_user, portfolio_id)
    if not portfolio:
        return jsonify({'message': 'Portfolio not found'}), 404

    portfolio.view_portfolio()
    # Since view_portfolio() prints to console, we'll return the portfolio data
    details = get_portfolio_details(portfolio_id)
    return jsonify(details)


# Watchlist Routes
@app.route('/api/watchlists', methods=['GET', 'POST'])
@token_required
def watchlists(current_user):
    if request.method == 'GET':
        watchlists_data = get_user_watchlists(current_user)
        return jsonify(watchlists_data)

    elif request.method == 'POST':
        data = request.get_json()
        watchlist = Watchlist(data['name'])
        for symbol in data.get('symbols', []):
            watchlist.add_to_watchlist(symbol)
        success = save_watchlist(current_user, watchlist)
        if success:
            return jsonify({'message': 'Watchlist created'}), 201
        return jsonify({'message': 'Error creating watchlist'}), 500


@app.route('/api/watchlists/<int:watchlist_id>', methods=['GET', 'PUT', 'DELETE'])
@token_required
def watchlist(current_user, watchlist_id):
    watchlist = load_watchlist(current_user, watchlist_id)
    if not watchlist:
        return jsonify({'message': 'Watchlist not found'}), 404

    if request.method == 'GET':
        details = get_watchlist_details(watchlist_id)
        return jsonify(details)

    elif request.method == 'PUT':
        data = request.get_json()
        if 'name' in data:
            watchlist.name = data['name']
        # Add/remove symbols as needed
        success = save_watchlist(current_user, watchlist)
        if success:
            return jsonify({'message': 'Watchlist updated'})
        return jsonify({'message': 'Error updating watchlist'}), 500

    elif request.method == 'DELETE':
        success = delete_watchlist(current_user, watchlist_id)
        if success:
            return jsonify({'message': 'Watchlist deleted'})
        return jsonify({'message': 'Error'}), 501


# Watchlist Operations
@app.route('/api/watchlists/<int:watchlist_id>/add', methods=['POST'])
@token_required
def add_to_watchlist(current_user, watchlist_id):
    watchlist = load_watchlist(current_user, watchlist_id)
    if not watchlist:
        return jsonify({'message': 'Watchlist not found'}), 404

    data = request.get_json()
    watchlist.add_to_watchlist(data['symbol'], data.get('notes', ''))
    success = save_watchlist(current_user, watchlist)
    if success:
        return jsonify({'message': 'Symbol added to watchlist'})
    return jsonify({'message': 'Error updating watchlist'}), 500


@app.route('/api/watchlists/<int:watchlist_id>/remove', methods=['POST'])
@token_required
def remove_from_watchlist(current_user, watchlist_id):
    watchlist = load_watchlist(current_user, watchlist_id)
    if not watchlist:
        return jsonify({'message': 'Watchlist not found'}), 404

    data = request.get_json()
    watchlist.remove_from_watchlist(data['symbol'])
    success = save_watchlist(current_user, watchlist)
    if success:
        return jsonify({'message': 'Symbol removed from watchlist'})
    return jsonify({'message': 'Error updating watchlist'}), 500


@app.route('/api/custom-strategies', methods=['GET', 'POST'])
@token_required
def custom_strategies(current_user):
    from q9 import CustomStrategyManager
    custom_strategy_manager = CustomStrategyManager()

    if request.method == 'GET':
        # Get all custom strategies for the user
        result = custom_strategy_manager.list_custom_strategies_json(current_user)
        if result['hasStrategies'] == 'True':
            return jsonify(result)
        return jsonify({'hasStrategies': 'False', 'message': result['data'][0] if result['data'] else 'No custom strategies found'}), 200

    elif request.method == 'POST':
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['portfolio_id', 'name', 'symbol', 'algorithm_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'hasStrategies': 'False', 'message': f'Missing required field: {field}'}), 400
        
        # Validate that the custom algorithm exists and belongs to user
        manager = get_algorithm_manager()
        algorithm_data = manager.get_algorithm(data['algorithm_id'], str(current_user))
        if not algorithm_data:
            return jsonify({'hasStrategies': 'False', 'message': 'Custom algorithm not found'}), 404
        
        # Create parameters with algorithm_id
        parameters = data.get('parameters', {})
        parameters['algorithm_id'] = data['algorithm_id']
        
        success, message = custom_strategy_manager.create_custom_strategy(
            current_user,
            data['portfolio_id'],
            data['name'],
            data['symbol'],
            data['algorithm_id'],
            parameters
        )
        
        if success:
            # Return updated strategy list after creation
            return jsonify(custom_strategy_manager.list_custom_strategies_json(current_user)), 201
        return jsonify({'hasStrategies': 'False', 'message': message}), 400


@app.route('/api/custom-strategies/<int:strategy_id>', methods=['GET', 'PUT', 'DELETE'])
@token_required
def custom_strategy(current_user, strategy_id):
    from q9 import CustomStrategyManager
    custom_strategy_manager = CustomStrategyManager()

    if request.method == 'GET':
        # Return the specific custom strategy
        strategy = custom_strategy_manager.get_custom_strategy(current_user, strategy_id)
        if not strategy:
            return jsonify({'hasStrategies': 'False', 'message': 'Custom strategy not found'}), 404
        return jsonify({'hasStrategies': 'True', 'data': strategy})

    elif request.method == 'PUT':
        # Update custom strategy (delete and recreate)
        data = request.get_json()
        current_strategy = custom_strategy_manager.get_custom_strategy(current_user, strategy_id)
        if not current_strategy:
            return jsonify({'hasStrategies': 'False', 'message': 'Custom strategy not found'}), 404

        # Delete old strategy
        success, message = custom_strategy_manager.delete_custom_strategy(current_user, strategy_id)
        if not success:
            return jsonify({'hasStrategies': 'False', 'message': message}), 400

        # Validate algorithm if provided
        algorithm_id = data.get('algorithm_id', current_strategy['algorithm_id'])
        if algorithm_id:
            manager = get_algorithm_manager()
            algorithm_data = manager.get_algorithm(algorithm_id, str(current_user))
            if not algorithm_data:
                return jsonify({'hasStrategies': 'False', 'message': 'Custom algorithm not found'}), 404

        # Create parameters
        parameters = data.get('parameters', current_strategy.get('parameters', {}))
        if isinstance(parameters, str):
            parameters = json.loads(parameters)
        parameters['algorithm_id'] = algorithm_id

        success, message = custom_strategy_manager.create_custom_strategy(
            current_user,
            current_strategy['portfolio_id'],
            data.get('name', current_strategy['name']),
            data.get('symbol', current_strategy['symbol']),
            algorithm_id,
            parameters
        )
        
        if success:
            return jsonify(custom_strategy_manager.list_custom_strategies_json(current_user))
        return jsonify({'hasStrategies': 'False', 'message': message}), 400

    elif request.method == 'DELETE':
        success, message = custom_strategy_manager.delete_custom_strategy(current_user, strategy_id)
        if success:
            return jsonify(custom_strategy_manager.list_custom_strategies_json(current_user))
        return jsonify({'hasStrategies': 'False', 'message': message}), 400


@app.route('/api/custom-strategies/<int:strategy_id>/toggle', methods=['POST'])
@token_required
def toggle_custom_strategy(current_user, strategy_id):
    from q9 import CustomStrategyManager
    custom_strategy_manager = CustomStrategyManager()
    data = request.get_json()
    active = data.get('is_active', False)
    
    success, message = custom_strategy_manager.toggle_custom_strategy(current_user, strategy_id, active)
    if success:
        return jsonify(custom_strategy_manager.list_custom_strategies_json(current_user))
    return jsonify({'hasStrategies': 'False', 'message': message}), 400
@app.route('/api/strategies', methods=['GET', 'POST'])
@token_required
def strategies(current_user):
    strategy_manager = StrategyManager()

    if request.method == 'GET':
        # Use the list_strategies_json method that returns consistent format
        result = strategy_manager.list_strategies_json(current_user)
        if result['hasStrategies'] == 'True':
            return jsonify(result)
        return jsonify({'hasStrategies': 'False', 'message': result['data'][0]}), 400

    elif request.method == 'POST':
        data = request.get_json()
        
        # Handle custom algorithm integration
        algorithm_id = data.get('algorithm_id')
        if data.get('strategy_type') == 'CUSTOM' and algorithm_id:
            # Validate that the custom algorithm exists and belongs to user
            manager = get_algorithm_manager()
            algorithm_data = manager.get_algorithm(algorithm_id, str(current_user))
            if not algorithm_data:
                return jsonify({'hasStrategies': 'False', 'message': 'Custom algorithm not found'}), 404
            
            # Add algorithm_id to parameters for later reference
            parameters = data.get('parameters', {})
            parameters['algorithm_id'] = algorithm_id
            data['parameters'] = parameters
        
        success, message = strategy_manager.create_strategy(
            current_user,
            data['portfolio_id'],
            data['name'],
            data['symbol'],
            data['strategy_type'],
            data['parameters']
        )
        if success:
            # Return updated strategy list after creation
            return jsonify(strategy_manager.list_strategies_json(current_user)), 201
        return jsonify({'hasStrategies': 'False', 'message': message}), 400


@app.route('/api/strategies/<int:strategy_id>', methods=['GET', 'PUT', 'DELETE'])
@token_required
def strategy(current_user, strategy_id):
    strategy_manager = StrategyManager()

    if request.method == 'GET':
        # Return the specific strategy from the list
        result = strategy_manager.list_strategies_json(current_user)
        if result['hasStrategies'] == 'False':
            return jsonify(result), 400
        
        strategy = next((s for s in result['data'] if s['id'] == strategy_id), None)
        if not strategy:
            return jsonify({'hasStrategies': 'False', 'message': 'Strategy not found'}), 404
        return jsonify({'hasStrategies': 'True', 'data': strategy})

    elif request.method == 'PUT':
        data = request.get_json()
        current_list = strategy_manager.list_strategies_json(current_user)
        if current_list['hasStrategies'] == 'False':
            return jsonify(current_list), 400
        
        current_strategy = next((s for s in current_list['data'] if s['id'] == strategy_id), None)
        if not current_strategy:
            return jsonify({'hasStrategies': 'False', 'message': 'Strategy not found'}), 404

        # Update strategy (delete and recreate as before)
        success, message = strategy_manager.delete_strategy(current_user, strategy_id)
        if not success:
            return jsonify({'hasStrategies': 'False', 'message': message}), 400

        # Handle custom algorithm integration for updates
        algorithm_id = data.get('algorithm_id')
        if data.get('strategy_type') == 'CUSTOM' and algorithm_id:
            # Validate that the custom algorithm exists and belongs to user
            manager = get_algorithm_manager()
            algorithm_data = manager.get_algorithm(algorithm_id, str(current_user))
            if not algorithm_data:
                return jsonify({'hasStrategies': 'False', 'message': 'Custom algorithm not found'}), 404
            
            # Add algorithm_id to parameters for later reference
            parameters = data.get('parameters', current_strategy['parameters'])
            if isinstance(parameters, str):
                parameters = json.loads(parameters)
            parameters['algorithm_id'] = algorithm_id
            data['parameters'] = parameters
        
        success, message = strategy_manager.create_strategy(
            current_user,
            current_strategy['portfolio_id'],
            data.get('name', current_strategy['name']),
            data.get('symbol', current_strategy['symbol']),
            data.get('strategy_type', current_strategy['strategy_type']),
            data.get('parameters', current_strategy['parameters'])
        )
        if success:
            # Return updated list after modification
            return jsonify(strategy_manager.list_strategies_json(current_user))
        return jsonify({'hasStrategies': 'False', 'message': message}), 400

    elif request.method == 'DELETE':
        success, message = strategy_manager.delete_strategy(current_user, strategy_id)
        if success:
            # Return updated list after deletion
            return jsonify(strategy_manager.list_strategies_json(current_user))
        return jsonify({'hasStrategies': 'False', 'message': message}), 400


@app.route('/api/strategies/<int:strategy_id>/toggle', methods=['POST'])
@token_required
def toggle_strategy(current_user, strategy_id):
    strategy_manager = StrategyManager()
    data = request.get_json()
    active = data.get('is_active', False)
    
    success, message = strategy_manager.toggle_strategy(current_user, strategy_id, active)
    if success:
        # Return updated list after toggle
        return jsonify(strategy_manager.list_strategies_json(current_user))
    return jsonify({'hasStrategies': 'False', 'message': message}), 400


# Market Data Routes
@app.route('/api/market/price/<symbol>', methods=['GET'])
@token_required
def get_price(current_user, symbol):
    price = get_stock_price(symbol, live=True)
    if price is None:
        return jsonify({'message': 'Could not fetch price'}), 404
    return jsonify({'symbol': symbol, 'price': price})
    
@app.route('/api/market/price2/<symbol>', methods=['GET'])
def get_price2(symbol):
    price = get_stock_price(symbol, live=True)
    if price is None:
        return jsonify({'message': 'Could not fetch price'}), 404
    return jsonify({'symbol': symbol, 'price': price})


@app.route('/api/market/historical/<symbol>/<date>', methods=['GET'])
def get_historical_priceFlask(symbol, date):
    price = get_historical_price(symbol, date)
    if price is None:
        return jsonify({'message': 'Could not fetch historical price'}), 404
    return jsonify({'symbol': symbol, 'date': date, 'price': price})
    return price


@app.route('/api/strategyCRON87w782w')
def strategy_CRON():
    executor = StrategyExecutor()
    result1=executor.execute_all_strategies()
    return jsonify(result1)


# Advice Routes
@app.route('/api/advice/<symbol>', methods=['GET'])
def get_advice(symbol):
    try:
        advice_data = generate_advice_sheet(symbol)
        if 'error' in advice_data:
            return jsonify(advice_data), 404
        return jsonify(advice_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
import threading
import json
import os
from datetime import datetime, timedelta

# Dictionary to store interpreter instances per user session
# Use threading.Lock to ensure thread safety
user_interpreters = {}
interpreters_lock = threading.Lock()

# Directory to store interpreter state files
terminal_state_dir = 'terminal_state'
if not os.path.exists(terminal_state_dir):
    os.makedirs(terminal_state_dir)

def save_interpreter_state(interpreter, session_key):
    """Save only the essential state data of the interpreter to a JSON file"""
    try:
        state_file = os.path.join(terminal_state_dir, f"{session_key}_state.json")
        state_data = {
            'current_portfolio': None,
            'current_watchlist': None,
            'user_id': getattr(interpreter, 'user_id', None)
        }
        
        # Save portfolio state if it exists
        if interpreter.current_portfolio:
            portfolio_data = {
                'name': getattr(interpreter.current_portfolio, 'name', None),
                'portfolio': getattr(interpreter.current_portfolio, 'portfolio', {}),
                'db_id': getattr(interpreter.current_portfolio, 'db_id', None),
                'user_id': getattr(interpreter.current_portfolio, 'user_id', None)
            }
            state_data['current_portfolio'] = portfolio_data
        
        # Save watchlist state if it exists
        if interpreter.current_watchlist:
            watchlist_data = {
                'name': getattr(interpreter.current_watchlist, 'name', None),
                'watchlist': getattr(interpreter.current_watchlist, 'watchlist', {}),
                'db_id': getattr(interpreter.current_watchlist, 'db_id', None),
                'user_id': getattr(interpreter.current_watchlist, 'user_id', None)
            }
            state_data['current_watchlist'] = watchlist_data
        
        with open(state_file, 'w') as f:
            json.dump(state_data, f, default=str)
        print(f"DEBUG: Saved interpreter state to file for session {session_key}")
    except Exception as e:
        print(f"DEBUG: Failed to save interpreter state to file: {e}")

def load_interpreter_state(session_key, current_user):
    """Load the interpreter state from JSON file and create a new interpreter with that state"""
    try:
        state_file = os.path.join(terminal_state_dir, f"{session_key}_state.json")
        if not os.path.exists(state_file):
            return QuarkScriptInterpreter(current_user)
        
        with open(state_file, 'r') as f:
            state_data = json.load(f)
        
        # Create new interpreter
        interpreter = QuarkScriptInterpreter(current_user)
        
        # Restore portfolio if it exists in state
        if state_data.get('current_portfolio'):
            portfolio_data = state_data['current_portfolio']
            # Create a new portfolio object and set its attributes
            from q9 import Simulation
            portfolio_obj = Simulation(portfolio_data.get('name', 'Restored Portfolio'), 0)  # Initial cash will be overridden
            portfolio_obj.portfolio = portfolio_data.get('portfolio', {})
            portfolio_obj.db_id = portfolio_data.get('db_id')
            portfolio_obj.user_id = portfolio_data.get('user_id', current_user)
            interpreter.current_portfolio = portfolio_obj
        
        # Restore watchlist if it exists in state
        if state_data.get('current_watchlist'):
            watchlist_data = state_data['current_watchlist']
            # Create a new watchlist object and set its attributes
            from q9 import Watchlist
            watchlist_obj = Watchlist(watchlist_data.get('name', 'Restored Watchlist'), current_user)
            watchlist_obj.watchlist = watchlist_data.get('watchlist', {})
            watchlist_obj.db_id = watchlist_data.get('db_id')
            watchlist_obj.user_id = watchlist_data.get('user_id', current_user)
            interpreter.current_watchlist = watchlist_obj
        
        print(f"DEBUG: Loaded interpreter state from file for session {session_key}")
        return interpreter
    except Exception as e:
        print(f"DEBUG: Failed to load interpreter state from file: {e}")
        # Return fresh interpreter if loading fails
        return QuarkScriptInterpreter(current_user)

@app.route('/api/terminal', methods=['POST'])
@token_required
def terminal(current_user):
    data = request.get_json()
    command = data.get('command')
    
    if not command:
        return jsonify({'error': 'No command provided'}), 400

    # Create a unique key for the user session
    user_id = current_user.id if hasattr(current_user, 'id') else current_user
    session_key = f"terminal_{user_id}"
    
    with interpreters_lock:
        print(f"DEBUG: Available sessions: {list(user_interpreters.keys())}")
        
        # Load from file if not in memory
        if session_key not in user_interpreters:
            user_interpreters[session_key] = load_interpreter_state(session_key, current_user)
        
        interpreter = user_interpreters[session_key]
        print(f"DEBUG: Before execution - current_portfolio: {interpreter.current_portfolio}, current_watchlist: {interpreter.current_watchlist}")
        success, result = interpreter.execute(command)
        print(f"DEBUG: After execution - current_portfolio: {interpreter.current_portfolio}, current_watchlist: {interpreter.current_watchlist}")
        
        # Save interpreter state to file
        save_interpreter_state(interpreter, session_key)
    
    return jsonify({
        'success': success,
        'result': result
    })
    
@app.route('/api/terminal_bot', methods=['POST'])
def terminal_bot():
    data = request.get_json()
    command = data.get('command')
    discord_id = data.get('discord_user_id')
    current_user= get_user_id_by_discord_id(discord_id)
    
    if not command:
        return jsonify({'error': 'No command provided'}), 400
    
    if not current_user:
        return jsonify({'error': 'Not verified'}), 400

    # Create a unique key for the user session
    user_id = current_user.id if hasattr(current_user, 'id') else current_user
    session_key = f"terminal_{user_id}"
    
    with interpreters_lock:
        # Load from file if not in memory
        if session_key not in user_interpreters:
            user_interpreters[session_key] = load_interpreter_state(session_key, current_user)
        
        interpreter = user_interpreters[session_key]
        print(f"DEBUG: Before execution - current_portfolio: {interpreter.current_portfolio}, current_watchlist: {interpreter.current_watchlist}")
        success, result = interpreter.execute(command)
        print(f"DEBUG: After execution - current_portfolio: {interpreter.current_portfolio}, current_watchlist: {interpreter.current_watchlist}")
        
        # Save interpreter state to file
        save_interpreter_state(interpreter, session_key)
    
    return jsonify({
        'success': success,
        'result': result
    })
    
# Backtest Routes
@app.route('/api/backtest', methods=['POST'])
@token_required
def run_backtest(current_user):
    data = request.get_json()
    portfolio = Simulation(data.get('name', 'Backtest'), data.get('initial_cash', 100000))

    try:
        strategy_type = data['strategy_type']
        if strategy_type == 'MOMENTUM':
            results = portfolio.run_backtest(
                strategy=portfolio.momentum_strategy,
                symbol=data['symbol'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                lookback_days=data.get('lookback_days', 14),
                threshold=data.get('threshold', 0.05)
            )
        elif strategy_type == 'BOLLINGER':
            results = portfolio.run_backtest(
                strategy=portfolio.bollinger_bands_strategy,
                symbol=data['symbol'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                window=data.get('window', 20),
                num_std=data.get('num_std', 2)
            )
        elif strategy_type == 'MACROSS':
            results = portfolio.run_backtest(
                strategy=portfolio.moving_average_crossover,
                symbol=data['symbol'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                short_window=data.get('short_window', 50),
                long_window=data.get('long_window', 200)
            )
        elif strategy_type == 'RSI':
            results = portfolio.run_backtest(
                strategy=portfolio.rsi_strategy,
                symbol=data['symbol'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                rsi_window=data.get('rsi_window', 14),
                overbought=data.get('overbought', 70),
                oversold=data.get('oversold', 30)
            )
        elif strategy_type == 'MACD':
            results = portfolio.run_backtest(
                strategy=portfolio.macd_strategy,
                symbol=data['symbol'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                fast=data.get('fast', 12),
                slow=data.get('slow', 26),
                signal=data.get('signal', 9)
            )
        elif strategy_type == 'MEANREVERSION':
            results = portfolio.run_backtest(
                strategy=portfolio.mean_reversion_strategy,
                symbol=data['symbol'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                window=data.get('window', 20),
                z_threshold=data.get('z_threshold', 2)
            )
        elif strategy_type == 'BREAKOUT':
            results = portfolio.run_backtest(
                strategy=portfolio.breakout_strategy,
                symbol=data['symbol'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                window=data.get('window', 20),
                multiplier=data.get('multiplier', 1.01)
            )
        elif strategy_type == 'VOLUMESPIKE':
            results = portfolio.run_backtest(
                strategy=portfolio.volume_spike_strategy,
                symbol=data['symbol'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                window=data.get('window', 20),
                multiplier=data.get('multiplier', 2.5)
            )
        elif strategy_type == 'KELTNER':
            results = portfolio.run_backtest(
                strategy=portfolio.keltner_channels_strategy,
                symbol=data['symbol'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                window=data.get('window', 20),
                atr_multiplier=data.get('atr_multiplier', 2)
            )
        elif strategy_type == 'STOCHASTIC':
            results = portfolio.run_backtest(
                strategy=portfolio.stochastic_oscillator_strategy,
                symbol=data['symbol'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                k_window=data.get('k_window', 14),
                d_window=data.get('d_window', 3),
                overbought=data.get('overbought', 80),
                oversold=data.get('oversold', 20)
            )
        elif strategy_type == 'PARABOLICSAR':
            results = portfolio.run_backtest(
                strategy=portfolio.parabolic_sar_strategy,
                symbol=data['symbol'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                acceleration=data.get('acceleration', 0.02),
                maximum=data.get('maximum', 0.2)
            )
        elif strategy_type == 'BUYHOLD':
            results = portfolio.run_backtest(
                strategy=portfolio.buy_and_hold,
                symbol=data['symbol'],
                start_date=data['start_date'],
                end_date=data['end_date']
            )
                    
        else:
            return jsonify({'message': 'Invalid strategy type'}), 400
        
        save_portfolio(current_user, portfolio)

        return jsonify(results)
    except Exception as e:
        return jsonify({'message': str(e)}), 400

#################### NEW UPDATEEEEE ##################

def read_sector_performance_data() -> Dict[str, Any]:
    """Reads cached sector performance data from files"""
    periods = {
        "1_day": 1/30,
        "3_days": 3/30,
        "7_days": 7/30,
        "1_month": 1,
        "6_months": 6
    }
    
    data_dir = "sector_data"
    result = {}
    
    for period_key in periods.keys():
        file_path = os.path.join(data_dir, f"{period_key}.json")
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    result[period_key] = json.load(f)
            else:
                result[period_key] = {}
        except Exception as e:
            print(f"Error reading {period_key} data: {str(e)}")
            result[period_key] = {}
    
    return result

@app.route('/api/market/sector-performance', methods=['GET'])
def get_sector_performance():
    try:
        time_window_months = int(request.args.get('time_window_months', 6))
        visualize = request.args.get('visualize', 'false').lower() == 'true'
        #all_periods = request.args.get('all_periods', 'false').lower() == 'true'
        all_periods=True
        if all_periods:
            results = read_sector_performance_data()
            return jsonify({
                'status': 'success',
                'data': results,
                'visualization_path': '/sector_analysis_plots/' if visualize else None
            })
        else:
            # For single period, we still need to generate it on demand
            # (or you could modify to read from cache if you prefer)
            results = run_sector_analysis(time_window_months=time_window_months, visualize=visualize)
            return jsonify({
                'status': 'success',
                'data': results,
                'visualization_path': '/sector_analysis_plots/' if visualize else None
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def read_forecast_data() -> Dict[str, Any]:
    """Reads the latest forecast data from file"""
    forecast_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forecast_cache")
    result = {}
    
    forecast_files = sorted([
        f for f in os.listdir(forecast_dir) 
        if f.startswith("forecast_") and f.endswith(".json")
    ], reverse=True)
    
    if forecast_files:
        latest_file = os.path.join(forecast_dir, forecast_files[0])
        try:
            with open(latest_file, 'r') as f:
                result = json.load(f)
        except Exception as e:
            print(f"Error reading forecast data: {str(e)}")
    
    return result

@app.route('/api/forecast-trends', methods=['GET'])
def get_forecast_trends():
    try:
        forecast_data = read_forecast_data()
        return jsonify(forecast_data)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

####

@app.route('/api/internal/generate-sector-performance', methods=['POST','GET'])
def generate_sector_performance():
    """Endpoint to generate and save all sector performance data (to be called by CRON)"""
    #try:
        # Define time periods (same as before)
    periods = {
        "1_day": 1/30,
        "3_days": 3/30,
        "7_days": 7/30,
        "1_month": 1,
        "6_months": 6
    }
    
    data_dir = "sector_data"
    os.makedirs(data_dir, exist_ok=True)
    
    for period_key, time_value in periods.items():
        try:
            data = run_sector_analysis(time_window_months=time_value, visualize=False)
            file_path = os.path.join(data_dir, f"{period_key}.json")
            with open(file_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error generating {period_key} data: {str(e)}")
            continue
        
#        return jsonify({'status': 'success', 'message': 'Sector performance data updated'})
    
#    except Exception as e:
#        return jsonify({'status': 'error', 'message': str(e)}), 500
        


@app.route('/api/internal/generate-forecast-trends', methods=['POST','GET'])
def generate_forecast_trends():
    """Endpoint to generate and save forecast data (to be called by CRON)"""
    try:
        forecast_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forecast_cache")
        os.makedirs(forecast_dir, exist_ok=True)
        
        new_data = forecast_stock_trends()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(forecast_dir, f"forecast_{timestamp}.json")
        
        with open(file_path, 'w') as f:
            json.dump(new_data, f)
        
        # Keep only the latest 3 forecast files
        forecast_files = sorted([
            f for f in os.listdir(forecast_dir) 
            if f.startswith("forecast_") and f.endswith(".json")
        ], reverse=True)
        
        for old_file in forecast_files[3:]:
            try:
                os.remove(os.path.join(forecast_dir, old_file))
            except Exception as e:
                print(f"Error cleaning up old forecast file {old_file}: {str(e)}")
        
        return jsonify({'status': 'success', 'message': 'Forecast data updated'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
        


@app.route('/dbchanges_x73')
def db_changes():
    conn = sqlite3.connect('trading_system.db')
    c = conn.cursor()
    # Create temp table with new schema
    """
    c.execute('''CREATE TABLE strategies_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    portfolio_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy_type TEXT NOT NULL CHECK(strategy_type IN (
                        'MOMENTUM', 'BOLLINGER', 'MACROSS', 'RSI', 'MACD', 
                        'MEANREVERSION', 'BREAKOUT', 'VOLUMESPIKE', 'KELTNER',
                        'STOCHASTIC', 'PARABOLICSAR', 'BUYHOLD', 'QUARKS'
                    )),
                    parameters TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_executed TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(portfolio_id) REFERENCES portfolios(id)
                )''')
    """
    
    # Drop old table
    c.execute('''CREATE TABLE IF NOT EXISTS discord_users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  user_id INTEGER NOT NULL,
                  discord_id TEXT NOT NULL,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')

    
    return 'worked ig'

@app.route('/api/algorithms/for-strategies', methods=['GET'])
@token_required
def get_algorithms_for_strategies(current_user: int):
    """Get algorithms formatted for strategy dropdown selection"""
    try:
        manager = get_algorithm_manager()
        algorithms = manager.get_user_algorithms(str(current_user))
        
        # Format algorithms specifically for strategy selection
        formatted_algorithms = []
        for algo in algorithms:
            formatted_algorithms.append({
                'id': algo['id'],
                'name': algo['name'],
                'description': algo.get('description', ''),
                'created_date': algo.get('created_date'),
                'updated_date': algo.get('updated_date')
            })
        
        return jsonify({
            'success': True,
            'algorithms': formatted_algorithms
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Get all user algorithms
@app.route('/api/algorithms', methods=['GET'])
@token_required
def get_user_algorithms(current_user: int):
    """Get all custom algorithms for the current user"""
    try:
        manager = get_algorithm_manager()
        algorithms = manager.get_user_algorithms(str(current_user))
        # Convert NumPy types to native Python types for JSON serialization
        algorithms = convert_numpy_types(algorithms)
        return jsonify({
            'success': True,
            'algorithms': algorithms,
            'count': len(algorithms)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Create new custom algorithm
@app.route('/api/algorithms', methods=['POST'])
@token_required
def create_custom_algorithm(current_user: int):
    """Create a new custom algorithm"""
    try:
        manager = get_algorithm_manager()
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'Algorithm name is required'}), 400
        
        algorithm_id = manager.save_algorithm(str(current_user), data)
        
        return jsonify({
            'success': True,
            'algorithm_id': algorithm_id,
            'message': 'Algorithm created successfully'
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Get specific algorithm
@app.route('/api/algorithms/<algorithm_id>', methods=['GET'])
@token_required
def get_algorithm(current_user: int, algorithm_id: str):
    """Get a specific algorithm by ID"""
    try:
        manager = get_algorithm_manager()
            
        algorithm_data = manager.get_algorithm(algorithm_id, str(current_user))
        
        if not algorithm_data:
            return jsonify({
                'success': False,
                'error': 'Algorithm not found'
            }), 404
        
        # Convert NumPy types to native Python types for JSON serialization
        algorithm_data = convert_numpy_types(algorithm_data)
        
        return jsonify({
            'success': True,
            'algorithm': algorithm_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Update algorithm
@app.route('/api/algorithms/<algorithm_id>', methods=['PUT'])
@token_required
def update_algorithm(current_user: int, algorithm_id: str):
    """Update an existing algorithm"""
    try:
        manager = get_algorithm_manager()
            
        data = request.get_json()
        data['id'] = algorithm_id  # Ensure ID is set
        
        # Verify algorithm belongs to user
        existing = manager.get_algorithm(algorithm_id, str(current_user))
        if not existing:
            return jsonify({
                'success': False,
                'error': 'Algorithm not found'
            }), 404
        
        manager.save_algorithm(str(current_user), data)
        
        return jsonify({
            'success': True,
            'message': 'Algorithm updated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Delete algorithm
@app.route('/api/algorithms/<algorithm_id>', methods=['DELETE'])
@token_required
def delete_algorithm(current_user: int, algorithm_id: str):
    """Delete an algorithm"""
    try:
        manager = get_algorithm_manager()
            
        success = manager.delete_algorithm(algorithm_id, str(current_user))
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Algorithm deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Algorithm not found or could not be deleted'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/algorithms/templates', methods=['GET'])
@token_required
def get_algorithm_templates(current_user: int):
    """Get predefined algorithm templates"""
    try:
        # Define available templates - INCLUDING BOTH OLD AND NEW
        templates = {
            # ========== OLD TEMPLATES (Keep these) ==========
            'rsi_strategy': {
                'name': 'RSI Strategy Template',
                'description': 'Simple RSI-based buy/sell strategy',
                'category': 'Basic',
                'config': {
                    'name': 'RSI Strategy',
                    'description': 'Buy when RSI < 30, sell when RSI > 70',
                    'buy_rules': [{
                        'id': 'rsi_buy_rule',
                        'name': 'RSI Oversold',
                        'signal_type': 'BUY',
                        'conditions': [{
                            'id': 'rsi_oversold',
                            'indicator_type': 'RSI',
                            'indicator_params': {'period': 14},
                            'comparison': '<',
                            'value': 30
                        }],
                        'logic_operator': 'AND'
                    }],
                    'sell_rules': [{
                        'id': 'rsi_sell_rule',
                        'name': 'RSI Overbought',
                        'signal_type': 'SELL',
                        'conditions': [{
                            'id': 'rsi_overbought',
                            'indicator_type': 'RSI',
                            'indicator_params': {'period': 14},
                            'comparison': '>',
                            'value': 70
                        }],
                        'logic_operator': 'AND'
                    }]
                }
            },
            'multi_strategy': {
                'name': 'Multi-Strategy Template',
                'description': 'Combines multiple indicators for decision making',
                'category': 'Basic',
                'config': {
                    'name': 'Multi-Strategy Algorithm',
                    'description': 'Combines RSI and other indicators',
                    'buy_rules': [{
                        'id': 'multi_buy_rule',
                        'name': 'Multi-Indicator Buy',
                        'signal_type': 'BUY',
                        'conditions': [
                            {
                                'id': 'rsi_oversold',
                                'indicator_type': 'RSI',
                                'indicator_params': {'period': 14},
                                'comparison': '<',
                                'value': 35
                            },
                            {
                                'id': 'macd_bullish',
                                'indicator_type': 'MACD',
                                'indicator_params': {'fast': 12, 'slow': 26, 'signal': 9, 'component': 'histogram'},
                                'comparison': '>',
                                'value': 0
                            }
                        ],
                        'logic_operator': 'AND'
                    }],
                    'sell_rules': [{
                        'id': 'multi_sell_rule',
                        'name': 'Multi-Indicator Sell',
                        'signal_type': 'SELL',
                        'conditions': [
                            {
                                'id': 'rsi_overbought',
                                'indicator_type': 'RSI',
                                'indicator_params': {'period': 14},
                                'comparison': '>',
                                'value': 65
                            }
                        ],
                        'logic_operator': 'OR'
                    }]
                }
            },
            
            # ========== NEW ADVANCED TEMPLATES ==========
            'quantum_momentum': {
                'name': 'Quantum Momentum Matrix',
                'description': 'Multi-timeframe momentum convergence with volume confirmation',
                'category': 'Momentum',
                'parameters': {
                    'macd_fast': {'type': 'int', 'default': 12, 'min': 5, 'max': 20, 'description': 'MACD fast period'},
                    'macd_slow': {'type': 'int', 'default': 26, 'min': 20, 'max': 35, 'description': 'MACD slow period'},
                    'rsi_period': {'type': 'int', 'default': 14, 'min': 7, 'max': 21, 'description': 'RSI period'},
                    'rsi_level': {'type': 'int', 'default': 55, 'min': 40, 'max': 65, 'description': 'RSI minimum level'},
                    'adx_level': {'type': 'int', 'default': 25, 'min': 20, 'max': 35, 'description': 'ADX trend strength minimum'},
                    'stop_loss_pct': {'type': 'float', 'default': 0.02, 'min': 0.01, 'max': 0.05, 'description': 'Stop loss percentage'},
                    'take_profit_pct': {'type': 'float', 'default': 0.06, 'min': 0.03, 'max': 0.1, 'description': 'Take profit percentage'}
                }
            },
            'alpha_convergence': {
                'name': 'Alpha Convergence System', 
                'description': 'Mean reversion + momentum hybrid for high-probability entries',
                'category': 'Mean Reversion',
                'parameters': {
                    'bb_period': {'type': 'int', 'default': 20, 'min': 14, 'max': 26, 'description': 'Bollinger Band period'},
                    'rsi_period': {'type': 'int', 'default': 14, 'min': 7, 'max': 21, 'description': 'RSI period'},
                    'oversold_level': {'type': 'int', 'default': 32, 'min': 25, 'max': 40, 'description': 'RSI oversold level'},
                    'target_level': {'type': 'int', 'default': 85, 'min': 70, 'max': 95, 'description': 'Bollinger Band target level'},
                    'stop_loss_pct': {'type': 'float', 'default': 0.015, 'min': 0.01, 'max': 0.04, 'description': 'Stop loss percentage'},
                    'take_profit_pct': {'type': 'float', 'default': 0.045, 'min': 0.02, 'max': 0.08, 'description': 'Take profit percentage'}
                }
            },
            'volatility_breakout': {
                'name': 'Volatility Breakout System',
                'description': 'Identifies low-volatility consolidation followed by high-volume breakouts',
                'category': 'Breakout',
                'parameters': {
                    'breakout_period': {'type': 'int', 'default': 20, 'min': 14, 'max': 30, 'description': 'Breakout lookback period'},
                    'consolidation_level': {'type': 'int', 'default': 40, 'min': 30, 'max': 60, 'description': 'Bollinger Band consolidation level'},
                    'stop_loss_pct': {'type': 'float', 'default': 0.01, 'min': 0.005, 'max': 0.03, 'description': 'Stop loss percentage'},
                    'take_profit_pct': {'type': 'float', 'default': 0.04, 'min': 0.02, 'max': 0.07, 'description': 'Take profit percentage'}
                }
            },
            'smart_money_flow': {
                'name': 'Smart Money Flow Strategy',
                'description': 'Follows institutional money flow using OBV, MFI, and large block trades',
                'category': 'Volume Analysis',
                'parameters': {
                    'mfi_period': {'type': 'int', 'default': 14, 'min': 10, 'max': 21, 'description': 'Money Flow Index period'},
                    'mfi_level': {'type': 'int', 'default': 60, 'min': 50, 'max': 70, 'description': 'MFI strength level'},
                    'stop_loss_pct': {'type': 'float', 'default': 0.018, 'min': 0.01, 'max': 0.04, 'description': 'Stop loss percentage'},
                    'take_profit_pct': {'type': 'float', 'default': 0.055, 'min': 0.03, 'max': 0.09, 'description': 'Take profit percentage'}
                }
            }
        }
        
        all_categories = list(set([t.get('category', 'Basic') for t in templates.values()]))
        # Make sure 'Basic' is always included
        if 'Basic' not in all_categories:
            all_categories.append('Basic')
        all_categories.sort()
        
        return jsonify({
            'success': True,
            'templates': templates,
            'total_templates': len(templates),
            'categories': all_categories
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/algorithms/<algorithm_id>/backtest', methods=['POST'])
@token_required
def backtest_custom_algorithm(current_user: int, algorithm_id: str):
    """Run backtest on a custom algorithm with real market data and optionally save as portfolio"""
    try:
        import sys
        import traceback
        
        print("=== BACKTEST REQUEST STARTED ===", file=sys.stderr)
        
        manager = get_algorithm_manager()
        data = request.get_json()
        
        # Validate required parameters
        required_fields = ['symbol', 'start_date', 'end_date']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # Get algorithm configuration
        algorithm_data = manager.get_algorithm(algorithm_id, str(current_user))
        if not algorithm_data:
            return jsonify({'success': False, 'error': 'Algorithm not found'}), 404
        
        ensure_numeric_values(algorithm_data['config'])
        # Create algorithm instance
        algorithm = CustomAlgorithm(algorithm_data['config'])
        
        # Get real market data
        symbol = data['symbol'].upper()
        start_date = data['start_date']
        end_date = data['end_date']
        initial_cash = data.get('initial_cash', 100000)
        save_as_portfolio = data.get('save_as_portfolio', False)
        portfolio_name = data.get('portfolio_name', f"{algorithm_data['config']['name']} - {symbol} Backtest")
        
        # Fetch real market data
        market_data = fetch_market_data(symbol, start_date, end_date)
        
        if len(market_data) < 50:
            return jsonify({'success': False, 'error': f'Insufficient data: only {len(market_data)} data points available'}), 400
        
        # --- CRITICAL FIXES FROM TEST SCRIPT ---
        # 1. Rename columns to match algorithm expectations
        market_data.rename(columns={
            'Open': 'OPEN',
            'High': 'HIGH', 
            'Low': 'LOW',
            'Close': 'CLOSE',
            'Volume': 'VOLUME'
        }, inplace=True)
        
        # 2. Handle timezone issues - SIMPLIFIED APPROACH
        print(f"Original DATE column type: {type(market_data['DATE'].iloc[0])}", file=sys.stderr)
        print(f"First date value: {market_data['DATE'].iloc[0]}", file=sys.stderr)
        
        # Convert to simple timezone-naive datetime (most reliable approach)
        market_data['DATE'] = pd.to_datetime(market_data['DATE'])
        
        # If dates have timezone info, remove it completely
        if hasattr(market_data['DATE'].iloc[0], 'tz') and market_data['DATE'].iloc[0].tz is not None:
            print("Dates have timezone info, converting to naive...", file=sys.stderr)
            market_data['DATE'] = market_data['DATE'].dt.tz_convert(None)
        
        print(f"Processed DATE column type: {type(market_data['DATE'].iloc[0])}", file=sys.stderr)
        print(f"First processed date value: {market_data['DATE'].iloc[0]}", file=sys.stderr)
        
        # 3. Set DATE as index for proper signal matching
        market_data = market_data.set_index('DATE')
        market_data.index.name = 'DATE'
        
        print(f"Prepared market data with columns: {market_data.columns.tolist()}", file=sys.stderr)
        print(f"Data index type: {type(market_data.index)}", file=sys.stderr)
        print(f"First few index values: {market_data.index[:3]}", file=sys.stderr)
        
        # Run backtest - let the algorithm handle its own logic
        try:
            backtest_results = algorithm.backtest(market_data, initial_cash)
        except KeyError as ke:
            if 'action' in str(ke):
                # Return a clear error about the algorithm issue
                return jsonify({
                    'success': False,
                    'error': 'Algorithm configuration error: Missing "action" key in trade data',
                    'details': 'The custom algorithm needs to be updated to include "action" key in trade records or fix the calculate_win_rate method',
                    'fix_suggestion': 'Update useralgo.py line 483 to handle missing action keys properly'
                }), 400
            else:
                # Re-raise other KeyErrors
                raise
        except Exception as e:
            # Handle other algorithm errors
            error_traceback = traceback.format_exc()
            print(f"Algorithm execution failed: {error_traceback}", file=sys.stderr)
            
            return jsonify({
                'success': False,
                'error': f'Algorithm execution failed: {str(e)}',
                'error_type': type(e).__name__,
                'details': error_traceback
            }), 400
        
        backtest_results = convert_numpy_types(backtest_results)
        
        # Create price history
        price_history = {}
        for date_val, row in market_data.iterrows():
            if isinstance(date_val, pd.Timestamp):
                formatted_date = date_val.strftime('%Y-%m-%d')
            elif isinstance(date_val, datetime):
                formatted_date = date_val.strftime('%Y-%m-%d')
            elif isinstance(date_val, np.datetime64):
                formatted_date = pd.to_datetime(date_val).strftime('%Y-%m-%d')
            elif isinstance(date_val, str):
                try:
                    parsed_date = pd.to_datetime(date_val)
                    formatted_date = parsed_date.strftime('%Y-%m-%d')
                except:
                    formatted_date = date_val
            else:
                formatted_date = str(date_val)
            
            price_history[formatted_date] = float(row['CLOSE'])
        
        # Process transactions - handle the data structure returned by the algorithm
        transactions = []
        if isinstance(backtest_results, dict) and 'trades' in backtest_results:
            transactions = backtest_results.get('trades', [])
        
        formatted_transactions = []
        
        for i, transaction in enumerate(transactions):
            try:
                # Extract transaction type - the algorithm should provide this
                transaction_type = 'UNKNOWN'
                if isinstance(transaction, dict):
                    # Try to get type from various possible keys
                    for key in ['type', 'action', 'signal', 'order_type']:
                        if key in transaction:
                            transaction_type = str(transaction[key]).upper()
                            break
                
                # Extract other fields with safe defaults
                timestamp = str(transaction.get('timestamp', transaction.get('date', ''))) if isinstance(transaction, dict) else ''
                price = float(transaction.get('price', transaction.get('close', 0))) if isinstance(transaction, dict) else 0.0
                quantity = int(transaction.get('quantity', transaction.get('shares', 0))) if isinstance(transaction, dict) else 0
                
                formatted_transaction = {
                    'date': timestamp.split(' ')[0] if timestamp else '',
                    'price': price,
                    'quantity': quantity,
                    'symbol': symbol,
                    'timestamp': timestamp,
                    'type': transaction_type
                }
                
                formatted_transactions.append(formatted_transaction)
                
            except Exception as trans_error:
                print(f"Error processing transaction {i}: {trans_error}", file=sys.stderr)
                continue
        
        # Calculate final values
        final_value = initial_cash
        if isinstance(backtest_results, dict):
            final_value = float(backtest_results.get('final_value', backtest_results.get('final_portfolio_value', initial_cash)))
        
        return_pct = (final_value - initial_cash) / initial_cash
        
        # Add performance metrics to response
        performance_metrics = {}
        if isinstance(backtest_results, dict):
            performance_metrics = {
                'total_return': backtest_results.get('total_return', 0),
                'annualized_return': backtest_results.get('annualized_return', 0),
                'volatility': backtest_results.get('volatility', 0),
                'sharpe_ratio': backtest_results.get('sharpe_ratio', 0),
                'sortino_ratio': backtest_results.get('sortino_ratio', 0),
                'max_drawdown': backtest_results.get('max_drawdown', 0),
                'win_rate': backtest_results.get('win_rate', 0),
                'profit_factor': backtest_results.get('profit_factor', 0),
                'total_trades': backtest_results.get('total_trades', 0)
            }
        
        # Create response
        main_result = {
            "final_value": final_value,
            "initial_cash": float(initial_cash),
            "price_history": price_history,
            "return": return_pct,
            "transactions": formatted_transactions,
            "performance_metrics": performance_metrics
        }
        
        # Save as portfolio if requested
        portfolio_id = None
        if save_as_portfolio:
            try:
                # Create a new portfolio with backtest results
                portfolio = Simulation(portfolio_name, float(initial_cash))
                
                # Apply all the transactions from the backtest
                for transaction in formatted_transactions:
                    if transaction['type'] == 'BUY':
                        portfolio.add_historical_transaction(
                            transaction['symbol'],
                            transaction['quantity'],
                            'BUY',
                            transaction['timestamp'],
                            price=transaction['price']
                        )
                    elif transaction['type'] == 'SELL':
                        portfolio.add_historical_transaction(
                            transaction['symbol'],
                            transaction['quantity'],
                            'SELL',
                            transaction['timestamp'],
                            price=transaction['price']
                        )
                
                # Update portfolio return and final value
                portfolio.portfolio['return'] = return_pct
                portfolio.portfolio['price_history'] = price_history
                
                # Add algorithm metadata to portfolio logs
                portfolio.logs.append(f"Portfolio created from algorithm backtest: {algorithm_data['config']['name']}")
                portfolio.logs.append(f"Symbol: {symbol}, Period: {start_date} to {end_date}")
                portfolio.logs.append(f"Algorithm ID: {algorithm_id}")
                
                # Save the portfolio
                success = save_portfolio(current_user, portfolio)
                if success:
                    portfolio_id = portfolio.db_id
                    main_result['portfolio_id'] = portfolio_id
                    print(f"Portfolio saved with ID: {portfolio_id}", file=sys.stderr)
                else:
                    print("Failed to save portfolio", file=sys.stderr)
                    
            except Exception as portfolio_error:
                print(f"Error saving portfolio: {portfolio_error}", file=sys.stderr)
                # Don't fail the entire request if portfolio save fails
                pass
        
        response_data = {
            'success': True,
            'result': main_result,
            'data_points': len(market_data),
            'symbol': symbol,
            'period': f"{start_date} to {end_date}"
        }
        
        if portfolio_id:
            response_data['portfolio_created'] = True
            response_data['portfolio_id'] = portfolio_id
            response_data['portfolio_name'] = portfolio_name
        
        return jsonify(response_data)
        
    except Exception as e:
        import sys
        import traceback
        
        print(f"CRITICAL ERROR: {type(e).__name__}: {str(e)}", file=sys.stderr)
        print(f"TRACEBACK: {traceback.format_exc()}", file=sys.stderr)
        
        return jsonify({
            'success': False,
            'error': f"Backtest failed: {str(e)}",
            'error_type': str(type(e).__name__)
        }), 500

@app.route('/api/algorithms/from-template', methods=['POST'])
@token_required
def create_from_template(current_user: int):
    """Create a new algorithm from a template"""
    try:
        manager = get_algorithm_manager()
        data = request.get_json()
        
        template_name = data.get('template_name')
        algorithm_name = data.get('name')
        
        if not template_name or not algorithm_name:
            return jsonify({
                'success': False,
                'error': 'Template name and algorithm name are required'
            }), 400
        
        # Get parameters with defaults
        params = data.get('parameters', {})
        
        # Map template names to factory functions (BOTH OLD AND NEW)
        template_factories = {
            # Old templates
            'rsi_strategy': lambda: create_rsi_oversold_algorithm(
                params.get('rsi_period', 14),
                params.get('oversold_level', 30),
                params.get('overbought_level', 70)
            ),
            'multi_strategy': lambda: create_multi_strategy_algorithm([
                {
                    'name': 'RSI Strategy',
                    'weight': 1.0,
                    'buy_conditions': [{
                        'id': 'rsi_oversold',
                        'indicator_type': 'RSI',
                        'indicator_params': {'period': params.get('rsi_period', 14)},
                        'comparison': '<',
                        'value': params.get('oversold_level', 30)
                    }],
                    'sell_conditions': [{
                        'id': 'rsi_overbought',
                        'indicator_type': 'RSI',
                        'indicator_params': {'period': params.get('rsi_period', 14)},
                        'comparison': '>',
                        'value': params.get('overbought_level', 70)
                    }]
                }
            ]),
            
            # New templates
            'quantum_momentum': lambda: create_quantum_momentum_matrix(
                macd_fast=params.get('macd_fast', 12),
                macd_slow=params.get('macd_slow', 26),
                macd_signal=params.get('macd_signal', 9),
                rsi_period=params.get('rsi_period', 14),
                rsi_level=params.get('rsi_level', 55),
                adx_period=params.get('adx_period', 14),
                adx_level=params.get('adx_level', 25),
                stop_loss=params.get('stop_loss_pct', 0.02),
                take_profit=params.get('take_profit_pct', 0.06),
                position_size=params.get('position_size', 0.12)
            ),
            'alpha_convergence': lambda: create_alpha_convergence_system(
                bb_period=params.get('bb_period', 20),
                bb_std=params.get('bb_std', 2),
                rsi_period=params.get('rsi_period', 14),
                oversold_level=params.get('oversold_level', 32),
                macd_fast=params.get('macd_fast', 12),
                macd_slow=params.get('macd_slow', 26),
                macd_signal=params.get('macd_signal', 9),
                target_level=params.get('target_level', 85),
                stop_loss=params.get('stop_loss_pct', 0.015),
                take_profit=params.get('take_profit_pct', 0.045),
                position_size=params.get('position_size', 0.15)
            ),
            'volatility_breakout': lambda: create_volatility_breakout_system(
                breakout_period=params.get('breakout_period', 20),
                consolidation_level=params.get('consolidation_level', 40),
                stop_loss=params.get('stop_loss_pct', 0.01),
                take_profit=params.get('take_profit_pct', 0.04),
                position_size=params.get('position_size', 0.18)
            ),
            'smart_money_flow': lambda: create_smart_money_flow(
                mfi_period=params.get('mfi_period', 14),
                mfi_level=params.get('mfi_level', 60),
                stop_loss=params.get('stop_loss_pct', 0.018),
                take_profit=params.get('take_profit_pct', 0.055),
                position_size=params.get('position_size', 0.1)
            )
        }
        
        # Map frontend template names to backend template names
        template_name_mapping = {
            'quantum_momentum_matrix': 'quantum_momentum',
            'alpha_convergence_system': 'alpha_convergence',
            'volatility_breakout_system': 'volatility_breakout',
            'smart_money_flow': 'smart_money_flow'
        }
        
        # Use mapped name if available, otherwise use original
        backend_template_name = template_name_mapping.get(template_name, template_name)
        
        if backend_template_name not in template_factories:
            return jsonify({
                'success': False,
                'error': f'Template "{template_name}" not found'
            }), 404
        
        # Call the appropriate factory function
        config = template_factories[backend_template_name]()
        
        # Customize with user's name
        config['name'] = algorithm_name
        config['description'] = data.get('description', config.get('description', ''))
        ensure_numeric_values(config)
        # Save algorithm
        algorithm_id = manager.save_algorithm(str(current_user), config)
        
        return jsonify({
            'success': True,
            'algorithm_id': algorithm_id,
            'message': 'Algorithm created from template successfully',
            'template_used': template_name
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to create algorithm from template: {str(e)}'
        }), 500


# Algorithm optimization endpoints
@app.route('/api/algorithms/<algorithm_id>/optimize', methods=['POST'])
@token_required
def optimize_algorithm(current_user: int, algorithm_id: str):
    """Run grid search optimization with real market data"""
    try:
        manager = get_algorithm_manager()
            
        data = request.get_json()
        
        # Validate required parameters
        if not data.get('parameter_grid'):
            return jsonify({
                'success': False,
                'error': 'parameter_grid is required'
            }), 400
        
        if not data.get('symbol'):
            return jsonify({
                'success': False,
                'error': 'symbol is required for optimization'
            }), 400
        
        # Get algorithm configuration
        algorithm_data = manager.get_algorithm(algorithm_id, str(current_user))
        if not algorithm_data:
            return jsonify({
                'success': False,
                'error': 'Algorithm not found'
            }), 404
        
        # Get real market data for optimization
        symbol = data['symbol'].upper()
        start_date = data.get('start_date', '2022-01-01')  # Default to 2+ years of data
        end_date = data.get('end_date', '2024-12-31')
        
        try:
            market_data = fetch_market_data(symbol, start_date, end_date)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to fetch market data: {str(e)}'
            }), 400
        
        # Create optimizer with real data
        optimizer = AlgorithmOptimizer(market_data)
        
        # Get the template function based on algorithm type
        algorithm_name = algorithm_data['config'].get('name', '').lower()
        if 'rsi' in algorithm_name:
            template_func = create_rsi_oversold_algorithm
        elif 'mean reversion' in algorithm_name:
            template_func = create_mean_reversion_algorithm
        elif 'momentum' in algorithm_name:
            template_func = create_momentum_algorithm
        else:
            # Default to RSI if unknown
            template_func = create_rsi_oversold_algorithm
        
        metric = data.get('optimization_metric', 'sharpe_ratio')
        optimization_results = optimizer.grid_search_optimization(
            template_func, 
            data['parameter_grid'], 
            metric
        )
        
        # Convert NumPy types to native Python types for JSON serialization
        optimization_results = convert_numpy_types(optimization_results)
        
        return jsonify({
            'success': True,
            'optimization_results': optimization_results,
            'data_points': len(market_data),
            'symbol': symbol,
            'period': f"{start_date} to {end_date}"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Replace the walk-forward analysis endpoint in your routes file with this:
@app.route('/api/algorithms/<algorithm_id>/walk-forward', methods=['POST'])
@token_required
def walk_forward_analysis(current_user: int, algorithm_id: str):
    """Perform walk-forward analysis with real market data"""
    try:
        manager = get_algorithm_manager()
            
        data = request.get_json()
        
        # Validate required parameters
        if not data.get('symbol'):
            return jsonify({
                'success': False,
                'error': 'symbol is required for walk-forward analysis'
            }), 400
        
        # Get algorithm configuration
        algorithm_data = manager.get_algorithm(algorithm_id, str(current_user))
        if not algorithm_data:
            return jsonify({
                'success': False,
                'error': 'Algorithm not found'
            }), 404
        
        # Get parameters
        train_periods = data.get('train_periods', 252)  # 1 year default
        test_periods = data.get('test_periods', 63)     # 3 months default
        symbol = data['symbol'].upper()
        
        # Calculate required data length
        min_data_length = train_periods + (test_periods * 3)  # At least 3 test periods
        start_date = data.get('start_date', '2020-01-01')  # Default to 5+ years
        end_date = data.get('end_date', '2024-12-31')
        
        # Fetch real market data
        try:
            market_data = fetch_market_data(symbol, start_date, end_date)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to fetch market data: {str(e)}'
            }), 400
        
        # Validate we have enough data
        if len(market_data) < min_data_length:
            return jsonify({
                'success': False,
                'error': f'Insufficient data: need at least {min_data_length} data points, got {len(market_data)}'
            }), 400
        
        # Create optimizer and run walk-forward analysis
        optimizer = AlgorithmOptimizer(market_data)
        walk_forward_results = optimizer.walk_forward_analysis(
            algorithm_data['config'],
            train_periods,
            test_periods
        )
        
        # Convert NumPy types to native Python types for JSON serialization
        walk_forward_results = convert_numpy_types(walk_forward_results)
        
        return jsonify({
            'success': True,
            'walk_forward_results': walk_forward_results,
            'data_points': len(market_data),
            'symbol': symbol,
            'period': f"{start_date} to {end_date}"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
# Range → yfinance period/interval mapping
RANGE_MAP = {
    "1d": ("7d", "15m"),
    "3d": ("1mo", "30m"),
    "1w": ("1mo", "60m"),
    "1m": ("3mo", "1d"),
    "3m": ("6mo", "1d"),
    "6m": ("1y", "1d"),
    "1y": ("2y", "1d")
}

# Range → timedelta for trimming
TRIM_MAP = {
    "1d": timedelta(days=1),
    "3d": timedelta(days=3),
    "1w": timedelta(weeks=1),
    "1m": timedelta(days=30),
    "3m": timedelta(days=90),
    "6m": timedelta(days=180),
    "1y": timedelta(days=365)
}

@app.route("/api/candles/<ticker>", methods=["GET"])
def get_candles(ticker):
    range_param = request.args.get("range", "1d")
    if range_param not in RANGE_MAP:
        return jsonify({"error": f"Invalid range. Choose from {list(RANGE_MAP.keys())}"}), 400
    
    period, interval = RANGE_MAP[range_param]
    
    try:
        # Fetch data
        df = yf.download(ticker, period=period, interval=interval, timeout=30)
        if df.empty:
            return jsonify({"error": "No data found for this ticker/range."}), 404
        
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # Reset index and ensure datetime column exists
        df = df.reset_index()
        if 'Date' not in df.columns:
            # For intraday data, yfinance names it 'Datetime'
            if 'Datetime' in df.columns:
                df.rename(columns={'Datetime': 'Date'}, inplace=True)
            else:
                return jsonify({"error": "No datetime index found"}), 500
        
        df["Date"] = pd.to_datetime(df["Date"])
        
        # Trim to exactly requested range
        # Get current time in IST
        ist = pytz.timezone('Asia/Kolkata')
        start_date = datetime.now(ist) - TRIM_MAP[range_param]
        
        # Convert df["Date"] to IST if it has timezone info
        if df["Date"].dt.tz is not None:
            df["Date"] = df["Date"].dt.tz_convert(ist)
        else:
            # If no timezone, assume it's already in IST
            df["Date"] = df["Date"].dt.tz_localize(ist)
        
        df = df[df["Date"] >= start_date]
        
        if "Volume" not in df.columns:
            df["Volume"] = 0
        
        candles = [
            [row["Date"].strftime("%Y-%m-%d %H:%M"), float(row["Open"]), float(row["High"]),
             float(row["Low"]), float(row["Close"])]
            for _, row in df.iterrows()
        ]
        volumes = [
            [row["Date"].strftime("%Y-%m-%d %H:%M"), int(row["Volume"])]
            for _, row in df.iterrows()
        ]
        
        return jsonify({
            "candles": candles,
            "volumes": volumes
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
@app.route('/api/algorithms/indicators', methods=['GET'])
@token_required
def get_available_indicators(current_user):
    """Get all available technical indicators for custom algorithms"""
    try:
        # Define all available indicators with their parameters
        indicators = {
            "RSI": {
                "name": "Relative Strength Index",
                "description": "Measures the speed and change of price movements. Values range from 0 to 100.",
                "parameters": {
                    "period": {
                        "type": "int",
                        "default": 14,
                        "min": 5,
                        "max": 30,
                        "description": "RSI calculation period"
                    }
                }
            },
            "MACD": {
                "name": "Moving Average Convergence Divergence",
                "description": "Trend-following momentum indicator that shows the relationship between two moving averages.",
                "parameters": {
                    "fast": {
                        "type": "int",
                        "default": 12,
                        "min": 5,
                        "max": 20,
                        "description": "MACD fast period"
                    },
                    "slow": {
                        "type": "int",
                        "default": 26,
                        "min": 20,
                        "max": 35,
                        "description": "MACD slow period"
                    },
                    "signal": {
                        "type": "int",
                        "default": 9,
                        "min": 5,
                        "max": 15,
                        "description": "MACD signal period"
                    },
                    "component": {
                        "type": "string",
                        "default": "histogram",
                        "options": ["histogram", "macd", "signal"],
                        "description": "Which MACD component to use"
                    }
                }
            },
            "BOLLINGER": {
                "name": "Bollinger Bands",
                "description": "Volatility indicator consisting of a middle band (SMA) with two outer bands.",
                "parameters": {
                    "period": {
                        "type": "int",
                        "default": 20,
                        "min": 10,
                        "max": 30,
                        "description": "Bollinger Band period"
                    },
                    "std": {
                        "type": "float",
                        "default": 2.0,
                        "min": 1.0,
                        "max": 3.0,
                        "description": "Standard deviation multiplier"
                    },
                    "component": {
                        "type": "string",
                        "default": "bb_percent",
                        "options": ["bb_percent", "upper", "lower", "middle"],
                        "description": "Which Bollinger Band component to use"
                    }
                }
            },
            "ADX": {
                "name": "Average Directional Index",
                "description": "Measures trend strength without regard to trend direction.",
                "parameters": {
                    "period": {
                        "type": "int",
                        "default": 14,
                        "min": 7,
                        "max": 21,
                        "description": "ADX calculation period"
                    },
                    "component": {
                        "type": "string",
                        "default": "adx",
                        "options": ["adx", "plus_di", "minus_di"],
                        "description": "Which ADX component to use"
                    }
                }
            },
            "STOCHASTIC": {
                "name": "Stochastic Oscillator",
                "description": "Momentum indicator comparing a particular closing price to a range of prices over time.",
                "parameters": {
                    "k_period": {
                        "type": "int",
                        "default": 14,
                        "min": 5,
                        "max": 21,
                        "description": "Stochastic %K period"
                    },
                    "d_period": {
                        "type": "int",
                        "default": 3,
                        "min": 2,
                        "max": 7,
                        "description": "Stochastic %D period (smoothing)"
                    },
                    "slow": {
                        "type": "boolean",
                        "default": True,
                        "description": "Use slow stochastic (smoothed)"
                    }
                }
            },
            "VOLUME": {
                "name": "Volume",
                "description": "Trading volume indicator showing the number of shares traded.",
                "parameters": {
                    "lookback": {
                        "type": "int",
                        "default": 20,
                        "min": 5,
                        "max": 50,
                        "description": "Lookback period for volume analysis"
                    },
                    "multiplier": {
                        "type": "float",
                        "default": 1.5,
                        "min": 1.0,
                        "max": 3.0,
                        "description": "Volume multiplier threshold"
                    }
                }
            },
            "OBV": {
                "name": "On-Balance Volume",
                "description": "Momentum indicator that uses volume flow to predict changes in stock price.",
                "parameters": {
                    "lookback": {
                        "type": "int",
                        "default": 20,
                        "min": 5,
                        "max": 50,
                        "description": "Lookback period for OBV analysis"
                    },
                    "multiplier": {
                        "type": "float",
                        "default": 1.05,
                        "min": 1.0,
                        "max": 2.0,
                        "description": "OBV multiplier threshold"
                    }
                }
            },
            "MFI": {
                "name": "Money Flow Index",
                "description": "Momentum indicator that uses price and volume to identify overbought/oversold conditions.",
                "parameters": {
                    "period": {
                        "type": "int",
                        "default": 14,
                        "min": 7,
                        "max": 21,
                        "description": "MFI calculation period"
                    }
                }
            },
            "VWAP": {
                "name": "Volume Weighted Average Price",
                "description": "Trading benchmark that gives the average price a security has traded at throughout the day.",
                "parameters": {
                    "period": {
                        "type": "int",
                        "default": 20,
                        "min": 10,
                        "max": 50,
                        "description": "VWAP calculation period"
                    },
                    "multiplier": {
                        "type": "float",
                        "default": 1.01,
                        "min": 1.0,
                        "max": 1.1,
                        "description": "VWAP multiplier threshold"
                    }
                }
            },
            "SMA": {
                "name": "Simple Moving Average",
                "description": "Average of closing prices over a specified period.",
                "parameters": {
                    "period": {
                        "type": "int",
                        "default": 20,
                        "min": 5,
                        "max": 200,
                        "description": "SMA calculation period"
                    }
                }
            },
            "EMA": {
                "name": "Exponential Moving Average",
                "description": "Weighted average that gives more importance to recent prices.",
                "parameters": {
                    "period": {
                        "type": "int",
                        "default": 20,
                        "min": 5,
                        "max": 200,
                        "description": "EMA calculation period"
                    }
                }
            },
            "PRICE": {
                "name": "Price",
                "description": "Current or historical price data for analysis.",
                "parameters": {
                    "lookback": {
                        "type": "int",
                        "default": 20,
                        "min": 1,
                        "max": 100,
                        "description": "Lookback period for price analysis"
                    },
                    "vwap_period": {
                        "type": "int",
                        "default": 20,
                        "min": 5,
                        "max": 50,
                        "description": "VWAP period for price comparison"
                    }
                }
            },
            "CCI": {
                "name": "Commodity Channel Index",
                "description": "Versatile indicator that can be used to identify a new trend or warn of extreme conditions.",
                "parameters": {
                    "period": {
                        "type": "int",
                        "default": 20,
                        "min": 10,
                        "max": 40,
                        "description": "CCI calculation period"
                    }
                }
            },
            "WILLIAMS_R": {
                "name": "Williams %R",
                "description": "Momentum indicator that measures overbought and oversold levels.",
                "parameters": {
                    "period": {
                        "type": "int",
                        "default": 14,
                        "min": 7,
                        "max": 21,
                        "description": "Williams %R calculation period"
                    }
                }
            },
            "ATR": {
                "name": "Average True Range",
                "description": "Measures market volatility by decomposing the entire range of an asset price.",
                "parameters": {
                    "period": {
                        "type": "int",
                        "default": 14,
                        "min": 7,
                        "max": 21,
                        "description": "ATR calculation period"
                    }
                }
            }
        }

        # Define comparison operators
        comparisons = {
            ">": "Greater than",
            ">=": "Greater than or equal to",
            "<": "Less than",
            "<=": "Less than or equal to",
            "==": "Equal to",
            "!=": "Not equal to",
            "crosses_above": "Crosses above a value",
            "crosses_below": "Crosses below a value",
            "changes": "Changes direction"
        }

        return jsonify({
            "success": True,
            "indicators": indicators,
            "comparisons": comparisons,
            "total_indicators": len(indicators)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)