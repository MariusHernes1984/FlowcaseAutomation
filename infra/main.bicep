// ============================================================================
// Flowcase MCP — Azure infrastructure (single-user dev deployment)
// ----------------------------------------------------------------------------
// Resources created (all in one resource group):
//
//   * Log Analytics workspace       (Container Apps logs)
//   * User-assigned Managed Identity (reads Key Vault + pulls from ACR)
//   * Azure Container Registry       (hosts the flowcase-mcp image)
//   * Key Vault + 2 secrets          (flowcase-api-key, mcp-api-key)
//   * Storage Account + File Share   (availability.xlsx)
//   * Container Apps Environment
//   * Container App                  (the MCP server itself)
//
// Deploy with:
//   az deployment group create \
//     -g rg-flowcase-mcp-dev \
//     -f infra/main.bicep \
//     -p principalId=<your-entra-object-id>
//
// After the first deploy, see docs/deployment.md for the build/push/update
// flow to replace the placeholder image with the real flowcase-mcp image.
// ============================================================================

@description('Short project name, used as prefix for every resource name')
param projectName string = 'flowcasemcp'

@description('Environment suffix (dev / test / prod)')
param envName string = 'dev'

@description('Azure region. Norway East for Atea data residency')
param location string = 'norwayeast'

@description('Object ID of the user who should be able to read secrets (for setting them post-deploy)')
param principalId string

@description('Placeholder image until a real one is pushed to ACR')
param initialImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Container CPU cores (0.25 is plenty for a single-user MCP)')
param containerCpu string = '0.25'

@description('Container memory')
param containerMemory string = '0.5Gi'

var suffix = '${projectName}-${envName}'
var suffixCompact = toLower(replace(suffix, '-', ''))

// ---------------------------------------------------------------------------
// Log Analytics — required for Container Apps environment logging
// ---------------------------------------------------------------------------
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${suffix}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ---------------------------------------------------------------------------
// User-assigned Managed Identity — used by Container App for ACR pull and
// Key Vault reads
// ---------------------------------------------------------------------------
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'mi-${suffix}'
  location: location
}

// ---------------------------------------------------------------------------
// Azure Container Registry
// ---------------------------------------------------------------------------
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: 'cr${suffixCompact}'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}

resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, identity.id, 'acrpull')
  scope: acr
  properties: {
    // AcrPull built-in role
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d'
    )
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Key Vault (RBAC mode)
// ---------------------------------------------------------------------------
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${suffix}'
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: null
  }
}

// Container App's identity reads secrets
resource kvReaderForIdentity 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, identity.id, 'secrets-user')
  scope: kv
  properties: {
    // Key Vault Secrets User
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '4633458b-17de-408a-b874-0445c86b69e6'
    )
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// The deploying user needs to set/read secrets
resource kvAdminForPrincipal 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, principalId, 'secrets-officer')
  scope: kv
  properties: {
    // Key Vault Secrets Officer
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'b86a8fe4-44ce-4948-aee5-eccb2c155cd7'
    )
    principalId: principalId
    principalType: 'User'
  }
}

// ---------------------------------------------------------------------------
// Storage Account + File Share for availability.xlsx
// ---------------------------------------------------------------------------
resource storage 'Microsoft.Storage/storageAccounts@2023-04-01' = {
  name: 'st${suffixCompact}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-04-01' = {
  parent: storage
  name: 'default'
}

resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-04-01' = {
  parent: fileService
  name: 'availability'
  properties: {
    accessTier: 'TransactionOptimized'
    shareQuota: 5
  }
}

// ---------------------------------------------------------------------------
// Cosmos DB — serverless SQL API for web-app state
// (users, agents, chat history — all PII kept in Norway East)
// ---------------------------------------------------------------------------
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: 'cosmos-${suffix}'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    disableLocalAuth: false
    publicNetworkAccess: 'Enabled'
    minimalTlsVersion: 'Tls12'
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmos
  name: 'flowcase'
  properties: {
    resource: {
      id: 'flowcase'
    }
  }
}

resource cosmosUsers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: cosmosDb
  name: 'users'
  properties: {
    resource: {
      id: 'users'
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
      }
    }
  }
}

resource cosmosAgents 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: cosmosDb
  name: 'agents'
  properties: {
    resource: {
      id: 'agents'
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
      }
    }
  }
}

resource cosmosChats 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: cosmosDb
  name: 'chats'
  properties: {
    resource: {
      id: 'chats'
      partitionKey: {
        // Partition by user so each user's history lives together.
        paths: ['/userId']
        kind: 'Hash'
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Container Apps Environment + storage link for file share
// ---------------------------------------------------------------------------
resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${suffix}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource envStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: env
  name: 'availability'
  properties: {
    azureFile: {
      accountName: storage.name
      accountKey: storage.listKeys().keys[0].value
      shareName: fileShare.name
      accessMode: 'ReadOnly'
    }
  }
}

// ---------------------------------------------------------------------------
// Container App
// ---------------------------------------------------------------------------
resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-${suffix}'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  dependsOn: [
    acrPullRole
    kvReaderForIdentity
  ]
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          identity: identity.id
        }
      ]
      secrets: [
        {
          name: 'flowcase-api-key'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/flowcase-api-key'
          identity: identity.id
        }
        {
          name: 'mcp-api-key'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/mcp-api-key'
          identity: identity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'flowcase-mcp'
          image: initialImage
          resources: {
            cpu: json(containerCpu)
            memory: containerMemory
          }
          env: [
            {
              name: 'FLOWCASE_MCP_TRANSPORT'
              value: 'streamable-http'
            }
            {
              name: 'PORT'
              value: '8000'
            }
            {
              name: 'FLOWCASE_BASE_URL'
              value: 'https://servicehub.atea.com/flowcase'
            }
            {
              name: 'FLOWCASE_API_KEY_HEADER'
              value: 'Ocp-Apim-Subscription-Key'
            }
            {
              name: 'FLOWCASE_DEFAULT_COUNTRY'
              value: 'no'
            }
            {
              name: 'FLOWCASE_DEFAULT_LANGUAGE'
              value: 'no'
            }
            {
              name: 'FLOWCASE_AVAILABILITY_PATH'
              value: '/data/availability.xlsx'
            }
            {
              name: 'FLOWCASE_API_KEY'
              secretRef: 'flowcase-api-key'
            }
            {
              name: 'FLOWCASE_MCP_API_KEY'
              secretRef: 'mcp-api-key'
            }
          ]
          volumeMounts: [
            {
              volumeName: 'availability'
              mountPath: '/data'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              periodSeconds: 10
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'availability'
          storageName: envStorage.name
          storageType: 'AzureFile'
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Outputs — used by the deployment flow in docs/deployment.md
// ---------------------------------------------------------------------------
output acrLoginServer string = acr.properties.loginServer
output acrName string = acr.name
output keyVaultName string = kv.name
output storageAccountName string = storage.name
output fileShareName string = fileShare.name
output containerAppName string = app.name
output containerAppFqdn string = app.properties.configuration.ingress.fqdn
output identityClientId string = identity.properties.clientId
output cosmosAccountName string = cosmos.name
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output cosmosDatabaseName string = cosmosDb.name

// ============================================================================
// Flowcase Web orchestrator — Container App
// ============================================================================

@description('Hostname (FQDN suffix inside the Container Apps environment) of the Flowcase MCP, used as MCP_URL. Auto-derived from the MCP app FQDN.')
var mcpInternalUrl = 'https://${app.properties.configuration.ingress.fqdn}/mcp'

resource webApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-${suffix}-web'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  dependsOn: [
    acrPullRole
    kvReaderForIdentity
  ]
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8001
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          identity: identity.id
        }
      ]
      secrets: [
        {
          name: 'admin-password'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/admin-password'
          identity: identity.id
        }
        {
          name: 'jwt-secret'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/jwt-secret'
          identity: identity.id
        }
        {
          name: 'azure-openai-api-key'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/azure-openai-api-key'
          identity: identity.id
        }
        {
          name: 'cosmos-key'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/cosmos-key'
          identity: identity.id
        }
        {
          name: 'mcp-api-key'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/mcp-api-key'
          identity: identity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'flowcase-web'
          image: initialImage
          resources: {
            cpu: json(containerCpu)
            memory: containerMemory
          }
          env: [
            {
              name: 'ENVIRONMENT'
              value: envName
            }
            {
              name: 'PORT'
              value: '8001'
            }
            {
              name: 'FLOWCASE_WEB_STATIC_DIR'
              value: '/app/static'
            }
            {
              name: 'ADMIN_EMAIL'
              value: 'marius.hernes@atea.no'
            }
            {
              name: 'ADMIN_PASSWORD'
              secretRef: 'admin-password'
            }
            {
              name: 'JWT_SECRET'
              secretRef: 'jwt-secret'
            }
            {
              name: 'COSMOS_ENDPOINT'
              value: cosmos.properties.documentEndpoint
            }
            {
              name: 'COSMOS_KEY'
              secretRef: 'cosmos-key'
            }
            {
              name: 'COSMOS_DATABASE'
              value: cosmosDb.name
            }
            {
              // kateecosystem-resource hosts gpt-5.4-mini and Claude 4.6
              // family, so we point the orchestrator there. Sweden Central
              // is still EU for data residency.
              name: 'AZURE_OPENAI_ENDPOINT'
              value: 'https://kateecosystem-resource.cognitiveservices.azure.com/'
            }
            {
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'azure-openai-api-key'
            }
            {
              name: 'DEFAULT_LLM_DEPLOYMENT'
              value: 'gpt-5.4-mini'
            }
            {
              name: 'MCP_URL'
              value: mcpInternalUrl
            }
            {
              name: 'MCP_API_KEY'
              secretRef: 'mcp-api-key'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8001
              }
              initialDelaySeconds: 15
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8001
              }
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
      }
    }
  }
}

output webAppName string = webApp.name
output webAppFqdn string = webApp.properties.configuration.ingress.fqdn
