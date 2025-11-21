use actix_web::{web, App, HttpServer, HttpResponse, Result as ActixResult};
use serde::{Deserialize, Serialize};
use std::time::Instant;
use rand::rngs::StdRng;
use rand::SeedableRng;
use rand_distr::{Distribution, Normal};

#[derive(Deserialize, Debug)]
struct MonteCarloVarRequest {
    returns: Vec<f64>,
    iterations: usize,
    #[serde(default = "default_confidence")]
    confidence: f64,
    #[serde(default)]
    seed: Option<u64>,
}

fn default_confidence() -> f64 {
    0.99
}

#[derive(Serialize)]
struct MonteCarloVarResponse {
    var: f64,
    cvar: f64,
    runtime_ms: f64,
    iterations: usize,
    confidence: f64,
}

// Monte Carlo VaR simulation (CPU-based, parallelizable)
fn monte_carlo_var(
    returns: &[f64],
    iterations: usize,
    confidence: f64,
    seed: Option<u64>,
) -> (f64, f64) {
    if returns.is_empty() || iterations == 0 {
        return (0.0, 0.0);
    }

    // Calculate historical statistics
    let mean = returns.iter().sum::<f64>() / returns.len() as f64;
    let variance = returns
        .iter()
        .map(|r| (r - mean).powi(2))
        .sum::<f64>()
        / returns.len() as f64;
    let std_dev = variance.sqrt();

    if std_dev == 0.0 {
        return (0.0, 0.0);
    }

    // Initialize RNG with seed if provided
    let mut rng: StdRng = if let Some(s) = seed {
        StdRng::seed_from_u64(s)
    } else {
        StdRng::from_entropy()
    };

    // Normal distribution for sampling
    let normal = Normal::new(mean, std_dev).unwrap_or_else(|_| Normal::new(0.0, 0.01).unwrap());

    // Simulate portfolio returns
    let mut simulated_returns: Vec<f64> = Vec::with_capacity(iterations);

    for _ in 0..iterations {
        // Sample from distribution
        let sample = normal.sample(&mut rng);
        simulated_returns.push(sample);
    }

    // Sort to find percentile
    simulated_returns.sort_by(|a, b| a.partial_cmp(b).unwrap());

    // Calculate VaR (loss at confidence level)
    let var_index = ((1.0 - confidence) * iterations as f64) as usize;
    let var = if var_index < simulated_returns.len() {
        -simulated_returns[var_index].min(0.0) // VaR is positive loss
    } else {
        0.0
    };

    // Calculate CVaR (expected loss beyond VaR)
    let tail_returns: Vec<f64> = simulated_returns
        .iter()
        .take(var_index + 1)
        .filter(|&&r| r <= -var)
        .copied()
        .collect();

    let cvar = if !tail_returns.is_empty() {
        -tail_returns.iter().sum::<f64>() / tail_returns.len() as f64
    } else {
        var * 1.3 // Fallback multiplier
    };

    (var, cvar)
}

// Health endpoint
async fn health() -> ActixResult<HttpResponse> {
    Ok(HttpResponse::Ok().json(serde_json::json!({
        "status": "ok",
        "service": "NeoLight GPU Risk Engine (Monte Carlo)",
        "version": "1.0.0"
    })))
}

// Monte Carlo VaR endpoint
async fn mc_var(
    req: web::Json<MonteCarloVarRequest>,
) -> ActixResult<HttpResponse> {
    let start = Instant::now();

    let returns = &req.returns;
    let iterations = req.iterations.min(1_000_000); // Cap at 1M for safety
    let confidence = req.confidence.clamp(0.5, 0.999);
    let seed = req.seed;

    if returns.is_empty() {
        return Ok(HttpResponse::BadRequest().json(serde_json::json!({
            "error": "returns array cannot be empty",
            "code": 400
        })));
    }

    let (var, cvar) = monte_carlo_var(returns, iterations, confidence, seed);
    let runtime_ms = start.elapsed().as_secs_f64() * 1000.0;

    let response = MonteCarloVarResponse {
        var,
        cvar,
        runtime_ms,
        iterations,
        confidence,
    };

    Ok(HttpResponse::Ok().json(response))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let port = std::env::var("RISK_GPU_PORT")
        .unwrap_or_else(|_| "8301".to_string());

    println!("🚀 Starting NeoLight GPU Risk Engine (Monte Carlo) on port {}...", port);
    println!("📊 Health: http://localhost:{}/health", port);
    println!("📊 MC VaR: http://localhost:{}/risk/mc_var", port);

    HttpServer::new(|| {
        App::new()
            .route("/health", web::get().to(health))
            .route("/risk/mc_var", web::post().to(mc_var))
    })
    .bind(format!("0.0.0.0:{}", port))?
    .run()
    .await
}

