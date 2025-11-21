# 📋 Render Services Assessment Template

**Date:** _________________  
**Assessor:** _________________

---

## Assessment Checklist

For each service in your Render dashboard, fill in the details below.

### Service 1

- **Service Name:** _________________
- **Type:** [ ] Web Service [ ] Background Worker [ ] Database [ ] Static Site [ ] Other: _______
- **Last Deployed:** _________________
- **Status:** [ ] Running [ ] Suspended [ ] Stopped
- **Monthly Cost:** $_______
- **Has Database:** [ ] Yes [ ] No
- **Has Important Data:** [ ] Yes [ ] No
- **Related to NeoLight:** [ ] Yes [ ] No
- **Last Used:** _________________
- **Action:** [ ] KEEP [ ] SUSPEND [ ] DELETE
- **Notes:** 
  ```
  _________________________________________________
  _________________________________________________
  ```

---

### Service 2

- **Service Name:** _________________
- **Type:** [ ] Web Service [ ] Background Worker [ ] Database [ ] Static Site [ ] Other: _______
- **Last Deployed:** _________________
- **Status:** [ ] Running [ ] Suspended [ ] Stopped
- **Monthly Cost:** $_______
- **Has Database:** [ ] Yes [ ] No
- **Has Important Data:** [ ] Yes [ ] No
- **Related to NeoLight:** [ ] Yes [ ] No
- **Last Used:** _________________
- **Action:** [ ] KEEP [ ] SUSPEND [ ] DELETE
- **Notes:** 
  ```
  _________________________________________________
  _________________________________________________
  ```

---

### Service 3

- **Service Name:** _________________
- **Type:** [ ] Web Service [ ] Background Worker [ ] Database [ ] Static Site [ ] Other: _______
- **Last Deployed:** _________________
- **Status:** [ ] Running [ ] Suspended [ ] Stopped
- **Monthly Cost:** $_______
- **Has Database:** [ ] Yes [ ] No
- **Has Important Data:** [ ] Yes [ ] No
- **Related to NeoLight:** [ ] Yes [ ] No
- **Last Used:** _________________
- **Action:** [ ] KEEP [ ] SUSPEND [ ] DELETE
- **Notes:** 
  ```
  _________________________________________________
  _________________________________________________
  ```

---

## Decision Guide

### ✅ KEEP if:
- ✅ NeoLight-related or trading-related
- ✅ Currently in active use
- ✅ Has important data you need
- ✅ Connected to production systems
- ✅ Recently deployed/updated

### ⏸️ SUSPEND if:
- ⏸️ You might need it later
- ⏸️ Has data you want to preserve
- ⏸️ You're unsure about deleting
- ⏸️ Costs money but not actively used
- ⏸️ **Suspending saves money while keeping data**

### ❌ DELETE if:
- ❌ Old test deployments
- ❌ Services you don't recognize
- ❌ Duplicate services
- ❌ No data or value
- ❌ Haven't been used in months
- ❌ Clearly not needed

---

## Data Extraction Checklist

**Before deleting any service, extract:**

- [ ] Environment variables (copy from Environment tab)
- [ ] Database backups (if applicable)
- [ ] Configuration files
- [ ] Build/start commands
- [ ] Any custom settings
- [ ] API keys or secrets

---

## Action Plan

### Services to KEEP: ___
### Services to SUSPEND: ___
### Services to DELETE: ___

### Estimated Monthly Savings: $_______

---

## Notes

```
_________________________________________________
_________________________________________________
_________________________________________________
```

---

## How to Take Action in Render

### To SUSPEND a Service:
1. Go to service → Settings
2. Click "Suspend Service"
3. Confirm suspension
4. Service stops, data preserved

### To DELETE a Service:
1. Go to service → Settings
2. Click "Delete Service"
3. Type service name to confirm
4. ⚠️ **This cannot be undone!**

### To EXPORT Data:
1. **Environment Variables:**
   - Go to service → Environment
   - Copy all variables
   - Save to local file

2. **Database (if applicable):**
   - Go to database service
   - Use backup/export feature
   - Download backup file

---

**💡 Tip:** When in doubt, **SUSPEND** instead of DELETE. You can always delete later!

