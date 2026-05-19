// Task Tracker - Azure infrastructure (Bicep)
//
// Provisions:
//   * Log Analytics workspace + Application Insights
//   * Azure Container Registry (for the FastAPI image)
//   * User-assigned Managed Identity (so the container app can pull from ACR
//     without storing creds)
//   * Container Apps Environment
//   * Container App running the FastAPI backend
//   * Static Web App for the React frontend
//
// Deployed via `azd up`. The image build/push and SPA upload are handled by
// azd via azure.yaml.

targetScope = 'resourceGroup'

@minLength(1)
@maxLength(64)
@description('Name of the the environment (used as prefix for all resources).')
param environmentName string

@minLength(1)
@description('Primary location for all resources.')
param location string

@description('Tenant ID for Entra ID auth.')
param tenantId string

@description('Client ID of the Task Tracker API app registration.')
param apiClientId string

@secure()
@description('Client secret of the Task Tracker API app registration.')
param apiClientSecret string

@description('Client ID of the Task Tracker SPA app registration.')
param spaClientId string

@description('Dataverse URL. Use a placeholder when running with the SQLite store.')
param dataverseUrl string = 'https://example.crm.dynamics.com'

@description('Container image tag. Set by azd when it pushes a new image.')
param apiImageName string = ''

// ---------- Names ----------
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var prefix = 'tt'
var tags = {
  'azd-env-name': environmentName
}

// ---------- Observability ----------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-log-${resourceToken}'
  location: location
  tags: tags
  properties: {
    retentionInDays: 30
    sku: { name: 'PerGB2018' }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${prefix}-appi-${resourceToken}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ---------- Managed Identity ----------
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-mi-${resourceToken}'
  location: location
  tags: tags
}

// ---------- Container Registry ----------
resource registry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: 'ttacr${resourceToken}'
  location: location
  tags: union(tags, { 'azd-service-name': 'api' })
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

// AcrPull role for the managed identity
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, managedIdentity.id, 'AcrPull')
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ---------- Container Apps Environment ----------
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-cae-${resourceToken}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ---------- Container App (FastAPI) ----------
resource apiContainerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-api-${resourceToken}'
  location: location
  tags: union(tags, { 'azd-service-name': 'api' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${managedIdentity.id}': {} }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        corsPolicy: {
          allowedOrigins: ['*']            // tightened post-deploy via env var
          allowedMethods: ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
        }
      }
      registries: [
        {
          server: registry.properties.loginServer
          identity: managedIdentity.id
        }
      ]
      secrets: [
        { name: 'api-client-secret', value: apiClientSecret }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: !empty(apiImageName) ? apiImageName : 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'TENANT_ID', value: tenantId }
            { name: 'API_CLIENT_ID', value: apiClientId }
            { name: 'API_CLIENT_SECRET', secretRef: 'api-client-secret' }
            { name: 'SPA_CLIENT_ID', value: spaClientId }
            { name: 'API_SCOPE_NAME', value: 'access_as_user' }
            { name: 'DATAVERSE_URL', value: dataverseUrl }
            { name: 'DATAVERSE_TABLE', value: 'cr123_tasks' }
            { name: 'ALLOWED_ORIGINS', value: 'https://${staticWebApp.properties.defaultHostname}' }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8000 }
              initialDelaySeconds: 10
              periodSeconds: 30
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
  dependsOn: [
    acrPullRole
  ]
}

// ---------- Static Web App (React) ----------
resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: '${prefix}-swa-${resourceToken}'
  location: location
  tags: union(tags, { 'azd-service-name': 'web' })
  sku: { name: 'Free', tier: 'Free' }
  properties: {
    repositoryUrl: ''
    branch: ''
    buildProperties: {
      appLocation: 'frontend'
      outputLocation: 'dist'
    }
  }
}

// ---------- Outputs ----------
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.properties.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = registry.name
output AZURE_CONTAINER_APPS_ENVIRONMENT_NAME string = containerAppsEnv.name
output AZURE_RESOURCE_GROUP string = resourceGroup().name
output API_BASE_URL string = 'https://${apiContainerApp.properties.configuration.ingress.fqdn}'
output STATIC_WEB_APP_NAME string = staticWebApp.name
output STATIC_WEB_APP_HOSTNAME string = staticWebApp.properties.defaultHostname
output APPLICATIONINSIGHTS_CONNECTION_STRING string = appInsights.properties.ConnectionString
output MANAGED_IDENTITY_CLIENT_ID string = managedIdentity.properties.clientId
