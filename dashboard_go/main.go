package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
)

// Structured logging
type LogLevel string

const (
	LogLevelInfo  LogLevel = "INFO"
	LogLevelWarn  LogLevel = "WARN"
	LogLevelError LogLevel = "ERROR"
)

func structuredLog(level LogLevel, message string, fields map[string]interface{}) {
	timestamp := time.Now().UTC().Format(time.RFC3339)
	logData := map[string]interface{}{
		"timestamp": timestamp,
		"level":     string(level),
		"message":   message,
	}
	for k, v := range fields {
		logData[k] = v
	}
	jsonData, _ := json.Marshal(logData)
	log.Println(string(jsonData))
}

// MetaMetricsCache - In-memory cache for meta-metrics (Phase 5600)
type MetaMetricsCache struct {
	mu          sync.RWMutex
	Data        map[string]interface{}
	Timestamp   string
	LastUpdated time.Time
}

// TelemetryQueue - Concurrent telemetry processing
type TelemetryQueue struct {
	queue chan map[string]interface{}
	mu    sync.RWMutex
}

var (
	metaCache      = &MetaMetricsCache{Data: make(map[string]interface{})}
	telemetryQueue = &TelemetryQueue{queue: make(chan map[string]interface{}, 100)}
	rootDir        = getRootDir()
	stateDir       = filepath.Join(rootDir, "state")
	runtimeDir     = filepath.Join(rootDir, "runtime")
	logsDir        = filepath.Join(rootDir, "logs")
	port           = getEnv("NEOLIGHT_DASHBOARD_PORT", "8100")
	logPath        = getEnv("LOG_PATH", filepath.Join(rootDir, "logs", "dashboard_go.log"))
	metricsPath    = getEnv("METRICS_PATH", filepath.Join(rootDir, "state", "meta_metrics.json"))
	startTime      = time.Now()
	version        = "1.0.0"
)

func getRootDir() string {
	home := os.Getenv("HOME")
	if home == "" {
		home = os.Getenv("USERPROFILE") // Windows
	}
	return filepath.Join(home, "neolight")
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func init() {
	// Ensure directories exist
	os.MkdirAll(stateDir, 0755)
	os.MkdirAll(runtimeDir, 0755)
	os.MkdirAll(logsDir, 0755)

	// Start telemetry processor goroutine
	go processTelemetryQueue()

	structuredLog(LogLevelInfo, "Dashboard initialized", map[string]interface{}{
		"port":         port,
		"log_path":     logPath,
		"metrics_path": metricsPath,
	})
}

// processTelemetryQueue - Background goroutine for concurrent telemetry processing
func processTelemetryQueue() {
	for telemetry := range telemetryQueue.queue {
		// Process telemetry asynchronously
		go func(tel map[string]interface{}) {
			// Update cache
			metaCache.mu.Lock()
			metaCache.Data = tel
			metaCache.Timestamp = time.Now().UTC().Format(time.RFC3339)
			metaCache.LastUpdated = time.Now()
			metaCache.mu.Unlock()

			// Persist to file
			if data, err := json.MarshalIndent(tel, "", "  "); err == nil {
				ioutil.WriteFile(metricsPath, data, 0644)
			}

			structuredLog(LogLevelInfo, "Telemetry processed", map[string]interface{}{
				"agents": len(getMapValue(tel, "per_agent", make(map[string]interface{})).(map[string]interface{})),
			})
		}(telemetry)
	}
}

func getMapValue(m map[string]interface{}, key string, defaultValue interface{}) interface{} {
	if v, ok := m[key]; ok {
		return v
	}
	return defaultValue
}

// HealthResponse - Health check response
type HealthResponse struct {
	Status    string `json:"status"`
	Uptime    string `json:"uptime"`
	Version   string `json:"version"`
	Timestamp string `json:"timestamp"`
}

// StatusResponse - System status response
type StatusResponse struct {
	System struct {
		CPU    float64 `json:"cpu"`
		Memory float64 `json:"memory"`
		Disk   float64 `json:"disk"`
		Uptime string  `json:"uptime"`
	} `json:"system"`
	Guardian struct {
		Logs   map[string]string `json:"logs"`
		Agents []interface{}     `json:"agents"`
	} `json:"guardian"`
}

// Health check endpoint
func healthHandler(c *fiber.Ctx) error {
	uptime := time.Since(startTime)
	uptimeStr := fmt.Sprintf("%dh%dm", int(uptime.Hours()), int(uptime.Minutes())%60)

	response := HealthResponse{
		Status:    "ok",
		Uptime:    uptimeStr,
		Version:   version,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	}

	return c.JSON(response)
}

// Status endpoint
func statusHandler(c *fiber.Ctx) error {
	status := StatusResponse{}
	status.System.Uptime = time.Now().UTC().Format(time.RFC3339)
	status.System.CPU = 0.0
	status.System.Memory = 0.0
	status.System.Disk = 0.0
	status.Guardian.Logs = make(map[string]string)
	status.Guardian.Agents = []interface{}{}

	return c.JSON(status)
}

// UpdateMetaMetrics - POST /meta/metrics (called by Phase 5600)
func updateMetaMetrics(c *fiber.Ctx) error {
	var data map[string]interface{}
	if err := c.BodyParser(&data); err != nil {
		structuredLog(LogLevelError, "Failed to parse meta-metrics", map[string]interface{}{
			"error": err.Error(),
		})
		return c.Status(400).JSON(fiber.Map{"error": err.Error()})
	}

	// Send to telemetry queue for concurrent processing
	select {
	case telemetryQueue.queue <- data:
		structuredLog(LogLevelInfo, "Meta-metrics queued", map[string]interface{}{})
	default:
		structuredLog(LogLevelWarn, "Telemetry queue full, dropping message", map[string]interface{}{})
	}

	return c.JSON(fiber.Map{
		"status":    "ok",
		"timestamp": time.Now().UTC().Format(time.RFC3339),
	})
}

// GetMetaMetrics - GET /meta/metrics (Phase 5600 endpoint)
func getMetaMetrics(c *fiber.Ctx) error {
	metaCache.mu.RLock()
	defer metaCache.mu.RUnlock()

	// If cache is empty, try to build from files
	if len(metaCache.Data) == 0 {
		metrics := buildMetaMetricsFromFiles()
		if metrics != nil {
			metaCache.Data = metrics
			metaCache.Timestamp = time.Now().UTC().Format(time.RFC3339)
		}
	}

	response := make(map[string]interface{})
	for k, v := range metaCache.Data {
		response[k] = v
	}
	response["cache_timestamp"] = metaCache.Timestamp

	return c.JSON(response)
}

// GetGovernorAllocations - GET /governor/allocations
func getGovernorAllocations(c *fiber.Ctx) error {
	allocFile := filepath.Join(runtimeDir, "capital_governor_allocations.json")
	if _, err := os.Stat(allocFile); os.IsNotExist(err) {
		// Fallback to allocations_override.json
		allocFile = filepath.Join(runtimeDir, "allocations_override.json")
		if _, err := os.Stat(allocFile); os.IsNotExist(err) {
			return c.JSON(fiber.Map{
				"allocations": make(map[string]float64),
				"timestamp":   time.Now().UTC().Format(time.RFC3339),
			})
		}
	}

	data, err := ioutil.ReadFile(allocFile)
	if err != nil {
		structuredLog(LogLevelError, "Failed to read allocations", map[string]interface{}{
			"error": err.Error(),
		})
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}

	var allocData map[string]interface{}
	if err := json.Unmarshal(data, &allocData); err != nil {
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}

	return c.JSON(allocData)
}

// GetPerformance - GET /meta/performance
func getPerformance(c *fiber.Ctx) error {
	perfFile := filepath.Join(stateDir, "performance_attribution.json")
	if _, err := os.Stat(perfFile); os.IsNotExist(err) {
		return c.JSON(fiber.Map{
			"decisions":   []interface{}{},
			"last_update": nil,
		})
	}

	data, err := ioutil.ReadFile(perfFile)
	if err != nil {
		structuredLog(LogLevelError, "Failed to read performance", map[string]interface{}{
			"error": err.Error(),
		})
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}

	var perfData map[string]interface{}
	if err := json.Unmarshal(data, &perfData); err != nil {
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}

	return c.JSON(perfData)
}

// GetRegime - GET /meta/regime
func getRegime(c *fiber.Ctx) error {
	regimeFile := filepath.Join(runtimeDir, "market_regime.json")
	if _, err := os.Stat(regimeFile); os.IsNotExist(err) {
		return c.JSON(fiber.Map{
			"regime":    "UNKNOWN",
			"timestamp": time.Now().UTC().Format(time.RFC3339),
		})
	}

	data, err := ioutil.ReadFile(regimeFile)
	if err != nil {
		structuredLog(LogLevelError, "Failed to read regime", map[string]interface{}{
			"error": err.Error(),
		})
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}

	var regimeData map[string]interface{}
	if err := json.Unmarshal(data, &regimeData); err != nil {
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}

	return c.JSON(regimeData)
}

// buildMetaMetricsFromFiles - Fallback to build metrics from files if cache empty
func buildMetaMetricsFromFiles() map[string]interface{} {
	return map[string]interface{}{
		"timestamp":    time.Now().UTC().Format(time.RFC3339),
		"per_agent":    make(map[string]interface{}),
		"per_strategy": make(map[string]interface{}),
		"guardian": map[string]interface{}{
			"is_paused": false,
			"drawdown":  0.0,
			"reason":    "Normal operation",
		},
		"breakers": map[string]interface{}{
			"quote_state": "CLOSED",
			"trade_state": "CLOSED",
		},
		"mode": "TEST_MODE",
		"summary": map[string]interface{}{
			"total_agents":     0,
			"total_strategies": 0,
		},
	}
}

// Error handler middleware
func errorHandler(c *fiber.Ctx, err error) error {
	code := fiber.StatusInternalServerError
	message := "Internal Server Error"

	if e, ok := err.(*fiber.Error); ok {
		code = e.Code
		message = e.Message
	}

	structuredLog(LogLevelError, "Request error", map[string]interface{}{
		"path":   c.Path(),
		"method": c.Method(),
		"error":  err.Error(),
		"code":   code,
	})

	return c.Status(code).JSON(fiber.Map{
		"error": message,
		"code":  code,
	})
}

func main() {
	app := fiber.New(fiber.Config{
		AppName:           "NeoLight Dashboard (Go)",
		ServerHeader:      "NeoLight/1.0",
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       120 * time.Second,
		CaseSensitive:     false,
		StrictRouting:     false,
		EnablePrintRoutes: false,
		ErrorHandler:      errorHandler,
	})

	// Middleware
	app.Use(recover.New(recover.Config{
		EnableStackTrace: true,
	}))
	app.Use(logger.New(logger.Config{
		Format: "[${time}] ${status} - ${method} ${path} ${latency}\n",
		Output: os.Stdout,
	}))
	app.Use(cors.New(cors.Config{
		AllowOrigins: "*",
		AllowMethods: "GET,POST,PUT,DELETE,OPTIONS",
		AllowHeaders: "Content-Type,Authorization",
	}))

	// Health check
	app.Get("/health", healthHandler)

	// Status endpoint
	app.Get("/status", statusHandler)

	// Phase 5600 endpoints
	app.Get("/meta/metrics", getMetaMetrics)
	app.Post("/meta/metrics", updateMetaMetrics)
	app.Get("/meta/performance", getPerformance)
	app.Get("/meta/regime", getRegime)

	// Governor endpoints
	app.Get("/governor/allocations", getGovernorAllocations)

	// Atlas Bridge endpoint (Phase 5400)
	app.Post("/atlas/update", func(c *fiber.Ctx) error {
		var data map[string]interface{}
		if err := c.BodyParser(&data); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": err.Error()})
		}

		// Store in telemetry queue
		select {
		case telemetryQueue.queue <- data:
		default:
			structuredLog(LogLevelWarn, "Telemetry queue full, dropping atlas update", map[string]interface{}{})
		}

		return c.JSON(fiber.Map{
			"status":    "ok",
			"timestamp": time.Now().UTC().Format(time.RFC3339),
		})
	})

	// Root endpoint
	app.Get("/", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"service": "NeoLight Dashboard (Go)",
			"version": version,
			"status":  "running",
			"uptime":  time.Since(startTime).String(),
			"endpoints": []string{
				"/health",
				"/status",
				"/meta/metrics",
				"/meta/performance",
				"/meta/regime",
				"/governor/allocations",
			},
		})
	})

	// Start server
	structuredLog(LogLevelInfo, "Starting dashboard server", map[string]interface{}{
		"port": port,
	})

	if err := app.Listen(":" + port); err != nil {
		structuredLog(LogLevelError, "Failed to start server", map[string]interface{}{
			"error": err.Error(),
		})
		log.Fatalf("❌ Failed to start server: %v", err)
	}
}
