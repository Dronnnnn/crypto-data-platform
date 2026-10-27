# Dot-source from the repo root: . ./scripts/connect_redshift.ps1
$ErrorActionPreference = 'Stop'
$terraformOutputsJson = & terraform -chdir=terraform output -json
if ($LASTEXITCODE -ne 0) { throw 'Cannot read Terraform outputs' }
$terraformOutputs = ($terraformOutputsJson -join "`n") | ConvertFrom-Json
Remove-Variable terraformOutputsJson
function Get-TerraformValue([string]$Name, [switch]$Optional) {
    $property = $terraformOutputs.PSObject.Properties[$Name]
    if (-not $property) {
        if ($Optional) { return $null }
        throw "Missing Terraform output: $Name"
    }
    return [string]$property.Value.value
}
$env:DBT_REDSHIFT_HOST = Get-TerraformValue 'redshift_endpoint_host'
$env:DBT_REDSHIFT_PORT = Get-TerraformValue 'redshift_endpoint_port'
$env:DBT_REDSHIFT_DBNAME = Get-TerraformValue 'redshift_database_name'
$env:DBT_REDSHIFT_SCHEMA = 'analytics'
$env:AWS_DEFAULT_REGION = 'ap-southeast-1'
$env:AWS_REGION = $env:AWS_DEFAULT_REGION
$env:ATHENA_WORKGROUP = Get-TerraformValue 'athena_workgroup_name'
$namespaceName = Get-TerraformValue 'redshift_namespace_name' -Optional
if (-not $namespaceName) {
    # Older applied state predates this output; discover it without applying Terraform.
    $workgroupName = Get-TerraformValue 'redshift_workgroup_name'
    $namespaceName = & aws redshift-serverless get-workgroup --workgroup-name $workgroupName --region $env:AWS_REGION --query workgroup.namespaceName --output text
    if ($LASTEXITCODE -ne 0 -or -not $namespaceName) { throw 'Cannot discover namespace' }
}
$namespaceJson = & aws redshift-serverless get-namespace --namespace-name $namespaceName --region $env:AWS_REGION --output json
if ($LASTEXITCODE -ne 0) { throw 'Cannot read namespace metadata' }
$namespaceData = ($namespaceJson | ConvertFrom-Json).namespace
$secretJson = & aws secretsmanager get-secret-value --secret-id $namespaceData.adminPasswordSecretArn --region $env:AWS_REGION --query SecretString --output text
if ($LASTEXITCODE -ne 0) { throw 'Cannot retrieve managed password' }
$secretData = $secretJson | ConvertFrom-Json
$env:DBT_REDSHIFT_USER = $namespaceData.adminUsername
$env:DBT_ENV_SECRET_REDSHIFT_PASSWORD = $secretData.password
Remove-Variable secretJson, secretData, namespaceJson, namespaceData
if (-not $env:DBT_ENV_SECRET_REDSHIFT_PASSWORD) { throw 'Managed password was empty' }
Write-Host 'Redshift variables exported for this shell; password was not printed.'
