# Configuration Guide

## Configuration Files

The project uses two main configuration files:

1. **`config/config.yaml`** - Application settings
2. **`.env`** - Environment variables and secrets

Both files have templates (`*.template`) in the repository.

## Setup

1. Copy the templates:
   ```bash
   cp config/config.yaml.template config/config.yaml
   cp .env.template .env
   ```

2. Edit both files with your specific settings:
   ```bash
   nano config/config.yaml
   nano .env
   ```

3. Never commit the actual config files (they're in `.gitignore`)

## config.yaml

Main application configuration in YAML format.

### ClinVar Settings

```yaml
clinvar:
  # FTP source URLs for ClinVar data
  source_url: "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
  checksum_url: "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz.md5"

  # Where to save downloaded files
  download_dir: "data/downloads"
```

**Notes:**
- URLs should remain as-is (official NCBI FTP servers)
- `download_dir` is relative to project root
- Directory will be created automatically if it doesn't exist

### Filtering

```yaml
filtering:
  # Enable/disable data filtering
  enabled: false

  # Filter by chromosomes (null = all)
  chromosomes: null
  # Example: ["1", "2", "X", "Y"]

  # Filter by clinical significance (null = all)
  clinical_significance_filter: null
  # Example: ["Pathogenic", "Likely pathogenic"]
```

**Use cases:**
- Enable filtering to create smaller test datasets
- Filter specific chromosomes for analysis
- Create focused packages for specific clinical significance levels

### Quilt Settings

```yaml
quilt:
  # S3 bucket for the Quilt registry (REQUIRED)
  bucket: "your-clinvar-registry"

  # Package name in Quilt
  package_name: "biodata/clinvar"

  # Full registry URL
  registry: "s3://your-clinvar-registry"

  # Push to registry (set to false for testing locally)
  push_to_registry: true
```

**Important:**
- Replace `your-clinvar-registry` with your actual S3 bucket name
- Bucket must be created before running pipeline
- Package name uses convention: `namespace/name`

### Quality Settings

```yaml
quality:
  thresholds:
    # Minimum acceptable quality score (0-100)
    min_quality_score: 75

    # Maximum acceptable null percentage
    max_null_percentage: 15

    # Maximum acceptable conflict rate (%)
    max_conflict_rate: 5

    # Maximum acceptable drift between versions (%)
    max_drift_percentage: 20

  # Where to save quality reports
  output_dir: "output/quality_reports"
```

**Threshold tuning:**
- Start conservative (high min_quality_score, low max_* values)
- Adjust based on your data and requirements
- Use `analyze_history.py` to see historical values

### Alerting

```yaml
alerts:
  # Enable/disable alerts
  enabled: false

  # Email for notifications
  email: null  # e.g., "alerts@example.com"

  # Slack webhook for notifications
  slack_webhook: null  # e.g., "https://hooks.slack.com/..."
```

**Setup:**
- Email requires SMTP settings in `.env`
- Slack requires webhook URL from your Slack workspace
- Leave as `null` to disable that notification type

### Scheduling

```yaml
scheduling:
  # How often to check for new ClinVar releases (days)
  check_interval_days: 7

  # Automatically run pipeline when new release detected
  auto_run: false
```

**Typical values:**
- `check_interval_days: 7` - Check weekly (ClinVar releases monthly)
- `auto_run: true` - Only if you have scheduled execution set up (cron/Lambda)

### Logging

```yaml
logging:
  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  level: "INFO"

  # Directory for log files
  log_dir: "logs"

  # Write logs to file
  file_logging: true

  # Write logs to console
  console_logging: true
```

**Log levels:**
- `DEBUG` - Detailed information for diagnosing problems
- `INFO` - General informational messages (recommended for production)
- `WARNING` - Warning messages for potentially harmful situations
- `ERROR` - Error messages for serious problems
- `CRITICAL` - Critical errors, system may not continue

## .env

Environment variables for secrets and credentials.

### AWS Configuration

```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
```

**How to get credentials:**
1. Log in to AWS Console
2. Go to IAM → Users → Your User
3. Create Access Key
4. Copy Key ID and Secret

**Recommended IAM permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-clinvar-registry",
        "arn:aws:s3:::your-clinvar-registry/*"
      ]
    }
  ]
}
```

### Quilt Configuration

```bash
QUILT_BUCKET=your-clinvar-registry
```

### Email Configuration (Optional)

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

**Note:** For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

### Slack Configuration (Optional)

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**How to get webhook:**
1. Go to your Slack workspace settings
2. Create an Incoming Webhook
3. Copy the URL

## Loading Configuration

The application loads configuration in this order (later overrides earlier):

1. Built-in defaults (in code)
2. `config/config.yaml` file
3. Environment variables
4. Command-line arguments

## Validation

Configuration is validated on startup:

- Required fields are checked
- File paths are validated
- URLs are checked
- Credentials are tested
- Thresholds are validated

Errors will be reported with helpful messages.

## Best Practices

1. **Never commit actual config files**
   - They contain sensitive data
   - Use `.template` files for examples

2. **Start with templates**
   - Copy `.template` files
   - Modify as needed
   - Keep template files up-to-date

3. **Use environment variables for secrets**
   - Store in `.env` (git-ignored)
   - Never hardcode credentials
   - Use IAM roles on AWS when possible

4. **Test configuration changes**
   - Dry-run before committing
   - Verify thresholds with historical data
   - Test alerts with dry-run mode

5. **Document custom settings**
   - Add comments to your config.yaml
   - Keep notes on why values were chosen
   - Update when circumstances change

## Troubleshooting

**"Config file not found"**
```bash
# Make sure you copied the template
cp config/config.yaml.template config/config.yaml
```

**"AWS credentials not found"**
```bash
# Check your .env file exists
ls -la .env

# Or use aws configure
aws configure

# Test credentials
aws sts get-caller-identity
```

**"Slack webhook invalid"**
```bash
# Test the webhook with curl
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test"}' \
  https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**"S3 bucket not accessible"**
```bash
# Check bucket exists
aws s3 ls | grep your-clinvar-registry

# Check credentials permissions
aws s3 ls s3://your-clinvar-registry/
```

## Environment-Specific Configs

For different environments, create separate config files:

```bash
config/config.yaml.dev      # Development settings
config/config.yaml.prod     # Production settings
config/config.yaml.test     # Testing settings
```

Then use via CLI:
```bash
poetry run python scripts/run_pipeline.py --config config/config.yaml.prod
```

Or set environment variable:
```bash
export CONFIG_FILE=config/config.yaml.prod
poetry run python scripts/run_pipeline.py
```
