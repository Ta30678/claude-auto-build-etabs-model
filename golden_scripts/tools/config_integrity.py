"""Config integrity verification — prevents element array tampering."""
import hashlib
import json

ELEMENT_KEYS = ("columns", "beams", "walls", "small_beams", "slabs")


def compute_integrity(config):
    """Return _integrity dict with counts + SHA-256 hash."""
    counts = {k: len(config.get(k, [])) for k in ELEMENT_KEYS}
    data = {k: config.get(k, []) for k in ELEMENT_KEYS}
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    h = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {"element_counts": counts, "element_hash": h}


def verify_integrity(config):
    """Verify config integrity. Returns (ok, message)."""
    stored = config.get("_integrity")
    if stored is None:
        return False, "Missing _integrity field — config may have been manually edited"

    current = compute_integrity(config)
    # Check counts
    diffs = []
    for k in ELEMENT_KEYS:
        expected = stored["element_counts"].get(k, 0)
        actual = current["element_counts"][k]
        if expected != actual:
            delta = actual - expected
            verb = "DELETED" if delta < 0 else "ADDED"
            diffs.append(f"  {k}: expected {expected}, got {actual} "
                         f"({abs(delta)} {verb})")
    if diffs:
        return False, "Element count mismatch:\n" + "\n".join(diffs)

    # Check hash
    if stored["element_hash"] != current["element_hash"]:
        return False, ("Element hash mismatch — content modified "
                       "(counts unchanged)")

    return True, "OK"


def stamp_config(config):
    """Add _integrity to config in-place and return it."""
    config["_integrity"] = compute_integrity(config)
    return config
