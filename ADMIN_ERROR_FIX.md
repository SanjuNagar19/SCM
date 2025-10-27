# Admin Page Error Fix

## Issue Description
The admin page was throwing a `ValueError` due to incorrect tuple unpacking when iterating over student data.

**Error Location:** Line 593 in `app.py`
```python
for student_email, _, _ in students:  # ❌ INCORRECT - trying to unpack 4 items into 3 variables
```

**Error Message:**
```
ValueError: This app has encountered an error...
File "/mount/src/scm/app.py", line 911, in <module>
    admin_page()
File "/mount/src/scm/app.py", line 593, in admin_page
    for student_email, _, _ in students:
```

## Root Cause
The `get_all_students()` function in `backend.py` returns 4 columns:
```python
cur.execute("SELECT email, name, roll_number, created_at FROM students ORDER BY email")
```

This returns tuples with 4 elements: `(email, name, roll_number, created_at)`

However, the admin page code was trying to unpack only 3 elements:
```python
for student_email, _, _ in students:  # Only 3 variables for 4 tuple elements
```

## Solution Applied
Fixed the tuple unpacking to match the actual data structure:

**Before:**
```python
for student_email, _, _ in students:
```

**After:**
```python
for student_email, _, _, _ in students:
```

This correctly unpacks:
- `student_email` → email
- `_` → name (ignored)
- `_` → roll_number (ignored) 
- `_` → created_at (ignored)

## Verification
- ✅ App starts without errors
- ✅ Admin page loads successfully
- ✅ Student metrics display correctly
- ✅ Chat interaction count works properly

## Related Code Pattern
Other parts of the admin page correctly use the 4-element unpacking:
```python
for email, name, roll_number, _ in students:  # ✅ CORRECT pattern used elsewhere
```

The error was an isolated case where the wrong unpacking pattern was used.

## Status: RESOLVED ✅
The admin page now functions correctly without ValueError exceptions.