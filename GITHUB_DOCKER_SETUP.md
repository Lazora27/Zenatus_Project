# GitHub & Docker Integration Guide

This guide explains how to connect your GitHub repository with Docker Hub to enable automated builds and pushes.

## 1. Create a Docker Hub Account
If you haven't already:
1. Go to [hub.docker.com](https://hub.docker.com/).
2. Sign up for a free account.
3. Create a new repository named `zenatus-backtester` (optional, can be created automatically on push).

## 2. Generate Docker Hub Access Token
For security, use an Access Token instead of your password.
1. Log in to Docker Hub.
2. Go to **Account Settings** -> **Security**.
3. Click **New Access Token**.
4. Description: `GitHub Actions`
5. Permissions: `Read, Write, Delete`
6. **Copy the token immediately** (you won't see it again).

## 3. Configure GitHub Secrets
Now, tell GitHub your credentials so the workflow can log in.
1. Go to your GitHub Repository: `https://github.com/Lazora27/Zenatus_Project`
2. Click **Settings** (Top bar).
3. In the left sidebar, verify **Secrets and variables** -> **Actions**.
4. Click **New repository secret**.

### Add the following secrets:

| Name | Value | Description |
| :--- | :--- | :--- |
| `DOCKERHUB_USERNAME` | `your-dockerhub-username` | Your actual username on Docker Hub |
| `DOCKERHUB_TOKEN` | `dckr_pat_...` | The Access Token you copied in Step 2 |

## 4. Enable the Workflow
The workflow file is located at `.github/workflows/docker-build.yml`.
It currently has the "Push" step commented out. To enable it:

1. Open `.github/workflows/docker-build.yml`
2. Uncomment the lines at the bottom (lines 45-59):
   ```yaml
   # - name: Login to Docker Hub
   #   ...
   # - name: Push Docker Image
   #   ...
   ```
3. Commit and push the changes.

## 5. Verification
1. Go to the **Actions** tab in your GitHub repository.
2. You should see a workflow run named "Docker Build & Test".
3. If it's green ✅, your image is successfully built (and pushed, if enabled).
