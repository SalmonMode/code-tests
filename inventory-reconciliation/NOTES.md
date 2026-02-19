# Inventory Reconciliation Notes

## Ownership Convention
- `## User Notes` is user-authored.
- `## Codex Notes (AI-authored only)` is assistant-authored only.
- Assistant entries are appended using `### [Codex] <title>`.

## User Notes
Starting off, I'm looking through the data sets by eye to find any trouble while having the AI agent do the same. I will have the AI agent place its findings in marked sections as I go.

First issues I noticed:
- SKU formatting in second file is not consistent
- Date formatting in second file is not consistent
- White space in second file is not clean
- Columns are different in each file

Suspected issue:
- SKUs won't line up. Might need to have multiple approaches. One with SKU as the key, another where product name is key

## Codex Notes (AI-authored only)

### [Codex] Data sample scan: potential issues
- Schema drift between snapshots:
  - `snapshot_1.csv` headers: `sku,name,quantity,location,last_counted`
  - `snapshot_2.csv` headers: `sku,product_name,qty,warehouse,updated_at`
- `snapshot_2.csv` has SKU format inconsistencies that break direct joins:
  - `SKU005` (`inventory-reconciliation/data/snapshot_2.csv:6`)
  - `sku-008` (`inventory-reconciliation/data/snapshot_2.csv:9`)
  - `SKU018` (`inventory-reconciliation/data/snapshot_2.csv:19`)
- `snapshot_2.csv` has a duplicate key after normalization: `SKU-045` appears twice with conflicting attributes (`inventory-reconciliation/data/snapshot_2.csv:44`, `inventory-reconciliation/data/snapshot_2.csv:54`).
- `snapshot_2.csv` includes an invalid negative quantity: `-5` for `SKU-045` (`inventory-reconciliation/data/snapshot_2.csv:54`).
- `snapshot_2.csv` mixes numeric styles in `qty` (integers plus `70.0` and `80.00`), which may require type normalization (`inventory-reconciliation/data/snapshot_2.csv:3`, `inventory-reconciliation/data/snapshot_2.csv:8`).
- `snapshot_2.csv` has inconsistent date format (`01/15/2024`) while others use `YYYY-MM-DD` (`inventory-reconciliation/data/snapshot_2.csv:34`).
- Whitespace quality issues exist in both snapshots (leading/trailing spaces in product names), not just snapshot 2:
  - `inventory-reconciliation/data/snapshot_1.csv:36`
  - `inventory-reconciliation/data/snapshot_1.csv:53`
  - `inventory-reconciliation/data/snapshot_2.csv:3`
  - `inventory-reconciliation/data/snapshot_2.csv:11`
  - `inventory-reconciliation/data/snapshot_2.csv:22`
- `snapshot_1.csv` contains a blank trailing row (`inventory-reconciliation/data/snapshot_1.csv:77`).
- After normalizing SKU formats, likely true inventory set changes are:
  - Only in snapshot 1: `SKU-025`, `SKU-026`
  - Only in snapshot 2: `SKU-076`, `SKU-077`, `SKU-078`, `SKU-079`, `SKU-080`

### [Codex] Parser library scaffold completed
- Added `inventory_parser` package to normalize both snapshot schemas into one canonical row model:
  - `inventory-reconciliation/inventory_parser/models.py`
  - `inventory-reconciliation/inventory_parser/normalize.py`
  - `inventory-reconciliation/inventory_parser/parser.py`
  - `inventory-reconciliation/inventory_parser/__init__.py`
- Implemented `parse_snapshot(...)` and `parse_both_snapshots(...)` for unified parsing output.
- Added row-level issue flags for:
  - SKU normalization/format problems
  - quantity problems (invalid, non-integral, negative, decimal formatting)
  - whitespace trimming on text fields
  - non-ISO or invalid date values
- Added tests validating schema detection and normalization behavior:
  - `inventory-reconciliation/tests/test_inventory_parser.py`
- Test run status: `python3 -m unittest discover -s tests -v` passes (`4` tests).

## User Notes

Will now start by building library of tools to parse the two data sets into a unified structure. Having the agent set up the libraries and parsing systems using simple dataclasses, set up the python environment, and implement tests for the library code I'm having it write.

I instructed it to define tests for the library utilities themselves irrespective of the actual data files so I can be sure they're working as I expect. It takes some modifications to get it verifying the right things, though, rather than just trying to get code coverage.

## User Notes

I'm having the AI agent add tests to check my earlier mentioned concern that there may be a discrepency between using the name as the key and the SKU as the key. The agent will add its findings here.

### [Codex] Latest pytest findings
- Test run: `20` passed, `0` failed.
- Parser checks passed for both schemas and expected row counts (`75`, `79`, `154` combined).
- Normalization checks passed for malformed SKUs, decimal quantity formatting, negative quantities, and non-ISO dates.
- Reconciliation finding: SKU-keyed and name-keyed outputs differ (for example, `multimeter professional` appears as added only under name-key matching).
