# GitHub Secrets Integration Guide

This guide explains how to safely add your credentials to GitHub so that the automated workflows (Docker Build, Tests, etc.) can function correctly.

## ⚠️ IMPORTANT SECURITY WARNING
You have shared sensitive credentials (API Keys, Tokens) in the chat.
**These keys are now considered compromised.**
For maximum security, you should:
1. Revoke the OpenAI Key (`sk-svcacct-...`).
2. Revoke the GitHub PATs (`github_pat_...`, `ghp_...`).
3. Generate NEW keys/tokens.
4. Use the NEW keys in the steps below.

## Step 1: Go to GitHub Settings
1. Open your repository on GitHub: `https://github.com/Lazora27/Zenatus_Project`
2. Click on the **Settings** tab (top navigation bar).
3. In the left sidebar, scroll down to **Secrets and variables**.
4. Click on **Actions**.

## Step 2: Add Repository Secrets
You need to add the following secrets one by one by clicking **New repository secret**.

| Secret Name | Value to Enter | Description |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | `sk-svcacct-...` (Use your NEW key) | Required for AI Agents |
| `GH_PAT` | `github_pat_...` (Use your NEW key) | Required for Git Sync operations |
| `DOCKERHUB_USERNAME` | Your DockerHub Username | For pushing Docker images |
| `DOCKERHUB_TOKEN` | Your DockerHub Access Token | Generated in DockerHub Settings |

## Step 3: Verify Workflow
After adding the secrets:
1. Go to the **Actions** tab.
2. Select the "Docker Build & Test" workflow.
3. Click **Run workflow** (if available) or push a commit to trigger it.

## Note on Local Docker Usage
If you want to use these keys locally in Docker (e.g. for the Alert Agent), you should create a `.env` file in `/opt/Zenatus_Backtester/` and add them there:

```bash
# /opt/Zenatus_Backtester/.env
OPENAI_API_KEY=sk-...
GH_PAT=github_pat_...
```

Then update `docker-compose.yml` to use this file:
```yaml
services:
  backtester:
    env_file: .env
    ...
```
