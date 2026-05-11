"""
Dump Aggressive Trading Strategy Presets to MongoDB Atlas
Creates various aggressive parameter configurations for different templates
"""

import sys
import os
from datetime import datetime
from preset_manager import preset_manager

def create_aggressive_presets():
    """Create and dump aggressive preset configurations"""
    
    # Connect to MongoDB
    if not preset_manager.connect():
        print("❌ Failed to connect to MongoDB")
        return False
    
    print("✅ Connected to MongoDB Atlas")
    
    # Aggressive presets for different templates
    aggressive_presets = [
        # RSI Aggressive Strategy
        {
            "userId": "system",
            "algorithm": "rsi_strategy",
            "presetName": "Ultra Aggressive RSI",
            "params": {
                "rsi_period": 7,
                "rsi_oversold": 25,
                "rsi_overbought": 75,
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.08,
                "max_position_size": 0.25,
                "max_daily_loss": 0.03
            }
        },
        {
            "userId": "system",
            "algorithm": "rsi_strategy",
            "presetName": "High Risk RSI Swing",
            "params": {
                "rsi_period": 14,
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.12,
                "max_position_size": 0.30,
                "max_daily_loss": 0.05
            }
        },
        
        # MACD Aggressive Strategy
        {
            "userId": "system",
            "algorithm": "macd_strategy",
            "presetName": "Aggressive MACD Scalping",
            "params": {
                "macd_fast": 8,
                "macd_slow": 17,
                "macd_signal": 5,
                "stop_loss_pct": 0.01,
                "take_profit_pct": 0.05,
                "max_position_size": 0.20,
                "max_daily_loss": 0.02
            }
        },
        {
            "userId": "system",
            "algorithm": "macd_strategy",
            "presetName": "High Leverage MACD",
            "params": {
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "stop_loss_pct": 0.025,
                "take_profit_pct": 0.15,
                "max_position_size": 0.35,
                "max_daily_loss": 0.08
            }
        },
        
        # Bollinger Bands Aggressive Strategy
        {
            "userId": "system",
            "algorithm": "bollinger_bands_strategy",
            "presetName": "Aggressive BB Breakout",
            "params": {
                "bb_period": 15,
                "bb_std": 1.8,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.08,
                "max_position_size": 0.25,
                "max_daily_loss": 0.04
            }
        },
        {
            "userId": "system",
            "algorithm": "bollinger_bands_strategy",
            "presetName": "High Risk BB Squeeze",
            "params": {
                "bb_period": 20,
                "bb_std": 2.2,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.12,
                "max_position_size": 0.30,
                "max_daily_loss": 0.06
            }
        },
        
        # Multi-Strategy Aggressive
        {
            "userId": "system",
            "algorithm": "multi_strategy",
            "presetName": "Ultra Aggressive Multi",
            "params": {
                "rsi_period": 7,
                "rsi_oversold": 25,
                "rsi_overbought": 75,
                "macd_fast": 8,
                "macd_slow": 17,
                "macd_signal": 5,
                "bb_period": 15,
                "bb_std": 1.8,
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.10,
                "max_position_size": 0.30,
                "max_daily_loss": 0.05,
                "strategy_weights": {"rsi": 0.4, "macd": 0.4, "bb": 0.2}
            }
        },
        {
            "userId": "system",
            "algorithm": "multi_strategy",
            "presetName": "High Leverage Multi-Strategy",
            "params": {
                "rsi_period": 10,
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "bb_period": 20,
                "bb_std": 2.0,
                "stop_loss_pct": 0.025,
                "take_profit_pct": 0.15,
                "max_position_size": 0.35,
                "max_daily_loss": 0.08,
                "strategy_weights": {"rsi": 0.35, "macd": 0.35, "bb": 0.3}
            }
        },
        
        # Momentum Strategy Aggressive
        {
            "userId": "system",
            "algorithm": "momentum_strategy",
            "presetName": "Aggressive Momentum Hunter",
            "params": {
                "lookback_period": 10,
                "momentum_threshold": 0.03,
                "volume_multiplier": 1.5,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.08,
                "max_position_size": 0.25,
                "max_daily_loss": 0.04
            }
        },
        {
            "userId": "system",
            "algorithm": "momentum_strategy",
            "presetName": "High Risk Momentum",
            "params": {
                "lookback_period": 15,
                "momentum_threshold": 0.05,
                "volume_multiplier": 2.0,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.12,
                "max_position_size": 0.30,
                "max_daily_loss": 0.06
            }
        },
        
        # Mean Reversion Aggressive
        {
            "userId": "system",
            "algorithm": "mean_reversion_strategy",
            "presetName": "Aggressive Mean Reversion",
            "params": {
                "lookback_period": 20,
                "std_dev_threshold": 1.5,
                "stop_loss_pct": 0.025,
                "take_profit_pct": 0.06,
                "max_position_size": 0.20,
                "max_daily_loss": 0.03
            }
        },
        {
            "userId": "system",
            "algorithm": "mean_reversion_strategy",
            "presetName": "High Risk Reversion",
            "params": {
                "lookback_period": 25,
                "std_dev_threshold": 1.8,
                "stop_loss_pct": 0.035,
                "take_profit_pct": 0.09,
                "max_position_size": 0.25,
                "max_daily_loss": 0.05
            }
        }
    ]
    
    print(f"\n🚀 Creating {len(aggressive_presets)} aggressive presets...")
    
    success_count = 0
    for i, preset in enumerate(aggressive_presets, 1):
        try:
            result = preset_manager.save_preset(
                preset["userId"],
                preset["algorithm"],
                preset["presetName"],
                preset["params"]
            )
            
            if result["success"]:
                print(f"✅ [{i}/{len(aggressive_presets)}] Created: {preset['presetName']} for {preset['algorithm']}")
                success_count += 1
            else:
                print(f"❌ [{i}/{len(aggressive_presets)}] Failed: {preset['presetName']} - {result['error']}")
                
        except Exception as e:
            print(f"❌ [{i}/{len(aggressive_presets)}] Error creating {preset['presetName']}: {str(e)}")
    
    print(f"\n📊 Summary:")
    print(f"✅ Successfully created: {success_count} presets")
    print(f"❌ Failed: {len(aggressive_presets) - success_count} presets")
    
    # Verify by fetching some presets
    print(f"\n🔍 Verifying created presets...")
    try:
        sample_presets = preset_manager.get_presets("system", "rsi_strategy")
        print(f"Found {len(sample_presets)} RSI presets:")
        for preset in sample_presets[:3]:  # Show first 3
            print(f"  - {preset['presetName']}")
    except Exception as e:
        print(f"Error verifying presets: {e}")
    
    preset_manager.disconnect()
    return success_count > 0

if __name__ == "__main__":
    print("🎯 Dumping Aggressive Trading Strategy Presets to MongoDB Atlas")
    print("=" * 60)
    
    success = create_aggressive_presets()
    
    if success:
        print("\n🎉 All aggressive presets successfully dumped to MongoDB!")
        print("Users can now access these pre-configured aggressive strategies.")
    else:
        print("\n❌ Failed to create presets. Check the error messages above.")
        sys.exit(1)