"""Verify database tables after migration."""
import sqlite3

conn = sqlite3.connect('boxcostpro.db')
cursor = conn.cursor()

# Get all tables
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = [row[0] for row in cursor.fetchall()]

print(f'\nTotal tables: {len(tables)}\n')

# New tables from this migration
new_tables = [
    'support_tickets', 'support_messages', 'support_agents', 'sla_rules',
    'admin_audit_logs', 'auth_audit_logs', 'admin_login_audit_logs', 'email_logs',
    'coupons', 'coupon_usages',
    'two_factor_auth', 'two_factor_backup_codes',
    'features', 'user_entitlements', 'tenant_entitlements', 'plan_templates', 'entitlement_logs',
    'subscription_plans', 'user_subscriptions', 'subscription_overrides',
    'payment_methods', 'transactions', 'usage_records'
]

print('New tables created:')
created = [t for t in tables if t in new_tables]
for table in created:
    print(f'  ✓ {table}')

print(f'\nCreated: {len(created)}/{len(new_tables)} tables')

conn.close()
