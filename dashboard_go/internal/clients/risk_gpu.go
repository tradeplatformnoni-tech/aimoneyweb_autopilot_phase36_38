package clients

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// RiskGPUClient - Client for GPU Risk Engine
type RiskGPUClient struct {
	BaseURL    string
	HTTPClient *http.Client
}

// NewRiskGPUClient creates a new GPU risk client
func NewRiskGPUClient() *RiskGPUClient {
	baseURL := "http://localhost:8301"
	if url := getEnv("RISK_GPU_URL", ""); url != "" {
		baseURL = url
	}

	return &RiskGPUClient{
		BaseURL: baseURL,
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// MonteCarloVarRequest - Request for Monte Carlo VaR
type MonteCarloVarRequest struct {
	Returns    []float64 `json:"returns"`
	Iterations int       `json:"iterations"`
	Confidence float64   `json:"confidence,omitempty"`
	Seed       *int64    `json:"seed,omitempty"`
}

// MonteCarloVarResponse - Response from Monte Carlo VaR
type MonteCarloVarResponse struct {
	Var        float64 `json:"var"`
	CVar       float64 `json:"cvar"`
	RuntimeMs  float64 `json:"runtime_ms"`
	Iterations int     `json:"iterations"`
	Confidence float64 `json:"confidence"`
}

// ComputeMonteCarloVar computes VaR using Monte Carlo simulation
func (c *RiskGPUClient) ComputeMonteCarloVar(
	returns []float64,
	iterations int,
	confidence float64,
) (*MonteCarloVarResponse, error) {
	reqBody := MonteCarloVarRequest{
		Returns:    returns,
		Iterations: iterations,
		Confidence: confidence,
	}

	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	resp, err := c.HTTPClient.Post(
		c.BaseURL+"/risk/mc_var",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	var result MonteCarloVarResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// Helper function (should be in a utils package)
func getEnv(key, defaultValue string) string {
	// Simple implementation - in production, use os.Getenv
	return defaultValue
}
