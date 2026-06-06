# Deploy all 3 Lambda functions to AWS
# Run from project root: .\scripts\deploy_lambdas.ps1

$ErrorActionPreference = "Stop"
$REGION    = "us-east-1"
$S3_BUCKET = "commitmatch-team074"
$ROLE_ARN  = "arn:aws:iam::162168468428:role/commmitmatch-lambda-role"   # <-- paste your Lambda execution role ARN here

if (-not $ROLE_ARN) {
    Write-Error "Set ROLE_ARN at the top of this script before running."
    exit 1
}

# ── Step 0: Upload CSV to S3 ─────────────────────────────────────────────────
Write-Host "`n[0] Uploading CSV to S3..."
aws s3 cp data/Dataset_demo.csv "s3://$S3_BUCKET/Dataset_demo.csv" --region $REGION
Write-Host "    CSV uploaded."

# ── Step 1: Install dependencies ─────────────────────────────────────────────
Write-Host "`n[1] Installing Lambda dependencies..."
$pkgDir = "lambda\package"
if (Test-Path $pkgDir) { Remove-Item $pkgDir -Recurse -Force }
New-Item -ItemType Directory -Path $pkgDir | Out-Null
pip install twilio pandas boto3 -t $pkgDir -q
Write-Host "    Done."

# ── Helper: zip and deploy one function ──────────────────────────────────────
function Deploy-Lambda {
    param($Name, $Handler, $Schedule, $Description)

    Write-Host "`n[*] Deploying $Name..."

    # Build zip
    $zipPath = "lambda\${Name}.zip"
    if (Test-Path $zipPath) { Remove-Item $zipPath }

    Copy-Item "lambda\${Name}.py" "$pkgDir\${Name}.py"
    Compress-Archive -Path "$pkgDir\*" -DestinationPath $zipPath -Force
    Remove-Item "$pkgDir\${Name}.py"

    # Env vars for the function
    $envVars = "Variables={" +
        "AWS_REGION=$REGION," +
        "S3_BUCKET=$S3_BUCKET," +
        "CSV_KEY=Dataset_demo.csv," +
        "TWILIO_ACCOUNT_SID=$env:TWILIO_ACCOUNT_SID," +
        "TWILIO_AUTH_TOKEN=$env:TWILIO_AUTH_TOKEN," +
        "TWILIO_WHATSAPP_FROM=$env:TWILIO_WHATSAPP_FROM," +
        "DEMO_PHONE_1=$env:DEMO_PHONE_1," +
        "WEBSOCKET_ENDPOINT=$env:WEBSOCKET_ENDPOINT," +
        "WEBSOCKET_API_ID=$env:WEBSOCKET_API_ID" +
    "}"

    # Create or update function
    $exists = aws lambda get-function --function-name $Name --region $REGION 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    Updating existing function..."
        aws lambda update-function-code `
            --function-name $Name `
            --zip-file "fileb://$zipPath" `
            --region $REGION | Out-Null
        aws lambda update-function-configuration `
            --function-name $Name `
            --environment $envVars `
            --region $REGION | Out-Null
    } else {
        Write-Host "    Creating new function..."
        aws lambda create-function `
            --function-name $Name `
            --runtime python3.12 `
            --role $ROLE_ARN `
            --handler "${Name}.handler" `
            --zip-file "fileb://$zipPath" `
            --timeout 300 `
            --memory-size 512 `
            --environment $envVars `
            --description $Description `
            --region $REGION | Out-Null
    }

    # Create EventBridge rule
    $ruleName = "commitmatch-${Name}-trigger"
    aws events put-rule `
        --name $ruleName `
        --schedule-expression $Schedule `
        --state ENABLED `
        --region $REGION | Out-Null

    $funcArn = (aws lambda get-function --function-name $Name --region $REGION | ConvertFrom-Json).Configuration.FunctionArn

    # Allow EventBridge to invoke the function
    try {
        aws lambda add-permission `
            --function-name $Name `
            --statement-id "${ruleName}-invoke" `
            --action lambda:InvokeFunction `
            --principal events.amazonaws.com `
            --source-arn (aws events describe-rule --name $ruleName --region $REGION | ConvertFrom-Json).Arn `
            --region $REGION | Out-Null
    } catch {}

    aws events put-targets `
        --rule $ruleName `
        --targets "Id=${Name},Arn=${funcArn}" `
        --region $REGION | Out-Null

    Write-Host "    $Name deployed with schedule: $Schedule"
}

# ── Step 2: Deploy each function ─────────────────────────────────────────────
Deploy-Lambda `
    -Name        "standby_promoter" `
    -Handler     "standby_promoter.handler" `
    -Schedule    "rate(30 minutes)" `
    -Description "Promotes standby donor when primary silent for 4 hours"

Deploy-Lambda `
    -Name        "rhythm_nudger" `
    -Handler     "rhythm_nudger.handler" `
    -Schedule    "cron(30 3 * * ? *)" `
    -Description "Daily nudge to donors with upcoming donation window (9am IST)"

Deploy-Lambda `
    -Name        "shortage_detector" `
    -Handler     "shortage_detector.handler" `
    -Schedule    "rate(6 hours)" `
    -Description "Detects blood group shortages, creates DynamoDB alerts"

# ── Step 3: Cleanup ──────────────────────────────────────────────────────────
Remove-Item $pkgDir -Recurse -Force
Write-Host "`n All 3 Lambda functions deployed successfully."
Write-Host "   View them at: https://$REGION.console.aws.amazon.com/lambda/home?region=$REGION#/functions"
