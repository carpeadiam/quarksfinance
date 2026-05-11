import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import sqlite3
import uuid
algorithm_manager = None
def init_algorithm_manager():
    """Initialize the algorithm manager"""
    global algorithm_manager
    algorithm_manager = UserAlgorithmManager()

class IndicatorCalculator:
    """Calculate technical indicators for custom algorithms"""
    
    @staticmethod
    def calculate_rsi(data: pd.DataFrame, period: int = 14, price_col: str = 'CLOSE') -> pd.Series:
        """Calculate RSI indicator"""
        delta = data[price_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        # Ensure we always return a pandas Series with proper fillna handling
        if isinstance(rsi, pd.Series):
            return rsi.fillna(50)
        else:
            # Convert to Series if it's not already (shouldn't happen in normal cases)
            return pd.Series(rsi, index=data.index).fillna(50)
    
    @staticmethod
    def calculate_macd(data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, price_col: str = 'CLOSE') -> Dict[str, pd.Series]:
        """Calculate MACD indicator"""
        ema_fast = data[price_col].ewm(span=fast).mean()
        ema_slow = data[price_col].ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def calculate_bollinger_bands(data: pd.DataFrame, period: int = 20, std: float = 2, price_col: str = 'CLOSE') -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = data[price_col].rolling(window=period).mean()
        rolling_std = data[price_col].rolling(window=period).std()
        upper_band = sma + (rolling_std * std)
        lower_band = sma - (rolling_std * std)
        
        return {
            'middle': sma,
            'upper': upper_band,
            'lower': lower_band,
            'bb_percent': ((data[price_col] - lower_band) / (upper_band - lower_band)) * 100
        }
    
    @staticmethod
    def calculate_sma(data: pd.DataFrame, period: int = 20, price_col: str = 'CLOSE') -> pd.Series:
        """Calculate Simple Moving Average"""
        result = data[price_col].rolling(window=period).mean()
        # Ensure we always return a pandas Series
        if isinstance(result, pd.Series):
            return result
        else:
            return pd.Series(result, index=data.index)
    
    @staticmethod
    def calculate_ema(data: pd.DataFrame, period: int = 20, price_col: str = 'CLOSE') -> pd.Series:
        """Calculate Exponential Moving Average"""
        result = data[price_col].ewm(span=period).mean()
        # Ensure we always return a pandas Series
        if isinstance(result, pd.Series):
            return result
        else:
            return pd.Series(result, index=data.index)
    
    @staticmethod
    def calculate_stochastic(data: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator"""
        high_max = data['HIGH'].rolling(window=k_period).max()
        low_min = data['LOW'].rolling(window=k_period).min()
        k_percent = ((data['CLOSE'] - low_min) / (high_max - low_min)) * 100
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'k_percent': k_percent.fillna(50),
            'd_percent': d_percent.fillna(50)
        }
    
    @staticmethod
    def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = data['HIGH'] - data['LOW']
        high_close_prev = (data['HIGH'] - data['CLOSE'].shift()).abs()
        low_close_prev = (data['LOW'] - data['CLOSE'].shift()).abs()
        
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        # Ensure we always return a pandas Series with proper fillna handling
        if isinstance(atr, pd.Series):
            return atr.fillna(0)
        else:
            # Convert to Series if it's not already (shouldn't happen in normal cases)
            return pd.Series(atr, index=data.index).fillna(0)
    
    @staticmethod
    def calculate_williams_r(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Williams %R oscillator"""
        high_max = data['HIGH'].rolling(window=period).max()
        low_min = data['LOW'].rolling(window=period).min()
        williams_r = ((high_max - data['CLOSE']) / (high_max - low_min)) * -100
        return williams_r.fillna(-50)
    
    @staticmethod
    def calculate_cci(data: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Commodity Channel Index"""
        typical_price = (data['HIGH'] + data['LOW'] + data['CLOSE']) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mean_deviation = typical_price.rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - x.mean()))
        )
        cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
        return cci.fillna(0)
    
    @staticmethod
    def calculate_adx(data: pd.DataFrame, period: int = 14) -> Dict[str, pd.Series]:
        """Calculate Average Directional Index"""
        high_diff = data['HIGH'].diff()
        low_diff = data['LOW'].diff()
        
        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), -low_diff, 0)
        
        atr = IndicatorCalculator.calculate_atr(data, period)
        
        plus_di_series = pd.Series(plus_dm, index=data.index).rolling(window=period).sum() / atr * 100
        minus_di_series = pd.Series(minus_dm, index=data.index).rolling(window=period).sum() / atr * 100
        
        dx_values = 100 * np.abs(plus_di_series - minus_di_series) / (plus_di_series + minus_di_series)
        dx_series = pd.Series(dx_values, index=data.index)
        adx = dx_series.rolling(window=period).mean()
        
        # Ensure all results are pandas Series
        def ensure_series(val, index):
            if isinstance(val, pd.Series):
                return val.fillna(0)
            else:
                return pd.Series(val, index=index).fillna(0)
        
        return {
            'adx': ensure_series(adx, data.index),
            'plus_di': ensure_series(plus_di_series, data.index),
            'minus_di': ensure_series(minus_di_series, data.index)
        }
    
    @staticmethod
    def calculate_obv(data: pd.DataFrame) -> pd.Series:
        """Calculate On-Balance Volume"""
        obv = [0]
        for i in range(1, len(data)):
            if data['CLOSE'].iloc[i] > data['CLOSE'].iloc[i-1]:
                obv.append(obv[-1] + data['VOLUME'].iloc[i])
            elif data['CLOSE'].iloc[i] < data['CLOSE'].iloc[i-1]:
                obv.append(obv[-1] - data['VOLUME'].iloc[i])
            else:
                obv.append(obv[-1])
        return pd.Series(obv, index=data.index)
    
    @staticmethod
    def calculate_vwap(data: pd.DataFrame) -> pd.Series:
        """Calculate Volume Weighted Average Price"""
        typical_price = (data['HIGH'] + data['LOW'] + data['CLOSE']) / 3
        volume_price = typical_price * data['VOLUME']
        cumulative_volume_price = volume_price.cumsum()
        cumulative_volume = data['VOLUME'].cumsum()
        vwap = cumulative_volume_price / cumulative_volume
        return vwap.fillna(data['CLOSE'])
    
    @staticmethod
    def calculate_mfi(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Money Flow Index"""
        typical_price = (data['HIGH'] + data['LOW'] + data['CLOSE']) / 3
        raw_money_flow = typical_price * data['VOLUME']
        
        positive_flow = []
        negative_flow = []
        
        for i in range(1, len(typical_price)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.append(raw_money_flow.iloc[i])
                negative_flow.append(0)
            elif typical_price.iloc[i] < typical_price.iloc[i-1]:
                positive_flow.append(0)
                negative_flow.append(raw_money_flow.iloc[i])
            else:
                positive_flow.append(0)
                negative_flow.append(0)
        
        positive_flow = [0] + positive_flow
        negative_flow = [0] + negative_flow
        
        pos_mf = pd.Series(positive_flow, index=data.index).rolling(window=period).sum()
        neg_mf = pd.Series(negative_flow, index=data.index).rolling(window=period).sum()
        
        mfi = 100 - (100 / (1 + (pos_mf / neg_mf)))
        # Ensure we always return a pandas Series
        if isinstance(mfi, pd.Series):
            return mfi.fillna(50)
        else:
            return pd.Series(mfi, index=data.index).fillna(50)

class StrategyCondition:
    """Represents a single strategy condition (e.g., RSI > 70)"""
    
    def __init__(self, condition_data: dict):
        self.id = condition_data.get('id')
        self.indicator_type = condition_data.get('indicator_type')
        self.indicator_params = condition_data.get('indicator_params', {})
        self.comparison = condition_data.get('comparison')  # '>', '<', '>=', '<=', '==', 'crosses_above', 'crosses_below'
        self.value = condition_data.get('value')
        self.timeframe = condition_data.get('timeframe', 0)  # lookback periods
        
    def evaluate(self, data: pd.DataFrame, calculator: IndicatorCalculator) -> pd.Series:
        """Evaluate condition against data and return boolean series"""
        # Calculate the indicator
        if self.indicator_type == 'RSI':
            period = self.indicator_params.get('period', 14)
            indicator_values = calculator.calculate_rsi(data, period)
        elif self.indicator_type == 'MACD':
            fast = self.indicator_params.get('fast', 12)
            slow = self.indicator_params.get('slow', 26)
            signal = self.indicator_params.get('signal', 9)
            macd_data = calculator.calculate_macd(data, fast, slow, signal)
            # For MACD, we might want to check MACD line, signal line, or histogram
            component = self.indicator_params.get('component', 'macd')
            indicator_values = macd_data[component]
        elif self.indicator_type == 'BOLLINGER':
            period = self.indicator_params.get('period', 20)
            std = self.indicator_params.get('std', 2)
            bb_data = calculator.calculate_bollinger_bands(data, period, std)
            component = self.indicator_params.get('component', 'bb_percent')
            indicator_values = bb_data[component]
        elif self.indicator_type == 'SMA':
            period = self.indicator_params.get('period', 20)
            indicator_values = calculator.calculate_sma(data, period)
        elif self.indicator_type == 'EMA':
            period = self.indicator_params.get('period', 20)
            indicator_values = calculator.calculate_ema(data, period)
        elif self.indicator_type == 'STOCHASTIC':
            k_period = self.indicator_params.get('k_period', 14)
            d_period = self.indicator_params.get('d_period', 3)
            stoch_data = calculator.calculate_stochastic(data, k_period, d_period)
            component = self.indicator_params.get('component', 'k_percent')
            indicator_values = stoch_data[component]
        elif self.indicator_type == 'WILLIAMS_R':
            period = self.indicator_params.get('period', 14)
            indicator_values = calculator.calculate_williams_r(data, period)
        elif self.indicator_type == 'CCI':
            period = self.indicator_params.get('period', 20)
            indicator_values = calculator.calculate_cci(data, period)
        elif self.indicator_type == 'ADX':
            period = self.indicator_params.get('period', 14)
            adx_data = calculator.calculate_adx(data, period)
            component = self.indicator_params.get('component', 'adx')
            indicator_values = adx_data[component]
        elif self.indicator_type == 'OBV':
            indicator_values = calculator.calculate_obv(data)
        elif self.indicator_type == 'VWAP':
            indicator_values = calculator.calculate_vwap(data)
        elif self.indicator_type == 'MFI':
            period = self.indicator_params.get('period', 14)
            indicator_values = calculator.calculate_mfi(data, period)
        elif self.indicator_type == 'PRICE':
            indicator_values = data['CLOSE']
        elif self.indicator_type == 'VOLUME':
            indicator_values = data['VOLUME']
        else:
            # Default to price if unknown indicator
            indicator_values = data['CLOSE']
        
        # Apply timeframe shift if needed
        if self.timeframe > 0:
            indicator_values = indicator_values.shift(self.timeframe)
        
        # Apply comparison
        if self.comparison == '>':
            return indicator_values > self.value
        elif self.comparison == '<':
            return indicator_values < self.value
        elif self.comparison == '>=':
            return indicator_values >= self.value
        elif self.comparison == '<=':
            return indicator_values <= self.value
        elif self.comparison == '==':
            return indicator_values == self.value
        elif self.comparison == 'crosses_above':
            return (indicator_values > self.value) & (indicator_values.shift(1) <= self.value)
        elif self.comparison == 'crosses_below':
            return (indicator_values < self.value) & (indicator_values.shift(1) >= self.value)
        else:
            return pd.Series([False] * len(data), index=data.index)

class StrategyRule:
    """Represents a trading rule with multiple conditions"""
    
    def __init__(self, rule_data: dict):
        self.id = rule_data.get('id')
        self.name = rule_data.get('name')
        self.signal_type = rule_data.get('signal_type')  # 'BUY', 'SELL', 'HOLD'
        self.conditions = [StrategyCondition(cond) for cond in rule_data.get('conditions', [])]
        self.logic_operator = rule_data.get('logic_operator', 'AND')  # 'AND', 'OR', 'MAJORITY'
        self.weight = rule_data.get('weight', 1.0)
        
    def evaluate(self, data: pd.DataFrame, calculator: IndicatorCalculator) -> pd.Series:
        """Evaluate all conditions in the rule"""
        if not self.conditions:
            return pd.Series([False] * len(data), index=data.index)
        
        # Evaluate all conditions
        condition_results = []
        for condition in self.conditions:
            result = condition.evaluate(data, calculator)
            condition_results.append(result)
        
        # Combine conditions based on logic operator
        if self.logic_operator == 'AND':
            final_result = condition_results[0]
            for result in condition_results[1:]:
                final_result = final_result & result
        elif self.logic_operator == 'OR':
            final_result = condition_results[0]
            for result in condition_results[1:]:
                final_result = final_result | result
        elif self.logic_operator == 'MAJORITY':
            # At least half of conditions must be true
            condition_sum = sum(condition_results)
            final_result = condition_sum >= (len(condition_results) / 2)
        else:
            # Default to AND
            final_result = condition_results[0]
            for result in condition_results[1:]:
                final_result = final_result & result
        
        # Ensure we return a boolean Series with proper fillna handling
        if isinstance(final_result, pd.Series):
            return final_result.fillna(False)
        else:
            # Convert to Series if it's not already
            return pd.Series(final_result, index=data.index).fillna(False)

class RiskManager:
    """Risk management system for trading algorithms"""
    
    def __init__(self, risk_config: dict):
        self.max_position_size = risk_config.get('max_position_size', 0.1)  # 10% of portfolio
        self.stop_loss_pct = risk_config.get('stop_loss_pct', 0.02)  # 2% stop loss
        self.take_profit_pct = risk_config.get('take_profit_pct', 0.06)  # 6% take profit
        self.max_daily_loss = risk_config.get('max_daily_loss', 0.05)  # 5% max daily loss
        self.max_drawdown = risk_config.get('max_drawdown', 0.15)  # 15% max drawdown
        self.position_sizing_method = risk_config.get('position_sizing_method', 'fixed')  # 'fixed', 'volatility', 'kelly'
        self.volatility_lookback = risk_config.get('volatility_lookback', 20)
        
    def calculate_position_size(self, portfolio_value: float, price: float, 
                              volatility: Optional[float] = None) -> int:
        """Calculate position size based on risk management rules"""
        max_investment = portfolio_value * self.max_position_size
        
        if self.position_sizing_method == 'fixed':
            return int(max_investment / price)
        elif self.position_sizing_method == 'volatility' and volatility:
            # Inverse volatility weighting
            volatility_factor = 1 / (volatility + 0.01)  # Add small value to avoid division by zero
            adjusted_investment = max_investment * min(volatility_factor, 2.0)  # Cap at 2x
            return int(adjusted_investment / price)
        else:
            return int(max_investment / price)
    
    def check_stop_loss(self, entry_price: float, current_price: float, position_type: str) -> bool:
        """Check if stop loss should be triggered"""
        if position_type == 'LONG':
            return current_price <= entry_price * (1 - self.stop_loss_pct)
        elif position_type == 'SHORT':
            return current_price >= entry_price * (1 + self.stop_loss_pct)
        return False
    
    def check_take_profit(self, entry_price: float, current_price: float, position_type: str) -> bool:
        """Check if take profit should be triggered"""
        if position_type == 'LONG':
            return current_price >= entry_price * (1 + self.take_profit_pct)
        elif position_type == 'SHORT':
            return current_price <= entry_price * (1 - self.take_profit_pct)
        return False
    
    def check_daily_loss_limit(self, daily_pnl: float, portfolio_value: float) -> bool:
        """Check if daily loss limit is exceeded"""
        daily_loss_pct = abs(daily_pnl) / portfolio_value
        return daily_loss_pct >= self.max_daily_loss
    
    def calculate_drawdown(self, portfolio_values: List[float]) -> float:
        """Calculate current drawdown"""
        if len(portfolio_values) < 2:
            return 0.0
        
        peak = max(portfolio_values)
        current_value = portfolio_values[-1]
        drawdown = (peak - current_value) / peak
        return drawdown
    
    def check_max_drawdown(self, portfolio_values: List[float]) -> bool:
        """Check if maximum drawdown is exceeded"""
        current_drawdown = self.calculate_drawdown(portfolio_values)
        return current_drawdown >= self.max_drawdown

class PerformanceAnalyzer:
    """Analyze trading performance and generate metrics"""
    
    @staticmethod
    def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if returns.std() == 0:
            return 0.0
        excess_returns = returns.mean() - risk_free_rate / 252  # Daily risk-free rate
        return excess_returns / returns.std() * np.sqrt(252)  # Annualized
    
    @staticmethod
    def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio (using downside deviation)"""
        excess_returns = returns - risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0
        return excess_returns.mean() / downside_returns.std() * np.sqrt(252)
    
    @staticmethod
    def calculate_max_drawdown(portfolio_values: List[float]) -> dict:
        """Calculate maximum drawdown and related metrics"""
        values = np.array(portfolio_values)
        peak = np.maximum.accumulate(values)
        drawdown = (peak - values) / peak
        
        max_dd = np.max(drawdown)
        max_dd_idx = np.argmax(drawdown)
        
        # Find the peak before max drawdown
        peak_idx = np.argmax(values[:max_dd_idx + 1]) if max_dd_idx > 0 else 0
        
        return {
            'max_drawdown': max_dd,
            'max_drawdown_duration': max_dd_idx - peak_idx,
            'peak_index': peak_idx,
            'trough_index': max_dd_idx
        }
    
    @staticmethod
    def calculate_win_rate(trades: List[dict]) -> dict:
        """Calculate win rate and related trading metrics"""
        if not trades:
            return {
                'win_rate': 0, 
                'total_trades': 0, 
                'winning_trades': 0, 
                'losing_trades': 0,
                'average_win': 0,
                'average_loss': 0,
                'profit_factor': 0
            }
        
        winning_trades = 0
        losing_trades = 0
        total_profit = 0
        total_loss = 0
        
        for i in range(0, len(trades) - 1, 2):  # Buy and sell pairs
            if i + 1 < len(trades):
                buy_trade = trades[i]
                sell_trade = trades[i + 1]
                
                # FIX: Use 'type' key instead of 'action' key
                # The trades are created with 'type' key in the backtest method
                buy_action = buy_trade.get('type', 'BUY')  # Default to BUY if type is missing
                sell_action = sell_trade.get('type', 'SELL')  # Default to SELL if type is missing
                
                if buy_action == 'BUY' and sell_action == 'SELL':
                    pnl = sell_trade['value'] - buy_trade['value']
                    if pnl > 0:
                        winning_trades += 1
                        total_profit += pnl
                    else:
                        losing_trades += 1
                        total_loss += abs(pnl)
        
        total_trades = winning_trades + losing_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        avg_win = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        # Handle case where there are no losing trades
        if total_loss == 0:
            if total_profit > 0:
                profit_factor = float('inf')  # Infinite profit factor
            else:
                profit_factor = 0  # No profit, no loss
        else:
            profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        return {
            'win_rate': win_rate,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'average_win': avg_win,
            'average_loss': avg_loss,
            'profit_factor': profit_factor
        }

class MultiStrategyDecision:
    """Handles multi-strategy decision making (e.g., 2 out of 3 strategies say BUY)"""
    
    def __init__(self, decision_config: dict):
        self.strategy_weights = decision_config.get('strategy_weights', {})
        self.decision_threshold = decision_config.get('decision_threshold', 0.5)  # 0.5 = majority
        self.require_unanimous = decision_config.get('require_unanimous', False)
        
    def make_decision(self, strategy_signals: Dict[str, str]) -> str:
        """
        Make final trading decision based on multiple strategy signals
        Args:
            strategy_signals: Dict of strategy_name -> signal ('BUY', 'SELL', 'HOLD')
        Returns:
            Final signal: 'BUY', 'SELL', or 'HOLD'
        """
        if not strategy_signals:
            return 'HOLD'
        
        buy_weight = 0
        sell_weight = 0
        total_weight = 0
        
        for strategy_name, signal in strategy_signals.items():
            weight = self.strategy_weights.get(strategy_name, 1.0)
            total_weight += weight
            
            if signal == 'BUY':
                buy_weight += weight
            elif signal == 'SELL':
                sell_weight += weight
        
        if total_weight == 0:
            return 'HOLD'
        
        buy_ratio = buy_weight / total_weight
        sell_ratio = sell_weight / total_weight
        
        if self.require_unanimous:
            if buy_ratio == 1.0:
                return 'BUY'
            elif sell_ratio == 1.0:
                return 'SELL'
            else:
                return 'HOLD'
        else:
            if buy_ratio >= self.decision_threshold:
                return 'BUY'
            elif sell_ratio >= self.decision_threshold:
                return 'SELL'
            else:
                return 'HOLD'

class CustomAlgorithm:
    """Main custom algorithm class"""
    
    def __init__(self, algorithm_config: dict):
        self.id = algorithm_config.get('id', str(uuid.uuid4()))
        self.name = algorithm_config.get('name')
        self.description = algorithm_config.get('description', '')
        self.user_id = algorithm_config.get('user_id')
        self.created_date = algorithm_config.get('created_date', datetime.now())
        
        # Trading rules
        self.buy_rules = [StrategyRule(rule) for rule in algorithm_config.get('buy_rules', [])]
        self.sell_rules = [StrategyRule(rule) for rule in algorithm_config.get('sell_rules', [])]
        
        # Multi-strategy decision making
        self.multi_strategy_config = algorithm_config.get('multi_strategy_config', {})
        self.multi_strategy_decision = MultiStrategyDecision(self.multi_strategy_config)
        
        # Risk management
        self.risk_management = algorithm_config.get('risk_management', {})
        self.risk_manager = RiskManager(self.risk_management) if self.risk_management else None
        
        # Performance tracking
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Calculator instance
        self.calculator = IndicatorCalculator()
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate buy/sell signals for the given data"""
        signals_df = pd.DataFrame(index=data.index)
        signals_df['signal'] = 'HOLD'
        
        # Evaluate buy rules
        buy_signals = []
        for rule in self.buy_rules:
            rule_result = rule.evaluate(data, self.calculator)
            buy_signals.append(rule_result)
        
        # Evaluate sell rules
        sell_signals = []
        for rule in self.sell_rules:
            rule_result = rule.evaluate(data, self.calculator)
            sell_signals.append(rule_result)
        
        # Combine buy signals (any rule can trigger buy)
        if buy_signals:
            final_buy_signal = buy_signals[0]
            for signal in buy_signals[1:]:
                final_buy_signal = final_buy_signal | signal
            signals_df.loc[final_buy_signal, 'signal'] = 'BUY'
        
        # Combine sell signals (any rule can trigger sell)
        if sell_signals:
            final_sell_signal = sell_signals[0]
            for signal in sell_signals[1:]:
                final_sell_signal = final_sell_signal | signal
            signals_df.loc[final_sell_signal, 'signal'] = 'SELL'
        
        return signals_df
        
    @staticmethod
    def convert_date_safely(date):
        """Safely convert various date types to string format - optimized for yfinance dates"""
        import sys
        
        # Handle None or NaN values
        if date is None or (hasattr(date, 'isna') and date.isna()):
            print(f"Warning: Received None/NaN date, cannot convert", file=sys.stderr)
            return None
        
        try:
            # Handle pandas Timestamp (most common from yfinance)
            if isinstance(date, pd.Timestamp):
                return date.strftime('%Y-%m-%d %H:%M:%S')
            
            # Handle datetime objects
            elif isinstance(date, datetime):
                return date.strftime('%Y-%m-%d %H:%M:%S')
            
            # Handle numpy datetime64
            elif isinstance(date, np.datetime64):
                return pd.to_datetime(date).strftime('%Y-%m-%d %H:%M:%S')
            
            # Handle string dates
            elif isinstance(date, str):
                try:
                    # Try to parse the string as a date
                    parsed_date = pd.to_datetime(date)
                    return parsed_date.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    # If it looks like a date string already, keep it
                    if any(sep in date for sep in ['-', '/', ' ']):
                        return date
                    else:
                        return date
            
            # Handle pandas DatetimeIndex elements or other datetime-like objects
            elif hasattr(date, 'strftime'):
                return date.strftime('%Y-%m-%d %H:%M:%S')
            
            # Handle pandas Period objects
            elif hasattr(date, 'to_timestamp'):
                return date.to_timestamp().strftime('%Y-%m-%d %H:%M:%S')
            
            # Handle other types by converting to pandas datetime first
            else:
                try:
                    # Convert to string first, then parse
                    date_str = str(date)
                    parsed_date = pd.to_datetime(date_str)
                    return parsed_date.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    # Final fallback - return as string representation
                    print(f"Warning: Could not convert date {date} of type {type(date)}: {e}", file=sys.stderr)
                    return str(date)
                    
        except Exception as e:
            print(f"Error in convert_date_safely for {date}: {e}", file=sys.stderr)
            return str(date)
    
    def backtest(self, data: pd.DataFrame, initial_cash: float = 100000) -> dict:
        """Run backtest on the algorithm with enhanced risk management"""
        signals = self.generate_signals(data)
        
        # Enhanced backtest implementation with risk management
        portfolio_value = initial_cash
        cash = initial_cash
        position = 0
        trades = []
        portfolio_values = [initial_cash]
        daily_returns = []
        entry_price = 0
        position_type = None
        daily_pnl = 0
        
        # Reset the index to ensure we have proper date handling
        data_with_date_index = data.copy()
        if 'DATE' in data_with_date_index.columns:
            data_with_date_index = data_with_date_index.set_index('DATE')
        
        for i, (date, row) in enumerate(data_with_date_index.iterrows()):
            signal = signals.loc[date, 'signal']
            price = row['CLOSE']
            
            # Convert the date from the iteration to a proper format
            # This date should be from your historical data, not current date
            historical_date = date  # This is the actual historical date from your data
            
            # Check risk management rules if we have a position
            current_price = float(price)
            if position > 0 and self.risk_manager:
                # Check stop loss
                if self.risk_manager.check_stop_loss(float(entry_price), current_price, 'LONG'):
                    value = position * price
                    cash += value
                    # Use the historical date, not current date
                    date_str = self.convert_date_safely(historical_date)
                    trades.append({
                        'timestamp': date_str,
                        'type': 'SELL',
                        'price': float(price),
                        'quantity': int(position),
                        'symbol': 'STOCK',
                        'value': float(value),
                        'reason': 'STOP_LOSS'
                    })
                    daily_pnl += value - (position * float(entry_price))
                    position = 0
                    position_type = None
                    entry_price = 0
                
                # Check take profit
                elif self.risk_manager.check_take_profit(float(entry_price), current_price, 'LONG'):
                    value = position * price
                    cash += value
                    # Use the historical date, not current date
                    date_str = self.convert_date_safely(historical_date)
                    trades.append({
                        'timestamp': date_str,
                        'type': 'SELL',
                        'price': float(price),
                        'quantity': int(position),
                        'symbol': 'STOCK',
                        'value': float(value),
                        'reason': 'TAKE_PROFIT'
                    })
                    daily_pnl += value - (position * float(entry_price))
                    position = 0
                    position_type = None
                    entry_price = 0
                
                # Check daily loss limit
                elif self.risk_manager.check_daily_loss_limit(float(daily_pnl), float(portfolio_value)):
                    continue  # Skip trading for the rest of the day
                
                # Check maximum drawdown
                elif self.risk_manager.check_max_drawdown(portfolio_values):
                    break  # Stop trading entirely
            
            # Normal trading logic
            if signal == 'BUY' and cash > price and position == 0:
                # Calculate position size with risk management
                if self.risk_manager:
                    volatility_val = data_with_date_index['CLOSE'].rolling(window=self.risk_manager.volatility_lookback).std().iloc[i]
                    volatility_float = float(volatility_val) if pd.notna(volatility_val) else None
                    shares = self.risk_manager.calculate_position_size(float(cash), current_price, volatility_float)
                else:
                    shares = int(cash * 0.95 / current_price)  # Use 95% of cash, leave 5% buffer
                
                if shares > 0:
                    cost = shares * current_price
                    cash -= cost
                    position = shares
                    entry_price = price
                    position_type = 'LONG'
                    # Use the historical date, not current date
                    date_str = self.convert_date_safely(historical_date)
                    trades.append({
                        'timestamp': date_str,
                        'type': 'BUY',
                        'price': float(current_price),
                        'quantity': int(shares),
                        'symbol': 'STOCK',
                        'value': float(cost),
                        'reason': 'SIGNAL'
                    })
                    daily_pnl -= cost
            
            elif signal == 'SELL' and position > 0:
                # Sell
                value = position * current_price
                cash += value
                # Use the historical date, not current date
                date_str = self.convert_date_safely(historical_date)
                trades.append({
                    'timestamp': date_str,
                    'type': 'SELL',
                    'price': float(current_price),
                    'quantity': int(position),
                    'symbol': 'STOCK',
                    'value': float(value),
                    'reason': 'SIGNAL'
                })
                daily_pnl += value - (position * float(entry_price))
                position = 0
                position_type = None
                entry_price = 0
            
            # Update portfolio value and daily returns
            current_portfolio_value = cash + (position * current_price)
            portfolio_values.append(float(current_portfolio_value))
            
            if len(portfolio_values) > 1:
                daily_return = (current_portfolio_value - portfolio_values[-2]) / portfolio_values[-2]
                daily_returns.append(daily_return)
            
            portfolio_value = float(current_portfolio_value)
        
        # Calculate final portfolio value
        final_price = data_with_date_index['CLOSE'].iloc[-1]
        final_value = cash + (position * final_price)
        
        # Calculate comprehensive metrics
        total_return = (final_value - initial_cash) / initial_cash
        returns_series = pd.Series(daily_returns)
        
        # Performance metrics
        sharpe_ratio = self.performance_analyzer.calculate_sharpe_ratio(returns_series)
        sortino_ratio = self.performance_analyzer.calculate_sortino_ratio(returns_series)
        max_drawdown_info = self.performance_analyzer.calculate_max_drawdown(portfolio_values)
        trading_metrics = self.performance_analyzer.calculate_win_rate(trades)
        
        # Volatility metrics
        volatility = returns_series.std() * np.sqrt(252) if len(returns_series) > 0 else 0
        
        # Process trades to ensure proper date formatting
        processed_trades = []
        prev_buy = None
        for trade in trades:
            processed_trade = trade.copy()
            
            # Ensure timestamp is properly formatted
            if 'timestamp' in processed_trade:
                # The timestamp should already be properly formatted by convert_date_safely
                # but ensure it's a string and extract just the date part for the 'date' field
                timestamp_str = str(processed_trade['timestamp'])
                processed_trade['date'] = timestamp_str.split(' ')[0]  # Extract just the date part
            
            # Calculate profit/loss for sell transactions
            if processed_trade.get('type') == 'SELL' and prev_buy:
                pl = (float(processed_trade.get('price', 0)) * int(processed_trade.get('quantity', 0))) - \
                     (float(prev_buy.get('price', 0)) * int(prev_buy.get('quantity', 0)))
                processed_trade['pl'] = pl
            
            # Track the previous buy transaction for P/L calculation
            if processed_trade.get('type') == 'BUY':
                prev_buy = processed_trade
            elif processed_trade.get('type') == 'SELL':
                prev_buy = None
            
            processed_trades.append(processed_trade)
        
        return {
            'initial_cash': initial_cash,
            'final_value': final_value,
            'total_return': total_return,
            'annualized_return': (1 + total_return) ** (252 / len(data)) - 1 if len(data) > 0 else 0,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown_info['max_drawdown'],
            'max_drawdown_duration': max_drawdown_info['max_drawdown_duration'],
            'total_trades': len(trades),
            'win_rate': trading_metrics['win_rate'],
            'profit_factor': trading_metrics['profit_factor'],
            'average_win': trading_metrics['average_win'],
            'average_loss': trading_metrics['average_loss'],
            'trades': processed_trades,
            'portfolio_values': portfolio_values,
            'daily_returns': daily_returns,
            'signals_generated': signals.to_dict('records')
        }
class UserAlgorithmManager:
    """Manages user custom algorithms - database operations"""
    
    def __init__(self, db_path: str = 'user_algorithms.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User algorithms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_algorithms (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                config JSON NOT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Algorithm backtests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS algorithm_backtests (
                id TEXT PRIMARY KEY,
                algorithm_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                start_date DATE,
                end_date DATE,
                initial_cash REAL,
                result JSON,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (algorithm_id) REFERENCES user_algorithms (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_algorithm(self, user_id: str, algorithm_config: dict) -> str:
        """Save a custom algorithm"""
        algorithm_id = algorithm_config.get('id', str(uuid.uuid4()))
        algorithm_config['id'] = algorithm_id
        algorithm_config['user_id'] = user_id
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_algorithms 
            (id, user_id, name, description, config, updated_date)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            algorithm_id,
            user_id,
            algorithm_config.get('name'),
            algorithm_config.get('description', ''),
            json.dumps(algorithm_config)
        ))
        
        conn.commit()
        conn.close()
        
        return algorithm_id
    
    def get_user_algorithms(self, user_id: str) -> List[dict]:
        """Get all algorithms for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, description, config, created_date, updated_date, is_active
            FROM user_algorithms 
            WHERE user_id = ? AND is_active = TRUE
            ORDER BY updated_date DESC
        ''', (user_id,))
        
        algorithms = []
        for row in cursor.fetchall():
            config = json.loads(row[3])
            algorithms.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'config': config,
                'created_date': row[4],
                'updated_date': row[5],
                'is_active': row[6]
            })
        
        conn.close()
        return algorithms
    
    def get_algorithm(self, algorithm_id: str, user_id: str) -> Optional[dict]:
        """Get a specific algorithm"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, description, config, created_date, updated_date
            FROM user_algorithms 
            WHERE id = ? AND user_id = ? AND is_active = TRUE
        ''', (algorithm_id, user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            config = json.loads(row[3])
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'config': config,
                'created_date': row[4],
                'updated_date': row[5]
            }
        return None
    
    def delete_algorithm(self, algorithm_id: str, user_id: str) -> bool:
        """Delete (deactivate) an algorithm"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE user_algorithms 
            SET is_active = FALSE, updated_date = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (algorithm_id, user_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def save_backtest_result(self, algorithm_id: str, symbol: str, start_date: str, 
                           end_date: str, initial_cash: float, result: dict) -> str:
        """Save backtest result"""
        backtest_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO algorithm_backtests 
            (id, algorithm_id, symbol, start_date, end_date, initial_cash, result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            backtest_id,
            algorithm_id,
            symbol,
            start_date,
            end_date,
            initial_cash,
            json.dumps(result)
        ))
        
        conn.commit()
        conn.close()
        
        return backtest_id

# Utility functions for common algorithm patterns
def create_rsi_oversold_algorithm(rsi_period: int = 14, oversold_level: int = 30, 
                                overbought_level: int = 70) -> dict:
    """Create a simple RSI-based algorithm"""
    return {
        'name': f'RSI {rsi_period} Strategy',
        'description': f'Buy when RSI < {oversold_level}, sell when RSI > {overbought_level}',
        'buy_rules': [{
            'id': 'rsi_buy_rule',
            'name': 'RSI Oversold',
            'signal_type': 'BUY',
            'conditions': [{
                'id': 'rsi_oversold',
                'indicator_type': 'RSI',
                'indicator_params': {'period': rsi_period},
                'comparison': '<',
                'value': oversold_level
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
                'indicator_params': {'period': rsi_period},
                'comparison': '>',
                'value': overbought_level
            }],
            'logic_operator': 'AND'
        }]
    }

def create_multi_strategy_algorithm(strategies_config: List[dict], 
                                  decision_threshold: float = 0.6) -> dict:
    """Create an algorithm that combines multiple strategies"""
    buy_rules = []
    sell_rules = []
    
    for i, strategy in enumerate(strategies_config):
        strategy_id = f'strategy_{i}'
        
        # Add buy rule for this strategy
        if 'buy_conditions' in strategy:
            buy_rules.append({
                'id': f'{strategy_id}_buy',
                'name': f'{strategy.get("name", strategy_id)} Buy',
                'signal_type': 'BUY',
                'conditions': strategy['buy_conditions'],
                'logic_operator': strategy.get('buy_logic', 'AND'),
                'weight': strategy.get('weight', 1.0)
            })
        
        # Add sell rule for this strategy  
        if 'sell_conditions' in strategy:
            sell_rules.append({
                'id': f'{strategy_id}_sell',
                'name': f'{strategy.get("name", strategy_id)} Sell',
                'signal_type': 'SELL',
                'conditions': strategy['sell_conditions'],
                'logic_operator': strategy.get('sell_logic', 'AND'),
                'weight': strategy.get('weight', 1.0)
            })
    
    return {
        'name': 'Multi-Strategy Algorithm',
        'description': f'Combines {len(strategies_config)} strategies with {decision_threshold} decision threshold',
        'buy_rules': buy_rules,
        'sell_rules': sell_rules,
        'multi_strategy_config': {
            'decision_threshold': decision_threshold,
            'strategy_weights': {f'strategy_{i}': s.get('weight', 1.0) 
                               for i, s in enumerate(strategies_config)}
        }
    }

def create_mean_reversion_algorithm(bb_period: int = 20, bb_std: float = 2, 
                                  rsi_period: int = 14, rsi_oversold: int = 30, 
                                  rsi_overbought: int = 70) -> dict:
    """Create a mean reversion algorithm using Bollinger Bands and RSI"""
    return {
        'name': f'Mean Reversion Strategy (BB {bb_period}, RSI {rsi_period})',
        'description': f'Buy when price touches lower BB and RSI < {rsi_oversold}, sell when price touches upper BB and RSI > {rsi_overbought}',
        'buy_rules': [{
            'id': 'mean_reversion_buy',
            'name': 'Mean Reversion Buy',
            'signal_type': 'BUY',
            'conditions': [
                {
                    'id': 'bb_lower_touch',
                    'indicator_type': 'BOLLINGER',
                    'indicator_params': {'period': bb_period, 'std': bb_std, 'component': 'bb_percent'},
                    'comparison': '<=',
                    'value': 5  # Price near lower band (5% or less)
                },
                {
                    'id': 'rsi_oversold',
                    'indicator_type': 'RSI',
                    'indicator_params': {'period': rsi_period},
                    'comparison': '<',
                    'value': rsi_oversold
                }
            ],
            'logic_operator': 'AND'
        }],
        'sell_rules': [{
            'id': 'mean_reversion_sell',
            'name': 'Mean Reversion Sell',
            'signal_type': 'SELL',
            'conditions': [
                {
                    'id': 'bb_upper_touch',
                    'indicator_type': 'BOLLINGER',
                    'indicator_params': {'period': bb_period, 'std': bb_std, 'component': 'bb_percent'},
                    'comparison': '>=',
                    'value': 95  # Price near upper band (95% or more)
                },
                {
                    'id': 'rsi_overbought',
                    'indicator_type': 'RSI',
                    'indicator_params': {'period': rsi_period},
                    'comparison': '>',
                    'value': rsi_overbought
                }
            ],
            'logic_operator': 'AND'
        }],
        'risk_management': {
            'stop_loss_pct': 0.03,
            'take_profit_pct': 0.08,
            'max_position_size': 0.15
        }
    }

def create_momentum_algorithm(ema_fast: int = 12, ema_slow: int = 26, 
                            adx_period: int = 14, adx_threshold: int = 25) -> dict:
    """Create a momentum-based algorithm using EMA crossover and ADX"""
    return {
        'name': f'Momentum Strategy (EMA {ema_fast}/{ema_slow}, ADX {adx_period})',
        'description': f'Buy on EMA crossover with strong trend (ADX > {adx_threshold}), sell on reverse crossover',
        'buy_rules': [{
            'id': 'momentum_buy',
            'name': 'Momentum Buy',
            'signal_type': 'BUY',
            'conditions': [
                {
                    'id': 'ema_crossover',
                    'indicator_type': 'EMA',
                    'indicator_params': {'period': ema_fast},
                    'comparison': 'crosses_above',
                    'value': 'EMA_SLOW'  # This would need special handling in evaluation
                },
                {
                    'id': 'strong_trend',
                    'indicator_type': 'ADX',
                    'indicator_params': {'period': adx_period, 'component': 'adx'},
                    'comparison': '>',
                    'value': adx_threshold
                }
            ],
            'logic_operator': 'AND'
        }],
        'sell_rules': [{
            'id': 'momentum_sell',
            'name': 'Momentum Sell',
            'signal_type': 'SELL',
            'conditions': [
                {
                    'id': 'ema_reverse_crossover',
                    'indicator_type': 'EMA',
                    'indicator_params': {'period': ema_fast},
                    'comparison': 'crosses_below',
                    'value': 'EMA_SLOW'
                }
            ],
            'logic_operator': 'AND'
        }],
        'risk_management': {
            'stop_loss_pct': 0.04,
            'take_profit_pct': 0.12,
            'max_position_size': 0.12,
            'position_sizing_method': 'volatility'
        }
    }

def create_volume_breakout_algorithm(volume_multiplier: float = 2.0, 
                                   price_breakout_pct: float = 0.02) -> dict:
    """Create a volume breakout algorithm"""
    return {
        'name': f'Volume Breakout Strategy ({volume_multiplier}x volume, {price_breakout_pct*100}% breakout)',
        'description': f'Buy on high volume breakouts above recent highs',
        'buy_rules': [{
            'id': 'volume_breakout_buy',
            'name': 'Volume Breakout Buy',
            'signal_type': 'BUY',
            'conditions': [
                {
                    'id': 'high_volume',
                    'indicator_type': 'VOLUME',
                    'indicator_params': {},
                    'comparison': '>',
                    'value': f'{volume_multiplier}x_avg_volume'  # Would need special handling
                },
                {
                    'id': 'price_breakout',
                    'indicator_type': 'PRICE',
                    'indicator_params': {},
                    'comparison': '>',
                    'value': f'20_day_high * {1 + price_breakout_pct}'  # Would need special handling
                }
            ],
            'logic_operator': 'AND'
        }],
        'sell_rules': [{
            'id': 'volume_breakout_sell',
            'name': 'Volume Breakout Sell',
            'signal_type': 'SELL',
            'conditions': [
                {
                    'id': 'low_volume_decline',
                    'indicator_type': 'VOLUME',
                    'indicator_params': {},
                    'comparison': '<',
                    'value': '0.5x_avg_volume'  # Would need special handling
                }
            ],
            'logic_operator': 'AND'
        }],
        'risk_management': {
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.15,
            'max_position_size': 0.08
        }
    }

class AlgorithmOptimizer:
    """Optimize algorithm parameters using various methods"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.results_cache = {}
    
    def grid_search_optimization(self, algorithm_template, 
                               parameter_grid: dict, metric: str = 'sharpe_ratio') -> dict:
        """Perform grid search optimization on algorithm parameters"""
        best_score = float('-inf')
        best_params = None
        best_result = None
        
        # Generate all parameter combinations
        param_names = list(parameter_grid.keys())
        param_values = list(parameter_grid.values())
        
        from itertools import product
        for param_combination in product(*param_values):
            params = dict(zip(param_names, param_combination))
            
            try:
                # Create algorithm with current parameters
                algorithm_config = algorithm_template(**params)
                algorithm = CustomAlgorithm(algorithm_config)
                
                # Run backtest
                result = algorithm.backtest(self.data)
                
                # Evaluate based on chosen metric
                score = result.get(metric, 0)
                
                if score > best_score:
                    best_score = score
                    best_params = params.copy()
                    best_result = result.copy()
                    
            except Exception as e:
                print(f"Error with parameters {params}: {e}")
                continue
        
        return {
            'best_parameters': best_params,
            'best_score': best_score,
            'best_result': best_result,
            'optimization_metric': metric
        }
    
    def walk_forward_analysis(self, algorithm_config: dict, 
                            train_periods: int = 252, 
                            test_periods: int = 63) -> dict:
        """Perform walk-forward analysis on algorithm"""
        results = []
        
        for i in range(train_periods, len(self.data) - test_periods, test_periods):
            # Split data
            train_data = self.data.iloc[i-train_periods:i]
            test_data = self.data.iloc[i:i+test_periods]
            
            # Train algorithm (in this case, just create it)
            algorithm = CustomAlgorithm(algorithm_config)
            
            # Test on out-of-sample data
            result = algorithm.backtest(test_data)
            result['period_start'] = test_data.index[0]
            result['period_end'] = test_data.index[-1]
            
            results.append(result)
        
        # Aggregate results
        total_returns = [r['total_return'] for r in results]
        sharpe_ratios = [r['sharpe_ratio'] for r in results]
        
        return {
            'period_results': results,
            'average_return': np.mean(total_returns),
            'average_sharpe': np.mean(sharpe_ratios),
            'return_std': np.std(total_returns),
            'sharpe_std': np.std(sharpe_ratios),
            'win_rate': len([r for r in total_returns if r > 0]) / len(total_returns)
        }
# =============================================================================
# ADVANCED ALGORITHM TEMPLATES - Add this to the VERY END of useralgo.py
# =============================================================================

def create_quantum_momentum_matrix(macd_fast=12, macd_slow=26, macd_signal=9, 
                                 rsi_period=14, rsi_level=55, adx_period=14, 
                                 adx_level=25, volume_lookback=20,
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
                        "value": 0
                    },
                    {
                        "id": "rsi_daily_strong",
                        "indicator_type": "RSI",
                        "indicator_params": {"period": rsi_period},
                        "comparison": ">",
                        "value": rsi_level
                    },
                    {
                        "id": "volume_confirmation",
                        "indicator_type": "VOLUME",
                        "comparison": ">",
                        "value": f"SMA_VOLUME_{volume_lookback}"
                    },
                    {
                        "id": "adx_trend_strength",
                        "indicator_type": "ADX",
                        "indicator_params": {"period": adx_period, "component": "adx"},
                        "comparison": ">",
                        "value": adx_level
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
                        "value": 0
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
                        "value": 70
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
                                  oversold_level=32, macd_fast=12, macd_slow=26, 
                                  macd_signal=9, target_level=85,
                                  stop_loss=0.015, take_profit=0.045, position_size=0.15):
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
                        "value": 15
                    },
                    {
                        "id": "rsi_oversold",
                        "indicator_type": "RSI",
                        "indicator_params": {"period": rsi_period},
                        "comparison": "<",
                        "value": oversold_level
                    },
                    {
                        "id": "macd_positive",
                        "indicator_type": "MACD",
                        "indicator_params": {"fast": macd_fast, "slow": macd_slow, "signal": macd_signal, "component": "histogram"},
                        "comparison": ">",
                        "value": 0
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
                        "value": target_level
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
                                    stop_loss=0.01, take_profit=0.04, position_size=0.18):
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
                        "comparison": ">",
                        "value": f"HIGH_{breakout_period}"
                    },
                    {
                        "id": "volume_surge",
                        "indicator_type": "VOLUME",
                        "comparison": ">",
                        "value": f"SMA_VOLUME_20"
                    },
                    {
                        "id": "low_volatility_setup",
                        "indicator_type": "BOLLINGER",
                        "indicator_params": {"period": 20, "std": 1.5, "component": "bb_percent"},
                        "comparison": "<",
                        "value": consolidation_level
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
                        "comparison": "<",
                        "value": f"HIGH_10_MINUS_2ATR"
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

def create_smart_money_flow(mfi_period=14, mfi_level=60, 
                          stop_loss=0.018, take_profit=0.055, position_size=0.1):
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
                        "comparison": ">",
                        "value": "OBV_20"
                    },
                    {
                        "id": "mfi_strong",
                        "indicator_type": "MFI",
                        "indicator_params": {"period": mfi_period},
                        "comparison": ">",
                        "value": mfi_level
                    },
                    {
                        "id": "price_above_vwap",
                        "indicator_type": "PRICE",
                        "comparison": ">",
                        "value": "VWAP"
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
                        "comparison": "<",
                        "value": "OBV_5"
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