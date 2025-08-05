# Secrets Vault System - Complete Guide

## Overview

The NeuroLM Secrets Vault is a comprehensive, secure system for managing API keys, credentials, and sensitive data. It provides enterprise-grade security with encryption, access logging, and key rotation capabilities.

## Features

### 🔐 Security Features
- **AES-256 Encryption**: All secrets encrypted with user-specific keys
- **PBKDF2 Key Derivation**: 100,000 iterations for strong key generation
- **Access Logging**: Complete audit trail of all secret operations
- **Automatic Expiration**: Support for time-based secret expiration
- **Key Rotation**: Built-in secret rotation with history tracking

### 🚀 User Experience
- **Web Interface**: Beautiful, responsive secrets manager at `/secrets`
- **API Management**: Dedicated API key management interface
- **Audit Dashboard**: Real-time security monitoring and logs
- **Mobile Support**: Fully responsive design for mobile devices

### 🔧 Technical Architecture
- **PostgreSQL Storage**: Secure database storage with proper indexing
- **Session Security**: Integrated with existing authentication system
- **Metadata Support**: Flexible metadata storage for secret organization
- **Backward Compatibility**: Legacy BYOK endpoints still supported

## Usage

### Accessing the Secrets Manager

1. **Navigate to `/secrets`** - Opens the complete secrets management interface
2. **Authentication Required** - Must be logged in to access
3. **Three Main Tabs**:
   - **API Keys**: Manage OpenAI, OpenRouter, and other API keys
   - **All Secrets**: Store any type of credential or secret
   - **Audit Log**: View security access history

### API Key Management

#### Adding API Keys
```javascript
// Via Web Interface
1. Go to /secrets → API Keys tab
2. Select provider (OpenAI, OpenRouter, etc.)
3. Enter API key
4. Click "Store API Key"

// Via API
POST /api/api-keys/store
{
  "provider": "openai",
  "api_key": "sk-..."
}
```

#### Viewing API Keys
```javascript
// Lists all API keys with masked values
GET /api/api-keys/list

// Response includes:
{
  "api_keys": [
    {
      "provider": "openai",
      "masked_key": "sk-...abc123",
      "created_at": "2025-07-15T22:21:30Z",
      "updated_at": "2025-07-15T22:21:30Z",
      "rotation_count": 0
    }
  ]
}
```

#### Rotating API Keys
```javascript
// Rotate with new value
POST /api/api-keys/rotate
{
  "provider": "openai",
  "new_key": "sk-new_key_here"
}
```

#### Deleting API Keys
```javascript
// Delete specific API key
DELETE /api/api-keys/openai
```

### General Secret Management

#### Storing Secrets
```javascript
POST /api/secrets/store
{
  "secret_type": "database",
  "secret_name": "prod_connection",
  "secret_value": "postgresql://user:pass@host:5432/db",
  "metadata": {
    "environment": "production",
    "team": "backend"
  }
}
```

#### Retrieving Secrets List
```javascript
GET /api/secrets/list
// Optional: GET /api/secrets/list?type=database
```

#### Deleting Secrets
```javascript
DELETE /api/secrets/database/prod_connection
```

#### Rotating Secrets
```javascript
POST /api/secrets/rotate
{
  "secret_type": "database",
  "secret_name": "prod_connection",
  "new_value": "postgresql://user:newpass@host:5432/db"
}
```

### Security Audit

#### Access Logs
```javascript
GET /api/secrets/access-log?limit=100

// Response includes:
{
  "access_log": [
    {
      "secret_type": "api_key",
      "secret_name": "openai",
      "action": "retrieve",
      "timestamp": "2025-07-15T22:21:30Z",
      "success": true,
      "ip_address": "127.0.0.1"
    }
  ]
}
```

## Database Schema

### user_secrets
```sql
CREATE TABLE user_secrets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    secret_type VARCHAR(50) NOT NULL,
    secret_name VARCHAR(100) NOT NULL,
    encrypted_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    UNIQUE(user_id, secret_type, secret_name)
);
```

### secret_access_log
```sql
CREATE TABLE secret_access_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    secret_type VARCHAR(50) NOT NULL,
    secret_name VARCHAR(100) NOT NULL,
    action VARCHAR(20) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE
);
```

## Integration with NeuroLM

### Model Access Control
The secrets vault integrates seamlessly with the tiered model access system:

1. **Free Tier**: No API keys required - access to 56+ free models
2. **OpenAI Tier**: OpenAI API key in vault - access to free + OpenAI models
3. **OpenRouter Tier**: OpenRouter API key in vault - access to free + OpenRouter models
4. **Premium Tier**: Both API keys - access to all models

### Backward Compatibility
The system maintains backward compatibility with existing BYOK endpoints:
- `POST /api/update-api-keys` - Legacy endpoint still works
- Existing API key retrieval functions updated to use vault
- Seamless migration from old to new system

## Security Considerations

### Encryption
- **Per-user encryption**: Each user's secrets encrypted with unique keys
- **Master key**: Configurable via `VAULT_MASTER_KEY` environment variable
- **Key derivation**: PBKDF2-HMAC-SHA256 with 100,000 iterations

### Access Control
- **Session-based**: Only authenticated users can access their secrets
- **User isolation**: Complete separation between users' secrets
- **Audit logging**: All operations logged with timestamps and IP addresses

### Best Practices
1. **Regular rotation**: Rotate API keys periodically
2. **Monitor access logs**: Check audit logs for suspicious activity
3. **Environment variables**: Use secure environment variables for master key
4. **HTTPS only**: Always use HTTPS in production

## Troubleshooting

### Common Issues

#### "Failed to store secret"
- Check user authentication
- Verify all required fields are provided
- Check server logs for detailed error messages

#### "Secret not found"
- Verify exact secret type and name
- Check if secret has expired
- Ensure user has permission to access

#### "Access denied"
- Verify user is logged in
- Check session validity
- Ensure proper authentication headers

### Debug Commands
```bash
# Check database tables
psql $DATABASE_URL -c "SELECT * FROM user_secrets LIMIT 5;"

# View access logs
psql $DATABASE_URL -c "SELECT * FROM secret_access_log ORDER BY timestamp DESC LIMIT 10;"

# Test API endpoints
curl -X GET "http://localhost:5000/api/secrets/list" -H "Cookie: session=YOUR_SESSION"
```

## API Reference

### Authentication
All endpoints require user authentication via session cookies.

### Endpoints

#### Secrets Management
- `POST /api/secrets/store` - Store a new secret
- `GET /api/secrets/list` - List user's secrets
- `DELETE /api/secrets/{type}/{name}` - Delete a secret
- `POST /api/secrets/rotate` - Rotate a secret
- `GET /api/secrets/access-log` - Get access log

#### API Key Management
- `POST /api/api-keys/store` - Store API key
- `GET /api/api-keys/list` - List API keys
- `DELETE /api/api-keys/{provider}` - Delete API key
- `POST /api/api-keys/rotate` - Rotate API key

#### Legacy Compatibility
- `POST /api/update-api-keys` - Legacy BYOK endpoint

## Future Enhancements

### Planned Features
1. **Organization Sharing**: Share secrets within team organizations
2. **Secret Templates**: Predefined templates for common secret types
3. **Import/Export**: Bulk operations for secret management
4. **Integration APIs**: Third-party integrations for secret syncing
5. **Advanced Permissions**: Role-based access control

### Performance Optimization
1. **Connection pooling**: Improve database performance
2. **Caching layer**: Redis integration for frequently accessed secrets
3. **Batch operations**: Bulk secret operations
4. **Compression**: Compress large secret values

## Conclusion

The NeuroLM Secrets Vault provides enterprise-grade security for sensitive data while maintaining an intuitive user experience. With comprehensive API coverage, beautiful web interface, and robust security features, it's the complete solution for credential management in the NeuroLM ecosystem.

For additional support or questions, refer to the main NeuroLM documentation or contact the development team.