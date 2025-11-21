use clap::Parser;
use serde::{Deserialize, Serialize};
use rayon::prelude::*;
use rand::Rng;

#[derive(Parser, Debug)]
#[command(name = "backtester_rust")]
#[command(about = "Distributed Monte Carlo Backtester")]
struct Args {
    #[arg(long)]
    symbols: String,
    #[arg(long)]
    start: String,
    #[arg(long)]
    end: String,
    #[arg(long)]
    strategies: String,
    #[arg(long, default_value = "500")]
    iters: usize,
    #[arg(long)]
    out: String,
}

#[derive(Serialize, Deserialize)]
struct BacktestResult {
    strategy: String,
    sharpe: f64,
    max_drawdown: f64,
    win_rate: f64,
    total_return: f64,
    trades: usize,
}

#[derive(Serialize)]
struct BacktestReport {
    symbols: Vec<String>,
    start_date: String,
    end_date: String,
    strategies: Vec<BacktestResult>,
    timestamp: String,
}

fn run_strategy_backtest(
    strategy: &str,
    symbols: &[String],
    iters: usize,
) -> BacktestResult {
    // Simplified backtest (would use actual historical data)
    let mut returns: Vec<f64> = Vec::new();
    
    use rand::Rng;
    let mut rng = rand::thread_rng();
    
    for _ in 0..iters {
        // Mock returns
        let ret = (rng.gen::<f64>() - 0.5) * 0.02;
        returns.push(ret);
    }
    
    let total_return = returns.iter().sum::<f64>();
    let mean_return = total_return / returns.len() as f64;
    let variance = returns.iter()
        .map(|r| (r - mean_return).powi(2))
        .sum::<f64>() / returns.len() as f64;
    let std_dev = variance.sqrt();
    
    let sharpe = if std_dev > 0.0 {
        mean_return / std_dev * (252.0_f64).sqrt()  // Annualized
    } else {
        0.0
    };
    
    let max_drawdown = returns.iter()
        .fold((0.0, 0.0), |(peak, max_dd), &r| {
            let new_peak = peak.max(r);
            let new_dd = max_dd.max((peak - r).max(0.0));
            (new_peak, new_dd)
        }).1;
    
    let win_rate = returns.iter()
        .filter(|&&r| r > 0.0)
        .count() as f64 / returns.len() as f64;
    
    BacktestResult {
        strategy: strategy.to_string(),
        sharpe,
        max_drawdown,
        win_rate,
        total_return,
        trades: iters,
    }
}

fn main() {
    let args = Args::parse();
    
    let symbols: Vec<String> = args.symbols.split(',').map(|s| s.trim().to_string()).collect();
    let strategies: Vec<String> = args.strategies.split(',').map(|s| s.trim().to_string()).collect();
    
    println!("🚀 Starting backtest: {} strategies on {} symbols", strategies.len(), symbols.len());
    
    // Parallel backtesting
    let results: Vec<BacktestResult> = strategies
        .par_iter()
        .map(|strategy| run_strategy_backtest(strategy, &symbols, args.iters))
        .collect();
    
    let report = BacktestReport {
        symbols,
        start_date: args.start,
        end_date: args.end,
        strategies: results,
        timestamp: chrono::Utc::now().to_rfc3339(),
    };
    
    // Write output
    std::fs::write(&args.out, serde_json::to_string_pretty(&report).unwrap())
        .expect("Failed to write backtest report");
    
    println!("✅ Backtest complete: {}", args.out);
    for result in &report.strategies {
        println!("  {}: Sharpe={:.2}, DD={:.2}%, Win={:.1}%", 
                 result.strategy, result.sharpe, result.max_drawdown * 100.0, result.win_rate * 100.0);
    }
}

