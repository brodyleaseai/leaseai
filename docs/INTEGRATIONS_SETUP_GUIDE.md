# LeaseAI Integrations Setup Guide

**Phase 7: Native API Integrations**

This guide provides step-by-step instructions for configuring and using all LeaseAI third-party integrations.

---

## Table of Contents

1. [Property Management Systems](#property-management-systems)
   - [Yardi Voyager](#1-yardi-voyager)
   - [MRI Software](#2-mri-software)
2. [Accounting & Payments](#accounting--payments)
   - [QuickBooks Online](#3-quickbooks-online)
3. [Document Management](#document-management)
   - [DocuSign eSignature](#4-docusign-esignature)
4. [Notifications](#notifications)
   - [Slack](#5-slack)
   - [Microsoft Teams](#6-microsoft-teams)
5. [Field Mappings Reference](#field-mappings-reference)
6. [Troubleshooting](#troubleshooting)

---

## Property Management Systems

### 1. Yardi Voyager

**Purpose:** Bidirectional sync of lease data with Yardi Voyager property management system.

#### Prerequisites
- Active Yardi Voyager account
- API access enabled by Yardi administrator
- OAuth 2.0 credentials (Client ID & Client Secret)

#### Setup Steps

1. **Register OAuth Application in Yardi**
   - Log into Yardi API Portal: https://api.yardi.com
   - Navigate to **Applications** → **Register New Application**
   - Fill in application details:
     - **Application Name:** LeaseAI
     - **Redirect URI:** `https://yourdomain.com/oauth/yardi/callback`
     - **Scopes:** `leases:read`, `leases:write`, `tenants:read`, `tenants:write`
   - Click **Register** and save your **Client ID** and **Client Secret**

2. **Configure in LeaseAI**
   - Navigate to **Integrations** page in LeaseAI
   - Click **Configure Yardi Integration**
   - Enter credentials:
     - **Client ID:** [Your Client ID]
     - **Client Secret:** [Your Client Secret]
     - **Entity ID:** [Your Yardi property entity ID]
     - **Environment:** Select `production` or `sandbox`
   - Click **Save Configuration**

3. **Complete OAuth Flow**
   - Click **Connect to Yardi**
   - You will be redirected to Yardi login
   - Log in with your Yardi credentials
   - Grant LeaseAI permission to access your data
   - You will be redirected back to LeaseAI

4. **Test Connection**
   - Click **Test Connection** button
   - Verify successful connection message

#### Usage

**Import Leases from Yardi:**
```python
from integrations.yardi import YardiVoyagerIntegration

# Initialize integration
yardi = YardiVoyagerIntegration(client_id='your-client', config={
    'client_id': 'YOUR_CLIENT_ID',
    'client_secret': 'YOUR_CLIENT_SECRET',
    'entity_id': 'YOUR_ENTITY_ID',
    'environment': 'production'
})

# Authenticate
yardi.authenticate()

# Import leases
result = yardi.import_leases(start_date='2024-01-01', end_date='2024-12-31')
print(f"Imported {result['lease_count']} leases")
```

**Export Lease to Yardi:**
```python
lease_data = {
    'tenant_name': 'ABC Corporation',
    'unit_number': '101',
    'lease_start_date': '2024-01-01',
    'lease_end_date': '2025-12-31',
    'monthly_rent': 5000.00,
    # ... other fields (see Field Mappings section)
}

result = yardi.export_lease(lease_data)
print(f"Exported lease ID: {result['yardi_lease_id']}")
```

#### Field Mappings: Yardi ↔ LeaseAI

| LeaseAI Field | Yardi API Field | Direction | Notes |
|---------------|-----------------|-----------|-------|
| `tenant_name` | `TenantName` | Both | Required |
| `unit_number` | `UnitCode` | Both | Required |
| `lease_start_date` | `LeaseFromDate` | Both | Format: YYYY-MM-DD |
| `lease_end_date` | `LeaseToDate` | Both | Format: YYYY-MM-DD |
| `monthly_rent` | `RentAmount` | Both | Decimal |
| `security_deposit` | `DepositAmount` | Both | Decimal |
| `square_footage` | `SquareFootage` | Both | Integer |
| `tenant_email` | `EmailAddress` | Both | |
| `tenant_phone` | `PhoneNumber` | Both | |
| `lease_status` | `LeaseStatus` | Both | Active/Expired/Terminated |

**Full 84-field mapping available in source code: `integrations/yardi.py`**

---

### 2. MRI Software

**Purpose:** Sync lease and tenant data with MRI Software property management platform.

#### Prerequisites
- Active MRI Software account
- API key with read/write permissions
- Property ID

#### Setup Steps

1. **Generate API Key in MRI**
   - Log into MRI Software portal
   - Navigate to **Settings** → **API Access**
   - Click **Generate New API Key**
   - Enter key description: "LeaseAI Integration"
   - Select permissions:
     - ✅ Read Leases
     - ✅ Write Leases
     - ✅ Read Tenants
     - ✅ Write Tenants
   - Click **Generate** and copy your **API Key**
   - **Important:** Save the key securely - it will only be shown once

2. **Get Property ID**
   - In MRI portal, navigate to **Properties**
   - Select your property
   - Copy the **Property ID** from the URL or property details

3. **Configure in LeaseAI**
   - Navigate to **Integrations** page
   - Click **Configure MRI Integration**
   - Enter credentials:
     - **API Key:** [Your API Key]
     - **Property ID:** [Your Property ID]
     - **Environment:** Select `production` or `sandbox`
   - Click **Save Configuration**

4. **Test Connection**
   - Click **Test Connection** button
   - Verify successful connection message

#### Usage

**Export Lease to MRI:**
```python
from integrations.mri import MRISoftwareIntegration

# Initialize integration
mri = MRISoftwareIntegration(client_id='your-client', config={
    'api_key': 'YOUR_API_KEY',
    'property_id': 'YOUR_PROPERTY_ID',
    'environment': 'production'
})

# Authenticate
mri.authenticate()

# Export lease
lease_data = {
    'tenant_name': 'XYZ Company',
    'unit_number': '202',
    'lease_start_date': '2024-03-01',
    'lease_end_date': '2026-02-28',
    'monthly_rent': 7500.00,
    # ... other fields
}

result = mri.export_lease(lease_data)
print(f"Lease created in MRI: {result['lease_id']}")
```

#### Field Mappings: MRI ↔ LeaseAI

| LeaseAI Field | MRI API Field | Direction | Notes |
|---------------|---------------|-----------|-------|
| `tenant_name` | `tenantName` | Both | Required |
| `unit_number` | `unitIdentifier` | Both | Required |
| `lease_start_date` | `leaseStartDate` | Both | ISO 8601 format |
| `lease_end_date` | `leaseEndDate` | Both | ISO 8601 format |
| `monthly_rent` | `monthlyRentAmount` | Both | Number |
| `security_deposit` | `securityDepositAmount` | Both | Number |
| `square_footage` | `unitSquareFeet` | Both | Number |

---

## Accounting & Payments

### 3. QuickBooks Online

**Purpose:** Export rent rolls and CAM charges as invoices in QuickBooks Online.

#### Prerequisites
- Active QuickBooks Online account
- QuickBooks Online Accountant or Plus subscription (required for API access)
- QuickBooks Developer account

#### Setup Steps

1. **Create QuickBooks App**
   - Go to https://developer.intuit.com
   - Sign in or create developer account
   - Click **Create an app** → **QuickBooks Online**
   - Enter app details:
     - **App Name:** LeaseAI
     - **App Description:** Lease management integration
     - **Redirect URI:** `https://yourdomain.com/oauth/quickbooks/callback`
   - Select **Scopes:**
     - ✅ Accounting (com.intuit.quickbooks.accounting)
   - Click **Create app**
   - Save your **Client ID** and **Client Secret**

2. **Get Company (Realm) ID**
   - Log into QuickBooks Online
   - Look at browser URL: `https://app.qbo.intuit.com/app/company/[REALM_ID]/...`
   - Copy the **Realm ID** (numeric value after `/company/`)

3. **Configure in LeaseAI**
   - Navigate to **Integrations** → **Accounting**
   - Click **Configure QuickBooks Integration**
   - Enter credentials:
     - **Client ID:** [Your Client ID]
     - **Client Secret:** [Your Client Secret]
     - **Realm ID:** [Your Company ID]
     - **Environment:** Select `production` or `sandbox`
   - Click **Save Configuration**

4. **Complete OAuth Flow**
   - Click **Connect to QuickBooks**
   - Sign in with QuickBooks credentials
   - Grant LeaseAI access
   - You will be redirected back to LeaseAI

#### Usage

**Export Rent Roll:**
```python
from integrations.quickbooks import QuickBooksIntegration

# Initialize integration
qb = QuickBooksIntegration(client_id='your-client', config={
    'client_id': 'YOUR_CLIENT_ID',
    'client_secret': 'YOUR_CLIENT_SECRET',
    'realm_id': 'YOUR_REALM_ID',
    'environment': 'production'
})

# Authenticate
qb.authenticate()

# Export rent roll
rent_roll = [
    {
        'tenant_name': 'ABC Corp',
        'amount': 5000.00,
        'period': 'January 2024',
        'due_date': '2024-01-01'
    },
    # ... more rent items
]

result = qb.export_rent_roll(rent_roll)
print(f"Created {result['created_count']} invoices")
```

**Export CAM Charges:**
```python
cam_charges = [
    {
        'tenant_name': 'ABC Corp',
        'total_cam_charge': 1200.00,
        'cam_breakdown': {
            'Maintenance': 500.00,
            'Insurance': 300.00,
            'Property Tax': 400.00
        },
        'due_date': '2024-01-15'
    },
    # ... more CAM charges
]

result = qb.export_cam_charges(cam_charges)
print(f"Created {result['created_count']} CAM invoices")
```

---

## Document Management

### 4. DocuSign eSignature

**Purpose:** Send lease amendments and agreements for electronic signature.

#### Prerequisites
- DocuSign account (Developer, Business Pro, or Enterprise)
- DocuSign Developer account
- Integration key (OAuth credentials)

#### Setup Steps

1. **Create DocuSign Integration**
   - Go to https://admindemo.docusign.com (demo) or https://admin.docusign.com (production)
   - Navigate to **Settings** → **Apps and Keys**
   - Click **Add App and Integration Key**
   - Enter app name: **LeaseAI**
   - Copy the **Integration Key** (Client ID)

2. **Generate Secret Key**
   - Under your app, click **Add Secret Key**
   - Copy the **Secret Key** immediately (only shown once)

3. **Configure Redirect URI**
   - Under **Redirect URIs**, click **Add URI**
   - Enter: `https://yourdomain.com/oauth/docusign/callback`
   - Click **Save**

4. **Get Account ID**
   - In DocuSign admin panel, look at URL or account settings
   - Copy your **Account ID** (GUID format)

5. **Configure in LeaseAI**
   - Navigate to **Integrations** → **Document Management**
   - Click **Configure DocuSign Integration**
   - Enter credentials:
     - **Integration Key:** [Your Integration Key]
     - **Secret Key:** [Your Secret Key]
     - **Account ID:** [Your Account ID]
     - **Environment:** Select `demo` or `production`
   - Click **Save Configuration**

#### Usage

**Send Amendment for Signature:**
```python
from integrations.docusign import DocuSignIntegration

# Initialize integration
docusign = DocuSignIntegration(client_id='your-client', config={
    'integration_key': 'YOUR_INTEGRATION_KEY',
    'secret_key': 'YOUR_SECRET_KEY',
    'account_id': 'YOUR_ACCOUNT_ID',
    'environment': 'production'
})

# Authenticate
docusign.authenticate()

# Prepare amendment data
amendment_data = {
    'id': 'amendment-123',
    'amendment_number': 'AMN-001',
    'document_name': 'Lease Amendment 001',
    'email_subject': 'Please sign: Lease Amendment for Unit 101',
    'email_body': 'Please review and sign the attached lease amendment.'
}

# Define signers
signers = [
    {
        'name': 'John Landlord',
        'email': 'landlord@example.com',
        'role': 'Landlord',
        'anchor_string': '/s1/',  # Where to place signature
        'date_anchor': '/d1/'      # Where to place date
    },
    {
        'name': 'Jane Tenant',
        'email': 'tenant@example.com',
        'role': 'Tenant',
        'anchor_string': '/s2/',
        'date_anchor': '/d2/'
    }
]

# Read PDF file
with open('amendment.pdf', 'rb') as f:
    pdf_content = f.read()

# Send for signature
result = docusign.send_amendment_for_signature(
    amendment_data=amendment_data,
    signers=signers,
    pdf_content=pdf_content
)

print(f"Envelope ID: {result['envelope_id']}")
```

**Check Signature Status:**
```python
status = docusign.get_envelope_status(envelope_id='your-envelope-id')
print(f"Status: {status['status']}")
print(f"Completed: {status['completed_signers']}/{status['completed_signers'] + status['pending_signers']}")
```

**Download Signed Document:**
```python
result = docusign.download_signed_document(envelope_id='your-envelope-id')

if result['success']:
    with open('signed_amendment.pdf', 'wb') as f:
        f.write(result['pdf_content'])
```

---

## Notifications

### 5. Slack

**Purpose:** Receive real-time lease alerts and notifications in Slack channels.

#### Prerequisites
- Slack workspace with admin permissions
- Ability to create incoming webhooks

#### Setup Steps

1. **Create Incoming Webhook**
   - Go to https://api.slack.com/apps
   - Click **Create New App** → **From scratch**
   - Enter **App Name:** LeaseAI Notifier
   - Select your workspace
   - Click **Create App**

2. **Enable Incoming Webhooks**
   - In your app settings, click **Incoming Webhooks**
   - Toggle **Activate Incoming Webhooks** to **On**
   - Click **Add New Webhook to Workspace**
   - Select the channel for notifications (e.g., `#leaseai-alerts`)
   - Click **Allow**
   - Copy the **Webhook URL** (starts with `https://hooks.slack.com/...`)

3. **Configure in LeaseAI**
   - Navigate to **Integrations** → **Notifications**
   - Click **Configure Slack Integration**
   - Enter:
     - **Webhook URL:** [Your Webhook URL]
     - **Default Channel:** `#leaseai-alerts` (optional)
     - **Bot Username:** `LeaseAI Bot` (optional)
   - Select notification preferences:
     - ✅ Lease expirations
     - ✅ CAM reconciliation completion
     - ✅ Anomaly detection alerts
     - ☐ Amendment signature status
   - Click **Save Configuration**

4. **Test Connection**
   - Click **Test Connection**
   - Check your Slack channel for test message

#### Usage

**Send Custom Notification:**
```python
from integrations.notifications import SlackNotifier

# Initialize notifier
slack = SlackNotifier(client_id='your-client', config={
    'webhook_url': 'YOUR_WEBHOOK_URL',
    'channel': '#leaseai-alerts',
    'username': 'LeaseAI Bot'
})

slack.authenticate()

# Send notification
result = slack.send_notification(
    title="Lease Renewal Required",
    message="Lease for ABC Corp expires in 30 days",
    color="warning",
    fields=[
        {'title': 'Tenant', 'value': 'ABC Corp', 'short': True},
        {'title': 'Unit', 'value': '101', 'short': True},
        {'title': 'Expiration', 'value': '2024-12-31', 'short': True}
    ]
)
```

**Pre-built Notification Types:**

- **Lease Expiration Alert:**
  ```python
  slack.notify_lease_expiration({
      'tenant_name': 'ABC Corp',
      'unit_number': '101',
      'expiration_date': '2024-12-31',
      'days_until_expiry': 30
  })
  ```

- **CAM Reconciliation Completion:**
  ```python
  slack.notify_cam_completion({
      'property_name': 'Oak Plaza',
      'period': 'Q1 2024',
      'total_expenses': 125000.00,
      'total_recoveries': 118500.00
  })
  ```

- **Anomaly Detection Alert:**
  ```python
  slack.notify_anomaly_detected({
      'anomaly_type': 'Rent Increase Mismatch',
      'severity': 'high',
      'lease_identifier': 'Unit 202 - XYZ Corp',
      'description': 'Detected 15% rent increase but lease specifies 3% annual cap'
  })
  ```

---

### 6. Microsoft Teams

**Purpose:** Receive real-time lease alerts and notifications in Microsoft Teams channels.

#### Prerequisites
- Microsoft Teams access
- Channel admin permissions

#### Setup Steps

1. **Create Incoming Webhook in Teams**
   - Open Microsoft Teams
   - Navigate to the channel where you want notifications
   - Click the **⋯** (more options) next to the channel name
   - Select **Connectors** (or **Manage team** → **Connectors**)
   - Search for **Incoming Webhook**
   - Click **Add** or **Configure**
   - Enter webhook name: **LeaseAI Notifications**
   - Optionally upload an icon
   - Click **Create**
   - Copy the **Webhook URL** (starts with `https://...webhook.office.com/...`)
   - Click **Done**

2. **Configure in LeaseAI**
   - Navigate to **Integrations** → **Notifications**
   - Click **Configure Teams Integration**
   - Enter:
     - **Webhook URL:** [Your Webhook URL]
   - Select notification preferences:
     - ✅ Lease expirations
     - ✅ CAM reconciliation completion
     - ✅ Anomaly detection alerts
     - ☐ Amendment signature status
   - Click **Save Configuration**

3. **Test Connection**
   - Click **Test Connection**
   - Check your Teams channel for test message

#### Usage

**Send Custom Notification:**
```python
from integrations.notifications import TeamsNotifier

# Initialize notifier
teams = TeamsNotifier(client_id='your-client', config={
    'webhook_url': 'YOUR_WEBHOOK_URL'
})

teams.authenticate()

# Send notification
result = teams.send_notification(
    title="Lease Renewal Required",
    message="Lease for ABC Corp expires in 30 days",
    theme_color="FFA500",  # Orange (hex without #)
    sections=[{
        'facts': [
            {'name': 'Tenant', 'value': 'ABC Corp'},
            {'name': 'Unit', 'value': '101'},
            {'name': 'Expiration', 'value': '2024-12-31'}
        ]
    }]
)
```

**Pre-built Notification Types:**

Same as Slack (see above) - just use `TeamsNotifier` instead:
- `teams.notify_lease_expiration(...)`
- `teams.notify_cam_completion(...)`
- `teams.notify_anomaly_detected(...)`

---

## Field Mappings Reference

### Complete Yardi Voyager Field Mappings (84 Fields)

Refer to `integrations/yardi.py` → `map_lease_to_yardi()` function for complete mapping including:
- **Basic Lease Info:** Dates, terms, status, type
- **Financial Terms:** Rent, deposits, escalations, CAM charges
- **Tenant Information:** Name, contact, business details
- **Unit Details:** Number, square footage, type, building
- **Lease Options:** Renewal options, purchase options, termination rights
- **Special Provisions:** Restrictions, allowances, concessions

### MRI Software Field Mappings

See `integrations/mri.py` → `map_lease_to_mri()` function for complete mapping.

---

## Troubleshooting

### Common Issues

#### Yardi Integration

**Issue:** OAuth authentication fails
- **Solution:** Verify Client ID and Client Secret are correct
- **Solution:** Check redirect URI matches exactly in Yardi portal
- **Solution:** Ensure API access is enabled by Yardi administrator

**Issue:** Import fails with "Invalid entity ID"
- **Solution:** Verify entity ID is correct (contact Yardi admin)
- **Solution:** Ensure entity has API access enabled

#### MRI Integration

**Issue:** API key authentication fails
- **Solution:** Verify API key is entered correctly (no extra spaces)
- **Solution:** Check API key has not expired
- **Solution:** Verify API key has correct read/write permissions

#### QuickBooks Integration

**Issue:** Cannot create invoices
- **Solution:** Verify QuickBooks account has active subscription (not expired trial)
- **Solution:** Check Chart of Accounts has required income accounts
- **Solution:** Ensure customers (tenants) exist or can be auto-created

**Issue:** OAuth token expires
- **Solution:** QuickBooks tokens expire after 1 hour - refresh tokens are valid for 100 days
- **Solution:** LeaseAI automatically refreshes tokens, but if issues persist, re-authenticate

#### DocuSign Integration

**Issue:** Cannot send envelopes
- **Solution:** Verify account has sufficient envelope allowance
- **Solution:** Check signers' email addresses are valid
- **Solution:** Ensure PDF document is valid and not corrupted

**Issue:** Signatures not anchoring correctly
- **Solution:** Add anchor strings (`/s1/`, `/s2/`) to PDF where signatures should appear
- **Solution:** Alternatively, use absolute positioning instead of anchor strings

#### Slack Integration

**Issue:** Test message not received
- **Solution:** Verify webhook URL is correct
- **Solution:** Check Slack channel still exists
- **Solution:** Ensure webhook has not been revoked

#### Microsoft Teams Integration

**Issue:** Notifications not appearing
- **Solution:** Verify webhook URL is correct and not expired
- **Solution:** Check Teams channel connectors are enabled
- **Solution:** Ensure webhook has not been removed from channel

### Getting Help

For additional support:
- **Documentation:** See `docs/` folder for detailed guides
- **API Reference:** Check source code in `integrations/` folder
- **GitHub Issues:** Report bugs at [repository URL]
- **Contact:** support@leaseai.com

---

## Security Best Practices

1. **API Keys and Secrets**
   - Store credentials securely using environment variables
   - Never commit credentials to Git
   - Rotate credentials regularly (every 90 days recommended)
   - Use separate credentials for production and development

2. **OAuth Tokens**
   - Tokens are stored encrypted in database
   - Refresh tokens automatically when expired
   - Revoke tokens when integration is disabled

3. **Webhook URLs**
   - Treat webhook URLs as sensitive credentials
   - Regenerate webhooks if exposed
   - Use HTTPS only for all API communication

4. **Audit Logging**
   - All integration syncs are logged in audit_log table
   - Monitor failed sync attempts
   - Review integration activity regularly

---

## Integration Architecture

### Base Integration Framework

All integrations inherit from `BaseIntegration` class providing:
- Standard authentication flow
- Automatic retry logic with exponential backoff
- Sync logging to database
- Error handling and reporting

### Available Mixins

- **LeaseExportMixin:** Export lease data to external systems
- **TenantExportMixin:** Export tenant data
- **BidirectionalSyncMixin:** Two-way sync capabilities
- **WebhookMixin:** Incoming webhook handler for real-time updates

### Creating Custom Integrations

To add a new integration:

1. Create new file in `integrations/` folder
2. Inherit from `BaseIntegration` and relevant mixins
3. Implement required methods:
   - `_get_integration_type()`
   - `authenticate()`
   - `test_connection()`
   - Custom sync methods
4. Add integration to management UI
5. Document setup steps in this guide

---

## Conclusion

This guide covers all supported LeaseAI integrations. For technical implementation details, see the source code in the `integrations/` directory.

For questions or feature requests, contact the LeaseAI development team.

**Last Updated:** October 2026  
**Version:** 1.0
