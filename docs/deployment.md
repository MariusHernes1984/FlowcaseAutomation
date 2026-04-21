# Azure deployment guide

This guide walks through deploying the Flowcase MCP server to Azure
Container Apps in the Atea **KATE** subscription, region **Norway East**.

Target shape: single-user development deployment with:

- All resources in `rg-flowcase-mcp-dev`
- Flowcase API key + MCP auth key in Key Vault
- `availability.xlsx` in an Azure Files share (read-only mount)
- Container image in Azure Container Registry
- X-API-Key header auth on the Streamable HTTP MCP endpoint

```
Claude Code / Foundry
        │  HTTPS  +  X-API-Key header
        ▼
Azure Container App (Norway East, scale 0→3)
        │
        ├── secret: FLOWCASE_API_KEY      ◄── Key Vault
        ├── secret: FLOWCASE_MCP_API_KEY  ◄── Key Vault
        └── volume: /data  (read-only)    ◄── Azure Files
```

## Prerequisites

```powershell
# Azure CLI 2.60+
az --version

# Log in to the KATE subscription
az login
az account set --subscription "KATE"
az account show --query name -o tsv    # confirm
```

You need **Contributor** on the resource group and **User Access
Administrator** (or Owner) so the template can create the role
assignments. If you don't have it, ask your Azure admin.

## 1 — Create the resource group

```powershell
$RG = "rg-flowcase-mcp-dev"
$LOC = "norwayeast"
az group create -n $RG -l $LOC
```

## 2 — Deploy the infrastructure

```powershell
# Your own Entra object ID (for Key Vault secret access)
$PRINCIPAL = (az ad signed-in-user show --query id -o tsv)

az deployment group create `
  --resource-group $RG `
  --template-file infra/main.bicep `
  --parameters principalId=$PRINCIPAL
```

The deployment takes ~3–5 minutes. On success you get outputs:

```
acrLoginServer      : crflowcasemcpdev.azurecr.io
keyVaultName        : kv-flowcasemcp-dev
storageAccountName  : stflowcasemcpdev
fileShareName       : availability
containerAppName    : ca-flowcasemcp-dev
containerAppFqdn    : ca-flowcasemcp-dev.<hash>.norwayeast.azurecontainerapps.io
```

## 3 — Set the secrets in Key Vault

```powershell
$KV = "kv-flowcasemcp-dev"

# Flowcase ServiceHub subscription key (same one you use locally)
az keyvault secret set `
  --vault-name $KV `
  --name flowcase-api-key `
  --value "<your-flowcase-subscription-key>"

# MCP client auth key — generate a long random string, treat as a password
$MCP_KEY = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
az keyvault secret set `
  --vault-name $KV `
  --name mcp-api-key `
  --value $MCP_KEY

Write-Host "MCP API key (save somewhere safe):" $MCP_KEY
```

## 4 — Upload the availability workbook

```powershell
$STORAGE = "stflowcasemcpdev"

az storage file upload `
  --account-name $STORAGE `
  --share-name availability `
  --source "data/availability.xlsx" `
  --path "availability.xlsx" `
  --auth-mode login
```

When you regenerate the PBI export, upload the new file with the same
command — the server's AvailabilityIndex auto-reloads on mtime changes.

## 5 — Build and push the container image

```powershell
$ACR = "crflowcasemcpdev"
az acr build `
  --registry $ACR `
  --image flowcase-mcp:latest `
  --file Dockerfile .
```

`az acr build` pushes the image to ACR without needing a local Docker
daemon. Takes ~2–3 minutes.

## 6 — Point the Container App at the real image

```powershell
$APP = "ca-flowcasemcp-dev"

az containerapp update `
  --name $APP `
  --resource-group $RG `
  --image crflowcasemcpdev.azurecr.io/flowcase-mcp:latest
```

After a few seconds, the app restarts with the real image and picks up
the injected secrets.

## 7 — Verify

```powershell
$FQDN = (az containerapp show -n $APP -g $RG --query properties.configuration.ingress.fqdn -o tsv)

# Health (no auth)
curl "https://$FQDN/health"
# expected: ok

# Auth rejects missing key
curl -w "%{http_code}\n" "https://$FQDN/mcp"
# expected: 401

# Auth rejects wrong key
curl -w "%{http_code}\n" -H "X-API-Key: wrong" "https://$FQDN/mcp"
# expected: 403
```

## 8 — Connect Claude Code to the hosted MCP

Add a remote MCP to your Claude Code config (`~/.claude/settings.json`
or the per-project `.mcp.json`):

```json
{
  "mcpServers": {
    "flowcase-prod": {
      "url": "https://ca-flowcasemcp-dev.<hash>.norwayeast.azurecontainerapps.io/mcp",
      "headers": {
        "X-API-Key": "<the MCP key from step 3>"
      }
    }
  }
}
```

Reload Claude Code — you should see the same seven tools as the local
`flowcase` MCP, but fetched over HTTPS.

---

## Operations

### Rotate the MCP API key

```powershell
$NEW_KEY = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
az keyvault secret set --vault-name $KV --name mcp-api-key --value $NEW_KEY
az containerapp revision restart --name $APP --resource-group $RG
```

Update the `X-API-Key` header in every MCP client afterwards.

### Ship a new image version

```powershell
az acr build --registry $ACR --image flowcase-mcp:latest --file Dockerfile .
az containerapp update --name $APP --resource-group $RG --image crflowcasemcpdev.azurecr.io/flowcase-mcp:latest
```

### Scale to zero when idle

The Bicep sets `minReplicas: 0`. The app auto-scales up on first
request (~2–5 s cold start) and back to zero after idle.

### Read logs

```powershell
az containerapp logs show --name $APP --resource-group $RG --follow
```

### Destroy the whole environment

```powershell
az group delete -n $RG --yes --no-wait
# Key Vault is soft-deleted for 7 days. If you want to redeploy with the
# same name immediately, purge it:
az keyvault purge --name kv-flowcasemcp-dev --location norwayeast
```

---

## Cost estimate

With `minReplicas=0` and personal-use traffic patterns:

| Resource | Monthly (approx) |
|---|---|
| Container App (scale-to-zero) | ~NOK 10–50 |
| ACR Basic | ~NOK 50 |
| Key Vault | ~NOK 10 |
| Storage Account (File Share, <5 GB) | ~NOK 5 |
| Log Analytics (30-day retention) | ~NOK 20 |
| **Total** | **~NOK 100/mo** |

Scale grows roughly linearly with active users.

## Next steps when opening to the team

When more than one person needs access:

1. **Swap API-key auth for Entra ID** — Container Apps supports built-in
   Microsoft identity provider at the ingress level (no code change).
2. **Introduce per-user audit** — log the Entra user ID alongside each
   request for GDPR traceability.
3. **Raise scaling limits** — set `minReplicas: 1` for faster first
   response and bump `maxReplicas` based on concurrency needs.
4. **Private networking** — move the Container App into a VNet and
   restrict egress to the ServiceHub endpoint only if required by IT.
