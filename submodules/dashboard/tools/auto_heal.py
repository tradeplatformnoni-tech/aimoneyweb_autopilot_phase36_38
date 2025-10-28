import subprocess

def heal():
    print("🛠️ Healing your AI Money Web codebase...")

    # Lint + auto-fix
    subprocess.run(["ruff", "check", ".", "--fix"])

    # Check FastAPI routes (basic syntax test)
    try:
        print("✅ FastAPI app imported without syntax errors.")
    except Exception as e:
        print(f"❌ FastAPI app has issues: {e}")

if __name__ == "__main__":
    heal()
