#!/usr/bin/env python3
"""
Simple script to check for actual documentation issues in AGENTS.md vs code.
"""

import re

def check_agents_vs_adr():
    """Check AGENTS.md against accepted ADRs"""
    print("Checking AGENTS.md against accepted ADRs...")
    
    agents_content = open("AGENTS.md").read()
    
    issues = []
    
    # ADR 0001 - Split AGENT_PROVIDER into two independent variables
    with open("docs/adr/0001-two-agent-provider-variables.md") as f:
        adr0001 = f.read()
    
    if "AGENT_PROVIDER_AUTOMERGE" not in agents_content:
        issues.append("ADR 0001: AGENTS.md doesn't mention AGENT_PROVIDER_AUTOMERGE (ADR says it should be used by doc-gardener.yml and garbage-collector.yml)")
    
    # ADR 0002 - Plan.md before implementation gate
    with open("docs/adr/0002-plan-md-precommit-gate.md") as f:
        adr0002 = f.read()
    
    if "pre-commit" not in agents_content.lower():
        issues.append("ADR 0002: AGENTS.md doesn't mention pre-commit (ADR says it's in .githooks/pre-commit)")
    
    # ADR 0003 - Client-side git hooks
    with open("docs/adr/0003-client-side-hooks-branch-protection-stopgap.md") as f:
        adr0003 = f.read()
    
    if "client-side hooks" not in agents_content.lower():
        issues.append("ADR 0003: AGENTS.md doesn't mention client-side hooks (ADR says they're the stopgap)")
    
    if issues:
        print(f"\n❌ Found {len(issues)} ADR issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("\n✅ No ADR mismatches found")
        return True

def check_arch_docs_consistency():
    """Check consistency between architecture documentation"""
    print("\nChecking architecture docs consistency...")
    
    # Read all architecture files
    arch_content = open("docs/architecture/ARCHITECTURE.md").read()
    api_conventions = open("docs/architecture/api-conventions.md").read()
    agent_providers = open("docs/architecture/agent-providers.md").read()
    agents_content = open("AGENTS.md").read()
    
    issues = []
    
    # Check that AGENTS.md references ARCHITECTURE.md
    if "docs/architecture/ARCHITECTURE.md" not in agents_content:
        issues.append("AGENTS.md should reference docs/architecture/ARCHITECTURE.md (in AGENTS.md)")
    
    # Check that ARCHITECTURE.md references api-conventions.md
    if "api-conventions.md" not in arch_content:
        issues.append("ARCHITECTURE.md should reference api-conventions.md")
    
    # Check that AGENTS.md mentions ui-smoke for dashboard
    if "ui-smoke" not in agents_content:
        issues.append("AGENTS.md should mention ui-smoke (it has a UI dashboard section)")
    
    if issues:
        print(f"\n❌ Found {len(issues)} architecture doc issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("\n✅ No architecture doc consistency issues found")
        return True

def check_habit_completion_docs():
    """Check habit completion documentation consistency"""
    print("\nChecking habit completion documentation...")
    
    # Check AGENTS.md
    agents_content = open("AGENTS.md").read()
    
    # Check domains/habits README
    habits_readme = open("docs/domains/habits/README.md").read()
    
    issues = []
    
    # Check AGENTS.md mentions habit completion in docs
    if "habit completion (check-in)" not in agents_content.lower():
        issues.append("AGENTS.md should mention habit completion (check-in) section")
    
    # Check that both documents have completion info
    if "completion" not in habits_readme.lower():
        issues.append("docs/domains/habits/README.md should mention habit completion")
    
    # Check AGENTS.md endpoint path
    if "/{habit_id}/completions" not in agents_content:
        issues.append("AGENTS.md should mention /habits/{habit_id}/completions endpoint")
    
    if issues:
        print(f"\n❌ Found {len(issues)} habit completion doc issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("\n✅ No habit completion doc issues found")
        return True

def check_observability_docs():
    """Check observability documentation"""
    print("\nChecking observability documentation...")
    
    agents_content = open("AGENTS.md").read()
    
    issues = []
    
    # Check if metrics section is accurate
    if "/metrics" not in agents_content:
        issues.append("AGENTS.md should document /metrics endpoint")
    
    # Check if health check section exists
    if "health" not in agents_content.lower():
        issues.append("AGENTS.md should mention health check")
    
    # Check if make metrics-query is documented
    if "make metrics-query" not in agents_content:
        issues.append("AGENTS.md should document make metrics-query command")
    
    if issues:
        print(f"\n❌ Found {len(issues)} observability doc issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("\n✅ No observability doc issues found")
        return True

if __name__ == "__main__":
    print("=== DOCUMENTATION FRESHNESS GARDENER ===")
    
    all_good = True
    all_good &= check_agents_vs_adr()
    all_good &= check_arch_docs_consistency()
    all_good &= check_habit_completion_docs()
    all_good &= check_observability_docs()
    
    if all_good:
        print("\n✅ All documentation checks passed!")
    else:
        print("\n⚠️ Found issues that need to be fixed")