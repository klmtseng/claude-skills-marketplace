#!/usr/bin/env python3
"""Redirector — this file has been superseded by mechanical_audit_template.py.

The previous version contained domain-specific checks that are not part of this
general-purpose skill package. Import from mechanical_audit_template instead:

    import mechanical_audit_template as T

See references/mechanical-audit.md for the updated domain pack.
"""
# Re-export the new template so any existing imports keep working
from mechanical_audit_template import (  # noqa: F401
    check_coverage_scope,
    check_traintest_split_order,
    check_metric_selection_bias,
    check_mean_of_means,
    check_threshold_on_test,
    check_ci,
    check_lockfile_present,
)
