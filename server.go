package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"runtime"
	"strings"
	"syscall"
	"time"
)

// Global configuration
var (
	startTime = time.Now()
	ports     = []string{":5055", ":5060", ":5070"}
	logFile   *os.File
)

// -------------------- Utility --------------------

// safeLog creates/rotates the log file automatically
func safeLog() {
	var err error
	logFile, err = os.OpenFile("dashboard.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		log.Printf("[WARN] log file unavailable: %v", err)
		return
	}
	log.SetOutput(logFile)
}

// openBrowser tries to open a browser window for the dashboard
func openBrowser(url string) {
	var cmd string
	var args []string

	switch runtime.GOOS {
	case "windows":
		cmd = "rundll32"
		args = []string{"url.dll,FileProtocolHandler", url}
	case "darwin":
		cmd = "open"
		args = []string{url}
	default:
		cmd = "xdg-open"
		args = []string{url}
	}
	exec.Command(cmd, args...).Start()
}

// proxyJSON forwards data from backend AI agents with retries
func proxyJSON(target string, w http.ResponseWriter) {
	client := &http.Client{Timeout: 4 * time.Second}
	var resp *http.Response
	var err error

	for i := 0; i < 3; i++ {
		resp, err = client.Get(target)
		if err == nil {
			break
		}
		time.Sleep(500 * time.Millisecond)
	}

	if err != nil {
		log.Printf("[ERROR] proxy failure for %s: %v", target, err)
		http.Error(w, "Agent unavailable", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", resp.Header.Get("Content-Type"))
	io.Copy(w, resp.Body)
}

// -------------------- Routes --------------------

func widgetReward(w http.ResponseWriter, r *http.Request) { proxyJSON("http://127.0.0.1:9111/rewardz", w) }
func widgetParams(w http.ResponseWriter, r *http.Request) { proxyJSON("http://127.0.0.1:9112/params", w) }
func widgetGovern(w http.ResponseWriter, r *http.Request) { proxyJSON("http://127.0.0.1:9113/govern", w) }

func widgetPhase(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"phase":     50,
		"status":    "active",
		"timestamp": time.Now().Format(time.RFC3339),
	})
}

func healthz(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok", "service": "dashboard"})
}

func metrics(w http.ResponseWriter, r *http.Request) {
	uptime := time.Since(startTime).Round(time.Second).String()
	mem := &runtime.MemStats{}
	runtime.ReadMemStats(mem)

	data := map[string]any{
		"uptime":   uptime,
		"goroutine": runtime.NumGoroutine(),
		"alloc_mb":  mem.Alloc / 1024 / 1024,
		"timestamp": time.Now().Format(time.RFC3339),
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

// -------------------- Middleware --------------------

// addCORS allows web clients to fetch data safely
func addCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		if r.Method == "OPTIONS" {
			return
		}
		next.ServeHTTP(w, r)
	})
}

// -------------------- Main --------------------

func main() {
	safeLog()
	defer func() { if logFile != nil { logFile.Close() } }()

	log.Println("🧠 Starting NeoLight Dashboard...")

	mux := http.NewServeMux()

	// API endpoints
	mux.HandleFunc("/healthz", healthz)
	mux.HandleFunc("/metrics", metrics)
	mux.HandleFunc("/widgets/reward", widgetReward)
	mux.HandleFunc("/widgets/params", widgetParams)
	mux.HandleFunc("/widgets/govern", widgetGovern)
	mux.HandleFunc("/widgets/phase", widgetPhase)

	// Serve dashboard files
	fs := http.FileServer(http.Dir("."))
	mux.Handle("/", fs)

	// Wrap with CORS middleware
	handler := addCORS(mux)

	// Auto Port-Fallback logic
	var server *http.Server
	var listener net.Listener
	var lastErr error
	for _, p := range ports {
		ln, err := net.Listen("tcp", p)
		if err == nil {
			listener = ln
			server = &http.Server{Handler: handler}
			fmt.Printf("🚀 NeoLight Dashboard → http://127.0.0.1%s\n", p)
			fmt.Println("----------------------------------------------------")
			fmt.Println("Endpoints:")
			fmt.Println("• /widgets/reward")
			fmt.Println("• /widgets/params")
			fmt.Println("• /widgets/govern")
			fmt.Println("• /widgets/phase")
			fmt.Println("• /healthz")
			fmt.Println("• /metrics")
			fmt.Println("----------------------------------------------------")
			openBrowser(fmt.Sprintf("http://127.0.0.1%s", p))
			break
		}
		lastErr = err
		log.Printf("[WARN] Port %s unavailable: %v", p, err)
	}

	if listener == nil {
		log.Fatalf("[FATAL] No available ports: %v", lastErr)
	}

	// Graceful shutdown
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	go func() {
		if err := server.Serve(listener); err != nil && !strings.Contains(err.Error(), "closed") {
			log.Fatalf("[FATAL] server error: %v", err)
		}
	}()

	<-ctx.Done()
	log.Println("🛑 Shutting down dashboard gracefully...")
	server.Shutdown(context.Background())
	log.Println("✅ Dashboard stopped cleanly.")
}

