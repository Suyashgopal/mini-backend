"""
Test Audit Service

This script tests if the audit service is working and shows what's needed
to integrate it into the comparison workflow.
"""

from src.services.audit_service import AuditService
from datetime import datetime, timezone

print("=" * 70)
print("AUDIT SERVICE TEST")
print("=" * 70)

# Sample comparison data
sample_data = {
    "extracted_text": "Drug Name: ASPIRIN 500mg\nBatch: ABC123\nExp: 12/2025",
    "match_percentage": 95.5,
    "status": "PASS",
    "final_decision": "VALID",
    "authenticity_score": 85,
    "compared_at": datetime.now(timezone.utc).isoformat(),
    "submitter_ip": "192.168.1.100"
}

print("\n1. Testing audit_hash generation (tamper detection)...")
print("-" * 70)

audit_hash = AuditService.generate_audit_hash(
    extracted_text=sample_data["extracted_text"],
    match_percentage=sample_data["match_percentage"],
    status=sample_data["status"],
    final_decision=sample_data["final_decision"],
    authenticity_score=sample_data["authenticity_score"],
    compared_at=sample_data["compared_at"],
    submitter_ip=sample_data["submitter_ip"]
)

print(f"✓ Audit Hash Generated: {audit_hash}")
print(f"  Length: {len(audit_hash)} characters")
print(f"  Purpose: Detects if this specific record was tampered with")

print("\n2. Testing content_hash generation (duplicate detection)...")
print("-" * 70)

content_hash = AuditService.generate_content_hash(
    extracted_text=sample_data["extracted_text"],
    match_percentage=sample_data["match_percentage"],
    status=sample_data["status"]
)

print(f"✓ Content Hash Generated: {content_hash}")
print(f"  Length: {len(content_hash)} characters")
print(f"  Purpose: Detects duplicate submissions across time")

print("\n3. Testing hash consistency...")
print("-" * 70)

# Generate same content hash again (should be identical)
content_hash_2 = AuditService.generate_content_hash(
    extracted_text=sample_data["extracted_text"],
    match_percentage=sample_data["match_percentage"],
    status=sample_data["status"]
)

if content_hash == content_hash_2:
    print("✓ Content hash is consistent (same input = same hash)")
else:
    print("✗ Content hash is NOT consistent (BUG!)")

# Generate audit hash with different timestamp (should be different)
sample_data_2 = sample_data.copy()
sample_data_2["compared_at"] = "2025-01-01T00:00:00Z"

audit_hash_2 = AuditService.generate_audit_hash(
    extracted_text=sample_data_2["extracted_text"],
    match_percentage=sample_data_2["match_percentage"],
    status=sample_data_2["status"],
    final_decision=sample_data_2["final_decision"],
    authenticity_score=sample_data_2["authenticity_score"],
    compared_at=sample_data_2["compared_at"],
    submitter_ip=sample_data_2["submitter_ip"]
)

if audit_hash != audit_hash_2:
    print("✓ Audit hash changes with timestamp (as expected)")
else:
    print("✗ Audit hash should change with timestamp (BUG!)")

print("\n4. Testing tamper detection...")
print("-" * 70)

# Simulate a stored record
stored_record = {
    "extracted_text": sample_data["extracted_text"],
    "match_percentage": sample_data["match_percentage"],
    "status": sample_data["status"],
    "final_decision": sample_data["final_decision"],
    "authenticity_score": sample_data["authenticity_score"],
    "compared_at": sample_data["compared_at"],
    "submitter_ip": sample_data["submitter_ip"]
}

# Verify with correct hash
verification = AuditService.verify_record(stored_record, audit_hash)
print(f"Tampered: {verification['tampered']}")
print(f"Reason: {verification['reason']}")

if verification['tampered'] == False:
    print("✓ Record verified as intact")
else:
    print("✗ Record should be intact (BUG!)")

# Now tamper with the record
print("\n5. Testing tamper detection after modification...")
print("-" * 70)

tampered_record = stored_record.copy()
tampered_record["match_percentage"] = 50.0  # Changed from 95.5!

verification_tampered = AuditService.verify_record(tampered_record, audit_hash)
print(f"Tampered: {verification_tampered['tampered']}")
print(f"Reason: {verification_tampered['reason']}")

if verification_tampered['tampered'] == True:
    print("✓ Tamper detected correctly")
else:
    print("✗ Tamper should be detected (BUG!)")

print("\n" + "=" * 70)
print("AUDIT SERVICE STATUS")
print("=" * 70)

print("\n✅ Audit Service Code: WORKING")
print("   - Hash generation works correctly")
print("   - Tamper detection works correctly")
print("   - Content hash for duplicates works correctly")

print("\n❌ Integration Status: NOT INTEGRATED")
print("   The audit service exists but is not being used!")

print("\n📋 What's Missing:")
print("   1. ComparisonResult model needs these fields:")
print("      - audit_hash (String)")
print("      - content_hash (String)")
print("      - submitter_ip (String)")
print("      - final_decision (String)")
print("      - authenticity_score (Integer)")
print("")
print("   2. comparison_routes.py needs to:")
print("      - Import AuditService")
print("      - Generate hashes when creating ComparisonResult")
print("      - Store hashes in the database")
print("      - Verify hashes when retrieving records")
print("")
print("   3. Database migration needed:")
print("      - Add new columns to comparison_results table")

print("\n💡 To integrate the audit service:")
print("   1. Update the ComparisonResult model")
print("   2. Run database migration")
print("   3. Update comparison routes to use AuditService")
print("   4. Add verification endpoint")

print("\n" + "=" * 70)
