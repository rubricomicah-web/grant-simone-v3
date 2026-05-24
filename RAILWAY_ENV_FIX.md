# Railway Environment Variable Fix

Railway crashed because boolean environment variables were saved with literal quotes, for example:

PAYMENTS_ENABLED="false"
EMAIL_NOTIFICATIONS_ENABLED="false"

Railway passed those values to Python as `"false"`, and Pydantic could not parse them as booleans.

This build includes a safe parser that accepts both quoted and unquoted boolean values.

Still recommended in Railway Variables:

PAYMENTS_ENABLED=false
EMAIL_NOTIFICATIONS_ENABLED=false

Do not include quotes around booleans.
