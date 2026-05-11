"""
Algorithm Terminal Commands Module

This module provides terminal command implementations for custom algorithm management
in the QuarkScript interpreter.
"""

from useralgo import (
    UserAlgorithmManager, 
    CustomAlgorithm, 
    create_rsi_oversold_algorithm, 
    create_mean_reversion_algorithm, 
    create_momentum_algorithm, 
    create_volume_breakout_algorithm,
    create_quantum_momentum_matrix,
    create_alpha_convergence_system,
    create_volatility_breakout_system,
    create_smart_money_flow
)
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import json

class AlgorithmTerminalCommands:
    """Handles algorithm-related terminal commands"""
    
    def __init__(self, current_user):
        self.current_user = current_user
        self.algo_manager = UserAlgorithmManager()
        self.builtin_algorithms = {
            'rsi': create_rsi_oversold_algorithm,
            'mean_reversion': create_mean_reversion_algorithm,
            'momentum': create_momentum_algorithm,
            'volume_breakout': create_volume_breakout_algorithm,
            'quantum_momentum': create_quantum_momentum_matrix,
            'alpha_convergence': create_alpha_convergence_system,
            'volatility_breakout': create_volatility_breakout_system,
            'smart_money_flow': create_smart_money_flow
        }

    def handle_algorithm_commands(self, parts):
        """Handle algorithm-related commands"""
        if not parts:
            return False, "No command provided"
            
        command = parts[0].lower()
        
        if command == 'create_algo':
            return self.create_algorithm(parts[1:])

        elif command == 'list_algos':
            return self.list_algorithms()

        elif command == 'get_algo':
            if len(parts) < 2:
                return False, "Missing algorithm ID. Usage: get_algo <id>"
            return self.get_algorithm(parts[1])

        elif command == 'delete_algo':
            if len(parts) < 2:
                return False, "Missing algorithm ID. Usage: delete_algo <id>"
            return self.delete_algorithm(parts[1])

        elif command == 'run_backtest':
            if len(parts) < 2:
                return False, "Missing algorithm ID. Usage: run_backtest <id> [symbol=<symbol>] [start_date=<YYYY-MM-DD>] [end_date=<YYYY-MM-DD>] [initial_cash=<amount>]"
            
            # Parse parameters
            params = {}
            for i in range(2, len(parts)):
                if '=' in parts[i]:
                    key, value = parts[i].split('=', 1)
                    params[key.lower()] = value
            
            algo_id = parts[1]
            symbol = params.get('symbol', '^GSPC')  # Default to S&P 500
            start_date = params.get('start_date', '2020-01-01')
            end_date = params.get('end_date', datetime.now().strftime('%Y-%m-%d'))
            try:
                initial_cash = float(params.get('initial_cash', 100000))
            except ValueError:
                return False, "initial_cash must be a number"
                
            return self.run_backtest(algo_id, symbol, start_date, end_date, initial_cash)

        elif command == 'use_algo':
            if len(parts) < 2:
                return False, "Missing algorithm type. Usage: use_algo <type> [param1=value1] [param2=value2] ..."
            algo_type = parts[1].lower()
            if algo_type not in self.builtin_algorithms:
                available = ', '.join(self.builtin_algorithms.keys())
                return False, f"Unknown algorithm type: {algo_type}. Available types: {available}"
            
            # Parse parameters
            params = {}
            for i in range(2, len(parts)):
                if '=' in parts[i]:
                    key, value = parts[i].split('=', 1)
                    # Try to convert to appropriate type
                    try:
                        # Try integer first
                        if '.' not in value and '-' not in value:
                            params[key] = int(value)
                        # Try float
                        elif '.' in value:
                            params[key] = float(value)
                        # Keep as string
                        else:
                            params[key] = value
                    except ValueError:
                        params[key] = value
            
            # Create algorithm
            try:
                algo_func = self.builtin_algorithms[algo_type]
                algo_config = algo_func(**params)
                algo_id = self.algo_manager.save_algorithm(self.current_user.id, algo_config)
                return True, {
                    'id': algo_id,
                    'config': algo_config,
                    'message': f"{algo_type} algorithm created successfully with ID: {algo_id}"
                }
            except Exception as e:
                return False, f"Error creating algorithm: {str(e)}"

        return False, f"Unknown algorithm command: {command}"

    def create_algorithm(self, parts):
        """Create a new algorithm from JSON config"""
        if not parts:
            return False, "Missing JSON configuration. Usage: create_algo <json_config>"
        
        try:
            # Join all parts and parse as JSON
            json_str = ' '.join(parts)
            config = json.loads(json_str)
            
            # Validate required fields
            if 'name' not in config:
                return False, "Algorithm configuration must include 'name' field"
            
            # Save the algorithm
            algo_id = self.algo_manager.save_algorithm(self.current_user.id, config)
            return True, {
                'id': algo_id,
                'message': f"Algorithm '{config['name']}' created successfully with ID: {algo_id}"
            }
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {str(e)}"
        except Exception as e:
            return False, f"Error creating algorithm: {str(e)}"

    def list_algorithms(self):
        """List all user algorithms"""
        try:
            algorithms = self.algo_manager.get_user_algorithms(self.current_user.id)
            return True, {
                'count': len(algorithms),
                'algorithms': [{
                    'id': a['id'],
                    'name': a['name'],
                    'description': a['description'],
                    'created_date': a['created_date'],
                    'updated_date': a['updated_date']
                } for a in algorithms]
            }
        except Exception as e:
            return False, f"Error listing algorithms: {str(e)}"

    def get_algorithm(self, algo_id):
        """Get algorithm details"""
        try:
            algorithm = self.algo_manager.get_algorithm(algo_id, self.current_user.id)
            if not algorithm:
                return False, "Algorithm not found"
            return True, {
                'id': algorithm['id'],
                'name': algorithm['name'],
                'description': algorithm['description'],
                'config': algorithm['config'],
                'created_date': algorithm['created_date'],
                'updated_date': algorithm['updated_date']
            }
        except Exception as e:
            return False, f"Error retrieving algorithm: {str(e)}"

    def delete_algorithm(self, algo_id):
        """Delete an algorithm"""
        try:
            success = self.algo_manager.delete_algorithm(algo_id, self.current_user.id)
            if not success:
                return False, "Failed to delete algorithm or algorithm not found"
            return True, {"message": f"Algorithm {algo_id} deleted successfully"}
        except Exception as e:
            return False, f"Error deleting algorithm: {str(e)}"

    def run_backtest(self, algo_id, symbol, start_date, end_date, initial_cash):
        """Run a backtest on an algorithm"""
        try:
            # Get algorithm
            algorithm = self.algo_manager.get_algorithm(algo_id, self.current_user.id)
            if not algorithm:
                return False, "Algorithm not found"
            
            # Create algorithm instance
            algo = CustomAlgorithm(algorithm['config'])
            
            # Fetch real market data using yfinance
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(start=start_date, end=end_date, interval="1d")
                
                if data.empty:
                    # Fallback to dummy data if yfinance fails
                    dates = pd.date_range(start=start_date, end=end_date, freq='D')
                    n_days = len(dates)
                    
                    # Generate realistic price data
                    initial_price = 100
                    returns = np.random.normal(0.0005, 0.02, n_days)  # Daily returns
                    prices = [initial_price]
                    for r in returns[1:]:
                        prices.append(prices[-1] * (1 + r))
                    
                    data = pd.DataFrame({
                        'DATE': dates,
                        'OPEN': prices,
                        'HIGH': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                        'LOW': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                        'CLOSE': prices,
                        'VOLUME': np.random.randint(100000, 1000000, n_days)
                    })
                    data.set_index('DATE', inplace=True)
                else:
                    # Format yfinance data to match expected format
                    # Convert timestamp to string to avoid timezone issues
                    data.index = pd.to_datetime(data.index).strftime('%Y-%m-%d')
                    data.reset_index(inplace=True)
                    data.rename(columns={'index': 'DATE', 'Open': 'OPEN', 'High': 'HIGH', 
                                       'Low': 'LOW', 'Close': 'CLOSE', 'Volume': 'VOLUME'}, inplace=True)
                    
                    # Ensure all column names are uppercase
                    data.columns = [col.upper() for col in data.columns]
                    
                    # Ensure all data is of the correct type
                    numeric_columns = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
                    for col in numeric_columns:
                        if col in data.columns:
                            # Convert to numeric and fill NaN values with 0
                            data[col] = pd.to_numeric(data[col], errors='coerce')
                            data[col] = data[col].fillna(0)
                    
                    # Ensure DATE column is string
                    data['DATE'] = data['DATE'].astype(str)
                    
                    # Set the DATE column as the index to match what the backtest expects
                    data.set_index('DATE', inplace=True)
            except Exception as e:
                # Fallback to dummy data if yfinance fails
                print(f"Warning: Could not fetch real data for {symbol}, using dummy data. Error: {e}")
                dates = pd.date_range(start=start_date, end=end_date, freq='D')
                n_days = len(dates)
                
                # Generate realistic price data
                initial_price = 100
                returns = np.random.normal(0.0005, 0.02, n_days)  # Daily returns
                prices = [initial_price]
                for r in returns[1:]:
                    prices.append(prices[-1] * (1 + r))
                
                data = pd.DataFrame({
                    'DATE': dates,
                    'OPEN': prices,
                    'HIGH': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                    'LOW': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                    'CLOSE': prices,
                    'VOLUME': np.random.randint(100000, 1000000, n_days)
                })
                data.set_index('DATE', inplace=True)
            
            # Debug: Print data info
            print(f"Data shape: {data.shape}")
            print(f"Data columns: {data.columns.tolist()}")
            print(f"Data index: {data.index}")
            print(f"Data types:\n{data.dtypes}")
            
            # Run backtest
            # The data should have DATE as the index to match what the backtest method expects
            result = algo.backtest(data, initial_cash)
            result['algorithm_id'] = algo_id
            result['symbol'] = symbol
            result['start_date'] = start_date
            result['end_date'] = end_date
            
            # Convert numpy values to Python native types for JSON serialization
            def convert_numpy_types(obj):
                if isinstance(obj, dict):
                    return {key: convert_numpy_types(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [convert_numpy_types(item) for item in obj]
                elif isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif pd.isna(obj):
                    return None
                else:
                    return obj
            
            # Convert the result to ensure JSON serializability
            converted_result = convert_numpy_types(result)
            
            # Ensure converted_result is a dictionary
            if not isinstance(converted_result, dict):
                converted_result = {"value": converted_result}
            
            # Save backtest result
            backtest_id = self.algo_manager.save_backtest_result(
                algo_id, symbol, start_date, end_date, initial_cash, converted_result
            )
            
            # Safely extract and round numeric values for summary
            def safe_get(dictionary, key, default=0):
                """Safely get a value from dictionary, handling None and non-numeric values"""
                if not isinstance(dictionary, dict):
                    return default
                value = dictionary.get(key, default)
                if value is None:
                    return default
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return default
            
            def safe_round(value, decimals=4):
                """Safely round a value, handling None and non-numeric values"""
                if value is None:
                    return 0
                try:
                    return round(float(value), decimals)
                except (ValueError, TypeError):
                    return 0
            
            def safe_is_nan(value):
                """Safely check if a value is NaN"""
                if value is None:
                    return True
                try:
                    return np.isnan(float(value))
                except (ValueError, TypeError):
                    return True
            
            # Create summary with safe value extraction
            total_return = safe_get(converted_result, 'total_return')
            sharpe_ratio = safe_get(converted_result, 'sharpe_ratio')
            max_drawdown = safe_get(converted_result, 'max_drawdown')
            win_rate = safe_get(converted_result, 'win_rate')
            total_trades = safe_get(converted_result, 'total_trades', 0)
            
            return True, {
                'backtest_id': backtest_id,
                'result': converted_result,
                'summary': {
                    'total_return': safe_round(total_return, 4),
                    'sharpe_ratio': safe_round(sharpe_ratio, 4) if not safe_is_nan(sharpe_ratio) else 0,
                    'max_drawdown': safe_round(max_drawdown, 4),
                    'total_trades': int(total_trades),
                    'win_rate': safe_round(win_rate, 4) if not safe_is_nan(win_rate) else 0
                }
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Error running backtest: {str(e)}"