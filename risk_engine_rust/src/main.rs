use actix_web::{web, App, HttpServer, HttpResponse, Result as ActixResult, middleware::Logger};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH, Instant};
use std::fs;
use std::path::PathBuf;

// Risk state storage
struct AppState {
    risk_state: Mutex<RiskState>,
    start_time: Instant,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
struct RiskState {
    total_exposure: f64,
    active_positions: usize,
    var: f64,
    cvar: f64,
    drawdown: f64,
    last_update: String,
}

impl Default for RiskState {
    fn default() -> Self {
        RiskState {
            total_exposure: 0.0,
            active_positions: 0,
            var: 0.0,
            cvar: 0.0,
            drawdown: 0.0,
            last_update: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs()
                .to_string(),
        }
    }
}

// Position data for risk evaluation
#[derive(Deserialize, Debug, Clone)]
struct Position {
    symbol: String,
    quantity: f64,
    price: f64,
}

#[derive(Deserialize, Debug)]
struct RiskEvaluateRequest {
    positions: Vec<Position>,
    portfolio_value: f64,
    #[serde(default = "default_confidence")]
    confidence: f64,
}

fn default_confidence() -> f64 {
    0.99
}

#[derive(Serialize)]
struct RiskEvaluateResponse {
    value_at_risk: f64,
    conditional_var: f64,
    drawdown: f64,
    exposure: f64,
    timestamp: String,
}

#[derive(Deserialize, Debug)]
struct TradeValidationRequest {
    symbol: String,
    side: String, // "buy" or "sell"
    quantity: f64,
    price: f64,
    portfolio_value: f64,
    #[serde(default = "default_max_drawdown")]
    max_drawdown: f64,
    #[serde(default = "default_current_drawdown")]
    current_drawdown: f64,
}

fn default_max_drawdown() -> f64 {
    0.08
}

fn default_current_drawdown() -> f64 {
    0.0
}

#[derive(Serialize)]
struct TradeValidationResponse {
    approved: bool,
    reason: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    post_trade_exposure: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    projected_drawdown: Option<f64>,
    timestamp: String,
}

#[derive(Serialize)]
struct HealthResponse {
    status: String,
    service: String,
    version: String,
    uptime: String,
}

// Calculate Value at Risk (VaR) - Parametric method
fn compute_var(positions: &[Position], portfolio_value: f64, confidence: f64) -> f64 {
    if positions.is_empty() || portfolio_value <= 0.0 {
        return 0.0;
    }
    
    // Simplified parametric VaR: assume normal distribution
    // VaR = -z_score * portfolio_volatility * portfolio_value
    // Using historical volatility estimate (simplified)
    
    let total_value: f64 = positions.iter().map(|p| p.quantity * p.price).sum();
    let exposure_ratio = total_value / portfolio_value;
    
    // Simplified: assume 2% daily volatility for crypto
    let volatility = 0.02;
    
    // Z-score for confidence level
    let z_score = match confidence {
        c if c >= 0.99 => 2.33,  // 99% confidence
        c if c >= 0.95 => 1.65,  // 95% confidence
        _ => 1.28,               // 90% confidence
    };
    
    // VaR calculation
    let var = z_score * volatility * portfolio_value * exposure_ratio;
    
    var
}

// Calculate Conditional VaR (CVaR) - Expected loss beyond VaR
fn compute_cvar(_positions: &[Position], _portfolio_value: f64, var: f64, confidence: f64) -> f64 {
    if var <= 0.0 {
        return 0.0;
    }
    
    // Simplified CVaR: CVaR ≈ VaR * 1.3 (empirical multiplier)
    // More accurate: would use historical tail data
    let cvar_multiplier = match confidence {
        c if c >= 0.99 => 1.3,
        c if c >= 0.95 => 1.25,
        _ => 1.2,
    };
    
    var * cvar_multiplier
}

// Calculate drawdown from equity series
fn compute_drawdown(equity_history: &[f64]) -> f64 {
    if equity_history.is_empty() || equity_history.len() < 2 {
        return 0.0;
    }
    
    let mut peak = equity_history[0];
    let mut max_dd: f64 = 0.0;
    
    for &value in equity_history {
        if value > peak {
            peak = value;
        }
        if peak > 0.0 {
            let dd = (peak - value) / peak * 100.0;
            max_dd = max_dd.max(dd);
        }
    }
    
    max_dd
}

// Calculate exposure: Σ (abs(q × p)) / portfolio_value
fn compute_exposure(positions: &[Position], portfolio_value: f64) -> f64 {
    if portfolio_value <= 0.0 {
        return 0.0;
    }
    
    let total_abs_value: f64 = positions.iter()
        .map(|p| (p.quantity * p.price).abs())
        .sum();
    
    total_abs_value / portfolio_value
}

// Calculate drawdown from positions (simplified)
fn compute_drawdown_from_positions(positions: &[Position], portfolio_value: f64) -> f64 {
    let total_value: f64 = positions.iter().map(|p| p.quantity * p.price).sum();
    
    if portfolio_value > 0.0 {
        let drawdown = ((portfolio_value - total_value) / portfolio_value * 100.0).max(0.0);
        drawdown.min(100.0) // Cap at 100%
    } else {
        0.0
    }
}

// Risk evaluation endpoint
async fn evaluate_risk(
    req: web::Json<RiskEvaluateRequest>,
    state: web::Data<AppState>,
) -> ActixResult<HttpResponse> {
    let start = Instant::now();
    
    let positions = &req.positions;
    let portfolio_value = req.portfolio_value;
    let confidence = req.confidence;
    
    // Calculate metrics
    let exposure = compute_exposure(positions, portfolio_value);
    let drawdown = compute_drawdown_from_positions(positions, portfolio_value);
    let var = compute_var(positions, portfolio_value, confidence);
    let cvar = compute_cvar(positions, portfolio_value, var, confidence);
    
    // Update state
    let mut risk_state = state.risk_state.lock().unwrap();
    risk_state.total_exposure = exposure;
    risk_state.active_positions = positions.len();
    risk_state.var = var;
    risk_state.cvar = cvar;
    risk_state.drawdown = drawdown;
    risk_state.last_update = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
        .to_string();
    
    // Persist state
    persist_risk_state(&risk_state);
    
    let response = RiskEvaluateResponse {
        value_at_risk: var,
        conditional_var: cvar,
        drawdown,
        exposure,
        timestamp: SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs()
            .to_string(),
    };
    
    let latency = start.elapsed();
    if latency.as_micros() > 1000 {
        eprintln!("⚠️ Risk evaluation took {}μs (> 1ms)", latency.as_micros());
    }
    
    Ok(HttpResponse::Ok().json(response))
}

// Trade validation endpoint
async fn validate_trade(
    req: web::Json<TradeValidationRequest>,
    state: web::Data<AppState>,
) -> ActixResult<HttpResponse> {
    let start = Instant::now();
    
    let trade = &req;
    let risk_state = state.risk_state.lock().unwrap();
    
    // Check 1: Current drawdown vs max drawdown
    if trade.current_drawdown > trade.max_drawdown {
        return Ok(HttpResponse::Ok().json(TradeValidationResponse {
            approved: false,
            reason: format!(
                "Current drawdown {:.2}% exceeds maximum {:.2}%",
                trade.current_drawdown * 100.0,
                trade.max_drawdown * 100.0
            ),
            post_trade_exposure: None,
            projected_drawdown: None,
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs()
                .to_string(),
        }));
    }
    
    // Check 2: Post-trade exposure
    let trade_value = trade.quantity * trade.price;
    let post_trade_exposure = if trade.portfolio_value > 0.0 {
        (risk_state.total_exposure * trade.portfolio_value + trade_value) / trade.portfolio_value
    } else {
        0.0
    };
    
    let max_exposure: f64 = std::env::var("RISK_MAX_EXPOSURE")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(0.75);
    
    if post_trade_exposure > max_exposure {
        return Ok(HttpResponse::Ok().json(TradeValidationResponse {
            approved: false,
            reason: format!(
                "Post-trade exposure {:.2}% exceeds maximum {:.2}%",
                post_trade_exposure * 100.0,
                max_exposure * 100.0
            ),
            post_trade_exposure: Some(post_trade_exposure),
            projected_drawdown: None,
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs()
                .to_string(),
        }));
    }
    
    // Check 3: Projected drawdown
    let projected_drawdown = risk_state.drawdown; // Simplified: use current drawdown
    
    // Approve trade
    let latency = start.elapsed();
    if latency.as_micros() > 1000 {
        eprintln!("⚠️ Trade validation took {}μs (> 1ms)", latency.as_micros());
    }
    
    Ok(HttpResponse::Ok().json(TradeValidationResponse {
        approved: true,
        reason: "Within exposure limits".to_string(),
        post_trade_exposure: Some(post_trade_exposure),
        projected_drawdown: Some(projected_drawdown),
        timestamp: SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs()
            .to_string(),
    }))
}

// Health check endpoint
async fn health(state: web::Data<AppState>) -> ActixResult<HttpResponse> {
    let uptime_secs = state.start_time.elapsed().as_secs();
    
    Ok(HttpResponse::Ok().json(HealthResponse {
        status: "ok".to_string(),
        service: "NeoLight Risk Engine".to_string(),
        version: "1.0.0".to_string(),
        uptime: format!("{}s", uptime_secs),
    }))
}

// Get risk state endpoint
async fn get_risk_state(state: web::Data<AppState>) -> ActixResult<HttpResponse> {
    let risk_state = state.risk_state.lock().unwrap();
    Ok(HttpResponse::Ok().json(risk_state.clone()))
}

// Persist risk state to file
fn persist_risk_state(state: &RiskState) {
    let state_path = std::env::var("RISK_STATE_PATH")
        .unwrap_or_else(|_| "state/risk_state.json".to_string());
    
    if let Some(parent) = PathBuf::from(&state_path).parent() {
        if let Err(e) = fs::create_dir_all(parent) {
            eprintln!("⚠️ Failed to create state directory: {}", e);
            return;
        }
    }
    
    if let Ok(json) = serde_json::to_string_pretty(state) {
        if let Err(e) = fs::write(&state_path, json) {
            eprintln!("⚠️ Failed to persist risk state: {}", e);
        }
    }
}

// Load risk state from file
fn load_risk_state() -> RiskState {
    let state_path = std::env::var("RISK_STATE_PATH")
        .unwrap_or_else(|_| "state/risk_state.json".to_string());
    
    if let Ok(data) = fs::read_to_string(&state_path) {
        if let Ok(state) = serde_json::from_str::<RiskState>(&data) {
            return state;
        }
    }
    
    RiskState::default()
}

// Stress testing structures
#[derive(Deserialize, Debug)]
struct StressScenario {
    name: String,
    shocks: HashMap<String, f64>, // symbol -> shock percentage
}

#[derive(Deserialize, Debug)]
struct StressTestRequest {
    positions: Vec<Position>,
    scenarios: Vec<StressScenario>,
}

#[derive(Serialize)]
struct StressTestResult {
    name: String,
    pnl: f64,
    exposure_after: f64,
    drawdown_after: f64,
}

#[derive(Serialize)]
struct StressTestResponse {
    results: Vec<StressTestResult>,
    timestamp: String,
}

// Stress testing endpoint
async fn stress_test(
    req: web::Json<StressTestRequest>,
) -> ActixResult<HttpResponse> {
    let positions = &req.positions;
    let scenarios = &req.scenarios;
    
    let mut results = Vec::new();
    
    // Calculate initial portfolio value
    let initial_portfolio_value: f64 = positions.iter()
        .map(|p| p.quantity * p.price)
        .sum();
    
    for scenario in scenarios {
        let mut scenario_pnl = 0.0;
        let mut total_value_after = 0.0;
        
        // Apply shocks to positions
        for position in positions {
            let shock = scenario.shocks.get(&position.symbol)
                .copied()
                .unwrap_or(0.0);
            
            let new_price = position.price * (1.0 + shock);
            let position_value_after = position.quantity * new_price;
            let position_value_before = position.quantity * position.price;
            
            total_value_after += position_value_after;
            scenario_pnl += position_value_after - position_value_before;
        }
        
        // Calculate exposure after shock
        let exposure_after = if initial_portfolio_value > 0.0 {
            total_value_after / initial_portfolio_value
        } else {
            0.0
        };
        
        // Calculate drawdown after shock
        let drawdown_after = if initial_portfolio_value > 0.0 {
            ((initial_portfolio_value - total_value_after) / initial_portfolio_value * 100.0).max(0.0)
        } else {
            0.0
        };
        
        results.push(StressTestResult {
            name: scenario.name.clone(),
            pnl: scenario_pnl,
            exposure_after,
            drawdown_after,
        });
    }
    
    let response = StressTestResponse {
        results,
        timestamp: SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs()
            .to_string(),
    };
    
    Ok(HttpResponse::Ok().json(response))
}

// Error handler
async fn error_handler(err: actix_web::Error, _req: &actix_web::HttpRequest) -> HttpResponse {
    eprintln!("❌ Error: {}", err);
    
    HttpResponse::InternalServerError().json(serde_json::json!({
        "error": err.to_string(),
        "code": 500
    }))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize logging
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));
    
    let port = std::env::var("RISK_PORT")
        .unwrap_or_else(|_| "8300".to_string());
    
    let confidence: f64 = std::env::var("RISK_CONFIDENCE")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(0.99);
    
    let max_exposure: f64 = std::env::var("RISK_MAX_EXPOSURE")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(0.75);
    
    let max_drawdown: f64 = std::env::var("RISK_MAX_DRAWDOWN")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(0.08);
    
    println!("🚀 Starting NeoLight Risk Engine (Rust) on port {}...", port);
    println!("⚙️ Configuration:");
    println!("   Confidence: {}", confidence);
    println!("   Max Exposure: {}", max_exposure);
    println!("   Max Drawdown: {}", max_drawdown);
    println!("📊 Health: http://localhost:{}/health", port);
    println!("📊 Evaluate: http://localhost:{}/risk/evaluate", port);
    println!("📊 Validate: http://localhost:{}/risk/validate", port);
    println!("📊 State: http://localhost:{}/risk/state", port);
    
    // Load persisted state
    let initial_state = load_risk_state();
    
    let app_state = web::Data::new(AppState {
        risk_state: Mutex::new(initial_state),
        start_time: Instant::now(),
    });
    
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .wrap(Logger::default())
            .service(
                web::scope("")
                    .route("/health", web::get().to(health))
                    .route("/risk/evaluate", web::post().to(evaluate_risk))
                    .route("/risk/validate", web::post().to(validate_trade))
                    .route("/risk/state", web::get().to(get_risk_state))
                    .route("/risk/stress", web::post().to(stress_test))
            )
            .default_service(web::route().to(|| async {
                HttpResponse::NotFound().json(serde_json::json!({
                    "error": "Not Found",
                    "code": 404
                }))
            }))
    })
    .bind(format!("0.0.0.0:{}", port))?
    .run()
    .await
}
