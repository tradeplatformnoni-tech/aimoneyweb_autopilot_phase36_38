# AI Browser Assistant - Real-World Examples 🤖

## 🎯 **What It Can Do**

The AI Browser Assistant can automatically solve problems on websites:
- Login to accounts
- Fill forms
- Navigate complex flows
- Extract data
- Complete tasks

---

## 📋 **Example 1: Auto-Login to AutoDS**

```python
from agents.ai_browser_assistant import solve_website_problem

# Automatically log into AutoDS
result = solve_website_problem(
    url="https://www.autods.com/login",
    problem_description="Login to AutoDS account",
    actions=[
        {"type": "navigate", "url": "https://www.autods.com/login"},
        {"type": "wait_for", "selector": "input[type='email']", "timeout": 15},
        {"type": "fill", "selector": "input[type='email']", "value": "tradeplatformnoni@gmail.com"},
        {"type": "fill", "selector": "input[type='password']", "value": "your_password"},
        {"type": "click", "selector": "button[type='submit'], .login-button"},
        {"type": "wait", "seconds": 3},
        {"type": "screenshot", "filename": "autods_logged_in.png"},
    ]
)

if result["success"]:
    print("✅ Successfully logged into AutoDS!")
```

---

## 📋 **Example 2: Import Products from AutoDS**

```python
from agents.ai_browser_assistant import solve_website_problem

products = ["camera lens", "phone case", "wireless charger"]

result = solve_website_problem(
    url="https://www.autods.com",
    problem_description="Import products to AutoDS",
    actions=[
        # Login first
        {"type": "navigate", "url": "https://www.autods.com/login"},
        {"type": "fill", "selector": "input[type='email']", "value": "your_email"},
        {"type": "fill", "selector": "input[type='password']", "value": "your_password"},
        {"type": "click", "selector": "button[type='submit']"},
        {"type": "wait", "seconds": 5},
        
        # Navigate to import
        {"type": "navigate", "url": "https://www.autods.com/products/import"},
        {"type": "wait", "seconds": 3},
        
        # Import each product
        *[
            {
                "type": "fill",
                "selector": "input[type='search'], input[placeholder*='search' i]",
                "value": product
            }
            for product in products
        ] + [
            {"type": "click", "selector": "button:contains('Import'), .import-button"},
            {"type": "wait", "seconds": 2},
        ] * len(products),
        
        {"type": "screenshot", "filename": "products_imported.png"},
    ]
)
```

---

## 📋 **Example 3: Extract Data from Website**

```python
from agents.ai_browser_assistant import solve_website_problem

# Extract product prices from a page
result = solve_website_problem(
    url="https://example.com/products",
    problem_description="Extract product prices",
    actions=[
        {"type": "navigate", "url": "https://example.com/products"},
        {"type": "wait_for", "selector": ".product-item", "timeout": 10},
        {"type": "get_text", "selector": ".product-price"},
        {"type": "screenshot", "filename": "products.png"},
    ]
)

# Access extracted data
if result["actions_completed"]:
    for action in result["actions_completed"]:
        if "Got text" in action:
            print(f"Found: {action}")
```

---

## 📋 **Example 4: Complete Registration Form**

```python
# Automatically fill out any registration form
result = solve_website_problem(
    url="https://example.com/register",
    problem_description="Complete registration",
    actions=[
        {"type": "navigate", "url": "https://example.com/register"},
        {"type": "fill", "selector": "#name", "value": "John Doe"},
        {"type": "fill", "selector": "#email", "value": "john@example.com"},
        {"type": "fill", "selector": "#phone", "value": "555-1234"},
        {"type": "fill", "selector": "#address", "value": "123 Main St"},
        {"type": "click", "selector": "#agree-terms"},
        {"type": "click", "selector": "button.submit"},
        {"type": "wait", "seconds": 3},
        {"type": "screenshot", "filename": "registration_complete.png"},
    ]
)
```

---

## 📋 **Example 5: Navigate Multi-Step Flow**

```python
# Complete a complex multi-step process
result = solve_website_problem(
    url="https://example.com",
    problem_description="Complete multi-step process",
    actions=[
        # Step 1: Login
        {"type": "navigate", "url": "https://example.com/login"},
        {"type": "fill", "selector": "#email", "value": "user@example.com"},
        {"type": "fill", "selector": "#password", "value": "password"},
        {"type": "click", "selector": "button.login"},
        {"type": "wait", "seconds": 3},
        
        # Step 2: Navigate to dashboard
        {"type": "click", "selector": "a.dashboard"},
        {"type": "wait", "seconds": 2},
        
        # Step 3: Select option
        {"type": "click", "selector": ".option-1"},
        {"type": "wait", "seconds": 1},
        
        # Step 4: Fill form
        {"type": "fill", "selector": "#input-field", "value": "data"},
        {"type": "click", "selector": "button.submit"},
        {"type": "wait", "seconds": 2},
        
        # Step 5: Verify
        {"type": "screenshot", "filename": "process_complete.png"},
    ]
)
```

---

## 🔧 **Using the Browser Assistant Directly**

```python
from agents.ai_browser_assistant import AIBrowserAssistant

# Create assistant
assistant = AIBrowserAssistant(headless=False)
assistant.start()

# Navigate
assistant.navigate("https://example.com")

# Interact
assistant.click("button.submit")
assistant.fill_input("input#email", "user@example.com")

# Extract
text = assistant.get_text(".price")

# Screenshot
assistant.screenshot("result.png")

# Close
assistant.close()
```

---

## 🎯 **Integration with Your Agents**

### **In Dropship Agent:**

```python
from agents.ai_browser_assistant import AIBrowserAssistant

def import_products_via_browser():
    """Use AI browser to import products when API unavailable."""
    assistant = AIBrowserAssistant(headless=False)
    assistant.start()
    
    # Login to AutoDS
    assistant.navigate("https://www.autods.com/login")
    assistant.fill_input("input[type='email']", os.getenv("AUTODS_EMAIL"))
    assistant.fill_input("input[type='password']", os.getenv("AUTODS_PASSWORD"))
    assistant.click("button[type='submit']")
    assistant.wait_for_element(".dashboard", timeout=15)
    
    # Import products
    for product in top_products:
        assistant.navigate("https://www.autods.com/products/import")
        assistant.fill_input("#search", product)
        assistant.click("button.search")
        assistant.wait_for_element(".product-card", timeout=5)
        assistant.click(".product-card:first-child .import-btn")
        time.sleep(2)
    
    assistant.close()
```

---

## ⚡ **Speed Tips**

1. **Use headless mode for automation:**
   ```python
   assistant = AIBrowserAssistant(headless=True)  # Faster
   ```

2. **Batch operations:**
   - Group similar actions together
   - Reduce wait times between actions

3. **Parallel browsers:**
   - Run multiple browser instances
   - Process multiple tasks simultaneously

---

## 🛠️ **Troubleshooting**

### **Element not found:**
- Increase timeout
- Check selector is correct
- Add wait_for before interaction

### **Slow performance:**
- Use headless mode
- Reduce wait times
- Optimize selectors

### **Browser crashes:**
- Increase memory limits
- Use Playwright instead of Selenium
- Close unused browsers

---

**The AI Browser Assistant is ready to solve website problems automatically!** 🚀

