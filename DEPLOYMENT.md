# Deployment Guide - Zhang Estate Expense Tracker

**Platform**: Render.com
**Cost**: $7/month
**Technical Level**: Beginner-friendly
**Last Updated**: January 2026

---

## Why Render.com?

Based on your requirements (budget $5-10/month, critical data persistence, free subdomain), Render is the best choice:

- ✅ **$7/month** for persistent disk (database won't be lost on updates)
- ✅ **Extremely beginner-friendly** UI with point-and-click setup
- ✅ **Direct GitHub integration** - auto-deploys when you push code
- ✅ **Free SSL/HTTPS** certificate included (secure by default)
- ✅ **Free subdomain**: `yourapp.onrender.com`
- ✅ **Built-in health checks** and auto-restart if app crashes
- ✅ **No credit card needed** to start testing (has free tier)

**Alternative considered**: PythonAnywhere ($5/month) - also good but requires manual file uploads instead of Git integration.

---

## Pre-Deployment Checklist

Before deploying, we need to make the app production-ready with these code changes:

### ☐ 1. Create `Procfile`

**Location**: `/Users/yilunzhang/side_project/household_tracker/Procfile` (new file)

**Purpose**: Tells Render how to start the app with a production server (gunicorn instead of Flask's development server)

**Content**:
```
web: gunicorn app:app
```

### ☐ 2. Update `requirements.txt`

**Location**: `/Users/yilunzhang/side_project/household_tracker/requirements.txt`

**Add gunicorn** to the end:
```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
requests==2.31.0
python-dotenv==1.0.0
gunicorn==21.2.0
```

### ☐ 3. Update `app.py` - Database Path

**Location**: `/Users/yilunzhang/side_project/household_tracker/app.py` (line ~17)

**Current code**:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
```

**Replace with**:
```python
import os

# Use different database path for production (persistent disk) vs development
if os.environ.get('FLASK_ENV') == 'production':
    # Production: use /data directory which is mounted to persistent disk on Render
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/database.db'
else:
    # Development: use instance folder locally
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
```

Make sure `import os` is at the top of the file with the other imports.

### ☐ 4. Update `app.py` - Port Configuration

**Location**: `/Users/yilunzhang/side_project/household_tracker/app.py` (lines ~264-267)

**Current code**:
```python
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001)
```

**Replace with**:
```python
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    # Get port from environment variable (Render provides this)
    port = int(os.environ.get('PORT', 5001))

    # Disable debug mode in production
    debug_mode = os.environ.get('FLASK_ENV') != 'production'

    app.run(debug=debug_mode, host='0.0.0.0', port=port)
```

### ☐ 5. Verify `.gitignore`

**Location**: `/Users/yilunzhang/side_project/household_tracker/.gitignore`

Make sure these lines exist (to prevent committing database files):
```
instance/
data/
*.db
.env
__pycache__/
*.pyc
```

### ☐ 6. Test Locally

Before deploying, test that gunicorn works:

```bash
# Install gunicorn locally
pip install gunicorn

# Start the app with gunicorn
gunicorn app:app

# Visit http://localhost:8000 in your browser
# Make sure the app loads correctly
```

If it works, you're ready to deploy!

### ☐ 7. Commit and Push Changes

```bash
git add .
git commit -m "Prepare for production deployment on Render"
git push origin main
```

---

## Step-by-Step Deployment Guide

### Phase 1: Set Up Render Account

#### Step 1.1: Create Render Account
1. Go to **https://render.com**
2. Click **"Get Started"** button (top right corner)
3. Choose **"Sign up with GitHub"** (recommended for easier integration)
4. Authorize Render to access your GitHub account when prompted
5. You'll be redirected to the Render Dashboard

#### Step 1.2: Connect Your GitHub Repository
1. In the Render Dashboard, click the blue **"New +"** button (top right)
2. Select **"Web Service"** from the dropdown menu
3. On the "Create a new Web Service" page:
   - If this is your first time, click **"Connect account"** to link GitHub
   - You'll see a list of your GitHub repositories
   - Find and click **"Connect"** next to `yilunzh/household_finance`

---

### Phase 2: Configure Web Service

#### Step 2.1: Basic Settings

You'll see a form with several fields. Fill them in as follows:

| Setting | Value | Notes |
|---------|-------|-------|
| **Name** | `zhang-estate-tracker` | This will be your URL: `zhang-estate-tracker.onrender.com` |
| **Region** | Choose closest to you | e.g., "Oregon (US West)" or "Frankfurt (Europe)" |
| **Branch** | `main` | The Git branch to deploy from |
| **Root Directory** | (leave blank) | Your code is in the repository root |
| **Runtime** | `Python 3` | Auto-detected, just verify it says Python |
| **Build Command** | `pip install -r requirements.txt` | Installs your Python packages |
| **Start Command** | `gunicorn app:app` | Starts your app with gunicorn |

#### Step 2.2: Choose Instance Type

Scroll down to **"Instance Type"** section:
- Select **"Starter" - $7/month**
- This tier is required for persistent disk storage
- (You can test with "Free" tier first, but database will reset on each deploy)

#### Step 2.3: Add Persistent Disk (CRITICAL FOR DATABASE)

This is the most important step to prevent data loss!

1. Scroll to **"Disks"** section
2. Click **"Add Disk"** button
3. Fill in the disk settings:
   - **Name**: `database-storage`
   - **Mount Path**: `/opt/render/project/src/data`
   - **Size**: `1` GB (enough for thousands of transactions)
4. Click **"Save"**

**Important**: The mount path `/opt/render/project/src/data` matches the `/data` folder we configured in `app.py`. This is where your database file will be stored.

#### Step 2.4: Environment Variables

Scroll to **"Environment Variables"** section and add these:

| Key | Value | How to Add |
|-----|-------|------------|
| `FLASK_ENV` | `production` | Type manually |
| `SECRET_KEY` | (auto-generated) | Click "Generate" button - Render creates a secure random key |
| `PYTHON_VERSION` | `3.9.18` | Type manually (optional, but recommended) |

To add each variable:
1. Click **"Add Environment Variable"**
2. Enter the **Key** (variable name)
3. Enter the **Value** or click "Generate" for SECRET_KEY
4. Repeat for each variable

#### Step 2.5: Advanced Settings (Optional but Recommended)

Expand **"Advanced"** section:
- **Health Check Path**: `/` (Render will ping this URL to ensure app is running)
- **Auto-Deploy**: `Yes` (automatically deploys when you push to GitHub)

#### Step 2.6: Create Web Service

1. **Review all settings** - scroll up and down to verify everything is correct
2. Click the blue **"Create Web Service"** button at the bottom
3. You'll be redirected to your service's page showing build logs

---

### Phase 3: Monitor Deployment

#### Step 3.1: Watch the Build Logs

You'll see a live log stream. Render is now:
1. ✅ Cloning your GitHub repository
2. ✅ Installing Python 3.9
3. ✅ Running `pip install -r requirements.txt`
4. ✅ Starting gunicorn
5. ✅ Provisioning SSL certificate
6. ✅ Mounting persistent disk

**What to look for**:
- `Successfully installed Flask-3.0.0 ...` (dependencies installed)
- `Starting gunicorn` (app is starting)
- `Listening at: http://0.0.0.0:xxxxx` (app is running)
- `Deploy live for zhang-estate-tracker` (deployment complete!)

**Typical deployment time**: 5-10 minutes

#### Step 3.2: Check for Errors

If you see red error messages:
- **"Module not found"**: Missing package in requirements.txt
- **"Port already in use"**: Restart deployment (this is rare)
- **"Application failed to start"**: Check app.py for syntax errors

Most errors are fixable by updating code and pushing to GitHub (auto-redeploys).

---

### Phase 4: Test Your Live App

#### Step 4.1: Visit Your App

At the top of the Render page, you'll see:
**`https://zhang-estate-tracker.onrender.com`** ← Click this link

Your app should load! You should see the "Zhang Estate Expense Tracker" title.

#### Step 4.2: Test All Features

Go through each feature to ensure everything works:

1. **Add a transaction**:
   - Fill in date, merchant, amount
   - Select currency (USD or CAD)
   - Select who paid (Bibi or Pi)
   - Choose category
   - Click "Add Transaction"
   - ✅ Transaction should appear in the list

2. **Refresh the page**:
   - Press F5 or refresh button
   - ✅ Transaction should still be there (not lost)

3. **Edit a transaction**:
   - Click "Edit" button
   - Change some fields
   - Click "Save Changes"
   - ✅ Changes should be saved

4. **Delete a transaction**:
   - Click "Delete" button
   - Confirm deletion
   - ✅ Transaction should disappear

5. **View Reconciliation**:
   - Click "View Reconciliation" button
   - ✅ Should show who owes what based on transactions

6. **Test currency conversion**:
   - Add a transaction in CAD
   - ✅ Should show USD equivalent below

#### Step 4.3: Test Database Persistence (Critical!)

This verifies your data won't be lost on updates:

1. Add a few test transactions (if you haven't already)
2. Go back to Render dashboard
3. Click **"Manual Deploy"** dropdown (top right)
4. Select **"Clear build cache & deploy"**
5. Wait for redeployment to complete (3-5 minutes)
6. Visit your app again
7. ✅ **All your transactions should still be there!**

If they're gone, the persistent disk isn't configured correctly. Check Phase 2, Step 2.3.

---

## Phase 5: Ongoing Usage

### How to Update Your App

Whenever you want to add features or fix bugs:

1. **Make changes locally** in your code editor
2. **Test locally** by running the app on your computer
3. **Commit and push to GitHub**:
   ```bash
   git add .
   git commit -m "Description of what you changed"
   git push origin main
   ```
4. **Render auto-deploys** within 2-3 minutes
5. **Your data is preserved** on the persistent disk

### How to Backup Your Database

Regular backups are important! Do this weekly or monthly:

1. Go to Render dashboard
2. Click on your service (`zhang-estate-tracker`)
3. Click **"Shell"** tab (top menu)
4. Click **"Connect to shell"** button
5. In the terminal that appears, type:
   ```bash
   cat data/database.db > /tmp/backup.db
   ```
6. Use Render's file browser to download `/tmp/backup.db`

**Alternative**: Export to CSV from the app itself (built-in feature on reconciliation page).

### How to View Logs

If something breaks or you want to see what's happening:

1. Go to Render dashboard
2. Click **"Logs"** tab
3. You'll see real-time application logs
4. Look for error messages (in red) or Python tracebacks

### How to Monitor Usage

Render dashboard shows:
- **CPU Usage**: How much processing power your app uses
- **Memory Usage**: Should stay under 512MB
- **Request Count**: How many people are using the app
- **Disk Usage**: How much of your 1GB disk is used

---

## Cost Breakdown

### Monthly Costs
- **Web Service** (Starter plan): $7.00
- **Persistent Disk** (1GB): Included in Starter plan
- **SSL Certificate**: Free
- **Bandwidth**: First 100GB free, then $0.10/GB
- **Custom Domain** (optional): $0 (you can add your own domain for free if you own one)

**Total per month**: **$7.00**

### Annual Estimate
$7/month × 12 months = **$84/year**

### Upgrade Path
If you need more resources later:
- **Standard** ($25/month): 2GB RAM, faster performance
- **Pro** ($85/month): 4GB RAM, auto-scaling

For a household expense tracker, Starter tier is more than sufficient.

---

## Troubleshooting Common Issues

### ❌ Issue 1: "Application failed to respond"

**Symptoms**: App won't load, shows error page

**Causes**:
- App crashed during startup
- Port configuration incorrect
- Missing dependencies

**Solutions**:
1. Check Render logs (Logs tab) for Python errors
2. Verify `app.py` has `port = int(os.environ.get('PORT', 5001))`
3. Ensure all packages in `requirements.txt` installed successfully
4. Try redeploying: Manual Deploy → Clear build cache & deploy

---

### ❌ Issue 2: Database resets after every deploy

**Symptoms**: Transactions disappear when you update the app

**Causes**:
- Persistent disk not configured
- Wrong database path in code
- Disk not mounted to correct path

**Solutions**:
1. Verify in Render dashboard: Settings → Disks → should see `database-storage` mounted at `/opt/render/project/src/data`
2. Check `app.py` uses `sqlite:///data/database.db` in production (not `sqlite:///database.db`)
3. Redeploy after fixing

---

### ❌ Issue 3: "Module not found" error

**Symptoms**: Build fails with `ModuleNotFoundError: No module named 'something'`

**Causes**:
- Missing package in `requirements.txt`
- Typo in package name

**Solutions**:
1. Add missing package to `requirements.txt`
2. Commit and push to GitHub
3. Render will auto-redeploy with the new package

---

### ❌ Issue 4: App is slow to load

**Symptoms**: Takes 5+ seconds to load pages

**Causes**:
- Free tier "sleeps" after inactivity (takes 30-60 seconds to wake up)
- Too many database queries
- Not enough RAM

**Solutions**:
1. **If on Free tier**: Upgrade to Starter ($7/month) - doesn't sleep
2. **If on Starter tier and still slow**: Check Render metrics for high memory usage
3. **If very slow**: Upgrade to Standard ($25/month) for 2GB RAM

---

### ❌ Issue 5: Can't access app - "Too Many Requests"

**Symptoms**: App shows rate limit error

**Causes**:
- Free tier has rate limits
- Unusual spike in traffic

**Solutions**:
1. Upgrade to Starter tier (no rate limits)
2. Wait a few minutes for rate limit to reset

---

## Security Checklist

Before sharing your app URL with others:

- ✅ **SECRET_KEY is secure**: Auto-generated by Render (not the default dev key)
- ✅ **Debug mode disabled**: `FLASK_ENV=production` disables debug messages
- ✅ **HTTPS enabled**: Render provides free SSL certificate automatically
- ✅ **Database not in Git**: `.gitignore` excludes `*.db` files
- ⚠️ **No authentication**: Currently anyone with the URL can access the app
  - Consider adding login if you want to restrict access
  - Flask-Login is a good option for this

---

## Optional: Adding a Custom Domain

If you want `expenses.yourname.com` instead of `zhang-estate-tracker.onrender.com`:

1. **Buy a domain** (~$12/year from Namecheap, Google Domains, etc.)
2. **In Render dashboard**:
   - Go to Settings → Custom Domains
   - Click "Add Custom Domain"
   - Enter your domain (e.g., `expenses.yourname.com`)
3. **In your domain registrar** (where you bought the domain):
   - Add a CNAME record pointing to Render
   - Render will show you the exact DNS settings
4. **Wait 5-60 minutes** for DNS to propagate
5. **Visit your custom domain** - app should load with your domain!

Render handles SSL certificates for custom domains automatically.

---

## Next Steps After Deployment

Once your app is live:

### Week 1
1. ✅ Test all features thoroughly
2. ✅ Add real transactions to start using the app
3. ✅ Share URL with your wife/household members
4. ✅ Set up a reminder to backup database weekly

### Month 1
1. Monitor Render dashboard for any errors
2. Check that monthly bill is $7 as expected
3. Export CSV backup of transactions
4. Consider adding authentication if needed

### Ongoing
1. Update app with new features as needed (just push to GitHub)
2. Monthly database backups (export to CSV)
3. Review Render metrics to ensure app is healthy

---

## Getting Help

If you run into issues:

1. **Check this guide** - troubleshooting section covers common problems
2. **Render docs**: https://render.com/docs
3. **Render support**: support@render.com (good response time)
4. **GitHub repo**: Ask me (Claude) for help via GitHub issues

---

## Summary

**What you're deploying**:
- Flask web application for household expense tracking
- SQLite database with persistent storage
- Auto-deploy from GitHub
- Free HTTPS/SSL

**Where it's hosted**:
- Platform: Render.com
- URL: https://zhang-estate-tracker.onrender.com
- Cost: $7/month
- Uptime: 99.9% guaranteed

**What you need to do**:
1. Make code changes (Procfile, requirements.txt, app.py)
2. Push to GitHub
3. Sign up for Render
4. Configure web service (10 minutes)
5. Deploy and test

**Estimated time**: 30-60 minutes for first deployment

Good luck with your deployment! 🚀
