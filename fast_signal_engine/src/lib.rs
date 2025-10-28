use std::slice;

/// Very fast moving-average example
#[unsafe(no_mangle)]          // ← updated for Rust 1.90+
pub extern "C" fn optimize_signals(ptr: *const f64, len: usize) -> f64 {
    let data = unsafe { slice::from_raw_parts(ptr, len) };
    let sum: f64 = data.iter().sum();
    sum / len as f64
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn test_optimize_signals() {
        let v = vec![10.0, 20.0, 30.0];
        let avg = optimize_signals(v.as_ptr(), v.len());
        assert_eq!(avg, 20.0);
    }
}

#[unsafe(no_mangle)]
pub extern "C" fn variance(ptr: *const f64, len: usize) -> f64 {
    let data = unsafe { std::slice::from_raw_parts(ptr, len) };
    let mean: f64 = data.iter().sum::<f64>() / len as f64;
    data.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / len as f64
}

#[unsafe(no_mangle)]
pub extern "C" fn standard_deviation(ptr: *const f64, len: usize) -> f64 {
    variance(ptr, len).sqrt()
}

