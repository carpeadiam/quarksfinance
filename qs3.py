from q9 import *
from datetime import datetime, timedelta
import json
import os
# Add import for the algorithm terminal commands
from algo_terminal_commands import AlgorithmTerminalCommands

class QuarkScriptInterpreter:
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.current_portfolio = None
        self.current_watchlist = None
        self.strategy_types = {
        'MOMENTUM': 'Momentum Strategy',
        'BOLLINGER': 'Bollinger Bands',
        'MACROSS': 'Moving Average Crossover',
        'RSI': 'Relative Strength Index',
        'MACD': 'Moving Average Convergence Divergence',
        'MEANREVERSION': 'Mean Reversion',
        'BREAKOUT': 'Breakout Strategy',
        'VOLUMESPIKE': 'Volume Spike',
        'KELTNER': 'Keltner Channels',
        'STOCHASTIC': 'Stochastic Oscillator',
        'PARABOLICSAR': 'Parabolic SAR'
        }
        self.command_history = []
        self.vercel_env = os.getenv('VERCEL', False)
        # Initialize algorithm command handler
        # Create a mock user object for the algorithm commands
        if self.user_id:
            class MockUser:
                def __init__(self, user_id):
                    self.id = user_id
            mock_user = MockUser(self.user_id)
            self.algo_commands = AlgorithmTerminalCommands(mock_user)
        else:
            self.algo_commands = None

    def execute(self, command_input):
        """Execute one or more commands separated by semicolons"""
        commands = [cmd.strip() for cmd in command_input.split(';') if cmd.strip()]
        if not commands:
            return False, "Empty command"

        results = []
        for command in commands:
            parts = command.strip().split()
            if not parts:
                continue  # skip empty commands

            cmd = parts[0].upper()
            args = " ".join(parts[1:])

            # Add command to history (except for HISTORY itself)
            if cmd != "HISTORY" and cmd != "REPEAT":
                self.command_history.append(command)

            try:
                # Handle algorithm commands first
                if cmd in ['CREATE_ALGO', 'LIST_ALGOS', 'GET_ALGO', 'DELETE_ALGO', 'RUN_BACKTEST', 'USE_ALGO']:
                    if not self.user_id:
                        result = (False, "You must be logged in to use algorithm commands")
                    elif self.algo_commands is None:
                        result = (False, "Algorithm commands not available")
                    else:
                        result = self.algo_commands.handle_algorithm_commands(parts)
                elif cmd == "HISTORY":
                    result = self._handle_history(args)
                elif cmd == "REPEAT":
                    result = self._handle_repeat(args)
                elif cmd == "CREATE":
                    result = self._handle_create(args)
                elif cmd == "BUY":
                    result = self._handle_buy(args)
                elif cmd == "SELL":
                    result = self._handle_sell(args)
                elif cmd == "VIEW":
                    result = self._handle_view(args)
                elif cmd == "ADD":
                    result = self._handle_add(args)
                elif cmd == "REMOVE":
                    result = self._handle_remove(args)
                elif cmd == "STRATEGY":
                    result = self._handle_strategy(args)
                elif cmd == "RUN":
                    result = self._handle_run(args)
                elif cmd == "GENERATE":
                    result = self._handle_generate(args)
                elif cmd == "SAVE":
                    result = self._handle_save()
                elif cmd == "LOAD":
                    result = self._handle_load(args)
                elif cmd == "LIST":
                    result = self._handle_list(args)
                elif cmd == "PRICE":
                    result = self._handle_price(args)
                elif cmd == 'HISTORICAL_PRICE':
                    result = self._handle_historical_price(args)
                elif cmd == 'COMPARE_PRICE':
                    result = self._handle_compare_price(args)
                elif cmd == "HELP":
                    result = (True, print_help(return_output=True))
                elif cmd == "EXIT" or cmd == "QUIT":
                    print("Exiting QuarkScript.")
                    return True, ""
                else:
                    result = (False, f"Unknown command: {cmd}")

                results.append(result)

            except Exception as e:
                results.append((False, f"Error executing command '{command}': {str(e)}"))

        # Process results
        if len(results) == 1:
            return results[0]
        else:
            # For multiple commands, return a combined result
            all_success = all(result[0] for result in results)
            combined_message = "\n".join(
                f"Command {i+1}: {'SUCCESS' if success else 'ERROR'} - {message}"
                for i, (success, message) in enumerate(results)
            )
            return all_success, combined_message

    def execute_without_history(self, command_input):
        """Execute one or more commands without adding to history"""
        commands = [cmd.strip() for cmd in command_input.split(';') if cmd.strip()]
        if not commands:
            return False, "Empty command"

        results = []
        for command in commands:
            parts = command.strip().split()
            if not parts:
                continue

            cmd = parts[0].upper()
            args = " ".join(parts[1:])

            try:
                # Handle algorithm commands first
                if cmd in ['CREATE_ALGO', 'LIST_ALGOS', 'GET_ALGO', 'DELETE_ALGO', 'RUN_BACKTEST', 'USE_ALGO']:
                    if not self.user_id:
                        result = (False, "You must be logged in to use algorithm commands")
                    elif self.algo_commands is None:
                        result = (False, "Algorithm commands not available")
                    else:
                        result = self.algo_commands.handle_algorithm_commands(parts)
                elif cmd == "HISTORY":
                    result = self._handle_history(args)
                elif cmd == "REPEAT":
                    result = self._handle_repeat(args)
                elif cmd == "CREATE":
                    result = self._handle_create(args)
                elif cmd == "BUY":
                    result = self._handle_buy(args)
                elif cmd == "SELL":
                    result = self._handle_sell(args)
                elif cmd == "VIEW":
                    result = self._handle_view(args)
                elif cmd == "ADD":
                    result = self._handle_add(args)
                elif cmd == "REMOVE":
                    result = self._handle_remove(args)
                elif cmd == "STRATEGY":
                    result = self._handle_strategy(args)
                elif cmd == "RUN":
                    result = self._handle_run(args)
                elif cmd == "GENERATE":
                    result = self._handle_generate(args)
                elif cmd == "SAVE":
                    result = self._handle_save()
                elif cmd == "LOAD":
                    result = self._handle_load(args)
                elif cmd == "LIST":
                    result = self._handle_list(args)
                elif cmd == "PRICE":
                    result = self._handle_price(args)
                elif cmd == 'HISTORICAL_PRICE':
                    result = self._handle_historical_price(args)
                elif cmd == 'COMPARE_PRICE':
                    result = self._handle_compare_price(args)
                elif cmd == "HELP":
                    result = (True, print_help(return_output=True))
                elif cmd == "EXIT" or cmd == "QUIT":
                    print("Exiting QuarkScript.")
                    return True, ""
                else:
                    result = (False, f"Unknown command: {cmd}")

                results.append(result)

            except Exception as e:
                results.append((False, f"Error executing command '{command}': {str(e)}"))

        if len(results) == 1:
            return results[0]
        else:
            all_success = all(result[0] for result in results)
            combined_message = "\n".join(
                f"Command {i+1}: {'SUCCESS' if success else 'ERROR'} - {message}"
                for i, (success, message) in enumerate(results)
            )
            return all_success, combined_message
            

    def _handle_history(self, args):
        """Handle the HISTORY command to view command history"""
        params = self._parse_params(args)
        limit = int(params.get("limit", 10))  # Default to showing last 10 commands

        if not self.command_history:
            return True, "No command history available."

        history = self.command_history[-limit:] if limit > 0 else self.command_history
        output = [f"{i+1}: {cmd}" for i, cmd in enumerate(history)]
        return True, "Command History:\n" + "\n".join(output)

    def _handle_repeat(self, args):
        """Handle the REPEAT command to repeat a command from history"""
        params = self._parse_params(args)
        if "index" not in params:
            return False, "REPEAT command requires index parameter"

        try:
            index = int(params["index"]) - 1
            if index < 0 or index >= len(self.command_history):
                return False, f"Invalid index: {index+1}. History has {len(self.command_history)} commands."

            command = self.command_history[index]
            return self.execute_without_history(command)
        except ValueError:
            return False, "Index must be a number"

    def _handle_price(self, args):
        """Handle the PRICE command to get current stock price"""
        params = self._parse_params(args)
        if "symbol" not in params:
            return False, "PRICE command requires symbol parameter"

        price = get_stock_price(params["symbol"])
        if price is None:
            return False, f"Could not fetch price for {params['symbol']}"
        return True, f"Current price of {params['symbol']}: ₹{price:.2f}"

    def _handle_historical_price(self, args):
        """Handle the HISTORICAL_PRICE command to get historical stock price"""
        params = self._parse_params(args)
        if "symbol" not in params or "date" not in params:
            return False, "HISTORICAL_PRICE command requires symbol and date parameters"

        try:
            datetime.strptime(params["date"], "%Y-%m-%d")
        except ValueError:
            return False, "Invalid date format. Use YYYY-MM-DD"

        price = get_historical_price(params["symbol"], params["date"])
        if price is None:
            return False, f"Could not fetch historical price for {params['symbol']} on {params['date']}"

        return True, f"Price of {params['symbol']} on {params['date']}: ₹{price:.2f}"

    def _handle_compare_price(self, args):
        """Compare stock price between two dates and analyze trend pattern"""
        params = self._parse_params(args)
        if "symbol" not in params or "start_date" not in params:
            return False, "COMPARE_PRICE command requires symbol and start_date parameters"

        try:
            # Validate start date
            datetime.strptime(params["start_date"], "%Y-%m-%d")

            # Set end date to current date if not provided
            if "end_date" in params:
                end_date_str = params["end_date"]
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            else:
                end_date = datetime.now().date()
                end_date_str = end_date.strftime("%Y-%m-%d")

        except ValueError:
            return False, "Invalid date format. Use YYYY-MM-DD"

        # Get start date price
        start_price = get_historical_price(params["symbol"], params["start_date"])
        if start_price is None:
            return False, f"Could not fetch price for {params['symbol']} on {params['start_date']}"

        # Get end date price
        if "end_date" in params:
            end_price = get_historical_price(params["symbol"], params["end_date"])
            if end_price is None:
                return False, f"Could not fetch price for {params['symbol']} on {params['end_date']}"
        else:
            end_price = get_stock_price(params["symbol"])
            if end_price is None:
                return False, f"Could not fetch current price for {params['symbol']}"

        try:
            start_date = datetime.strptime(params["start_date"], "%Y-%m-%d").date()

            # Fetch data for the entire period
            df = stock_df(params["symbol"], from_date=start_date, to_date=end_date, series="EQ")

            if df.empty:
                return False, f"No data found for {params['symbol']} between {start_date} and {end_date}."

            # Analyze price movement pattern
            min_price = df['CLOSE'].min()
            max_price = df['CLOSE'].max()

            price_change = end_price - start_price
            percent_change = (price_change / start_price) * 100

            # Determine trend pattern
            if price_change > 0:
                if min_price >= start_price:
                    trend = "Steady Increase"
                    description = "The stock price never went below the starting price and ended higher."
                else:
                    trend = "Abnormal Increase"
                    description = "The stock price went below the starting price but ended higher."
            else:
                if max_price <= start_price:
                    trend = "Steady Decrease"
                    description = "The stock price never went above the starting price and ended lower."
                else:
                    trend = "Abnormal Decrease"
                    description = "The stock price went above the starting price but ended lower."

            # Prepare result
            result = {
                "symbol": params["symbol"],
                "start_date": params["start_date"],
                "end_date": end_date_str,
                "start_price": start_price,
                "end_price": end_price,
                "price_change": price_change,
                "percent_change": percent_change,
                "trend_pattern": trend,
                "description": description,
                "lowest_price": min_price,
                "highest_price": max_price
            }

            return True, result

        except Exception as e:
            return False, f"Error analyzing price trend: {str(e)}"

    def _handle_create(self, args):
        if "PORTFOLIO" in args:
            params = self._parse_params(args.replace("PORTFOLIO", ""))
            if not self.user_id:
                return False, "You must be logged in to create a portfolio"
            if "name" not in params or "cash" not in params:
                return False, "CREATE PORTFOLIO requires name and cash parameters"
            try:
                cash = float(params["cash"])
                self.current_portfolio = Simulation(params["name"], cash)
                
                # Automatically save the portfolio to get an ID
                save_result = save_portfolio(self.user_id, self.current_portfolio)
                print(f"DEBUG: save_portfolio returned {save_result}")  # Debug line
                
                if save_result:
                    # The save_portfolio function should have set the db_id on the portfolio object
                    # Check if the portfolio now has a db_id
                    portfolio_id = getattr(self.current_portfolio, 'db_id', None)
                    print(f"DEBUG: Portfolio ID after save: {portfolio_id}")  # Debug line
                    
                    if portfolio_id is not None:
                        # Successfully saved and ID assigned
                        return True, f"Portfolio '{params['name']}', ID: {portfolio_id} created with ₹{cash:.2f} cash and loaded"
                    else:
                        # The portfolio was saved but no ID was assigned - this is unexpected
                        print(f"DEBUG: Portfolio saved but no ID assigned")  # Debug line
                        return True, f"Portfolio '{params['name']}' created with ₹{cash:.2f} cash and loaded (ID unknown)"
                else:
                    print("DEBUG: save_portfolio failed")  # Debug line
                    # Even if save fails, we still have the portfolio in memory
                    return True, f"Portfolio '{params['name']}' created with ₹{cash:.2f} cash (not saved to database)"
            except ValueError:
                return False, "Cash amount must be a number"
        elif "WATCHLIST" in args:
            params = self._parse_params(args.replace("WATCHLIST", ""))
            if not self.user_id:
                return False, "You must be logged in to create a watchlist"
            if "name" not in params:
                return False, "CREATE WATCHLIST requires name parameter"
            self.current_watchlist = Watchlist(params["name"])
            
            # Automatically save the watchlist to get an ID
            save_result = save_watchlist(self.user_id, self.current_watchlist)
            
            if save_result:
                # The save_watchlist function should have set the db_id on the watchlist object
                watchlist_id = getattr(self.current_watchlist, 'db_id', None)
                
                if watchlist_id is not None:
                    # Successfully saved and ID assigned
                    return True, f"Watchlist '{params['name']}', ID: {watchlist_id} created and loaded"
                else:
                    # The watchlist was saved but no ID was assigned - this is unexpected
                    return True, f"Watchlist '{params['name']}' created and loaded (ID unknown)"
            else:
                return False, "Watchlist created in memory but failed to save to database"
        else:
            return False, "Invalid CREATE command. Use CREATE PORTFOLIO or CREATE WATCHLIST"

    def _handle_buy(self, args):
        params = self._parse_params(args)
        
        # Check if an id parameter is provided to load a specific portfolio
        if "id" in params:
            portfolio_id = int(params["id"])
            portfolio = load_portfolio(self.user_id, portfolio_id)
            if portfolio is None:
                return False, f"Could not load portfolio {portfolio_id}"
            
            # Ensure the loaded portfolio has its db_id set using a safe approach
            try:
                object.__setattr__(portfolio, 'db_id', portfolio_id)
            except:
                # If we can't set db_id directly, continue without it
                pass
                
            # Use this portfolio for the transaction
            target_portfolio = portfolio
            print(f"DEBUG: Using portfolio ID {portfolio_id} for buy operation")  # Debug line
        else:
            # Use the currently loaded portfolio
            target_portfolio = self.current_portfolio
            print(f"DEBUG: Using current portfolio for buy operation: {self.current_portfolio}")  # Debug line
            
        if not target_portfolio:
            return False, "No portfolio loaded. Use CREATE PORTFOLIO or LOAD PORTFOLIO first, or specify id parameter"

        if "symbol" not in params or "quantity" not in params:
            return False, "BUY command requires symbol and quantity parameters"

        try:
            quantity = int(params["quantity"])
            if quantity <= 0:
                return False, "Quantity must be a positive integer"
            
            print(f"DEBUG: Attempting to buy {quantity} shares of {params['symbol']}")  # Debug line
            target_portfolio.buy_stock(params["symbol"], quantity)
            print(f"DEBUG: Successfully bought {quantity} shares of {params['symbol']}")  # Debug line
            
            # If we used a specific portfolio ID, save it
            if "id" in params:
                save_portfolio(self.user_id, target_portfolio)
                print(f"DEBUG: Saved portfolio ID {portfolio_id} after buy operation")  # Debug line
            
            return True, f"Bought {quantity} shares of {params['symbol']}"
        except ValueError:
            return False, "Quantity must be a number"

    def _handle_sell(self, args):
        params = self._parse_params(args)
        
        # Check if an id parameter is provided to load a specific portfolio
        if "id" in params:
            portfolio_id = int(params["id"])
            portfolio = load_portfolio(self.user_id, portfolio_id)
            if portfolio is None:
                return False, f"Could not load portfolio {portfolio_id}"
            
            # Ensure the loaded portfolio has its db_id set using a safe approach
            try:
                object.__setattr__(portfolio, 'db_id', portfolio_id)
            except:
                # If we can't set db_id directly, continue without it
                pass
                
            # Use this portfolio for the transaction
            target_portfolio = portfolio
            print(f"DEBUG: Using portfolio ID {portfolio_id} for sell operation")  # Debug line
        else:
            # Use the currently loaded portfolio
            target_portfolio = self.current_portfolio
            print(f"DEBUG: Using current portfolio for sell operation: {self.current_portfolio}")  # Debug line
            
        if not target_portfolio:
            return False, "No portfolio loaded. Use CREATE PORTFOLIO or LOAD PORTFOLIO first, or specify id parameter"

        if "symbol" not in params or "quantity" not in params:
            return False, "SELL command requires symbol and quantity parameters"

        try:
            quantity = int(params["quantity"])
            if quantity <= 0:
                return False, "Quantity must be a positive integer"
            
            target_portfolio.sell_stock(params["symbol"], quantity)
            
            # If we used a specific portfolio ID, save it
            if "id" in params:
                save_portfolio(self.user_id, target_portfolio)
                print(f"DEBUG: Saved portfolio ID {portfolio_id} after sell operation")  # Debug line
            
            return True, f"Sold {quantity} shares of {params['symbol']}"
        except ValueError:
            return False, "Quantity must be a number"

    def _handle_view(self, args):
        if "PORTFOLIO" in args:
            if not self.current_portfolio:
                # Debug output to check why portfolio isn't loaded
                print(f"DEBUG: Current portfolio state - {self.current_portfolio}")
                return False, "No portfolio loaded. Use CREATE PORTFOLIO or LOAD PORTFOLIO first"
            
            try:
                # Safely extract portfolio values
                portfolio_name_raw = getattr(self.current_portfolio, 'name', 'Unknown')
                portfolio_name = str(self._safe_extract_value(portfolio_name_raw, 'Unknown'))
                portfolio_cash_raw = self.current_portfolio.portfolio.get('cash', 0)
                portfolio_cash_extracted = self._safe_extract_value(portfolio_cash_raw, 0)
                portfolio_cash = self._safe_float_convert(portfolio_cash_extracted)
                
                # Ensure we have a float value
                if portfolio_cash is None:
                    portfolio_cash = 0.0
                
                portfolio_summary = {
                    "name": portfolio_name,
                    "cash": portfolio_cash,
                    "holdings": [],
                    "total_value": portfolio_cash
                }
                
                for symbol, data in self.current_portfolio.portfolio['holdings'].items():
                    try:
                        # Safely extract data values
                        symbol_extracted = self._safe_extract_value(symbol, str(symbol))
                        symbol_str = str(symbol_extracted)
                        current_price = get_stock_price(symbol_str)
                        
                        if current_price is None:
                            avg_price_raw = data.get('avg_price', 0)
                            avg_price_extracted = self._safe_extract_value(avg_price_raw, 0)
                            current_price = self._safe_float_convert(avg_price_extracted)
                        
                        quantity_raw = data.get('quantity', 0)
                        quantity_extracted = self._safe_extract_value(quantity_raw, 0)
                        quantity = self._safe_int_convert(quantity_extracted)
                        
                        avg_price_raw = data.get('avg_price', 0)
                        avg_price_extracted = self._safe_extract_value(avg_price_raw, 0)
                        avg_price = self._safe_float_convert(avg_price_extracted)
                        
                        # Ensure we have valid values
                        if current_price is None:
                            current_price = avg_price if avg_price is not None else 0.0
                        
                        if quantity is None:
                            quantity = 0
                        
                        if avg_price is None:
                            avg_price = 0.0
                        
                        # Convert to basic Python types before calculations
                        current_price_safe = self._safe_extract_value(current_price, 0.0)
                        current_price_float = float(current_price_safe) if current_price_safe is not None else 0.0
                        
                        quantity_safe = self._safe_extract_value(quantity, 0)
                        quantity_int = int(quantity_safe) if quantity_safe is not None else 0
                        
                        avg_price_safe = self._safe_extract_value(avg_price, 0.0)
                        avg_price_float = float(avg_price_safe) if avg_price_safe is not None else 0.0
                        
                        holding_value = current_price_float * quantity_int
                        portfolio_summary["total_value"] += holding_value
                        
                        pl_value = holding_value - (avg_price_float * quantity_int)
                        
                        portfolio_summary["holdings"].append({
                            "symbol": symbol_str,
                            "quantity": quantity_int,
                            "avg_price": avg_price_float,
                            "current_price": current_price_float,
                            "value": holding_value,
                            "pl": pl_value
                        })
                    except Exception as e:
                        # Skip this holding if there's an error
                        continue
                
                return True, portfolio_summary
            except Exception as e:
                return False, f"Error viewing portfolio: {str(e)}"
                
        elif "WATCHLIST" in args:
            print(f"DEBUG: VIEW WATCHLIST called, current_watchlist={self.current_watchlist}")  # Debug line
            if not self.current_watchlist:
                return False, "No watchlist loaded. Use CREATE WATCHLIST or LOAD WATCHLIST first"
            
            try:
                watchlist_summary = []
                watchlist_name_raw = getattr(self.current_watchlist, 'name', 'Unknown')
                watchlist_name_extracted = self._safe_extract_value(watchlist_name_raw, 'Unknown')
                watchlist_name = str(watchlist_name_extracted)
                
                for symbol, data in self.current_watchlist.watchlist.items():
                    try:
                        # Extract values from potential pandas objects using a defensive approach
                        symbol_extracted = self._safe_extract_value(symbol, str(symbol))
                        symbol_str = str(symbol_extracted)
                        current_price = get_stock_price(symbol_str)
                        
                        # Handle potential pandas Series/DataFrame objects for initial_price
                        if isinstance(data, dict):
                            initial_price_raw = data.get('last_price', current_price)
                        else:
                            initial_price_raw = current_price
                        initial_price_extracted = self._safe_extract_value(initial_price_raw, current_price)
                        initial_price = self._safe_float_convert(initial_price_extracted)
                        
                        # Calculate change and change percentage safely
                        change_val = "N/A"
                        change_percent_val = "N/A"
                        current_price_safe = self._safe_extract_value(current_price, None)
                        current_price_float = self._safe_float_convert(current_price_safe)
                        initial_price_safe = self._safe_extract_value(initial_price, None)
                        initial_price_float = self._safe_float_convert(initial_price_safe)
                        
                        if current_price_float is not None and initial_price_float is not None:
                            try:
                                change_val = current_price_float - initial_price_float
                                change_percent_val = ((current_price_float - initial_price_float) / initial_price_float * 100) if initial_price_float != 0 else "N/A"
                            except (ValueError, TypeError, AttributeError):
                                pass
                        
                        # Extract notes safely
                        if isinstance(data, dict):
                            notes_raw = data.get('notes', '')
                        else:
                            notes_raw = ''
                        notes_extracted = self._safe_extract_value(notes_raw, '')
                        notes = str(notes_extracted)
                        
                        # Extract added_on safely
                        if isinstance(data, dict):
                            added_on_raw = data.get('added_on', 'N/A')
                        else:
                            added_on_raw = 'N/A'
                        added_on_extracted = self._safe_extract_value(added_on_raw, 'N/A')
                        added_on = str(added_on_extracted)
                        
                        current_price_str = str(current_price) if current_price is not None else "N/A"
                        initial_price_display = float(initial_price) if initial_price is not None else "N/A"
                        
                        watchlist_summary.append({
                            "symbol": symbol_str,
                            "added_on": added_on,
                            "initial_price": initial_price_display,
                            "current_price": current_price_str,
                            "change": change_val,
                            "change_percent": change_percent_val,
                            "notes": notes
                        })
                    except Exception as e:
                        # Skip this watchlist item if there's an error
                        continue
                
                return True, {
                    "name": watchlist_name,
                    "symbols": watchlist_summary
                }
            except Exception as e:
                return False, f"Error viewing watchlist: {str(e)}"
        else:
            return False, "Invalid VIEW command. Use VIEW PORTFOLIO or VIEW WATCHLIST"
            
    def _safe_extract_value(self, value, default=None):
        """Safely extract value from pandas objects or return as-is"""
        try:
            if value is None:
                return default
            # Check if it's a pandas object with iloc attribute
            if hasattr(value, 'iloc') and callable(getattr(value, 'iloc', None)):
                if len(value) > 0:
                    return value.iloc[0]
                else:
                    return default
            # Check if it's a sequence-like object (but not string)
            elif hasattr(value, '__len__') and not isinstance(value, (str, bytes)):
                if len(value) > 0:
                    return value[0]
                else:
                    return default
            else:
                return value
        except Exception:
            return default
            
    def _safe_float_convert(self, value):
        """Safely convert value to float"""
        try:
            if value is None:
                return None
            # Extract value first if it's a pandas object
            extracted_value = self._safe_extract_value(value, None)
            if extracted_value is None:
                return None
            return float(extracted_value)
        except (ValueError, TypeError, AttributeError):
            return None

    def _safe_int_convert(self, value):
        """Safely convert value to int"""
        try:
            if value is None:
                return None
            # Extract value first if it's a pandas object
            extracted_value = self._safe_extract_value(value, None)
            if extracted_value is None:
                return None
            return int(extracted_value)
        except (ValueError, TypeError, AttributeError):
            return None

    def _handle_add(self, args):
        if "TO WATCHLIST" not in args:
            return False, "Invalid ADD command. Use ADD TO WATCHLIST"

        if not self.current_watchlist:
            return False, "No watchlist loaded. Use CREATE WATCHLIST or LOAD WATCHLIST first"

        params = self._parse_params(args.replace("TO WATCHLIST", ""))
        if "symbol" not in params:
            return False, "ADD TO WATCHLIST command requires symbol parameter"

        notes = params.get("notes", "")
        success = self.current_watchlist.add_to_watchlist(params["symbol"], notes)
        if success:
            return True, f"Added {params['symbol']} to watchlist"
        else:
            return False, f"Failed to add {params['symbol']} to watchlist"

    def _handle_remove(self, args):
        if "FROM WATCHLIST" not in args:
            return False, "Invalid REMOVE command. Use REMOVE FROM WATCHLIST"

        if not self.current_watchlist:
            return False, "No watchlist loaded. Use CREATE WATCHLIST or LOAD WATCHLIST first"

        params = self._parse_params(args.replace("FROM WATCHLIST", ""))
        if "symbol" not in params:
            return False, "REMOVE FROM WATCHLIST command requires symbol parameter"

        success = self.current_watchlist.remove_from_watchlist(params["symbol"])
        if success:
            return True, f"Removed {params['symbol']} from watchlist"
        else:
            return False, f"Failed to remove {params['symbol']} from watchlist"

    def _handle_strategy(self, args):
        if not self.user_id:
            return False, "You must be logged in to manage strategies"

        manager = StrategyManager()
        
        if "CREATE" in args:
            params = self._parse_params(args.replace("CREATE", ""))
            if "name" not in params or "symbol" not in params or "type" not in params:
                return False, "STRATEGY CREATE requires name, symbol, and type parameters"
            
            if params["type"] not in self.strategy_types:
                return False, f"Invalid strategy type. Available types: {', '.join(self.strategy_types.keys())}"
            
            # Extract strategy parameters (everything except name, symbol, type)
            strategy_params = {k: v for k, v in params.items() if k not in ["name", "symbol", "type"]}
            
            # Get portfolio ID if we have a current portfolio
            portfolio_id = self.current_portfolio.db_id if self.current_portfolio else None
            if not portfolio_id:
                return False, "No portfolio selected. Create or load a portfolio first"
            
            success, message = manager.create_strategy(
                str(self.user_id),
                str(portfolio_id),
                str(params["name"]),
                str(params["symbol"]),
                str(params["type"]),
                strategy_params
            )
            return success, message
            
        elif "LIST" in args:
            success, result = manager.list_strategies(str(self.user_id))
            if not success:
                return False, result
            
            strategies = []
            # Ensure result is iterable
            try:
                iterable_result = list(result) if hasattr(result, '__iter__') else []
            except:
                return False, "Invalid result format"
                
            for item in iterable_result:
                # Handle case where item might be a string or other non-dict type
                if not isinstance(item, dict):
                    continue
                
                # Safely extract values with explicit type checking
                try:
                    strategy_id_raw = item.get("id", "") if isinstance(item, dict) else ""
                except:
                    strategy_id_raw = ""
                    
                try:
                    strategy_name_raw = item.get("name", "") if isinstance(item, dict) else ""
                except:
                    strategy_name_raw = ""
                    
                try:
                    strategy_symbol_raw = item.get("symbol", "") if isinstance(item, dict) else ""
                except:
                    strategy_symbol_raw = ""
                    
                try:
                    strategy_type_raw = item.get("strategy_type", "") if isinstance(item, dict) else ""
                except:
                    strategy_type_raw = ""
                    
                try:
                    portfolio_name_raw = item.get("portfolio_name", "") if isinstance(item, dict) else ""
                except:
                    portfolio_name_raw = ""
                    
                try:
                    is_active_raw = item.get("is_active", False) if isinstance(item, dict) else False
                except:
                    is_active_raw = False
                    
                try:
                    last_executed_raw = item.get("last_executed", "Never") if isinstance(item, dict) else "Never"
                except:
                    last_executed_raw = "Never"
                
                strategy_id = self._safe_extract_value(strategy_id_raw, "")
                strategy_name = self._safe_extract_value(strategy_name_raw, "")
                strategy_symbol = self._safe_extract_value(strategy_symbol_raw, "")
                strategy_type = self._safe_extract_value(strategy_type_raw, "")
                portfolio_name = self._safe_extract_value(portfolio_name_raw, "")
                is_active = self._safe_extract_value(is_active_raw, False)
                last_executed = self._safe_extract_value(last_executed_raw, "Never")
                
                # Convert to appropriate types with defaults
                try:
                    strategy_id = int(str(strategy_id)) if strategy_id not in [None, ""] else 0
                except (ValueError, TypeError):
                    strategy_id = 0
                    
                strategy_name = str(strategy_name) if strategy_name not in [None, ""] else ""
                strategy_symbol = str(strategy_symbol) if strategy_symbol not in [None, ""] else ""
                strategy_type = str(strategy_type) if strategy_type not in [None, ""] else ""
                portfolio_name = str(portfolio_name) if portfolio_name not in [None, ""] else ""
                
                try:
                    is_active = bool(is_active) if is_active not in [None, ""] else False
                except (ValueError, TypeError):
                    is_active = False
                    
                last_executed = str(last_executed) if last_executed not in [None, ""] else "Never"
                
                strategies.append({
                    "id": strategy_id,
                    "name": strategy_name,
                    "symbol": strategy_symbol,
                    "type": self.strategy_types.get(strategy_type, strategy_type),
                    "portfolio": portfolio_name,
                    "active": "Yes" if is_active else "No",
                    "last_executed": last_executed
                })
            
            return True, strategies
            
        elif "DELETE" in args:
            params = self._parse_params(args.replace("DELETE", ""))
            if "id" not in params:
                return False, "STRATEGY DELETE requires id parameter"
            
            try:
                strategy_id = int(params["id"])
                success, message = manager.delete_strategy(str(self.user_id), strategy_id)
                return success, message
            except ValueError:
                return False, "ID must be a number"
                
        elif "ENABLE" in args:
            params = self._parse_params(args.replace("ENABLE", ""))
            if "id" not in params:
                return False, "STRATEGY ENABLE requires id parameter"
                
            try:
                strategy_id = int(params["id"])
                success, message = manager.toggle_strategy(str(self.user_id), strategy_id, True)
                return success, message
            except ValueError:
                return False, "ID must be a number"
                
        elif "DISABLE" in args:
            params = self._parse_params(args.replace("DISABLE", ""))
            if "id" not in params:
                return False, "STRATEGY DISABLE requires id parameter"
                
            try:
                strategy_id = int(params["id"])
                success, message = manager.toggle_strategy(str(self.user_id), strategy_id, False)
                return success, message
            except ValueError:
                return False, "ID must be a number"
        else:
            return False, "Invalid STRATEGY command. Use CREATE, LIST, DELETE, ENABLE, or DISABLE"

    def _handle_run(self, args):
        if "STRATEGY" not in args:
            return False, "Invalid RUN command. Use RUN STRATEGY"
    
        if not self.current_portfolio:
            return False, "No portfolio loaded. Use CREATE PORTFOLIO or LOAD PORTFOLIO first"
    
        params = self._parse_params(args.replace("STRATEGY", ""))
        if "name" not in params or "symbol" not in params:
            return False, "RUN STRATEGY command requires name and symbol parameters"
    
        strategy_params = {k: v for k, v in params.items() if k not in ["name", "symbol"]}
        
        # Determine which strategy to run
        strategy_name = params["name"].upper()
        if strategy_name == "MOMENTUM":
            strategy = self.current_portfolio.momentum_strategy
        elif strategy_name == "BOLLINGER":
            strategy = self.current_portfolio.bollinger_bands_strategy
        elif strategy_name == "MACROSS":
            strategy = self.current_portfolio.moving_average_crossover
        elif strategy_name == "RSI":
            strategy = self.current_portfolio.rsi_strategy
        elif strategy_name == "MACD":
            strategy = self.current_portfolio.macd_strategy
        elif strategy_name == "MEANREVERSION":
            strategy = self.current_portfolio.mean_reversion_strategy
        elif strategy_name == "BREAKOUT":
            strategy = self.current_portfolio.breakout_strategy
        elif strategy_name == "VOLUMESPIKE":
            strategy = self.current_portfolio.volume_spike_strategy
        elif strategy_name == "KELTNER":
            strategy = self.current_portfolio.keltner_channels_strategy
        elif strategy_name == "STOCHASTIC":
            strategy = self.current_portfolio.stochastic_oscillator_strategy
        elif strategy_name == "PARABOLICSAR":
            strategy = self.current_portfolio.parabolic_sar_strategy
        else:
            available = ", ".join(self.strategy_types.keys())
            return False, f"Unknown strategy: {strategy_name}. Available: {available}"
    
        # Run backtest with the strategy
        result = self.current_portfolio.run_backtest(
            strategy=strategy,
            symbol=params["symbol"],
            start_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d"),
            **strategy_params
        )
        
        if result is None:
            return False, "Strategy execution failed"
        return True, result


    def _handle_generate(self, args):
        if "ADVICE" not in args:
            return False, "Invalid GENERATE command. Use GENERATE ADVICE"

        params = self._parse_params(args.replace("ADVICE", ""))
        if "symbol" not in params:
            return False, "GENERATE ADVICE command requires symbol parameter"

        advice = generate_advice_sheet(params["symbol"])
        if advice is None:
            return False, f"Could not generate advice for {params['symbol']}"
        return True, advice

    def _handle_save(self):
        success = True
        message = []
        
        print(f"DEBUG: _handle_save called, current_portfolio={self.current_portfolio}, current_watchlist={self.current_watchlist}")  # Debug line

        if self.current_portfolio:
            print(f"DEBUG: Saving portfolio: {self.current_portfolio.name}, ID: {getattr(self.current_portfolio, 'db_id', 'None')}")  # Debug line
            if save_portfolio(self.user_id, self.current_portfolio):
                message.append(f"Portfolio '{self.current_portfolio.name}' saved successfully")
            else:
                success = False
                message.append("Failed to save portfolio")

        if self.current_watchlist:
            print(f"DEBUG: Saving watchlist: {self.current_watchlist.name}, ID: {getattr(self.current_watchlist, 'db_id', 'None')}")  # Debug line
            if save_watchlist(self.user_id, self.current_watchlist):
                message.append(f"Watchlist '{self.current_watchlist.name}' saved successfully")
            else:
                success = False
                message.append("Failed to save watchlist")

        if not message:
            return False, "No portfolio or watchlist to save"
        return success, "\n".join(message)

    def _handle_load(self, args):
        print(f"DEBUG: _handle_load called with args: {args}")  # Debug line
        if "PORTFOLIO" in args:
            params = self._parse_params(args.replace("PORTFOLIO", ""))
            if "id" not in params:
                return False, "LOAD PORTFOLIO command requires id parameter"
    
            try:
                portfolio_id = int(params["id"])
                print(f"DEBUG: Attempting to load portfolio ID: {portfolio_id}")  # Debug line
                portfolio = load_portfolio(self.user_id, portfolio_id)
                print(f"DEBUG: Loaded portfolio object: {portfolio}")  # Debug line
                if portfolio is None:
                    return False, f"Could not load portfolio {portfolio_id}"
    
                # Ensure the loaded portfolio has its db_id set using a safe approach
                try:
                    object.__setattr__(portfolio, 'db_id', portfolio_id)
                except:
                    # If we can't set db_id directly, continue without it
                    pass
                    
                self.current_portfolio = portfolio
                print(f"DEBUG: Set current_portfolio to: {self.current_portfolio}")  # Debug line
                
                # Debug output to verify loading
                portfolio_name = self._safe_extract_value(portfolio.name, "Unknown")
                print(f"DEBUG: Loaded portfolio - Name: {portfolio_name}, ID: {portfolio_id}")
                
                return True, f"Loaded portfolio '{portfolio_name}' (ID: {portfolio_id})"
            except ValueError:
                return False, "ID must be a number"
    
        elif "WATCHLIST" in args:
            params = self._parse_params(args.replace("WATCHLIST", ""))
            if "id" not in params:
                return False, "LOAD WATCHLIST command requires id parameter"
    
            try:
                watchlist_id = int(params["id"])
                print(f"DEBUG: Attempting to load watchlist ID: {watchlist_id}")  # Debug line
                watchlist = load_watchlist(self.user_id, watchlist_id)
                print(f"DEBUG: Loaded watchlist object: {watchlist}")  # Debug line
                if watchlist is None:
                    return False, f"Could not load watchlist {watchlist_id}"
    
                # Ensure the loaded watchlist has its db_id set using a safe approach
                try:
                    object.__setattr__(watchlist, 'db_id', watchlist_id)
                except:
                    # If we can't set db_id directly, continue without it
                    pass
                    
                self.current_watchlist = watchlist
                print(f"DEBUG: Set current_watchlist to: {self.current_watchlist}")  # Debug line
                
                # Extract watchlist name safely
                watchlist_name = self._safe_extract_value(watchlist.name, "Unknown")
                return True, f"Loaded watchlist '{watchlist_name}' (ID: {watchlist_id})"
            except ValueError:
                return False, "ID must be a number"
    
        else:
            return False, "Invalid LOAD command. Use LOAD PORTFOLIO or LOAD WATCHLIST"
            
    def _handle_list(self, args):
        if not self.user_id:
            return False, "You must be logged in to list items"

        if "PORTFOLIOS" in args:
            portfolios_data = get_user_portfolios(self.user_id)
            if not portfolios_data or not portfolios_data.get('portfolios'):
                return True, "No portfolios found"
            
            portfolio_list = []
            portfolios_list = portfolios_data.get('portfolios', [])
            for p in portfolios_list:
                try:
                    portfolio_id_raw = p.get('id', 0)
                    portfolio_id = int(str(self._safe_extract_value(portfolio_id_raw, 0)))
                    portfolio_name_raw = p.get('name', '')
                    portfolio_name = str(self._safe_extract_value(portfolio_name_raw, ''))
                    created_at_raw = p.get('created_at', '')
                    created_at = str(self._safe_extract_value(created_at_raw, ''))
                    cash_raw = p.get('data', {}).get('portfolio', {}).get('cash', 0)
                    cash = float(str(self._safe_extract_value(cash_raw, 0)))
                    holdings_data = p.get('data', {}).get('portfolio', {}).get('holdings', {})
                    holdings_count = len(holdings_data) if isinstance(holdings_data, dict) else 0
                    
                    portfolio_list.append({
                        "id": portfolio_id,
                        "name": portfolio_name,
                        "created_at": created_at,
                        "cash": cash,
                        "holdings": holdings_count
                    })
                except Exception:
                    continue
            
            return True, {
                "type": "portfolios",
                "count": len(portfolio_list),
                "items": portfolio_list
            }
            
        elif "WATCHLISTS" in args:
            watchlists_data = get_user_watchlists(self.user_id)
            if not watchlists_data or not watchlists_data.get('watchlists'):
                return True, "No watchlists found"
            
            watchlist_list = []
            watchlists_list = watchlists_data.get('watchlists', [])
            for w in watchlists_list:
                try:
                    watchlist_id_raw = w.get('id', 0)
                    watchlist_id = int(str(self._safe_extract_value(watchlist_id_raw, 0)))
                    watchlist_name_raw = w.get('name', '')
                    watchlist_name = str(self._safe_extract_value(watchlist_name_raw, ''))
                    created_at_raw = w.get('created_at', '')
                    created_at = str(self._safe_extract_value(created_at_raw, ''))
                    watchlist_summary = w.get('watchlist_summary', [])
                    symbol_count = len(watchlist_summary) if isinstance(watchlist_summary, list) else 0
                    
                    watchlist_list.append({
                        "id": watchlist_id,
                        "name": watchlist_name,
                        "created_at": created_at,
                        "symbol_count": symbol_count
                    })
                except Exception:
                    continue
            
            return True, {
                "type": "watchlists",
                "count": len(watchlist_list),
                "items": watchlist_list
            }
            
        elif "STRATEGIES" in args:
            manager = StrategyManager()
            success, result = manager.list_strategies(str(self.user_id))
            if not success:
                return False, result
            
            strategy_list = []
            # Ensure result is iterable
            try:
                iterable_result = list(result) if hasattr(result, '__iter__') else []
            except:
                return False, "Invalid result format"
                
            for s in iterable_result:
                # Handle case where item might be a string or other non-dict type
                if not isinstance(s, dict):
                    continue
                    
                try:
                    strategy_id_raw = s.get("id", 0)
                    strategy_id = int(str(self._safe_extract_value(strategy_id_raw, 0)))
                    strategy_name_raw = s.get("name", "")
                    strategy_name = str(self._safe_extract_value(strategy_name_raw, ""))
                    strategy_symbol_raw = s.get("symbol", "")
                    strategy_symbol = str(self._safe_extract_value(strategy_symbol_raw, ""))
                    strategy_type_raw = s.get("strategy_type", "")
                    strategy_type = str(self._safe_extract_value(strategy_type_raw, ""))
                    portfolio_name_raw = s.get("portfolio_name", "")
                    portfolio_name = str(self._safe_extract_value(portfolio_name_raw, ""))
                    is_active_raw = s.get("is_active", False)
                    is_active = bool(self._safe_extract_value(is_active_raw, False))
                    last_executed_raw = s.get("last_executed", "Never")
                    last_executed = str(self._safe_extract_value(last_executed_raw, "Never"))
                    
                    strategy_list.append({
                        "id": strategy_id,
                        "name": strategy_name,
                        "symbol": strategy_symbol,
                        "type": strategy_type,
                        "portfolio": portfolio_name,
                        "active": is_active,
                        "last_executed": last_executed
                    })
                except Exception:
                    continue
            
            return True, {
                "type": "strategies",
                "count": len(strategy_list),
                "items": strategy_list
            }
        else:
            return False, "Invalid LIST command. Use LIST PORTFOLIOS, LIST WATCHLISTS, or LIST STRATEGIES"

    def _parse_params(self, args):
        """Parse key-value pairs from command arguments."""
        params = {}
        for pair in args.split():
            if "=" in pair:
                # Handle cases where there might be spaces around the equals sign
                parts = pair.split("=")
                if len(parts) >= 2:
                    key = parts[0].strip()
                    value = "=".join(parts[1:]).strip().strip('"\'')
                    params[key] = value
        return params


def print_help(return_output=False):
    help_text = """
QuarkScript - Stock Trading System Command Reference

Portfolio Management:
  CREATE PORTFOLIO name=<name> cash=<amount> - Create new portfolio (automatically saved and loaded)
  LOAD PORTFOLIO id=<id>                    - Load existing portfolio
  VIEW PORTFOLIO                            - View current portfolio
  BUY symbol=<symbol> quantity=<shares> [id=<portfolio_id>]     - Buy shares in current portfolio or specific portfolio
  SELL symbol=<symbol> quantity=<shares> [id=<portfolio_id>]    - Sell shares from current portfolio or specific portfolio
  SAVE                                      - Save current portfolio/watchlist

Watchlist Management:
  CREATE WATCHLIST name=<name>              - Create new watchlist (automatically saved and loaded)
  LOAD WATCHLIST id=<id>                    - Load existing watchlist
  VIEW WATCHLIST                            - View current watchlist
  ADD TO WATCHLIST symbol=<symbol> [notes=<text>] - Add stock to watchlist
  REMOVE FROM WATCHLIST symbol=<symbol>     - Remove stock from watchlist
  SAVE                                      - Save current portfolio/watchlist

Strategy Management:
  STRATEGY CREATE name=<name> symbol=<symbol> type=<MOMENTUM|BOLLINGER|MACROSS|...> [params...]
    - Create new trading strategy
  STRATEGY LIST                             - List all strategies
  STRATEGY DELETE id=<id>                   - Delete a strategy
  STRATEGY ENABLE id=<id>                   - Enable a strategy
  STRATEGY DISABLE id=<id>                  - Disable a strategy
  RUN STRATEGY name=<name> symbol=<symbol> [params...] - Run strategy manually

Algorithm Management:
  USE_ALGO <type> [params...]               - Create algorithm from template (rsi, mean_reversion, momentum, volume_breakout, quantum_momentum, alpha_convergence, volatility_breakout, smart_money_flow)
  CREATE_ALGO                               - Create custom algorithm (not yet implemented)
  LIST_ALGOS                                - List all user algorithms
  GET_ALGO id=<id>                          - Get details of a specific algorithm
  DELETE_ALGO id=<id>                       - Delete an algorithm
  RUN_BACKTEST id=<id> [symbol=<symbol>] [start_date=<YYYY-MM-DD>] [end_date=<YYYY-MM-DD>] [initial_cash=<amount>]
    - Run backtest on an algorithm

Price Information:
  PRICE symbol=<symbol>                     - Get current stock price
  HISTORICAL_PRICE symbol=<symbol> date=<YYYY-MM-DD> - Get historical price
  COMPARE_PRICE symbol=<symbol> start_date=<YYYY-MM-DD> [end_date=<YYYY-MM-DD>]
    - Compare prices between dates

Listing Items:
  LIST PORTFOLIOS                           - List all portfolios
  LIST WATCHLISTS                           - List all watchlists
  LIST STRATEGIES                           - List all strategies

Analysis:
  GENERATE ADVICE symbol=<symbol>           - Generate trading advice for stock

Command History:
  HISTORY [limit=<number>]                  - Show command history
  REPEAT index=<number>                     - Repeat command from history

Other:
  HELP                                      - Show this help message
  EXIT                                      - Exit QuarkScript
  QUIT                                      - Exit QuarkScript

Strategy Parameters:
  MOMENTUM: lookback_days=<14> threshold=<0.05>
  BOLLINGER: window=<20> num_std=<2>
  MACROSS: short_window=<50> long_window=<200>
  RSI: window=<14> overbought=<70> oversold=<30>
  MACD: fast=<12> slow=<26> signal=<9>
  MEANREVERSION: window=<20> z_threshold=<2>
  BREAKOUT: window=<20> multiplier=<1.01>
  VOLUMESPIKE: window=<20> multiplier=<2.5>
  KELTNER: window=<20> atr_multiplier=<2>
  STOCHASTIC: k_window=<14> d_window=<3> overbought=<80> oversold=<20>
  PARABOLICSAR: acceleration=<0.02> maximum=<0.2>
"""
    if return_output:
        return help_text
    print(help_text)

def quark_script_main(user_id=None):
    interpreter = QuarkScriptInterpreter(user_id)
    print("Welcome to QuarkScript! Type your commands below (separate multiple commands with semicolons).")
    print("Type 'HELP' for available commands.")

    while True:
        try:
            command = input("QuarkScript> ")
            success, message = interpreter.execute(command)
            
            if isinstance(message, dict):
                # Pretty print dictionaries
                print(json.dumps(message, indent=2))
            elif isinstance(message, list):
                # Print lists with numbering
                for i, item in enumerate(message, 1):
                    print(f"{i}. {item}")
            else:
                print(message)
                
            if success and (command.upper().startswith("EXIT") or command.upper().startswith("QUIT")): 
                break

        except KeyboardInterrupt:
            print("\nExiting QuarkScript.")
            break
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    # For testing without auth:
    quark_script_main()