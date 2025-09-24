# 🚀 Koyeb Deployment Guide - No Docker Required

## Method 1: GitHub Deployment (Recommended)

Since Docker is not installed locally, this is the easiest method:

### Step 1: Create GitHub Repository

1. Create a new GitHub repository (e.g., `tls-web-monitor-koyeb`)
2. Upload all files from the `koyeb_deployment` folder to this repository
3. Make sure the repository is public (or connect private repo to Koyeb)

### Step 2: Deploy on Koyeb

1. **Go to Koyeb Dashboard**: https://app.koyeb.com/
2. **Create Account**: Sign up for free account
3. **Create New App**: Click "Create App"
4. **Select GitHub**: Choose "Deploy from GitHub"
5. **Connect Repository**: Select your `tls-web-monitor-koyeb` repository
6. **Configure Deployment**:
   - **Build Method**: Dockerfile (auto-detected)
   - **Branch**: main
   - **Root Directory**: Leave empty (if files are in root)

### Step 3: Set Environment Variables

In the Koyeb dashboard, add these environment variables:

```
KOYEB_DEPLOYMENT=true
CHROME_BIN=/usr/bin/google-chrome-stable
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

### Step 4: Configure Health Check

- **Health Check Path**: `/health`
- **Port**: 5000 (auto-detected)

### Step 5: Deploy

Click "Deploy" and wait for the build to complete!

---

## Method 2: Install Docker Desktop (Advanced)

If you want to test locally first:

### Step 1: Install Docker Desktop

1. Download from: https://www.docker.com/products/docker-desktop/
2. Install and restart your computer
3. Start Docker Desktop

### Step 2: Build and Test Locally

```bash
# Navigate to koyeb_deployment folder
cd C:\Users\Younis\Desktop\TLS_Web_Monitor\koyeb_deployment

# Build Docker image
docker build -t tls-monitor-koyeb .

# Test locally
docker run -p 5000:5000 --env KOYEB_DEPLOYMENT=true tls-monitor-koyeb

# Access at http://localhost:5000
```

### Step 3: Push to Docker Hub (Optional)

```bash
# Tag for Docker Hub
docker tag tls-monitor-koyeb yourusername/tls-monitor-koyeb

# Push to Docker Hub
docker push yourusername/tls-monitor-koyeb
```

### Step 4: Deploy on Koyeb

1. Go to Koyeb Dashboard
2. Create App
3. Select "Docker Image"
4. Enter: `yourusername/tls-monitor-koyeb:latest`
5. Set environment variables
6. Deploy!

---

## 🎯 Recommended Approach: GitHub Method

Since Docker is not installed, I recommend the **GitHub method**:

1. **Zero Local Setup**: No need to install Docker
2. **Automatic Builds**: Koyeb builds the Docker image for you
3. **Easy Updates**: Push to GitHub, auto-deploys
4. **Free Tier Perfect**: Works great on Koyeb's free plan

## 📋 Pre-Deployment Checklist

- [ ] Update `config.json` with your TLS credentials
- [ ] Configure email notifications in `config.json`
- [ ] Upload all files to GitHub repository
- [ ] Create Koyeb account
- [ ] Connect GitHub to Koyeb
- [ ] Set environment variables
- [ ] Deploy and monitor logs

## 🔧 Configuration Files to Update

### config.json
Update with your actual credentials:
```json
{
  "login_credentials": {
    "email": "your-tls-email@example.com",
    "password": "your-tls-password"
  },
  "notification": {
    "email": {
      "enabled": true,
      "sender_email": "your-gmail@gmail.com",
      "sender_password": "your-app-password"
    }
  }
}
```

## 🎉 After Deployment

1. **Monitor Logs**: Check Koyeb dashboard for Chrome installation success
2. **Test Login**: Verify TLS website login works
3. **Check Notifications**: Ensure email alerts are working
4. **Set Monitoring**: Monitor for visa slot notifications

Your app will be available at: `https://your-app-name.koyeb.app`

## 🆘 Troubleshooting

- **Build Fails**: Check Dockerfile and requirements.txt
- **Chrome Issues**: Review logs for Chrome installation errors  
- **Memory Errors**: Monitor memory usage in Koyeb dashboard
- **Login Fails**: Verify TLS credentials in config.json